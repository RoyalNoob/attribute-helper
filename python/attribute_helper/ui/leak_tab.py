"""Leak report tab: what a subnet or HDA leaks, overwrites, or deletes (plan phase 4)."""
from __future__ import annotations

import hou
from PySide6 import QtWidgets

from ..adapter.snapshot import SnapshotCache, collect_leaks
from ..core.report import LeakReport

SECTIONS = [
    ("leaked", "Leaked locals (created inside, alive at the output)"),
    ("written", "Outer writes (outer attributes changed inside; a hint)"),
    ("deleted", "Deleted outer attributes"),
    ("rebuilt", "Unknown (topology changed inside, so writes cannot be detected)"),
]


class LeakTab(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scope: hou.SopNode | None = None
        self.last: tuple | None = None

        pick = QtWidgets.QPushButton("Use selected subnet / HDA")
        self.label = QtWidgets.QLabel("Select a subnet or HDA, then click the button.")
        self.status = QtWidgets.QLabel()
        self.status.setWordWrap(True)
        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderLabels(["Attribute", "Class"])

        row = QtWidgets.QHBoxLayout()
        row.addWidget(pick)
        row.addWidget(self.label, 1)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(row)
        layout.addWidget(self.tree)
        layout.addWidget(self.status)
        pick.clicked.connect(self._on_pick)

    def _on_pick(self) -> None:
        sel = [n for n in hou.selectedNodes() if isinstance(n, hou.SopNode)]
        if sel:
            self.scope, self.last = sel[0], None
            self.label.setText(self.scope.path())

    def poll(self, cache: SnapshotCache, cook: bool, force: bool = False) -> None:
        if self.scope is None:
            return
        try:
            report, problems = collect_leaks(self.scope, cache, cook)
        except hou.ObjectWasDeleted:
            self.scope, self.last = None, None
            self.label.setText("The node was deleted. Select a subnet or HDA.")
            self.tree.clear()
            return
        if not force and (report, problems) == self.last:
            return
        self.last = (report, problems)
        self._fill(report)
        text = "; ".join(f"{p.rsplit('/', 1)[-1]}: {r}" for p, r in problems.items())
        self.status.setText(f"Not available: {text}" if text else "")

    def _fill(self, report: LeakReport | None) -> None:
        self.tree.clear()
        if report is None:
            return
        for field, title in SECTIONS:
            keys = getattr(report, field)
            section = QtWidgets.QTreeWidgetItem([f"{title}: {len(keys)}"])
            section.addChildren([QtWidgets.QTreeWidgetItem([k.name, k.cls]) for k in keys])
            self.tree.addTopLevelItem(section)
        self.tree.expandAll()
        self.tree.resizeColumnToContents(0)
