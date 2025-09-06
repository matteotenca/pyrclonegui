from typing import Any

from PyQt6 import QtCore
from PyQt6.QtCore import QAbstractTableModel, QModelIndex, QVariant


class TableModel(QAbstractTableModel):
    def __init__(self, data_set: list[list], parent=None):
        super(TableModel, self).__init__(parent)
        self._data_set = data_set

    def headerData(self, section: int, orientation: QtCore.Qt.Orientation, role: int = QtCore.Qt.ItemDataRole.DisplayRole) -> Any:
        """Returns the appropriate header string depending on the orientation of
       the header and the section. If anything other than the display role is
       requested, we return an invalid variant."""
        if role != QtCore.Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == QtCore.Qt.Orientation.Horizontal:
            return f"Column {section}"
        return f"Row {section}"

    def data(self, index: QModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole) -> Any:
        row = index.row()
        col = index.column()
        if not index.isValid() or row >= len(self._data_set) or col >= len(self._data_set[row]):
            return QVariant()
        if role != QtCore.Qt.ItemDataRole.DisplayRole and role != QtCore.Qt.ItemDataRole.EditRole:
            return QVariant()
        res = self._data_set[row][col]
        return res

    def setData(self, index: QModelIndex, value: Any, role: int = QtCore.Qt.ItemDataRole.EditRole) -> bool:
        row = index.row()
        col = index.column()
        if not index.isValid() or row >= len(self._data_set) or col >= len(self._data_set[row]):
            return False
        if role != QtCore.Qt.ItemDataRole.EditRole:
            return False
        self._data_set[row][col] = value
        self.dataChanged.emit(index, index, {role})
        return True

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._data_set)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._data_set[0])

    def flags(self, index: QModelIndex) -> QtCore.Qt.ItemFlag:
        row = index.row()
        col = index.column()
        if not index.isValid() or row >= len(self._data_set) or col >= len(self._data_set[row]):
            return QtCore.Qt.ItemFlag.ItemIsEnabled
        return super().flags(index) | QtCore.Qt.ItemFlag.ItemIsEditable
        # return index.flags()

    def insertRows(self, row: int, count: int, parent: QModelIndex = QModelIndex()) -> bool:
        self.beginInsertRows(parent, row, row + count - 1)
        for i in range(count):
            self._data_set.insert(row,["",""])
        self.endInsertRows()
        return True

    def removeRows(self, position: int, rows: int, parent: QModelIndex = QModelIndex()) -> bool:
        """Removes a number of rows from the model at the specified position."""
        self.beginRemoveRows(QModelIndex(), position, position + rows - 1)
        for row in range(rows):
            del self._data_set[position]
        self.endRemoveRows()
        return True

    def insertColumns(self, column: int, count: int, parent = ...):
        pass
    def removeColumns(self, column: int, count: int, parent: QModelIndex = QModelIndex()) ->bool:
        pass
