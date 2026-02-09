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
from qgis.PyQt.QtCore import pyqtSlot, Qt
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import QWidget, QListWidgetItem
from qgis.PyQt.uic import loadUiType

from qgis.core import QgsProject, QgsApplication

from wincan2teksi.core.settings import Settings
from wincan2teksi.core.section import section_at_id
from wincan2teksi.gui.featureselectorwidget import CanvasExtent

Ui_SectionWidget, _ = loadUiType(os.path.join(os.path.dirname(__file__), "../ui/sectionwidget.ui"))


warning_icon = QgsApplication.getThemeIcon("/mIconWarn.png")


class SectionWidget(QWidget, Ui_SectionWidget):
    def __init__(self, parent):
        QWidget.__init__(self, parent)
        self.setupUi(self)
        self.settings = Settings()
        self.projects = {}
        self.projectId = None
        self.section_id = None

        self.section_1_selector.feature_changed.connect(self.set_qgep_channel_id1)
        self.section_2_selector.feature_changed.connect(self.set_qgep_channel_id2)
        self.section_3_selector.feature_changed.connect(self.set_qgep_channel_id3)

        self.inspectionWidget.importChanged.connect(self.update_status)

        self.sectionListWidget.itemChanged.connect(self.sectionItemChanged)

        self.filter_unmatched_sections_active = False
        self.filterUnmatchedSectionsButton.clicked.connect(self.filter_unmatched_sections)

    def select_section(self, section_id):
        for r in range(0, self.sectionListWidget.count()):
            item = self.sectionListWidget.item(r)
            if section_id == item.data(Qt.ItemDataRole.UserRole):
                self.sectionListWidget.setCurrentItem(item)
                break

    def finish_init(self, iface, projects):
        layer_id = self.settings.channel_layer.value()
        for selector in (self.section_1_selector, self.section_2_selector, self.section_3_selector):
            selector.set_layer(QgsProject.instance().mapLayer(layer_id))
            selector.set_canvas(iface.mapCanvas())
        self.projects = projects
        self.inspectionWidget.finish_init(self.projects)

    def set_project_id(self, prjId=None):
        self.sectionListWidget.clear()

        if prjId is not None:
            self.projectId = prjId

        if self.projectId is None:
            return

        for s_id, section in self.projects[prjId].sections.items():
            title = f"{section.counter}: de {section.from_node} a {section.to_node}"
            item = QListWidgetItem(warning_icon, title)
            item.setData(Qt.ItemDataRole.UserRole, s_id)
            item.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsUserCheckable
            )
            item.setCheckState(
                Qt.CheckState.Checked if section.import_ else Qt.CheckState.Unchecked
            )
            self.sectionListWidget.addItem(item)
        self.update_status()

    def update_status(self):
        for r in range(0, self.sectionListWidget.count()):
            item = self.sectionListWidget.item(r)
            s_id = item.data(Qt.ItemDataRole.UserRole)
            section = self.projects[self.projectId].sections[s_id]
            ok = section.teksi_channel_id_1 is not None or section.use_previous_section is True
            if not ok:
                ok = True
                for inspection in section.inspections.values():
                    if inspection.import_:
                        ok = False
                        break
            if ok:
                # item.setIcon(QIcon())  # doesn't seem to be working next to checkboxes
                item.setBackground(Qt.GlobalColor.white)
            else:
                # item.setIcon(warning_icon)  # doesn't seem to be working next to checkboxes
                item.setBackground(QColor(255, 190, 190))

    def filter_unmatched_sections(self):
        self.filter_unmatched_sections_active = not self.filter_unmatched_sections_active
        if self.filter_unmatched_sections_active:
            self.filterUnmatchedSectionsButton.setText(self.tr("Show all sections"))
        else:
            self.filterUnmatchedSectionsButton.setText(self.tr("Filter unmatched sections"))
        for r in range(0, self.sectionListWidget.count()):
            item = self.sectionListWidget.item(r)
            if not self.filter_unmatched_sections_active:
                item.setHidden(False)
                continue

            s_id = item.data(Qt.ItemDataRole.UserRole)
            section = self.projects[self.projectId].sections[s_id]
            is_matched = (
                section.teksi_channel_id_1 is not None or section.use_previous_section is True
            )
            item.setHidden(is_matched)

    def sectionItemChanged(self, item):
        s_id = item.data(Qt.ItemDataRole.UserRole)
        if self.projectId is None:
            return
        self.projects[self.projectId].sections[s_id].import_ = bool(item.checkState())

    def set_qgep_channel_id1(self, feature):
        if self.projectId is None or self.section_id is None:
            return
        obj_id = feature.attribute("obj_id") if feature.isValid() else None
        self.projects[self.projectId].sections[self.section_id].teksi_channel_id_1 = obj_id
        self.update_status()

    def set_qgep_channel_id2(self, feature):
        if self.projectId is None or self.section_id is None:
            return
        obj_id = feature.attribute("obj_id") if feature.isValid() else None
        self.projects[self.projectId].sections[self.section_id].teksi_channel_id_2 = obj_id
        self.update_status()

    def set_qgep_channel_id3(self, feature):
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

    @pyqtSlot()
    def on_sectionListWidget_itemSelectionChanged(self):
        # Disconnect signals to avoid triggering updates while changing selection
        # Use try-except because signals might not be connected (e.g., after previous disconnect/reconnect cycle)
        for selector, channel_id_slot in (
            (self.section_1_selector, self.set_qgep_channel_id1),
            (self.section_2_selector, self.set_qgep_channel_id2),
            (self.section_3_selector, self.set_qgep_channel_id3),
        ):
            try:
                selector.feature_changed.disconnect(channel_id_slot)
            except TypeError:
                # Signal was not connected, which is fine - it means this isn't the first call
                # or the connection was already removed
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
        # self.inspectionWidget.clear()

        if self.projectId is None:
            return

        items = self.sectionListWidget.selectedItems()
        if len(items) < 1:
            return

        self.section_id = items[0].data(Qt.ItemDataRole.UserRole)

        # allow use of previous section if not on first section
        self.usePreviousSectionCheckBox.setEnabled(
            self.section_id != list(self.projects[self.projectId].sections.keys())[0]
        )

        section = self.projects[self.projectId].sections[self.section_id]

        for selector, channel_id, channel_id_slot in (
            (self.section_1_selector, section.teksi_channel_id_1, self.set_qgep_channel_id1),
            (self.section_2_selector, section.teksi_channel_id_2, self.set_qgep_channel_id2),
            (self.section_3_selector, section.teksi_channel_id_3, self.set_qgep_channel_id3),
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

    @pyqtSlot()
    def on_checkAllButton_clicked(self):
        for r in range(0, self.sectionListWidget.count()):
            if not self.sectionListWidget.item(r).isHidden():
                self.sectionListWidget.item(r).setCheckState(Qt.CheckState.Checked)

    @pyqtSlot()
    def on_uncheckAllButton_clicked(self):
        for r in range(0, self.sectionListWidget.count()):
            if not self.sectionListWidget.item(r).isHidden():
                self.sectionListWidget.item(r).setCheckState(Qt.CheckState.Unchecked)


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
