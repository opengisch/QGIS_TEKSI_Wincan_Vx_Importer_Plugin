# -----------------------------------------------------------
#
# QGIS Wincan 2 Teksi Plugin
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
import re
from qgis.PyQt.QtCore import pyqtSlot, Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QWidget, QHeaderView, QMenu, QMessageBox
from qgis.PyQt.uic import loadUiType

from qgis.core import QgsProject

from wincan2teksi.core.settings import Settings
from wincan2teksi.core.section import find_section, section_at_id
from wincan2teksi.gui.featureselectorwidget import CanvasExtent
from wincan2teksi.gui.sectionmodel import SectionTableModel, SectionFilterProxyModel

Ui_SectionWidget, _ = loadUiType(os.path.join(os.path.dirname(__file__), "../ui/sectionwidget.ui"))

_search_icon = QIcon(os.path.join(os.path.dirname(__file__), "..", "icons", "magnifier13.svg"))


class SectionWidget(QWidget, Ui_SectionWidget):
    def __init__(self, parent):
        QWidget.__init__(self, parent)
        self.setupUi(self)
        self.settings = Settings()
        self.projects = {}
        self.projectId = None
        self.section_id = None

        self._section_model = SectionTableModel(self)
        self._proxy_model = SectionFilterProxyModel(self)
        self._proxy_model.setSourceModel(self._section_model)
        self.sectionTableView.setModel(self._proxy_model)
        self.sectionTableView.horizontalHeader().setStretchLastSection(True)
        self.sectionTableView.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.sectionTableView.verticalHeader().hide()
        self.sectionTableView.verticalHeader().setDefaultSectionSize(20)
        self.sectionTableView.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.sectionTableView.customContextMenuRequested.connect(self._show_context_menu)

        self.section_1_selector.feature_changed.connect(self.set_teksi_channel_id1)
        self.section_2_selector.feature_changed.connect(self.set_teksi_channel_id2)
        self.section_3_selector.feature_changed.connect(self.set_teksi_channel_id3)

        self.inspectionWidget.importChanged.connect(self.update_status)

        self.sectionTableView.selectionModel().selectionChanged.connect(self._on_selection_changed)

        self.filter_unmatched_sections_active = False
        self.filterUnmatchedSectionsButton.clicked.connect(self.filter_unmatched_sections)

    def select_section(self, section_id):
        row = self._section_model.row_for_section_id(section_id)
        if row >= 0:
            proxy_index = self._proxy_model.mapFromSource(self._section_model.index(row, 0))
            if proxy_index.isValid():
                self.sectionTableView.setCurrentIndex(proxy_index)

    def finish_init(self, iface, projects):
        layer_id = self.settings.channel_layer.value()
        for selector in (self.section_1_selector, self.section_2_selector, self.section_3_selector):
            selector.set_layer(QgsProject.instance().mapLayer(layer_id))
            selector.set_canvas(iface.mapCanvas())
        self.projects = projects
        self.inspectionWidget.finish_init(self.projects)

    def set_project_id(self, prjId=None):
        if prjId is not None:
            self.projectId = prjId

        self._section_model.set_data(self.projects, self.projectId)
        # Reconnect selection signal after model reset
        self.sectionTableView.selectionModel().selectionChanged.connect(self._on_selection_changed)

    def update_status(self):
        self._section_model.refresh()

    def filter_unmatched_sections(self):
        self.filter_unmatched_sections_active = not self.filter_unmatched_sections_active
        if self.filter_unmatched_sections_active:
            self.filterUnmatchedSectionsButton.setText(self.tr("Show all sections"))
        else:
            self.filterUnmatchedSectionsButton.setText(self.tr("Filter unmatched sections"))
        self._proxy_model.set_filter_unmatched(self.filter_unmatched_sections_active)

    def set_teksi_channel_id1(self, feature):
        if self.projectId is None or self.section_id is None:
            return
        obj_id = feature.attribute("obj_id") if feature.isValid() else None
        self.projects[self.projectId].sections[self.section_id].teksi_channel_id_1 = obj_id
        self.update_status()

    def set_teksi_channel_id2(self, feature):
        if self.projectId is None or self.section_id is None:
            return
        obj_id = feature.attribute("obj_id") if feature.isValid() else None
        self.projects[self.projectId].sections[self.section_id].teksi_channel_id_2 = obj_id
        self.update_status()

    def set_teksi_channel_id3(self, feature):
        if self.projectId is None or self.section_id is None:
            return
        obj_id = feature.attribute("obj_id") if feature.isValid() else None
        self.projects[self.projectId].sections[self.section_id].teksi_channel_id_3 = obj_id
        self.update_status()

    @pyqtSlot(bool)
    def on_usePreviousSectionCheckBox_toggled(self, checked):
        if self.projectId is None or self.section_id is None:
            return
        self.projects[self.projectId].sections[self.section_id].use_previous_section = checked
        self.update_status()

    def _on_selection_changed(self, selected, deselected):
        # Disconnect signals to avoid triggering updates while changing selection
        for selector, channel_id_slot in (
            (self.section_1_selector, self.set_teksi_channel_id1),
            (self.section_2_selector, self.set_teksi_channel_id2),
            (self.section_3_selector, self.set_teksi_channel_id3),
        ):
            try:
                selector.feature_changed.disconnect(channel_id_slot)
            except TypeError:
                pass
            selector.clear()
        self.endNodeEdit.clear()
        self.pipeDiaEdit.clear()
        self.pipeMaterialEdit.clear()
        self.pipeWidthEdit.clear()
        self.profileEdit.clear()
        self.sectionlengthEdit.clear()
        self.sectionUseEdit.clear()
        self.startNodeEdit.clear()
        self.addressEdit.clear()

        self.section_id = None

        if self.projectId is None:
            return

        indexes = self.sectionTableView.selectionModel().selectedRows()
        if not indexes:
            return

        proxy_index = indexes[0]
        source_index = self._proxy_model.mapToSource(proxy_index)
        self.section_id = self._section_model.section_id_for_row(source_index.row())

        # allow use of previous section if not on first section
        self.usePreviousSectionCheckBox.setEnabled(
            not self._section_model.is_first_section(self.section_id)
        )

        section = self.projects[self.projectId].sections[self.section_id]

        for selector, channel_id, channel_id_slot in (
            (self.section_1_selector, section.teksi_channel_id_1, self.set_teksi_channel_id1),
            (self.section_2_selector, section.teksi_channel_id_2, self.set_teksi_channel_id2),
            (self.section_3_selector, section.teksi_channel_id_3, self.set_teksi_channel_id3),
        ):
            feature = section_at_id(channel_id)
            if feature.isValid():
                selector.set_feature(feature)
            selector.feature_changed.connect(channel_id_slot)

        self.section_1_selector.highlight_feature(CanvasExtent.Pan)

        self.usePreviousSectionCheckBox.setChecked(section.use_previous_section)
        self.endNodeEdit.setText(section.to_node)
        self.pipeDiaEdit.setText("{}".format(section.section_size))
        self.pipeMaterialEdit.setText(section.pipe_material)
        # self.pipeWidthEdit.setText("{}".format(section.pipe_width))
        self.profileEdit.setText(section.profile)
        self.sectionlengthEdit.setText("{}".format(section.section_length))
        self.sectionUseEdit.setText(section.section_use)
        self.startNodeEdit.setText(section.from_node)
        self.addressEdit.setText(section.address)

        self.inspectionWidget.set_section(self.projectId, self.section_id)

    def _show_context_menu(self, pos):
        index = self.sectionTableView.indexAt(pos)
        if not index.isValid():
            return
        source_index = self._proxy_model.mapToSource(index)
        row = source_index.row()
        col = source_index.column()
        from wincan2teksi.gui.sectionmodel import Column

        menu = QMenu(self)

        match_action = menu.addAction(_search_icon, self.tr("Match section"))

        edit_action = None
        reset_action = None
        if col in (Column["FromNode"], Column["ToNode"]):
            menu.addSeparator()
            edit_action = menu.addAction(self.tr("Edit"))
            if self._section_model.is_edited(row, col):
                reset_action = menu.addAction(self.tr("Reset to original"))

        action = menu.exec(self.sectionTableView.viewport().mapToGlobal(pos))
        if action == match_action:
            self._match_section(row)
        elif edit_action and action == edit_action:
            self.sectionTableView.edit(index)
        elif reset_action and action == reset_action:
            self._section_model.reset_to_original(row, col)

    def _match_section(self, source_row):
        s_id = self._section_model.section_id_for_row(source_row)
        if s_id is None or self.projectId is None:
            return
        section = self.projects[self.projectId].sections[s_id]
        if section.teksi_channel_id_1 is not None:
            reply = QMessageBox.question(
                self,
                self.tr("Section already matched"),
                self.tr("This section is already matched. Do you want to search again?"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        channel = self.projects[self.projectId].channel
        settings = Settings()
        feature = find_section(channel, section.from_node, section.to_node)
        if not feature.isValid() and settings.remove_trailing_chars.value():
            feature = find_section(
                channel,
                re.sub(r"\D*$", "", section.from_node),
                re.sub(r"\D*$", "", section.to_node),
            )
        if feature.isValid():
            section.teksi_channel_id_1 = feature.attribute("obj_id")
        else:
            section.teksi_channel_id_1 = None
        self.update_status()
        # Refresh detail pane if this section is currently selected
        if self.section_id == s_id:
            self._on_selection_changed(None, None)

    @pyqtSlot()
    def on_checkAllButton_clicked(self):
        self._set_visible_check_state(Qt.CheckState.Checked)

    @pyqtSlot()
    def on_uncheckAllButton_clicked(self):
        self._set_visible_check_state(Qt.CheckState.Unchecked)

    def _set_visible_check_state(self, state):
        from wincan2teksi.gui.sectionmodel import Column

        for row in range(self._proxy_model.rowCount()):
            source_index = self._proxy_model.mapToSource(
                self._proxy_model.index(row, Column["Number"])
            )
            self._section_model.setData(source_index, state, Qt.ItemDataRole.CheckStateRole)


"""
    @pyqtSlot()
    def on_previousButton_clicked(self):
        idx = self.sectionCombo.currentIndex()
        if idx > 0:
            self.sectionCombo.setCurrentIndex(idx-1)

    @pyqtSlot()
    def on_nextButton_clicked(self):
        idx = self.sectionCombo.currentIndex()
        if idx < self.sectionCombo.count()-1:
            self.sectionCombo.setCurrentIndex(idx+1)
"""
