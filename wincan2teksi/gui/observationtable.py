#!/usr/bin/env python
# coding: utf-8 -*-

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

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QTableWidget, QTableWidgetItem, QAbstractItemView

IMPORT = 0
FORCE_IMPORT = 1


class ObservationTable(QTableWidget):
    def __init__(self, parent):
        QTableWidget.__init__(self, parent)
        self.data = None
        self.projectId = None
        self.sectionId = None
        self.inspectionId = None

        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setColumnCount(0)
        self.setRowCount(0)
        self.horizontalHeader().setVisible(True)
        self.horizontalHeader().setMinimumSectionSize(15)
        self.verticalHeader().setVisible(True)
        self.verticalHeader().setDefaultSectionSize(25)

        self.itemClicked.connect(self.import_checkbox_clicked)

        self.column_headers = [
            self.tr("distance"),
            self.tr("code"),
            self.tr("description"),
            self.tr("mpeg"),
            self.tr("photo"),
            self.tr("rate"),
            self.tr("force"),
        ]

    def finish_init(self, data):
        self.data = data
        for c, col in enumerate(self.column_headers):
            self.insertColumn(c)
            item = QTableWidgetItem(col)
            font = item.font()
            font.setPointSize(font.pointSize() - 2)
            item.setFont(font)
            self.setHorizontalHeaderItem(c, item)
        self.adjustSize()

    def set_inspection(self, projectId, sectionId, inspectionId):
        self.clearContents()

        self.projectId = projectId
        self.sectionId = sectionId
        self.inspectionId = inspectionId

        for r in range(self.rowCount() - 1, -1, -1):
            self.removeRow(r)

        if self.projectId is None or self.sectionId is None or self.inspectionId is None:
            return

        for o_id, obs in (
            self.data[self.projectId]
            .sections[self.sectionId]
            .inspections[self.inspectionId]
            .observations.items()
        ):
            r = self.rowCount()
            self.insertRow(r)

            for c, data in enumerate(
                (
                    obs.distance,
                    obs.code,
                    obs.text,
                    obs.time,
                    obs.mmfiles,
                    obs.rate,
                    obs.force_import,
                )
            ):
                item = QTableWidgetItem(str(data) if c != 6 else None)
                if c in (0, 6):
                    item.setFlags(
                        Qt.ItemFlag.ItemIsEnabled
                        | Qt.ItemFlag.ItemIsSelectable
                        | Qt.ItemFlag.ItemIsUserCheckable
                    )
                    if c == 0:
                        item.setCheckState(
                            Qt.CheckState.Checked if obs.import_ else Qt.CheckState.Unchecked
                        )
                        item.setData(Qt.ItemDataRole.UserRole + 1, IMPORT)

                    else:
                        item.setCheckState(
                            Qt.CheckState.Checked if obs.force_import else Qt.CheckState.Unchecked
                        )
                        item.setData(Qt.ItemDataRole.UserRole + 1, FORCE_IMPORT)
                    item.setData(Qt.ItemDataRole.UserRole, o_id)
                else:
                    item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                font = item.font()
                font.setPointSize(font.pointSize() - 2)
                item.setFont(font)
                self.setItem(r, c, item)

        self.resizeColumnsToContents()

    def import_checkbox_clicked(self, item):
        if item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
            o_id = item.data(Qt.ItemDataRole.UserRole)
            data_column = item.data(Qt.ItemDataRole.UserRole + 1)
            if data_column == IMPORT:
                self.data[self.projectId].sections[self.sectionId].inspections[
                    self.inspectionId
                ].observations[o_id].import_ = (
                    True if item.checkState() == Qt.CheckState.Checked else False
                )
            elif data_column == FORCE_IMPORT:
                self.data[self.projectId].sections[self.sectionId].inspections[
                    self.inspectionId
                ].observations[o_id].force_import = (
                    True if item.checkState() == Qt.CheckState.Checked else False
                )
            else:
                raise ValueError(f"Unknown data column: {data_column}")
