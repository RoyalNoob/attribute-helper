"""Table model and filter (headless Qt). Run: hython tools/run_hython_tests.py"""
from PySide6 import QtCore

from attribute_helper.core.model import AttribKey
from attribute_helper.core.states import AttribSummary
from attribute_helper.ui.table_model import PALETTE, AttribFilter, AttribTableModel

Qt = QtCore.Qt


def rows():
    def row(cls, name, born):
        return AttribSummary(AttribKey(cls, name), "float", [born], [], 0, 0)
    return [row("point", "P", "/obj/g/box"), row("point", "mask", "/obj/g/wr"),
            row("prim", "mask", "/obj/g/wr"), row("detail", "count", "/obj/g/wr")]


def model_and_filter():
    model = AttribTableModel()
    model.set_rows(rows(), {"/obj/g/box": "box", "/obj/g/wr": "wr"})
    proxy = AttribFilter()
    proxy.setSourceModel(model)
    return model, proxy


def visible(proxy):
    return sorted((proxy.index(r, 2).data(), proxy.index(r, 1).data()) for r in range(proxy.rowCount()))


def test_filter_hides_standard_and_matches_name_and_class():
    model, proxy = model_and_filter()
    proxy.set_filter("", "", True)
    assert visible(proxy) == [("detail", "count"), ("point", "mask"), ("prim", "mask")]
    proxy.set_filter("mas", "", True)  # plain text means "contains"
    assert visible(proxy) == [("point", "mask"), ("prim", "mask")]
    proxy.set_filter("m*k", "prim", False)
    assert visible(proxy) == [("prim", "mask")]
    proxy.set_filter("", "", False)
    assert ("point", "P") in visible(proxy)


def test_born_column_shows_short_names():
    model, _ = model_and_filter()
    assert model.index(1, 4).data() == "wr"


def test_toggle_assigns_distinct_colors_and_untoggles():
    model, _ = model_and_filter()
    fired = []
    model.toggled.connect(lambda: fired.append(1))
    first, second = model.index(1, 0), model.index(2, 0)
    model.setData(first, Qt.Checked, Qt.CheckStateRole)
    model.setData(second, Qt.Checked, Qt.CheckStateRole)
    assert model.colors == {AttribKey("point", "mask"): PALETTE[0], AttribKey("prim", "mask"): PALETTE[1]}
    assert model.data(first, Qt.CheckStateRole) == Qt.Checked
    model.setData(first, Qt.Unchecked, Qt.CheckStateRole)
    assert list(model.colors) == [AttribKey("prim", "mask")]
    assert len(fired) == 3
    assert not model.setData(model.index(1, 1), "x", Qt.EditRole)  # only the first column toggles


def test_gui_modules_import_without_gui():
    import attribute_helper.overlay  # noqa: F401  (nodegraph is imported lazily)
    import attribute_helper.ui.panel  # noqa: F401


def test_leak_tab_ticks_and_stale_section():
    from PySide6 import QtWidgets
    from attribute_helper.adapter.scope import ExitResult
    from attribute_helper.core.policy import Finding
    from attribute_helper.core.report import LeakReport
    from attribute_helper.ui.leak_tab import RED, LeakTab

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])  # noqa: F841
    tab = LeakTab()
    saved = []
    tab.scope = object()
    import attribute_helper.ui.leak_tab as leak_tab
    original, leak_tab.set_intended = leak_tab.set_intended, lambda scope, f, on: saved.append((f, on))
    try:
        _check_leak_tab(tab, saved, RED, Finding, LeakReport, ExitResult)
    finally:
        leak_tab.set_intended = original


def _check_leak_tab(tab, saved, RED, Finding, LeakReport, ExitResult):

    tmp, fx = AttribKey("point", "tmp"), AttribKey("point", "fx")
    gone = Finding("deleted", AttribKey("point", "old"))
    tab._fill({Finding("leaked", fx), gone}, [ExitResult("/obj/g/sub", LeakReport([tmp, fx], [], [], []))])
    assert saved == []  # filling must not save
    top = [tab.tree.topLevelItem(i) for i in range(tab.tree.topLevelItemCount())]
    assert [t.text(0).rsplit(": ", 1)[1] for t in top] == ["2", "0", "0", "0", "1"]
    rows = {top[0].child(i).text(0): top[0].child(i) for i in range(2)}
    assert rows["tmp"].checkState(0) == Qt.Unchecked and rows["tmp"].foreground(0) == RED
    assert rows["fx"].checkState(0) == Qt.Checked
    assert top[4].child(0).text(0) == "old (deleted)"
    rows["tmp"].setCheckState(0, Qt.Checked)
    assert saved == [(Finding("leaked", tmp), True)]
