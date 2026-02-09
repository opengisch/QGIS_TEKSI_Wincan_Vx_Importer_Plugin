# -----------------------------------------------------------
#
# QGIS Quick Finder Plugin
# Copyright (C) 2013 Denis Rouzaud
#
# -----------------------------------------------------------
#
# licensed under the terms of GNU GPL 2
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# ---------------------------------------------------------------------

import os.path
from qgis.PyQt.QtCore import Qt, QObject, QSettings, QCoreApplication, QTranslator
from qgis.PyQt.QtGui import QIcon, QColor
from qgis.PyQt.QtWidgets import QAction, QFileDialog
from qgis.core import Qgis, QgsProject, QgsSettingsTree
from qgis.gui import QgsRubberBand, QgisInterface

from wincan2teksi.core.settings import Settings, PLUGIN_NAME
from wincan2teksi.core.read_data import read_data
from wincan2teksi.gui.databrowserdialog import DataBrowserDialog
from wincan2teksi.gui.settings_dialog import SettingsDialog
from pathlib import Path

DEBUG = True


class Wincan2Teksi(QObject):
    name = "&Wincan to TEKSI Importer"
    actions = None

    def __init__(self, iface: QgisInterface):
        QObject.__init__(self)
        self.iface = iface
        self.actions = {}
        self.settings = Settings()
        self.dlg = None

        # translation environment
        self.plugin_dir = Path(__file__).parent
        locale = QSettings().value("locale/userLocale")[0:2]
        locale_path = self.plugin_dir / "i18n" / f"QGIS_TEKSI_Wincan_Vx_Importer_Plugin_{locale}.qm"
        if locale_path.exists():
            self.translator = QTranslator()
            self.translator.load(str(locale_path))
            QCoreApplication.installTranslator(self.translator)

    def initGui(self):
        self.actions["openInspection"] = QAction(
            QIcon(str(self.plugin_dir / "icons" / "wincan_logo.png")),
            self.tr("Open an inspection report"),
            self.iface.mainWindow(),
        )
        self.actions["openInspection"].triggered.connect(self.open_inspection)
        self.iface.addPluginToMenu(self.name, self.actions["openInspection"])
        self.iface.addToolBarIcon(self.actions["openInspection"])

        self.actions["openSettings"] = QAction(self.tr("Settings"), self.iface.mainWindow())
        self.actions["openSettings"].triggered.connect(self.show_settings)
        self.iface.addPluginToMenu(self.name, self.actions["openSettings"])

        self.rubber = QgsRubberBand(self.iface.mapCanvas())
        self.rubber.setColor(QColor(255, 255, 50, 200))
        self.rubber.setIcon(self.rubber.ICON_CIRCLE)
        self.rubber.setIconSize(15)
        self.rubber.setWidth(4)
        self.rubber.setBrushStyle(Qt.BrushStyle.NoBrush)

    def unload(self):
        """Unload plugin"""
        for action in self.actions.values():
            self.iface.removePluginMenu(self.name, action)
            self.iface.removeToolBarIcon(action)
        if self.rubber:
            self.iface.mapCanvas().scene().removeItem(self.rubber)
            del self.rubber
        if self.dlg:
            self.dlg.close()

        QgsSettingsTree.unregisterPluginTreeNode(PLUGIN_NAME)

    # @pyqtSlot(str, QgsMessageBar.MessageLevel)
    # def display_message(self, message, level):
    #    self.iface.messageBar().pushMessage("Wincan 2 QGEP", message, level)

    def open_inspection(self):
        db3_path = self.settings.db3_path.value()
        if db3_path == "":
            db3_path = QgsProject.instance().homePath()
        file_path, _ = QFileDialog.getOpenFileName(
            None, "Open WIncan inspection data", db3_path, "Wincan file (*.db3)"
        )

        if file_path:
            absolute_path = os.path.dirname(os.path.realpath(file_path))
            parent_path = os.path.abspath(os.path.join(absolute_path, os.pardir))
            self.settings.db3_path.setValue(absolute_path)
            try:
                data = read_data(file_path)
            except Exception as e:
                self.iface.messageBar().pushMessage(
                    "Wincan 2 TEKSI",
                    f"Error reading Wincan file: {e}",
                    level=Qgis.MessageLevel.Critical,
                )
                return
            self.dlg = DataBrowserDialog(self.iface, data, parent_path)
            self.dlg.show()

    def show_settings(self):
        SettingsDialog().exec()
