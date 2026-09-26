from attribute_helper.core.model import AttribKey
from attribute_helper.core.policy import (
    Declaration, OutEntry, Violation, check, from_comment, from_lists, matches, parse_list)
from attribute_helper.core.report import leak_report

from test_states import snap

PT = lambda n: AttribKey("point", n)  # noqa: E731


def test_parse_list_spaces_commas_and_renames():
    assert parse_list("P, Cd  mask -> fx_mask\nw->v") == ["P", "Cd", "mask->fx_mask", "w->v"]


def test_from_lists_splits_renames():
    d = from_lists("*", "P Cd", "mask -> fx_mask height")
    assert d == Declaration(["*"], ["P", "Cd"], [OutEntry("mask", "fx_mask"), OutEntry("height")])


def test_from_comment_reads_marked_lines_and_ignores_the_rest():
    d = from_comment("Erosion setup\ninout: P\nOUT: mask -> fx_mask")
    assert d == Declaration(["*"], ["P"], [OutEntry("mask", "fx_mask")])
    assert from_comment("just a title") is None


def test_matches_patterns_exclusion_and_groups():
    assert matches(PT("mask"), ["m*"])
    assert not matches(PT("mask"), ["*", "^mask"])  # later entries win
    assert matches(PT("mask"), ["^mask", "*"])
    assert not matches(PT("top"), ["group:top"])  # group patterns only match groups
    assert matches(AttribKey("group:prim", "top"), ["group:t*"])
    assert not matches(AttribKey("group:prim", "top"), ["top"])


def scope(entry_attrs, exit_attrs, entry_topo=1, exit_topo=1):
    entry = snap("in", topo=entry_topo, **entry_attrs)
    exit = snap("sub", topo=exit_topo, **exit_attrs)
    return leak_report([entry], exit), [entry], exit


def test_each_finding_is_flagged_when_undeclared():
    # Outside: P, a, b. Inside: writes a, deletes b, creates tmp.
    report, entries, exit = scope(dict(point_P=1, point_a=2, point_b=3),
                                  dict(point_P=1, point_a=9, point_tmp=4))
    found = check(from_lists("*", "", ""), report, entries, exit)
    assert sorted(found, key=lambda v: v.kind) == [
        Violation("undeclared delete", "b", "point"),
        Violation("undeclared leak", "tmp", "point"),
        Violation("undeclared write", "a", "point")]


def test_declared_findings_are_clean():
    report, entries, exit = scope(dict(point_P=1, point_a=2, point_b=3),
                                  dict(point_P=1, point_a=9, point_tmp=4))
    assert check(from_lists("*", "a b", "tmp"), report, entries, exit) == []


def test_missing_output_and_collision():
    report, entries, exit = scope(dict(point_mask=1), dict(point_mask=5))
    # out: height is never produced; out: mask already exists outside and is not inout.
    found = check(from_lists("*", "", "height mask"), report, entries, exit)
    assert found == [Violation("missing output", "height"), Violation("collision", "mask")]


def test_rename_counts_as_declared_and_skips_collision():
    report, entries, exit = scope(dict(point_mask=1), dict(point_mask=5))
    assert check(from_lists("*", "", "mask -> fx_mask"), report, entries, exit) == []


def test_inout_name_in_out_is_not_a_collision():
    report, entries, exit = scope(dict(point_mask=1), dict(point_mask=5))
    assert check(from_lists("*", "mask", "mask"), report, entries, exit) == []


def test_out_patterns_declare_but_are_not_checked_for_missing():
    report, entries, exit = scope(dict(point_P=1), dict(point_P=1, point_fx_a=2))
    assert check(from_lists("*", "", "fx_* nothing_*"), report, entries, exit) == []


def test_unknown_after_topology_change_is_never_a_violation():
    report, entries, exit = scope(dict(point_a=2), dict(point_a=9), entry_topo=1, exit_topo=2)
    assert report.rebuilt == [PT("a")]
    assert check(from_lists("*", "", ""), report, entries, exit) == []


def test_groups_are_checked_with_group_prefix():
    report, entries, exit = scope(dict(point_P=1), dict(point_P=1, **{"group:prim_top": 2}))
    assert check(from_lists("*", "", ""), report, entries, exit) == [
        Violation("undeclared leak", "top", "group:prim")]
    assert check(from_lists("*", "", "group:top"), report, entries, exit) == []
