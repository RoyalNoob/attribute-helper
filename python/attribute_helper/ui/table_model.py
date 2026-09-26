"""Attribute table: one row per AttribSummary, a checkable first column for the overlay."""
from __future__ import annotations

from fnmatch import fnmatchcase

from PySide6 import QtCore, QtGui

from ..core.model import AttribKey
from ..core.states import AttribSummary

Qt = QtCore.Qt
COLUMNS = ["Show", "Name", "Class", "Type", "Born", "Deleted", "Written", "Rebuilt"]
PALETTE = [(1.0, 0.55, 0.0), (0.2, 0.75, 1.0), (1.0, 0.3, 0.6), (0.5, 0.9, 0.2),
           (0.75, 0.5, 1.0), (1.0, 0.9, 0.2), (0.2, 0.9, 0.75), (1.0, 0.45, 0.4)]
# Hidden by the "hide standard" filter.
STANDARD = frozenset({"P", "Pw", "N", "Cd", "Alpha", "uv", "v", "w", "id", "pscale", "width",
                      "orient", "up", "rest", "scale", "trans", "pivot", "transform", "name",
                      "piece", "class", "instance", "material_override"})


class AttribTableModel(QtCore.QAbstractTableModel):
    toggled = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows: list[AttribSummary] = []
        self.names: dict[str, str] = {}  # node id -> short name for display
        self.colors: dict[AttribKey, tuple[float, float, float]] = {}  # toggled keys

    def set_rows(self, rows: list[AttribSummary], names: dict[str, str]) -> None:
        self.beginResetModel()
        self.rows, self.names = rows, names
        self.endResetModel()

    def rowCount(self, parent=QtCore.QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 0 if parent.isValid() else len(COLUMNS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return COLUMNS[section]
        return None

    def flags(self, index):
        base = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        return base | Qt.ItemIsUserCheckable if index.column() == 0 else base

    def data(self, index, role=Qt.DisplayRole):
        row = self.rows[index.row()]
        col = index.column()
        if col == 0:
            if role == Qt.CheckStateRole:
                return Qt.Checked if row.key in self.colors else Qt.Unchecked
            if role == Qt.DecorationRole and row.key in self.colors:
                return QtGui.QColor.fromRgbF(*self.colors[row.key])
            return None
        if role == Qt.ToolTipRole and col == 6:
            return "A hint: some nodes change data IDs without changing values."
        if role == Qt.ToolTipRole and col == 7:
            return "Topology changed, so whether the value was written is unknown."
        if role != Qt.DisplayRole:
            return None
        return (None, row.key.name, row.key.cls, row.type,
                ", ".join(self.names.get(n, n) for n in row.born),
                ", ".join(self.names.get(n, n) for n in row.deleted),
                row.writes, row.rebuilt)[col]

    def setData(self, index, value, role=Qt.EditRole):
        if index.column() != 0 or role != Qt.CheckStateRole:
            return False
        key = self.rows[index.row()].key
        if key in self.colors:
            del self.colors[key]
        else:
            used = set(self.colors.values())
            free = [c for c in PALETTE if c not in used]
            # ponytail: colors repeat after 8 toggled keys; fine until someone needs more at once.
            self.colors[key] = free[0] if free else PALETTE[len(self.colors) % len(PALETTE)]
        self.dataChanged.emit(index, index)
        self.toggled.emit()
        return True


class AttribFilter(QtCore.QSortFilterProxyModel):
    """Name glob, class, and "hide standard attributes"."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pattern, self.cls, self.hide_standard = "*", "", True

    def set_filter(self, pattern: str, cls: str, hide_standard: bool) -> None:
        self.pattern = pattern.strip() or "*"
        if not any(c in self.pattern for c in "*?["):
            self.pattern = f"*{self.pattern}*"  # plain text means "contains"
        self.cls, self.hide_standard = cls, hide_standard
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        key = self.sourceModel().rows[source_row].key
        return (fnmatchcase(key.name, self.pattern)
                and (not self.cls or key.cls == self.cls)
                and not (self.hide_standard and key.name in STANDARD))
