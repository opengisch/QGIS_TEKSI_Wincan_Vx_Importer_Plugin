#!/usr/bin/env python
# -*- coding: utf-8 -*-

# -----------------------------------------------------------
#
# QGIS wincan 2 QGEP Plugin
# Copyright (C) 2016 Denis Rouzaud
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

import os
from qgis.PyQt.QtCore import pyqtSlot, pyqtSignal
from qgis.PyQt.QtWidgets import QWidget
from qgis.PyQt.uic import loadUiType

from wincan2teksi.core.settings import Settings

Ui_InspectionWidget, _ = loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/inspectionwidget.ui")
)


class InspectionWidget(QWidget, Ui_InspectionWidget):
    importChanged = pyqtSignal()

    def __init__(self, parent):
        QWidget.__init__(self, parent)
        self.setupUi(self)
        self.settings = Settings()
        self.data = None
        self.projectId = None
        self.sectionId = None
        self.inspectionId = None

    def finish_init(self, data):
        self.data = data
        self.observationTable.finish_init(data)

    def set_section(self, projectId, sectionId):
        self.inspectionCombo.clear()
        self.projectId = projectId
        self.sectionId = sectionId
        for i_id, inspection in (
            self.data[self.projectId].sections[self.sectionId].inspections.items()
        ):
            self.inspectionCombo.addItem(
                inspection.start_date.toString("dd.MM.yyyy HH:mm:ss"), i_id
            )
            # self.observationTable.clear()

    @pyqtSlot(int)
    def on_inspectionCombo_currentIndexChanged(self, idx):
        self.inspMethodEdit.clear()
        self.inspectionDirEdit.clear()
        self.inspectedLengthEdit.clear()
        self.operatorEdit.clear()

        if self.projectId is None or self.sectionId is None:
            return

        if idx < 0:
            self.observationTable.set_inspection(None, None, None)
            return

        self.inspectionId = self.inspectionCombo.itemData(idx)
        inspection = (
            self.data[self.projectId].sections[self.sectionId].inspections[self.inspectionId]
        )

        self.inspMethodEdit.setText(inspection.method)
        self.inspectionDirEdit.setText(str(inspection.direction))
        self.inspectedLengthEdit.setText("{}".format(inspection.inspection_length))
        self.operatorEdit.setText(inspection.operator)
        self.importCheckBox.setChecked(inspection.import_)

        self.observationTable.set_inspection(self.projectId, self.sectionId, self.inspectionId)

    @pyqtSlot(bool)
    def on_importCheckBox_clicked(self, toImport):
        if self.projectId is None or self.sectionId is None or self.inspectionId is None:
            return
        self.data[self.projectId].sections[self.sectionId].inspections[
            self.inspectionId
        ].import_ = toImport
        self.importChanged.emit()
