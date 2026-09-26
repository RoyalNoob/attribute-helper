"""Leak report tab: what a scope leaks, overwrites, or deletes. Tick a finding to mark it
intended; unticked findings are shown in red. A scope is a subnet, an HDA, or a network box."""
from __future__ import annotations

import hou
from PySide6 import QtCore, QtGui, QtWidgets

from ..adapter.scope import ExitResult, collect_scope, set_intended
from ..adapter.snapshot import SnapshotCache
from ..core.policy import Finding, findings

Qt = QtCore.Qt
TITLES = {
    "leaked": "Leaked locals (created inside, alive at the output)",
    "written": "Outer writes (outer attributes changed inside; a hint)",
    "deleted": "Deleted outer attributes",
    "rebuilt": "Unknown (topology changed inside, so writes cannot be detected)",
}
RED = QtGui.QBrush(QtGui.QColor(230, 80, 80))
HELP = ("Tick a finding to mark it intended. Unticked findings are shown in red.\n"
        "Ticks are saved in a hidden parameter on the subnet/HDA, or, for a network box, on the\n"
        "network that contains it (renaming the box loses its ticks).")


def _selected_scope():
    """A selected network box wins over a selected node."""
    items = hou.selectedItems()
    boxes = [i for i in items if isinstance(i, hou.NetworkBox)]
    nodes = [i for i in items if isinstance(i, hou.SopNode)]
    return (boxes or nodes or [None])[0]


class LeakTab(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scope = None  # hou.SopNode or hou.NetworkBox
        self.last: tuple | None = None

        pick = QtWidgets.QPushButton("Use selected subnet / HDA / box")
        self.label = QtWidgets.QLabel("Select a subnet, HDA, or network box, then click the button.")
        self.status = QtWidgets.QLabel()
        self.status.setWordWrap(True)
        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderLabels(["Attribute (tick = intended)", "Class"])
        self.tree.setToolTip(HELP)

        row = QtWidgets.QHBoxLayout()
        row.addWidget(pick)
        row.addWidget(self.label, 1)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(row)
        layout.addWidget(self.tree)
        layout.addWidget(self.status)
        pick.clicked.connect(self._on_pick)
        self.tree.itemChanged.connect(self._on_item_changed)

    def _on_pick(self) -> None:
        scope = _selected_scope()
        if scope is not None:
            self.scope, self.last = scope, None
            self.label.setText(scope.path())

    def _on_item_changed(self, item: QtWidgets.QTreeWidgetItem, column: int) -> None:
        finding = item.data(0, Qt.UserRole)
        if column != 0 or not isinstance(finding, Finding) or self.scope is None:
            return
        try:
            set_intended(self.scope, finding, item.checkState(0) == Qt.Checked)
        except hou.Error as e:  # for example, a box inside a locked HDA
            self.status.setText(f"Could not save: {e.instanceMessage()}")
            self.last = None  # redraw from the stored state

    def poll(self, cache: SnapshotCache, cook: bool, force: bool = False) -> None:
        if self.scope is None:
            return
        try:
            result = collect_scope(self.scope, cache, cook)
        except hou.ObjectWasDeleted:
            self.scope, self.last = None, None
            self.label.setText("The scope was deleted. Select a subnet, HDA, or network box.")
            self.tree.clear()
            return
        if not force and result == self.last:
            return
        self.last = result
        marked, exits, problems = result
        self._fill(marked, exits)
        reports = [e.report for e in exits if e.report is not None]
        open_count = len({f for r in reports for f in findings(r)} - marked)
        text = "; ".join(f"{p.rsplit('/', 1)[-1]}: {r}" for p, r in problems.items())
        self.status.setText("  ".join(filter(None, [
            f"{open_count} finding(s) not marked intended." if reports else "",
            f"Not available: {text}" if text else ""])))

    def _item(self, finding: Finding, ticked: bool, label: str = "") -> QtWidgets.QTreeWidgetItem:
        item = QtWidgets.QTreeWidgetItem([label or finding.key.name, finding.key.cls])
        item.setData(0, Qt.UserRole, finding)
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(0, Qt.Checked if ticked else Qt.Unchecked)
        if not ticked:
            for col in range(2):
                item.setForeground(col, RED)
        return item

    def _fill(self, marked: set[Finding], exits: list[ExitResult]) -> None:
        self.tree.blockSignals(True)  # building items must not save ticks
        self.tree.clear()
        found: set[Finding] = set()
        for exit in exits:
            parent = self.tree.invisibleRootItem()
            if len(exits) > 1:  # a box with several exits: one group per exit
                parent = QtWidgets.QTreeWidgetItem([f"Exit: {exit.exit.rsplit('/', 1)[-1]}"])
                self.tree.addTopLevelItem(parent)
            if exit.report is None:
                continue
            here = findings(exit.report)
            found.update(here)
            for kind, title in TITLES.items():
                rows = [f for f in here if f.kind == kind]
                section = QtWidgets.QTreeWidgetItem([f"{title}: {len(rows)}"])
                parent.addChild(section)
                section.addChildren([self._item(f, f in marked) for f in rows])
        stale = sorted(marked - found) if all(e.report for e in exits) else []
        if stale:
            section = QtWidgets.QTreeWidgetItem(
                [f"Marked intended, no longer found (untick to forget): {len(stale)}"])
            self.tree.addTopLevelItem(section)
            section.addChildren([self._item(f, True, f"{f.key.name} ({f.kind})") for f in stale])
        self.tree.expandAll()
        self.tree.resizeColumnToContents(0)
        self.tree.blockSignals(False)
