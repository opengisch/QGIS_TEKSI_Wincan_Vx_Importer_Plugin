# -*- coding: utf-8 -*-
"""
/***************************************************************************

 QGIS TEKSI Wincan Importer Plugin
 Copyright (C) 2019 Denis Rouzaud

 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os
from qgis.PyQt.QtCore import QStandardPaths
from qgis.PyQt.QtWidgets import QDialog
from qgis.PyQt.uic import loadUiType
from qgis.core import QgsMapLayerModel
from qgis.gui import QgsFileWidget

from wincan2teksi.core.settings import Settings

DialogUi, _ = loadUiType(os.path.join(os.path.dirname(__file__), "../ui/settings.ui"))

SETTINGS = (
    "wastewater_structure_layer",
    "join_maintence_wastewaterstructure_layer",
    "channel_layer",
    "cover_layer",
    "maintenance_layer",
    "damage_layer",
    "file_layer",
    "organisation_layer",
    "vl_damage_channel_layer",
    "vl_damage_single_class",
    "vl_wastewater_structure_structure_condition",
)


class SettingsDialog(QDialog, DialogUi):
    def __init__(self, parent=None):
        self.settings = Settings()
        QDialog.__init__(self, parent)
        self.setupUi(self)

        for setting_key in SETTINGS:
            widget = getattr(self, setting_key)
            setting = getattr(self.settings, setting_key)
            widget.setCurrentIndex(
                widget.findData(setting.value(), QgsMapLayerModel.CustomRole.LayerId)
            )

        # Import log directory
        self.import_log_dir_widget.setStorageMode(QgsFileWidget.StorageMode.GetDirectory)
        log_dir = self.settings.import_log_dir.value()
        if not log_dir:
            log_dir = os.path.join(
                QStandardPaths.writableLocation(
                    QStandardPaths.StandardLocation.GenericDataLocation
                ),
                "wincan2teksi",
                "import_logs",
            )
        self.import_log_dir_widget.setFilePath(log_dir)

        # Highlight settings
        self.highlight_color_button.setColor(self.settings.highlight_color.value())
        self.highlight_color_button.setAllowOpacity(True)
        self.highlight_buffer_spinbox.setValue(self.settings.highlight_buffer.value())
        self.highlight_width_spinbox.setValue(self.settings.highlight_width.value())

    def accept(self):
        for setting_key in SETTINGS:
            widget = getattr(self, setting_key)
            setting = getattr(self.settings, setting_key)
            setting.setValue(
                widget.itemData(widget.currentIndex(), QgsMapLayerModel.CustomRole.LayerId)
            )
        self.settings.import_log_dir.setValue(self.import_log_dir_widget.filePath())

        # Highlight settings
        self.settings.highlight_color.setValue(self.highlight_color_button.color())
        self.settings.highlight_buffer.setValue(self.highlight_buffer_spinbox.value())
        self.settings.highlight_width.setValue(self.highlight_width_spinbox.value())

        super(SettingsDialog, self).accept()
