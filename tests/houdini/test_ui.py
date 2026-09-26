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
