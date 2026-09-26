"""Adapter tests on real geometry. Run: hython tools/run_hython_tests.py"""
import hou

from attribute_helper.adapter.graph import walk
from attribute_helper.adapter.snapshot import NEEDS_COOK, SnapshotCache, collect
from attribute_helper.core.model import AttribKey, State
from attribute_helper.core.states import compute_states

B, W, P, R, D = State.BORN, State.WRITTEN, State.PASS, State.REBUILT, State.DELETED
PT_P, PT_M, PR_M = AttribKey("point", "P"), AttribKey("point", "mask"), AttribKey("prim", "mask")


def sop(parent, type_name, *inputs, **parms):
    node = parent.createNode(type_name)
    for i, src in enumerate(inputs):
        node.setInput(i, src)
    for name, value in parms.items():
        node.parm(name).set(value)
    return node


def geo():
    return hou.node("/obj").createNode("geo")


def states(target, cache=None, cook=True):
    graph, snaps, problems = collect(target, cache or SnapshotCache(), cook)
    return compute_states(graph, snaps), problems


def test_linear_chain():
    g = geo()
    box = sop(g, "box")
    wr = sop(g, "attribwrangle", box, snippet="f@mask = 1;")
    xf = sop(g, "xform", wr, tx=1)
    st, problems = states(xf)
    assert not problems
    assert st[box.path()][PT_P] == B
    assert st[wr.path()] == {PT_P: P, PT_M: B}
    assert st[xf.path()] == {PT_P: W, PT_M: P}


def test_deleted_attribute():
    g = geo()
    wr = sop(g, "attribwrangle", sop(g, "box"), snippet="f@mask = 1;")
    ad = sop(g, "attribdelete", wr, ptdel="mask")
    st, _ = states(ad)
    assert st[ad.path()][PT_M] == D
    assert st[ad.path()][PT_P] == P


def test_same_name_in_two_classes():
    g = geo()
    both = sop(g, "attribwrangle", sop(g, "box"),
               snippet='f@mask = 1; setprimattrib(0, "mask", 0, 1.0);')
    prim = sop(g, "attribwrangle", both, snippet="f@mask = 2;", **{"class": 1})  # 1 = primitives
    st, _ = states(prim)
    assert st[prim.path()][PT_M] == P
    assert st[prim.path()][PR_M] == W


def test_branch_and_merge_is_rebuilt():
    g = geo()
    box = sop(g, "box")
    merge = sop(g, "merge", sop(g, "attribwrangle", box, snippet="f@mask = 1;"), sop(g, "xform", box))
    st, _ = states(merge)
    assert st[merge.path()][PT_P] == R


def test_walk_order_and_boundary_through_subnet():
    g = geo()
    outer = sop(g, "xform", sop(g, "box"))
    sub = sop(g, "subnet", outer)
    dot = sub.createNetworkDot()
    dot.setInput(0, sub.indirectInputs()[0])
    inner = sop(sub, "xform", dot, tx=1)
    graph, nodes = walk(inner)
    # Dot resolved; the outer xform is the boundary, so the box behind it is not walked.
    assert graph.nodes == [outer.path(), inner.path()]
    assert graph.inputs_of(outer.path()) == []
    st, _ = states(inner)
    assert st[inner.path()][PT_P] == W  # compared with the outer box, not "born"


def test_cooked_only_never_cooks():
    g = geo()
    box = sop(g, "box")
    xf = sop(g, "xform", box)
    _, snaps, problems = collect(xf, SnapshotCache(), cook=False)
    assert snaps == {} and set(problems.values()) == {NEEDS_COOK}
    assert (box.cookCount(), xf.cookCount()) == (0, 0)
    xf.geometry()  # the viewport would do this
    _, snaps, problems = collect(xf, SnapshotCache(), cook=False)
    assert not problems and len(snaps) == 2


def test_cache_reuses_until_recook():
    g = geo()
    box = sop(g, "box")
    xf = sop(g, "xform", box)
    cache = SnapshotCache()
    _, first, _ = collect(xf, cache, cook=True)
    _, second, _ = collect(xf, cache, cook=True)
    assert all(first[k] is second[k] for k in first)
    xf.parm("tx").set(2)
    _, third, _ = collect(xf, cache, cook=True)
    assert third[box.path()] is first[box.path()]
    assert third[xf.path()] is not first[xf.path()]


def test_error_node_is_reported_and_walk_continues():
    g = geo()
    box = sop(g, "box")
    bad = sop(g, "attribwrangle", box, snippet="this is not vex")
    tail = sop(g, "null", bad)
    for cook in (False, True):
        cache = SnapshotCache()
        tail.geometry()  # try to cook, so cooked-only mode sees the error
        _, snaps, problems = collect(tail, cache, cook)
        assert box.path() in snaps
        assert "Error" in problems[bad.path()] or "error" in problems[bad.path()].lower()
        assert tail.path() in problems


def test_fixed_node_recooks_in_cook_mode():
    g = geo()
    wr = sop(g, "attribwrangle", sop(g, "box"), snippet="this is not vex")
    cache = SnapshotCache()
    _, _, problems = collect(wr, cache, cook=True)
    assert wr.path() in problems
    wr.parm("snippet").set("f@mask = 1;")
    _, snaps, problems = collect(wr, cache, cook=True)
    assert not problems and PT_M in snaps[wr.path()].attribs


def plan_subnet():
    """Outside: a and b. Inside: writes a, deletes b, creates tmp."""
    g = geo()
    outer = sop(g, "attribwrangle", sop(g, "box"), snippet="f@a = 1; f@b = 2;")
    sub = sop(g, "subnet", outer)
    write = sop(sub, "attribwrangle", sub.indirectInputs()[0], snippet="f@a = 5; f@tmp = 1;")
    delete = sop(sub, "attribdelete", write, ptdel="b")
    delete.setDisplayFlag(True)
    return g, outer, sub


def test_leak_report_plan_acceptance():
    from attribute_helper.adapter.scope import collect_scope

    _, _, sub = plan_subnet()
    decl, results, problems = collect_scope(sub, SnapshotCache(), cook=True)
    assert not problems and decl is None
    [result] = results
    assert result.report.leaked == [AttribKey("point", "tmp")]
    assert result.report.written == [AttribKey("point", "a")]
    assert result.report.deleted == [AttribKey("point", "b")]
    assert result.report.rebuilt == [] and result.violations is None


def test_subnet_declaration_from_spare_parms():
    from attribute_helper.adapter.scope import collect_scope

    _, _, sub = plan_subnet()
    for name in ("scope_inout", "scope_out"):
        sub.addSpareParmTuple(hou.StringParmTemplate(name, name, 1))
    sub.parm("scope_inout").set("a")
    sub.parm("scope_out").set("tmp -> fx_tmp, height")
    decl, [result], _ = collect_scope(sub, SnapshotCache(), cook=True)
    assert decl.in_ == ["*"]
    kinds = sorted((v.kind, v.name) for v in result.violations)
    assert kinds == [("missing output", "height"), ("undeclared delete", "b")]


def test_network_box_scope_two_exits_and_comment_declaration():
    from attribute_helper.adapter.scope import boundaries, collect_scope

    g = geo()
    src = sop(g, "attribwrangle", sop(g, "box"), snippet="f@a = 1;")
    other = sop(g, "attribwrangle", sop(g, "box"), snippet="f@c = 1;")
    tmp = sop(g, "attribwrangle", src, snippet="f@tmp = 1;")
    left = sop(g, "null", tmp)
    right = sop(g, "attribwrangle", tmp, other, snippet="f@a = 2;")
    box = g.createNetworkBox()
    for n in (tmp, left, right):
        box.addNode(n)
    sop(g, "null", left), sop(g, "null", right)  # both leave the box
    pairs = {e.name(): sorted(n.name() for n in ins) for e, ins in boundaries(box)}
    assert pairs == {left.name(): [src.name()], right.name(): sorted([src.name(), other.name()])}

    box.setComment("my scope\ninout: a\nout: tmp")
    decl, results, problems = collect_scope(box, SnapshotCache(), cook=True)
    assert not problems and decl.inout == ["a"]
    assert all(r.violations == [] for r in results)
    box.setComment("my scope\nout: tmp")
    _, results, _ = collect_scope(box, SnapshotCache(), cook=True)
    by_exit = {r.exit: [(v.kind, v.name) for v in r.violations] for r in results}
    assert by_exit == {left.path(): [], right.path(): [("undeclared write", "a")]}


def test_walk_enters_editable_subnet_but_not_locked_hda():
    from attribute_helper.core.states import summary

    g = geo()
    box = sop(g, "box")
    sub = sop(g, "subnet", box)
    inner = sop(sub, "attribwrangle", sub.indirectInputs()[0], snippet="f@tmp = 1;")
    inner.setDisplayFlag(True)
    tail = sop(g, "attribwrangle", sub, snippet="f@w = 1;")  # a locked HDA
    graph, _ = walk(tail)
    assert graph.nodes == [box.path(), inner.path(), sub.path(), tail.path()]
    assert graph.containers == {sub.path()}
    assert graph.inputs_of(inner.path()) == [box.path()]
    graph, snaps, problems = collect(tail, SnapshotCache(), cook=True)
    st = compute_states(graph, snaps)
    tmp = AttribKey("point", "tmp")
    assert st[inner.path()][tmp] == B and st[sub.path()][tmp] == B
    rows = {r.key: r for r in summary(graph, st, snaps)}
    assert rows[tmp].born == [inner.path()]


def test_groups_have_states():
    g = geo()
    grp = sop(g, "groupcreate", sop(g, "box"), groupname="top")
    delete = sop(g, "groupdelete", grp, group1="top")
    st, _ = states(delete)
    key = AttribKey("group:prim", "top")
    assert st[grp.path()][key] == B
    assert st[delete.path()][key] == D
