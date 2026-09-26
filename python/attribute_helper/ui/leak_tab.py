"""Leak report tab: what a scope leaks, overwrites, or deletes, and whether it breaks its
declaration (docs/attrib_scope_policy.md §7). A scope is a subnet, an HDA, or a network box."""
from __future__ import annotations

import hou
from PySide6 import QtGui, QtWidgets

from ..adapter.scope import PARMS, ExitResult, collect_scope
from ..adapter.snapshot import SnapshotCache
from ..core.model import AttribKey
from ..core.policy import Declaration, Violation

SECTIONS = [
    ("leaked", "Leaked locals (created inside, alive at the output)"),
    ("written", "Outer writes (outer attributes changed inside; a hint)"),
    ("deleted", "Deleted outer attributes"),
    ("rebuilt", "Unknown (topology changed inside, so writes cannot be detected)"),
]
RED = QtGui.QBrush(QtGui.QColor(230, 80, 80))
NO_DECLARATION = (f"No declaration. Add string parameters {', '.join(PARMS)} to the subnet/HDA, "
                  "or `in:` / `inout:` / `out:` lines to the network box comment.")


def _selected_scope():
    """A selected network box wins over a selected node."""
    items = hou.selectedItems()
    boxes = [i for i in items if isinstance(i, hou.NetworkBox)]
    nodes = [i for i in items if isinstance(i, hou.SopNode)]
    return (boxes or nodes or [None])[0]


def _describe(decl: Declaration | None) -> str:
    if decl is None:
        return NO_DECLARATION
    out = " ".join(f"{e.name}->{e.rename}" if e.rename else e.name for e in decl.out)
    return (f"Declared — in: {' '.join(decl.in_) or '-'}  |  inout: {' '.join(decl.inout) or '-'}"
            f"  |  out: {out or '-'}")


def _red(item: QtWidgets.QTreeWidgetItem) -> QtWidgets.QTreeWidgetItem:
    for col in range(3):
        item.setForeground(col, RED)
    return item


class LeakTab(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scope = None  # hou.SopNode or hou.NetworkBox
        self.last: tuple | None = None

        pick = QtWidgets.QPushButton("Use selected subnet / HDA / box")
        self.label = QtWidgets.QLabel("Select a subnet, HDA, or network box, then click the button.")
        self.decl = QtWidgets.QLabel()
        self.decl.setWordWrap(True)
        self.status = QtWidgets.QLabel()
        self.status.setWordWrap(True)
        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderLabels(["Attribute", "Class", "Declaration"])

        row = QtWidgets.QHBoxLayout()
        row.addWidget(pick)
        row.addWidget(self.label, 1)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(row)
        for w in (self.decl, self.tree, self.status):
            layout.addWidget(w)
        pick.clicked.connect(self._on_pick)

    def _on_pick(self) -> None:
        scope = _selected_scope()
        if scope is not None:
            self.scope, self.last = scope, None
            self.label.setText(scope.path())

    def poll(self, cache: SnapshotCache, cook: bool, force: bool = False) -> None:
        if self.scope is None:
            return
        try:
            result = collect_scope(self.scope, cache, cook)
        except hou.ObjectWasDeleted:
            self.scope, self.last = None, None
            self.label.setText("The scope was deleted. Select a subnet, HDA, or network box.")
            self.decl.setText("")
            self.tree.clear()
            return
        if not force and result == self.last:
            return
        self.last = result
        decl, exits, problems = result
        self.decl.setText(_describe(decl))
        self._fill(exits)
        text = "; ".join(f"{p.rsplit('/', 1)[-1]}: {r}" for p, r in problems.items())
        count = sum(len(e.violations or []) for e in exits)
        self.status.setText("  ".join(filter(None, [
            f"{count} violation(s)." if decl is not None else "",
            f"Not available: {text}" if text else ""])))

    def _fill(self, exits: list[ExitResult]) -> None:
        self.tree.clear()
        for exit in exits:
            parent = self.tree.invisibleRootItem()
            if len(exits) > 1:  # a box with several exits: one group per exit
                parent = QtWidgets.QTreeWidgetItem([f"Exit: {exit.exit.rsplit('/', 1)[-1]}"])
                self.tree.addTopLevelItem(parent)
            if exit.report is not None:
                self._fill_exit(parent, exit)
        self.tree.expandAll()
        self.tree.resizeColumnToContents(0)

    def _fill_exit(self, parent: QtWidgets.QTreeWidgetItem, exit: ExitResult) -> None:
        flagged: dict[tuple[str, str], Violation] = {
            (v.name, v.cls): v for v in exit.violations or []}
        for field, title in SECTIONS:
            keys: list[AttribKey] = getattr(exit.report, field)
            section = QtWidgets.QTreeWidgetItem([f"{title}: {len(keys)}"])
            parent.addChild(section)
            for k in keys:
                v = flagged.get((k.name, k.cls))
                note = v.kind if v else ("ok" if exit.violations is not None else "")
                item = QtWidgets.QTreeWidgetItem([k.name, k.cls, note])
                section.addChild(_red(item) if v else item)
        # Declared outputs with problems have no attribute row of their own.
        extra = [v for v in exit.violations or [] if v.kind in ("missing output", "collision")]
        if extra:
            section = QtWidgets.QTreeWidgetItem([f"Declared outputs with problems: {len(extra)}"])
            parent.addChild(section)
            section.addChildren([_red(QtWidgets.QTreeWidgetItem([v.name, "", v.kind])) for v in extra])
