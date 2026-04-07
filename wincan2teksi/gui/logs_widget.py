import logging
import os
from datetime import datetime

from qgis.PyQt.QtCore import (
    QAbstractItemModel,
    QCoreApplication,
    QModelIndex,
    QSortFilterProxyModel,
    Qt,
)
from qgis.PyQt.QtGui import QAction, QKeySequence, QShortcut
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QMenu,
    QStyle,
    QWidget,
)
from qgis.PyQt.uic import loadUiType

from wincan2teksi.core.utils import PLUGIN_LOGGER_NAME, LoggingBridge

Ui_LogsWidget, _ = loadUiType(os.path.join(os.path.dirname(__file__), "..", "ui", "logs_widget.ui"))

COLUMNS = ["Timestamp", "Level", "Module", "Message"]


class LogModel(QAbstractItemModel):
    def __init__(self, parent=None):
        QAbstractItemModel.__init__(self, parent)
        self.logs = []

    def add_log(self, log):
        self.beginInsertRows(QModelIndex(), len(self.logs), len(self.logs))
        self.logs.append(log)
        self.endInsertRows()

    def headerData(self, section, orientation, role=None):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return COLUMNS[section]
        return None

    def rowCount(self, parent=None):
        return len(self.logs)

    def columnCount(self, parent=None):
        return len(COLUMNS)

    def data(self, index, role=None):
        if not index.isValid():
            return None
        if (
            index.row() < 0
            or index.row() >= len(self.logs)
            or index.column() < 0
            or index.column() >= len(COLUMNS)
        ):
            return None

        log = self.logs[index.row()]
        col_name = COLUMNS[index.column()]
        value = log[col_name]

        if role == Qt.ItemDataRole.DisplayRole:
            return value
        elif role == Qt.ItemDataRole.ToolTipRole:
            if col_name == "Message":
                return value
        return None

    def index(self, row, column, parent=None):
        if row < 0 or row >= len(self.logs) or column < 0 or column >= len(COLUMNS):
            return QModelIndex()
        return self.createIndex(row, column)

    def parent(self, index):
        return QModelIndex()

    def flags(self, index):
        return (
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemNeverHasChildren
        )

    def clear(self):
        self.beginResetModel()
        self.logs = []
        self.endResetModel()


class LogFilterProxyModel(QSortFilterProxyModel):
    LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.level_filter = None
        self.text_filter = ""

    def setLevelFilter(self, level):
        self.level_filter = level
        self.invalidateFilter()

    def setTextFilter(self, text):
        self.text_filter = text
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        model = self.sourceModel()
        index_level = model.index(source_row, 1, source_parent)
        index_message = model.index(source_row, 3, source_parent)
        index_module = model.index(source_row, 2, source_parent)

        if self.level_filter and self.level_filter != "ALL":
            level = model.data(index_level, Qt.ItemDataRole.DisplayRole)
            try:
                filter_idx = self.LEVELS.index(self.level_filter)
                level_idx = self.LEVELS.index(level)
                if level_idx < filter_idx:
                    return False
            except ValueError:
                return False

        if self.text_filter:
            msg = model.data(index_message, Qt.ItemDataRole.DisplayRole) or ""
            mod = model.data(index_module, Qt.ItemDataRole.DisplayRole) or ""
            text = self.text_filter.lower()
            if text not in msg.lower() and text not in mod.lower():
                return False

        return True


class LogsWidget(QWidget, Ui_LogsWidget):
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self.setupUi(self)

        self.loggingBridge = LoggingBridge(
            level=logging.NOTSET, excluded_modules=["urllib3.connectionpool"]
        )
        self.logs_model = LogModel(self)

        self.proxy_model = LogFilterProxyModel(self)
        self.proxy_model.setSourceModel(self.logs_model)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.proxy_model.setFilterKeyColumn(-1)

        self.logs_treeView.setModel(self.proxy_model)
        self.logs_treeView.setAlternatingRowColors(True)
        self.logs_treeView.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.logs_treeView.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.logs_treeView.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.logs_treeView.setWordWrap(True)
        self.logs_treeView.setTextElideMode(Qt.TextElideMode.ElideNone)

        header = self.logs_treeView.header()
        header.setStretchLastSection(True)
        header.resizeSection(0, 150)
        header.resizeSection(1, 80)
        header.resizeSection(2, 150)
        self.logs_treeView.setUniformRowHeights(False)

        self.loggingBridge.loggedLine.connect(self.__logged_line)
        plugin_logger = logging.getLogger(PLUGIN_LOGGER_NAME)
        plugin_logger.setLevel(logging.DEBUG)
        plugin_logger.addHandler(self.loggingBridge)

        self.logs_level_comboBox.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.logs_level_comboBox.currentTextChanged.connect(self.proxy_model.setLevelFilter)
        self.logs_level_comboBox.setCurrentText("INFO")

        self.logs_clear_toolButton.setIcon(
            QApplication.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarCloseButton)
        )
        self.logs_clear_toolButton.clicked.connect(self.__logsClearClicked)

        self.logs_copy_all_toolButton.setIcon(
            QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton)
        )
        self.logs_copy_all_toolButton.clicked.connect(self.__copyAllLogs)

        self.logs_filter_LineEdit.textChanged.connect(self.proxy_model.setTextFilter)

        self.copy_shortcut = QShortcut(QKeySequence.StandardKey.Copy, self.logs_treeView)
        self.copy_shortcut.activated.connect(self.__copySelectedRows)

        self.logs_treeView.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.logs_treeView.customContextMenuRequested.connect(self.__showContextMenu)

    def close(self):
        logging.getLogger(PLUGIN_LOGGER_NAME).removeHandler(self.loggingBridge)

    def __logged_line(self, record, line):
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")

        log_entry = {
            "Timestamp": timestamp,
            "Level": record.levelname,
            "Module": record.name,
            "Message": record.getMessage(),
        }

        self.logs_model.add_log(log_entry)

        scroll_bar = self.logs_treeView.verticalScrollBar()
        scroll_bar.setValue(scroll_bar.maximum())

        QCoreApplication.processEvents()

    def __logsClearClicked(self):
        self.logs_model.clear()

    def __showContextMenu(self, position):
        selection_model = self.logs_treeView.selectionModel()
        has_selection = selection_model.hasSelection()
        selected_rows = selection_model.selectedRows() if has_selection else []

        menu = QMenu(self.logs_treeView)

        copy_action = QAction(self.tr("Copy"), menu)
        copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        copy_action.triggered.connect(self.__copySelectedRows)
        copy_action.setEnabled(has_selection)
        menu.addAction(copy_action)

        copy_message_action = QAction(self.tr("Copy message"), menu)
        copy_message_action.triggered.connect(self.__copySelectedMessage)
        copy_message_action.setEnabled(len(selected_rows) == 1)
        menu.addAction(copy_message_action)

        menu.exec(self.logs_treeView.viewport().mapToGlobal(position))

    def __copySelectedRows(self):
        selection_model = self.logs_treeView.selectionModel()
        selected_indexes = selection_model.selectedRows()

        if not selected_indexes:
            return

        selected_indexes.sort(key=lambda idx: idx.row())

        csv_lines = ["Timestamp,Level,Module,Message"]

        for proxy_index in selected_indexes:
            source_index = self.proxy_model.mapToSource(proxy_index)
            row = source_index.row()
            log_entry = self.logs_model.logs[row]

            def escape_csv(value):
                value = str(value)
                if "," in value or '"' in value or "\n" in value:
                    return '"' + value.replace('"', '""') + '"'
                return value

            csv_line = ",".join(
                [
                    escape_csv(log_entry["Timestamp"]),
                    escape_csv(log_entry["Level"]),
                    escape_csv(log_entry["Module"]),
                    escape_csv(log_entry["Message"]),
                ]
            )
            csv_lines.append(csv_line)

        clipboard = QApplication.clipboard()
        clipboard.setText("\n".join(csv_lines))

    def __copyAllLogs(self):
        if not self.logs_model.logs:
            return

        csv_lines = ["Timestamp,Level,Module,Message"]

        for log_entry in self.logs_model.logs:

            def escape_csv(value):
                value = str(value)
                if "," in value or '"' in value or "\n" in value:
                    return '"' + value.replace('"', '""') + '"'
                return value

            csv_line = ",".join(
                [
                    escape_csv(log_entry["Timestamp"]),
                    escape_csv(log_entry["Level"]),
                    escape_csv(log_entry["Module"]),
                    escape_csv(log_entry["Message"]),
                ]
            )
            csv_lines.append(csv_line)

        clipboard = QApplication.clipboard()
        clipboard.setText("\n".join(csv_lines))

    def __copySelectedMessage(self):
        selection_model = self.logs_treeView.selectionModel()
        selected_indexes = selection_model.selectedRows()

        if len(selected_indexes) != 1:
            return

        source_index = self.proxy_model.mapToSource(selected_indexes[0])
        row = source_index.row()
        log_entry = self.logs_model.logs[row]

        clipboard = QApplication.clipboard()
        clipboard.setText(str(log_entry["Message"]))
