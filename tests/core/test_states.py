from attribute_helper.core.model import AttribInfo, AttribKey, Graph, Snapshot, State
from attribute_helper.core.states import compute_states, lifetime, summary, wires

B, W, P, R, D = State.BORN, State.WRITTEN, State.PASS, State.REBUILT, State.DELETED
PT_P, PT_M, PR_M, DT_D = (AttribKey("point", "P"), AttribKey("point", "mask"),
                          AttribKey("prim", "mask"), AttribKey("detail", "d"))


def snap(node, topo=1, **attribs):
    """snap("n", topo=1, point_P=5) -> point P with data ID 5. None = unknown ID."""
    parsed = {}
    for spec, data_id in attribs.items():
        cls, name = spec.split("_", 1)
        parsed[AttribKey(cls, name)] = AttribInfo(
            "float", 1, None if data_id is None else (0, 0, 0, data_id))
    return Snapshot(node, parsed, (0, 0, 0, topo))


def run(inputs, *snaps):
    graph = Graph([s.node_id for s in snaps], inputs)
    snapshots = {s.node_id: s for s in snaps}
    return graph, snapshots, compute_states(graph, snapshots)


def test_linear_chain_born_pass_written():
    # box -> wrangle (adds mask) -> xform (moves P)
    _, _, st = run({"wr": ["box"], "xf": ["wr"]},
                   snap("box", point_P=1),
                   snap("wr", point_P=1, point_mask=2),
                   snap("xf", point_P=3, point_mask=2))
    assert st["box"] == {PT_P: B}
    assert st["wr"] == {PT_P: P, PT_M: B}
    assert st["xf"] == {PT_P: W, PT_M: P}


def test_generator_gives_born_for_all():
    _, _, st = run({}, snap("grid", point_P=1, prim_mask=2, detail_d=3))
    assert set(st["grid"].values()) == {B}


def test_deleted_attribute():
    _, _, st = run({"del": ["box"]}, snap("box", point_P=1, point_mask=2), snap("del", point_P=1))
    assert st["del"] == {PT_P: P, PT_M: D}


def test_same_name_in_two_classes_are_separate_keys():
    _, _, st = run({"n": ["box"]},
                   snap("box", point_mask=1, prim_mask=2),
                   snap("n", point_mask=1, prim_mask=9))
    assert st["n"] == {PT_M: P, PR_M: W}


def test_branch_and_merge():
    # box -> a (adds mask) and box -> b (moves P); merge(a, b) keeps topology of neither
    _, _, st = run({"a": ["box"], "b": ["box"], "m": ["a", "b"]},
                   snap("box", topo=1, point_P=1),
                   snap("a", topo=1, point_P=1, point_mask=2),
                   snap("b", topo=1, point_P=3),
                   snap("m", topo=7, point_P=8, point_mask=9))
    assert st["m"] == {PT_P: R, PT_M: R}


def test_pass_through_from_either_merge_input():
    _, _, st = run({"m": ["a", "b"]},
                   snap("a", point_P=1), snap("b", point_P=2), snap("m", point_P=2))
    assert st["m"] == {PT_P: P}


def test_topology_change_gives_rebuilt_not_written():
    _, _, st = run({"blast": ["box"]},
                   snap("box", topo=1, point_P=1, point_mask=2),
                   snap("blast", topo=5, point_P=3, point_mask=4))
    assert st["blast"] == {PT_P: R, PT_M: R}


def test_same_id_across_topology_change_is_still_pass():
    # Copy to Points kept the detail data ID although topology changed (S2).
    _, _, st = run({"ctp": ["box"]}, snap("box", topo=1, detail_d=1), snap("ctp", topo=2, detail_d=1))
    assert st["ctp"] == {DT_D: P}


def test_unknown_data_id_is_written_hint():
    _, _, st = run({"n": ["box"]}, snap("box", point_P=None), snap("n", point_P=None))
    assert st["n"] == {PT_P: W}


def test_unknown_topology_falls_back_to_written():
    box = snap("box", point_P=1)
    n = Snapshot("n", snap("x", point_P=2).attribs, None)
    _, _, st = run({"n": ["box"]}, box, n)
    assert st["n"] == {PT_P: W}


def test_missing_snapshot_leaves_node_and_direct_outputs_unknown():
    graph = Graph(["box", "slow", "tail"], {"slow": ["box"], "tail": ["slow"]})
    snapshots = {"box": snap("box", point_P=1), "tail": snap("tail", point_P=1)}
    assert set(compute_states(graph, snapshots)) == {"box"}


def test_lifetime_stops_at_delete():
    _, _, st = run({"wr": ["box"], "del": ["wr"], "tail": ["del"]},
                   snap("box", point_P=1),
                   snap("wr", point_P=1, point_mask=2),
                   snap("del", point_P=1),
                   snap("tail", point_P=1))
    assert lifetime(st, PT_M) == {"wr"}
    assert lifetime(st, PT_P) == {"box", "wr", "del", "tail"}


def test_summary_rows():
    graph, snaps, st = run({"wr": ["box"], "xf": ["wr"], "bl": ["xf"], "del": ["bl"]},
                           snap("box", topo=1, point_P=1),
                           snap("wr", topo=1, point_P=1, point_mask=2),
                           snap("xf", topo=1, point_P=3, point_mask=2),
                           snap("bl", topo=2, point_P=4, point_mask=5),
                           snap("del", topo=2, point_P=4))
    rows = {r.key: r for r in summary(graph, st, snaps)}
    assert list(rows) == [PT_P, PT_M]
    assert (rows[PT_P].born, rows[PT_P].deleted, rows[PT_P].writes, rows[PT_P].rebuilt) == (["box"], [], 1, 1)
    assert (rows[PT_M].born, rows[PT_M].deleted, rows[PT_M].writes, rows[PT_M].rebuilt) == (["wr"], ["del"], 0, 1)
    assert rows[PT_M].type == "float"


def test_wires_carry_key_into_delete_but_not_past_it_or_into_unknown():
    graph, _, st = run({"wr": ["box"], "m": ["wr", "box"], "del": ["m"], "tail": ["del"]},
                       snap("box", point_P=1),
                       snap("wr", point_P=1, point_mask=2),
                       snap("m", point_P=1, point_mask=2),
                       snap("del", point_P=1),
                       snap("tail", point_P=1))
    assert wires(graph, st, PT_M) == [("wr", "m"), ("m", "del")]  # not box -> m: no mask on box
    del st["tail"]  # unknown node: no wire into it
    assert ("del", "tail") not in wires(graph, st, PT_P)


def test_summary_skips_containers_so_inner_births_count_once():
    # sub contains inner; both are BORN for mask (sub = overall effect). Born lists inner only.
    snaps = [snap("box", point_P=1), snap("inner", point_P=1, point_mask=2),
             snap("sub", point_P=1, point_mask=2)]
    graph = Graph([s.node_id for s in snaps], {"inner": ["box"], "sub": ["box"]}, frozenset({"sub"}))
    st = compute_states(graph, {s.node_id: s for s in snaps})
    assert st["sub"][PT_M] == B
    rows = {r.key: r for r in summary(graph, st, {s.node_id: s for s in snaps})}
    assert rows[PT_M].born == ["inner"]
