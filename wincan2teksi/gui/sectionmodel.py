from qgis.PyQt.QtCore import QAbstractTableModel, QModelIndex, Qt, QSortFilterProxyModel
from qgis.PyQt.QtGui import QColor


Column = {"Number": 0, "FromNode": 1, "ToNode": 2}

COLUMN_HEADERS = ["#", "From node", "To node"]


class SectionTableModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._sections = []  # list of (section_id, section) tuples
        self._project_id = None
        self._projects = {}

    def set_data(self, projects, project_id):
        self.beginResetModel()
        self._projects = projects
        self._project_id = project_id
        if project_id is not None and project_id in projects:
            self._sections = list(projects[project_id].sections.items())
        else:
            self._sections = []
        self.endResetModel()

    def clear(self):
        self.beginResetModel()
        self._sections = []
        self._project_id = None
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return len(self._sections)

    def columnCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return len(COLUMN_HEADERS)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return COLUMN_HEADERS[section]
        return None

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        s_id, section = self._sections[index.row()]

        if role == Qt.ItemDataRole.DisplayRole:
            col = index.column()
            if col == Column["Number"]:
                return str(section.counter)
            elif col == Column["FromNode"]:
                return section.from_node or ""
            elif col == Column["ToNode"]:
                return section.to_node or ""

        elif role == Qt.ItemDataRole.CheckStateRole and index.column() == Column["Number"]:
            return Qt.CheckState.Checked if section.import_ else Qt.CheckState.Unchecked

        elif role == Qt.ItemDataRole.BackgroundRole:
            ok = section.teksi_channel_id_1 is not None or section.use_previous_section is True
            if not ok:
                ok = True
                for inspection in section.inspections.values():
                    if inspection.import_:
                        ok = False
                        break
            if ok:
                return QColor(Qt.GlobalColor.white)
            else:
                return QColor(255, 190, 190)

        elif role == Qt.ItemDataRole.UserRole:
            return s_id

        return None

    def flags(self, index):
        flags = super().flags(index)
        if index.column() == Column["Number"]:
            flags |= Qt.ItemFlag.ItemIsUserCheckable
        return flags

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if role == Qt.ItemDataRole.CheckStateRole and index.column() == Column["Number"]:
            s_id, section = self._sections[index.row()]
            section.import_ = value == Qt.CheckState.Checked.value
            self.dataChanged.emit(index, index, [role])
            return True
        return False

    def section_id_for_row(self, row):
        if 0 <= row < len(self._sections):
            return self._sections[row][0]
        return None

    def row_for_section_id(self, section_id):
        for row, (s_id, _) in enumerate(self._sections):
            if s_id == section_id:
                return row
        return -1

    def is_first_section(self, section_id):
        if self._sections:
            return self._sections[0][0] == section_id
        return True

    def refresh(self):
        if self.rowCount() > 0:
            self.dataChanged.emit(
                self.index(0, 0),
                self.index(self.rowCount() - 1, self.columnCount() - 1),
            )

    def set_all_check_state(self, state):
        for row in range(self.rowCount()):
            idx = self.index(row, Column["Number"])
            self.setData(idx, state, Qt.ItemDataRole.CheckStateRole)


class SectionFilterProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._filter_unmatched = False

    def set_filter_unmatched(self, enabled):
        self._filter_unmatched = enabled
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        if not self._filter_unmatched:
            return True
        model = self.sourceModel()
        s_id, section = model._sections[source_row]
        is_matched = section.teksi_channel_id_1 is not None or section.use_previous_section is True
        return not is_matched
