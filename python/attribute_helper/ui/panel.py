"""The Python Panel: header, filters, attribute table, overlay, and the poll loop (spike S6)."""
from __future__ import annotations

from dataclasses import dataclass

import hou
from PySide6 import QtCore, QtWidgets

from .. import overlay
from ..adapter.snapshot import NEEDS_COOK, SnapshotCache, collect
from ..core.model import Graph
from ..core.states import States, compute_states, summary
from .table_model import AttribFilter, AttribTableModel

POLL_MS = 250  # S6: an unchanged poll costs about 2 ms per 1000 nodes
CLASSES = ["", "point", "prim", "vertex", "detail"]


@dataclass
class View:
    level: hou.Node
    graph: Graph
    states: States
    problems: dict[str, str]


def _editor() -> hou.NetworkEditor | None:
    return hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)


class Panel(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.cache = SnapshotCache()
        self.pinned: hou.Node | None = None  # None = follow the display node
        self.view: View | None = None

        self.follow = QtWidgets.QCheckBox("Follow display node", checked=True)
        self.use_selected = QtWidgets.QPushButton("Use selected")
        self.cook = QtWidgets.QCheckBox("Cook on demand")
        self.cook.setToolTip("Off: nodes that need a cook are shown as not available.")
        refresh = QtWidgets.QPushButton("Refresh")
        self.target = QtWidgets.QLabel()
        self.search = QtWidgets.QLineEdit(placeholderText="Name filter (glob), e.g. *mask*")
        self.cls = QtWidgets.QComboBox()
        self.cls.addItems(["all classes"] + CLASSES[1:])
        self.hide_std = QtWidgets.QCheckBox("Hide standard", checked=True)
        self.status = QtWidgets.QLabel()
        self.status.setWordWrap(True)

        self.model = AttribTableModel(self)
        self.proxy = AttribFilter(self)
        self.proxy.setSourceModel(self.model)
        self.table = QtWidgets.QTableView()
        self.table.setModel(self.proxy)
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(1, QtCore.Qt.AscendingOrder)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setStretchLastSection(True)

        header = QtWidgets.QHBoxLayout()
        for w in (self.follow, self.use_selected, self.cook, refresh):
            header.addWidget(w)
        header.addStretch()
        filters = QtWidgets.QHBoxLayout()
        for w in (self.search, self.cls, self.hide_std):
            filters.addWidget(w)
        layout = QtWidgets.QVBoxLayout(self)
        for part in (header, filters):
            layout.addLayout(part)
        for w in (self.target, self.table, self.status):
            layout.addWidget(w)

        self.follow.toggled.connect(self._on_follow)
        self.use_selected.clicked.connect(self._on_use_selected)
        self.cook.toggled.connect(lambda _: self.poll(force=True))
        refresh.clicked.connect(self._on_refresh)
        self.search.textChanged.connect(self._on_filter)
        self.cls.currentIndexChanged.connect(self._on_filter)
        self.hide_std.toggled.connect(self._on_filter)
        self.model.toggled.connect(overlay.push)
        self.table.clicked.connect(self._on_row_clicked)

        overlay.install(self._shapes)
        self.timer = QtCore.QTimer(self, interval=POLL_MS, timeout=self.poll)
        self.timer.start()
        self.poll(force=True)

    # --- poll -------------------------------------------------------------------------

    def _target(self) -> hou.Node | None:
        if self.pinned is not None:
            try:
                self.pinned.path()
                return self.pinned
            except hou.ObjectWasDeleted:
                self.pinned = None
                self.follow.setChecked(True)
        editor = _editor()
        pwd = editor.pwd() if editor else None
        display = getattr(pwd, "displayNode", None)
        return display() if display else None

    def poll(self, force: bool = False) -> None:
        if not self.isVisible() and not force:
            return
        target = self._target()
        if not isinstance(target, hou.SopNode):
            self._show(None, "No SOP target. Enter a SOP network, or select a SOP and click Use selected.")
            return
        graph, snaps, problems = collect(target, self.cache, self.cook.isChecked())
        states = compute_states(graph, snaps)
        view = View(target.parent(), graph, states, problems)
        if not force and self.view and (self.view.level, self.view.graph, self.view.states,
                                        self.view.problems) == (view.level, graph, states, problems):
            return
        self.target.setText(f"Target: {target.path()}  ({len(graph.nodes)} nodes)")
        self._show(view, _problem_text(problems))
        self.model.set_rows(summary(graph, states, snaps),
                            {n: n.rsplit("/", 1)[-1] for n in graph.nodes})

    def _show(self, view: View | None, status: str) -> None:
        if view is None and self.view is None and self.status.text() == status:
            return
        self.view = view
        self.status.setText(status)
        if view is None:
            self.target.setText("")
            self.model.set_rows([], {})
        overlay.push()

    def _shapes(self, editor: hou.NetworkEditor) -> list:
        if self.view is None or not self.model.colors or editor.pwd() != self.view.level:
            return []
        return overlay.shapes(editor, self.view.graph, self.view.states, self.model.colors)

    # --- controls ---------------------------------------------------------------------

    def _on_follow(self, on: bool) -> None:
        if on:
            self.pinned = None
        self.poll(force=True)

    def _on_use_selected(self) -> None:
        sel = [n for n in hou.selectedNodes() if isinstance(n, hou.SopNode)]
        if sel:
            self.pinned = sel[0]
            self.follow.setChecked(False)
            self.poll(force=True)

    def _on_refresh(self) -> None:
        self.cache = SnapshotCache()
        self.poll(force=True)

    def _on_filter(self, *_) -> None:
        self.proxy.set_filter(self.search.text(), CLASSES[self.cls.currentIndex()],
                              self.hide_std.isChecked())

    def _on_row_clicked(self, index: QtCore.QModelIndex) -> None:
        if index.column() == 0:
            return  # the checkbox column toggles; do not also change the selection
        row = self.model.rows[self.proxy.mapToSource(index).row()]
        node = hou.node(row.born[0]) if row.born else None
        if node is None:
            return
        with hou.undos.disabler():  # the tool must leave no undo entries
            node.setSelected(True, clear_all_selected=True)

    def shutdown(self) -> None:
        self.timer.stop()
        overlay.uninstall()


def _problem_text(problems: dict[str, str]) -> str:
    if not problems:
        return ""
    waiting = sum(1 for r in problems.values() if r == NEEDS_COOK)
    errors = len(problems) - waiting
    parts = []
    if waiting:
        parts.append(f"{waiting} node(s) need a cook (turn on Cook on demand, or display them)")
    if errors:
        parts.append(f"{errors} node(s) have errors")
    return "Not available: " + "; ".join(parts) + "."
