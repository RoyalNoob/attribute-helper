from attribute_helper.core.model import AttribKey
from attribute_helper.core.policy import SELF, Finding, dump, findings, parse, toggle
from attribute_helper.core.report import LeakReport

TMP = Finding("leaked", AttribKey("point", "tmp"))
TOP = Finding("deleted", AttribKey("group:prim", "top"))


def test_findings_lists_every_report_entry_with_its_kind():
    report = LeakReport([AttribKey("point", "tmp")], [AttribKey("point", "a")], [], [AttribKey("prim", "r")])
    assert findings(report) == [TMP, Finding("written", AttribKey("point", "a")),
                                Finding("rebuilt", AttribKey("prim", "r"))]


def test_dump_and_parse_round_trip_with_scopes_and_groups():
    by_scope = {SELF: {TMP}, "netbox1": {TMP, TOP}}
    text = dump(by_scope)
    assert text.splitlines()[0] == ". leaked point tmp"
    assert parse(text) == by_scope


def test_parse_ignores_malformed_lines():
    assert parse("garbage\n. leaked point tmp\n. nonsense point x\n\n. leaked point") == {SELF: {TMP}}


def test_toggle_adds_removes_and_drops_empty_scopes():
    text = toggle("", SELF, TMP, True)
    text = toggle(text, "netbox1", TOP, True)
    assert parse(text) == {SELF: {TMP}, "netbox1": {TOP}}
    text = toggle(text, "netbox1", TOP, False)
    assert text == ". leaked point tmp"
    assert toggle(text, SELF, TMP, True) == text  # idempotent
    assert toggle(text, SELF, TMP, False) == ""
