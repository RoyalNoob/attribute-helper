from attribute_helper.core.model import AttribKey
from attribute_helper.core.report import leak_report

from test_states import snap


def test_plan_acceptance_case_one_of_each():
    # Outside: P, a, b. Inside: writes a, deletes b, creates tmp.
    entry = snap("in", topo=1, point_P=1, point_a=2, point_b=3)
    exit = snap("sub", topo=1, point_P=1, point_a=9, point_tmp=4)
    r = leak_report([entry], exit)
    assert r.leaked == [AttribKey("point", "tmp")]
    assert r.written == [AttribKey("point", "a")]
    assert r.deleted == [AttribKey("point", "b")]
    assert r.rebuilt == []


def test_topology_change_is_rebuilt_not_written():
    r = leak_report([snap("in", topo=1, point_a=2)], snap("sub", topo=2, point_a=9))
    assert (r.written, r.rebuilt) == ([], [AttribKey("point", "a")])


def test_generator_subnet_reports_every_output_as_born_inside():
    r = leak_report([], snap("sub", point_P=1, detail_n=2))
    assert r.leaked == [AttribKey("detail", "n"), AttribKey("point", "P")]
