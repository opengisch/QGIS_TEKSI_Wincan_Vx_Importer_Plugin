# encoding: utf-8
#
# #-----------------------------------------------------------
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

import re
import os

from qgis.PyQt.QtCore import pyqtSlot, QCoreApplication
from qgis.PyQt.QtWidgets import QDialog, QMessageBox
from qgis.PyQt.uic import loadUiType

from qgis.core import QgsProject, QgsFeature, QgsFeatureRequest
from qgis.gui import QgsGui, QgsAttributeEditorContext, QgisInterface

from wincan2teksi.core.settings import Settings
from wincan2teksi.core.exceptions import W2TLayerNotFound
from wincan2teksi.core.section import find_section, section_at_id
from wincan2teksi.core.vsacode import (
    damage_code_to_vl,
    damage_level_to_vl,
    damage_level_2_structure_condition,
    structure_condition_2_damage_level,
)
from wincan2teksi.core.layer_edit import edit
from wincan2teksi.core.read_data import WinCanData
from wincan2teksi.core.utils import info, logger

Ui_DataBrowserDialog, _ = loadUiType(
    os.path.join(os.path.dirname(__file__), "..", "ui", "databrowserdialog.ui")
)


class DataBrowserDialog(QDialog, Ui_DataBrowserDialog):
    def __init__(self, iface: QgisInterface, data: WinCanData, data_path=""):
        print(os.path.join(os.path.dirname(__file__), "..", "ui", "databrowserdialog.ui"))
        QDialog.__init__(self)
        self.setupUi(self)
        self.settings = Settings()
        self.projects = data.projects
        self.current_project_id = None
        self.channelNameEdit.setFocus()
        self.cancel = False

        self.data_path_line_edit.setText(data_path)

        self.meta_file_widget.setDefaultRoot(data_path)
        self.meta_file_widget.setReadOnly(True)

        if data.meta_file:
            self.meta_file_widget.setFilePath(data.meta_file)

        self.pdf_path_widget.setDefaultRoot(data_path)
        if data.pdf_file:
            self.pdf_path_widget.setFilePath(data.pdf_file)

        self.cannotImportArea.hide()
        self.progressBar.setTextVisible(True)
        self.progressBar.hide()
        self.cancelButton.hide()

        self.relationWidgetWrapper = None
        maintenance_layer = QgsProject.instance().mapLayer(self.settings.maintenance_layer.value())
        if maintenance_layer is not None:
            organisation_layer_id = self.settings.organisation_layer.value()
            widget_config = {
                "Layer": organisation_layer_id,
                "Key": "obj_id",
                "Value": "identifier",
                "AllowNull": True,
                "OrderByValue": True,
            }
            editor_context = QgsAttributeEditorContext()
            editor_context.setVectorLayerTools(iface.vectorLayerTools())
            self.relationWidgetWrapper = QgsGui.editorWidgetRegistry().create(
                "ValueRelation",
                maintenance_layer,
                maintenance_layer.fields().indexFromName("fk_operating_company"),
                widget_config,
                self.operatingCompanyComboBox,
                self,
            )

        self.sectionWidget.finish_init(iface, self.projects)

        for project in self.projects.values():
            self.projectCombo.addItem(project.name, project.pk)

        self.channelNameEdit.setText("")
        # self.on_searchButton_clicked()

    @pyqtSlot(str)
    def on_channelNameEdit_textChanged(self, txt):
        if self.current_project_id is not None:
            self.projects[self.current_project_id].channel = txt

    @pyqtSlot(int)
    def on_projectCombo_currentIndexChanged(self, idx):
        self.current_project_id = self.projectCombo.itemData(idx)
        self.channelNameEdit.setText(self.projects[self.current_project_id].channel)
        self.sectionWidget.set_project_id(self.current_project_id)

    @pyqtSlot()
    def on_cancelButton_clicked(self):
        self.cancel = True

    @pyqtSlot()
    def on_searchButton_clicked(self):
        if self.current_project_id is None:
            return

        self.sectionWidget.setEnabled(False)

        # init progress bar
        c = 0
        for project in self.projects.values():
            c += len(project.sections)
        self.progressBar.setMaximum(c)
        self.progressBar.setMinimum(0)
        self.progressBar.setValue(0)
        self.progressBar.setFormat("Searching channels %v/%m")
        self.progressBar.show()
        self.cancelButton.show()
        self.importButton.hide()
        self.cancel = False
        i = 0

        # find sections
        channel = self.projects[self.current_project_id].channel
        for project in self.projects.values():
            if self.cancel:
                break
            # former cleanup to remove previous search results
            has_channel = False
            for section in project.sections.values():
                if (
                    section.teksi_channel_id_1 is not None
                    or section.teksi_channel_id_2 is not None
                    or section.teksi_channel_id_3 is not None
                ):
                    has_channel = True
            if has_channel:
                reply = QMessageBox.question(
                    self,
                    self.tr("Clear previous search results?"),
                    self.tr(
                        "Performing a new search will remove all previous matching data. Do you want to continue?"
                    ),
                    QMessageBox.Yes | QMessageBox.No,
                )
                if reply != QMessageBox.Yes:
                    self.progressBar.hide()
                    self.cancelButton.hide()
                    self.importButton.show()
                    self.sectionWidget.setEnabled(True)
                    self.sectionWidget.set_project_id(self.current_project_id)
                    return
                for section in project.sections.values():
                    section.teksi_channel_id_1 = None
                    section.teksi_channel_id_2 = None
                    section.teksi_channel_id_3 = None

            for section in project.sections.values():
                QCoreApplication.processEvents()
                if self.cancel:
                    break
                try:
                    feature = find_section(channel, section.from_node, section.to_node)
                    if not feature.isValid() and self.settings.remove_trailing_chars.value():
                        # try without trailing alpha char
                        feature = find_section(
                            channel,
                            re.sub("\D*$", "", section.from_node),
                            re.sub("\D*$", "", section.to_node),
                        )
                    if feature.isValid():
                        section.teksi_channel_id_1 = feature.attribute("obj_id")
                except W2TLayerNotFound as e:
                    self.cannotImportArea.show()
                    self.cannotImportLabel.setText(
                        self.tr("The channel layer is missing in the project: {error}").format(
                            error=str(e)
                        )
                    )
                    self.hide_progress()
                    return
                self.progressBar.setValue(i)
                i += 1
        self.progressBar.hide()
        self.cancelButton.hide()
        self.importButton.show()

        self.sectionWidget.setEnabled(True)
        self.sectionWidget.set_project_id(self.current_project_id)

    @pyqtSlot()
    def on_importButton_clicked(self):
        self.cannotImportArea.hide()

        always_skip_invalid_codes = False

        # init progress bar
        c = 0
        for p_id in self.projects.keys():
            for section in self.projects[p_id].sections.values():
                c += 1
        self.progressBar.setMaximum(c)
        self.progressBar.setMinimum(0)
        self.progressBar.setValue(0)
        self.progressBar.setFormat("Checking channels %v/%m")
        self.progressBar.show()
        self.cancelButton.show()
        self.importButton.hide()
        self.cancel = False
        i = 0

        # initialize maintenance and damage layers and features
        maintenance_layer_id = self.settings.maintenance_layer.value()
        maintenance_layer = QgsProject.instance().mapLayer(maintenance_layer_id)
        damage_layer_id = self.settings.damage_layer.value()
        damage_layer = QgsProject.instance().mapLayer(damage_layer_id)
        join_layer_id = self.settings.join_maintence_wastewaterstructure_layer.value()
        join_layer = QgsProject.instance().mapLayer(join_layer_id)
        if join_layer is None:
            self.cannotImportArea.show()
            self.cannotImportLabel.setText(
                self.tr("The join layer '{layer_id}' is missing in the project.")
            )
            self.hide_progress()
            return
        features = {}  # dictionnary with waste water structure id (reach) as key, and as values: a dict with maintenance event and damages

        for p_id in self.projects.keys():
            previous_section_imported = True
            for s_id, section in self.projects[p_id].sections.items():
                QCoreApplication.processEvents()
                if self.cancel:
                    self.hide_progress()
                    return

                if section.import_ is not True:
                    previous_section_imported = False
                    continue

                for i_id, inspection in self.projects[p_id].sections[s_id].inspections.items():
                    if inspection.import_:
                        # offset in case of several sections in inspection
                        # data correspond to a single section in qgep data
                        distance_offset = 0

                        if section.use_previous_section is not True:
                            previous_section_imported = True
                            # get corresponding reaches in qgep project
                            reach_features = []

                            for fid in [
                                section.teksi_channel_id_1,
                                section.teksi_channel_id_2,
                                section.teksi_channel_id_3,
                            ]:
                                if fid is None:
                                    break
                                f = section_at_id(fid)
                                if f.isValid() is False:
                                    self.cannotImportArea.show()
                                    self.cannotImportLabel.setText(
                                        self.tr(
                                            "Inspection {i} from manhole {c1} to {c2}"
                                            " has an non-existent channel assigned.".format(
                                                i=section.counter,
                                                c1=section.from_node,
                                                c2=section.to_node,
                                            )
                                        )
                                    )
                                    self.sectionWidget.select_section(s_id)
                                    self.hide_progress()
                                    return
                                reach_features.append(QgsFeature(f))

                            if len(reach_features) == 0:
                                self.cannotImportArea.show()
                                self.cannotImportLabel.setText(
                                    self.tr(
                                        "Inspection {i} from manhole {c1} to {c2}"
                                        " has no channel assigned.".format(
                                            i=section.counter,
                                            c1=section.from_node,
                                            c2=section.to_node,
                                        )
                                    )
                                )
                                self.sectionWidget.select_section(s_id)
                                self.hide_progress()
                                return

                            # create maintenance/examination event (one per qgep reach feature)
                            for rf in reach_features:
                                # in case several sections in qgep data
                                # correspond to a single section in inspection data
                                mf = QgsFeature()
                                init_fields = maintenance_layer.fields()
                                mf.setFields(init_fields)
                                mf.initAttributes(init_fields.size())
                                mf["obj_id"] = maintenance_layer.dataProvider().defaultValue(
                                    maintenance_layer.fields().indexFromName("obj_id")
                                )
                                # mf['identifier'] = i_id  # use custom id to retrieve feature
                                mf["maintenance_event_type"] = "examination"
                                mf["kind"] = 4564  # vl_maintenance_event_kind: inspection
                                mf["operator"] = inspection.operator
                                mf["time_point"] = inspection.start_date
                                mf["remark"] = ""
                                mf["status"] = 2550  # vl_maintenance_event: accomplished
                                mf["inspected_length"] = section.section_length
                                mf["base_data"] = self.pdf_path_widget.filePath()
                                if self.relationWidgetWrapper is not None:
                                    mf["fk_operating_company"] = self.relationWidgetWrapper.value()
                                if inspection.direction == 1:
                                    mf["fk_reach_point"] = rf["rp_from_obj_id"]
                                else:
                                    mf["fk_reach_point"] = rf["rp_to_obj_id"]

                                features[rf["ws_obj_id"]] = {
                                    "maintenance": QgsFeature(mf),
                                    "damages": [],
                                    "media": [],
                                    "structure_condition": 4,
                                }

                        else:
                            # in case several sections in inspection data correspond to a single section in qgep data
                            # substract length from previous sections in inspection data
                            if not previous_section_imported:
                                self.cannotImportArea.show()
                                self.cannotImportLabel.setText(
                                    self.tr(
                                        "Inspection {i} from manhole {c1} to {c2}"
                                        " uses previous channel, but it is not defined.".format(
                                            i=section.counter,
                                            c1=section.from_node,
                                            c2=section.to_node,
                                        )
                                    )
                                )
                                self.sectionWidget.select_section(s_id)
                                self.hide_progress()
                                return
                            distance_offset = 0
                            offset_section_id = s_id
                            while (
                                self.projects[p_id].sections[offset_section_id].use_previous_section
                                is True
                            ):
                                # get previous section id
                                offset_section_id_index = list(self.projects[p_id].sections).index(
                                    offset_section_id
                                )
                                assert offset_section_id_index > 0
                                offset_section_id = list(self.projects[p_id].sections)[
                                    offset_section_id_index - 1
                                ]
                                # accumulate offset
                                distance_offset -= (
                                    self.projects[p_id].sections[offset_section_id].section_length
                                )
                                info(
                                    "using previous section: {} with distance offset {}".format(
                                        offset_section_id, distance_offset
                                    )
                                )

                                # add corresponding damages
                        reach_index = 0
                        structure_condition = 4  # = ok
                        for observation in (
                            self.projects[p_id]
                            .sections[s_id]
                            .inspections[i_id]
                            .observations.values()
                        ):
                            if observation.import_:
                                distance = observation.distance + distance_offset
                                if not observation.force_import:
                                    while (
                                        distance > reach_features[reach_index]["length_effective"]
                                    ):
                                        if reach_index < len(reach_features) - 1:
                                            distance -= reach_features[reach_index][
                                                "length_effective"
                                            ]
                                            reach_index += 1
                                        else:
                                            if (
                                                distance
                                                <= reach_features[reach_index]["length_effective"]
                                                + self.settings.tolerance_channel_length.value()
                                            ):  # add 50cm tolerance
                                                break
                                            else:
                                                self.cannotImportArea.show()
                                                self.cannotImportLabel.setText(
                                                    self.tr(
                                                        "Inspection {i} from manhole {c1} to {c2}"
                                                        " has observations further than the length"
                                                        " of the assigned channels.".format(
                                                            i=section.counter,
                                                            c1=section.from_node,
                                                            c2=section.to_node,
                                                        )
                                                    )
                                                )
                                                self.sectionWidget.select_section(s_id)
                                                self.hide_progress()
                                                return

                                # create maintenance/examination event
                                single_damage_class = damage_level_to_vl(observation.rate)
                                channel_damage_code = damage_code_to_vl(observation.code)
                                if channel_damage_code is not None:
                                    channel_damage_code = int(channel_damage_code)

                                if single_damage_class is None or channel_damage_code is None:
                                    if always_skip_invalid_codes:
                                        observation.import_ = False
                                        continue
                                    message = ""
                                    if single_damage_class is None:
                                        message = self.tr(
                                            "Invalid damage level: '{level}'".format(
                                                level=observation.rate
                                            )
                                        )
                                    if channel_damage_code is None:
                                        message += self.tr(
                                            "Invalid damage code: '{code}'".format(
                                                code=observation.code
                                            )
                                        )
                                    reply = QMessageBox.question(
                                        self,
                                        self.tr("Invalid damage data"),
                                        self.tr(
                                            "Inspection {i} from manhole {c1} to {c2} has invalid damage code or level.\n"
                                            f"{message}\n"
                                            "Insert without value?".format(
                                                i=section.counter,
                                                c1=section.from_node,
                                                c2=section.to_node,
                                            )
                                        ),
                                        QMessageBox.Yes | QMessageBox.YesToAll | QMessageBox.No,
                                    )
                                    if reply == QMessageBox.No:
                                        self.hide_progress()
                                        return
                                    elif reply == QMessageBox.YesToAll:
                                        always_skip_invalid_codes = True

                                    if single_damage_class is None:
                                        # set to unknown
                                        single_damage_class = 4561

                                df = QgsFeature()
                                init_fields = damage_layer.fields()
                                df.setFields(init_fields)
                                df.initAttributes(init_fields.size())
                                df["obj_id"] = damage_layer.dataProvider().defaultValue(
                                    damage_layer.fields().indexFromName("obj_id")
                                )
                                df["damage_type"] = "channel"
                                df["comments"] = observation.text
                                df["single_damage_class"] = single_damage_class
                                df["channel_damage_code"] = channel_damage_code
                                df["distance"] = distance
                                df["video_counter"] = observation.mpeg_position
                                # media files
                                mms = observation.mmfiles
                                # get wastewater structure id
                                ws_obj_id = reach_features[reach_index]["ws_obj_id"]
                                features[ws_obj_id]["damages"].append(df)
                                features[ws_obj_id]["media"].append(mms)
                                if observation.rate is not None:
                                    structure_condition = min(structure_condition, observation.rate)
                                features[ws_obj_id]["structure_condition"] = structure_condition
                self.progressBar.setValue(i)
                i += 1

        self.progressBar.setMaximum(len(features))
        self.progressBar.setMinimum(0)
        self.progressBar.setValue(0)
        self.progressBar.setFormat("Importing %v/%m")
        self.progressBar.show()
        self.cancelButton.show()
        self.importButton.hide()
        self.cancel = False

        file_layer_id = Settings().file_layer.value()
        file_layer = QgsProject.instance().mapLayer(file_layer_id)

        try:
            with edit(join_layer):
                with edit(file_layer):
                    with edit(damage_layer):
                        with edit(maintenance_layer):
                            i = 0
                            for ws_obj_id, elements in features.items():
                                QCoreApplication.processEvents()
                                if self.cancel:
                                    raise InterruptedError("Import cancelled by user")

                                maintenance = elements["maintenance"]
                                damages = elements["damages"]
                                media = elements["media"]
                                structure_condition = elements["structure_condition"]

                                if len(damages) == 0:
                                    continue

                                # write video for maintenance event
                                videos = []
                                for k, _ in enumerate(damages):
                                    for mf in media[k]:
                                        if mf[1] in videos:
                                            continue
                                        if mf[0] == "video":
                                            maintenance["videonumber"] = mf[1]

                                            of = QgsFeature()
                                            init_fields = file_layer.fields()
                                            of.setFields(init_fields)
                                            of.initAttributes(init_fields.size())
                                            of["obj_id"] = file_layer.dataProvider().defaultValue(
                                                file_layer.fields().indexFromName("obj_id")
                                            )
                                            of["class"] = 3825  # i.e. maintenance event
                                            of["kind"] = 3775  # i.e. video
                                            of["object"] = maintenance["obj_id"]
                                            of["identifier"] = mf[1]
                                            sep = os.path.sep
                                            of["path_relative"] = of["path_relative"] = (
                                                self.data_path_line_edit.text()
                                                + f"{sep}Video{sep}Sec"
                                            )
                                            ok = file_layer.addFeature(of)
                                            if ok:
                                                logger.debug(
                                                    f"adding feature to file layer (fid: {of['obj_id']}): ok"
                                                )
                                                videos.append(mf[1])
                                            else:
                                                _fields = ""
                                                for name, value in zip(
                                                    file_layer.fields().names(), of.attributes()
                                                ):
                                                    _fields += f"{name}: {value}\n"
                                                message = (
                                                    self.tr(
                                                        f"error adding feature to file layer (fid: {of['obj_id']}): error. "
                                                    )
                                                    + f"{_fields}"
                                                )
                                                logger.error(message)
                                                self.hide_progress()
                                                self.cannotImportArea.show()
                                                self.cannotImportLabel.setText(message)
                                                return
                                        logger.debug(
                                            f"no video found for maintenance event (fid: {maintenance['obj_id']})"
                                        )

                                # write maintenance feature
                                ok = maintenance_layer.addFeature(maintenance)
                                if ok:
                                    logger.debug(
                                        "adding feature to maintenance layer (fid: {}): ok".format(
                                            maintenance["obj_id"]
                                        )
                                    )
                                else:
                                    _fields = ""
                                    for name, value in zip(
                                        maintenance_layer.fields().names(), maintenance.attributes()
                                    ):
                                        _fields += f"{name}: {value}\n"
                                    message = (
                                        self.tr(
                                            f"error adding feature to maintenance layer (fid: {maintenance['obj_id']}): error. "
                                        )
                                        + f"{_fields}"
                                    )
                                    self.hide_progress()
                                    self.cannotImportArea.show()
                                    self.cannotImportLabel.setText(message)
                                    return

                                # set fkey maintenance event id to all damages
                                for k, _ in enumerate(damages):
                                    damages[k]["fk_examination"] = maintenance["obj_id"]

                                # write damages
                                for k, damage in enumerate(damages):
                                    ok = damage_layer.addFeature(damage)
                                    if ok:
                                        logger.debug(
                                            "adding feature to damage layer (fid: {}): {}".format(
                                                damage["obj_id"], "ok" if ok else "error"
                                            )
                                        )
                                    else:
                                        _fields = ""
                                        for name, value in zip(
                                            damage_layer.fields().names(), damage.attributes()
                                        ):
                                            _fields += f"{name}: {value}\n"
                                        message = (
                                            self.tr(
                                                f"error adding feature to damage layer (fid: {damage['obj_id']}): error. "
                                            )
                                            + f"{_fields}"
                                        )
                                        logger.error(message)
                                        self.hide_progress()
                                        self.cannotImportArea.show()
                                        self.cannotImportLabel.setText(message)
                                        return

                                    # add media files to od_file with reference to damage
                                    for mf in media[k]:
                                        of = QgsFeature()
                                        init_fields = file_layer.fields()
                                        of.setFields(init_fields)
                                        of.initAttributes(init_fields.size())
                                        of["obj_id"] = file_layer.dataProvider().defaultValue(
                                            file_layer.fields().indexFromName("obj_id")
                                        )
                                        of["class"] = 3871  # i.e. damage
                                        of["kind"] = (
                                            3772 if mf[0] == "picture" else 3775
                                        )  # i.e. video
                                        of["object"] = damage["obj_id"]
                                        of["identifier"] = mf[1]
                                        sep = os.path.sep
                                        if mf[0] == "picture":
                                            of["path_relative"] = (
                                                self.data_path_line_edit.text()
                                                + f"{sep}Picture{sep}Sec"
                                            )
                                        elif mf[0] == "video":
                                            of["path_relative"] = (
                                                self.data_path_line_edit.text()
                                                + f"{sep}Video{sep}Sec"
                                            )
                                        else:
                                            logger.error(
                                                f"unknown media type {mf[0]} for file {mf[1]}"
                                            )
                                            continue
                                        ok = file_layer.addFeature(of)

                                        if ok:
                                            logger.debug(
                                                "adding media to file layer (fid: {}): ok".format(
                                                    of["obj_id"]
                                                )
                                            )
                                        else:
                                            _fields = ""
                                            for name, value in zip(
                                                file_layer.fields().names(), of.attributes()
                                            ):
                                                _fields += f"{name}: {value}\n"
                                            message = (
                                                self.tr(
                                                    f"error adding media to file layer (fid: {of['obj_id']}): error. "
                                                )
                                                + f"{_fields}"
                                            )
                                            logger.error(message)
                                            self.hide_progress()
                                            self.cannotImportArea.show()
                                            self.cannotImportLabel.setText(message)
                                            return

                                # write in relation table (wastewater structure - maintenance events)
                                jf = QgsFeature()
                                init_fields = join_layer.fields()
                                jf.setFields(init_fields)
                                jf.initAttributes(init_fields.size())
                                jf["obj_id"] = join_layer.dataProvider().defaultValue(
                                    join_layer.fields().indexFromName("obj_id")
                                )
                                jf["fk_wastewater_structure"] = ws_obj_id
                                jf["fk_maintenance_event"] = maintenance["obj_id"]
                                ok = join_layer.addFeature(jf)
                                if ok:
                                    logger.debug(
                                        "adding feature to join layer (fid: {}): ok".format(
                                            jf["obj_id"]
                                        )
                                    )
                                else:
                                    _fields = ""
                                    for name, value in zip(
                                        join_layer.fields().names(), jf.attributes()
                                    ):
                                        _fields += f"{name}: {value}\n"
                                    message = (
                                        self.tr(
                                            f"error adding feature to join layer (fid: {jf['obj_id']}): error. "
                                        )
                                        + f"{_fields}"
                                    )
                                    logger.error(message)
                                    self.hide_progress()
                                    self.cannotImportArea.show()
                                    self.cannotImportLabel.setText(message)
                                    return

                                # get current reach
                                rf = QgsFeature()
                                layer_id = Settings().wastewater_structure_layer.value()
                                wsl = QgsProject.instance().mapLayer(layer_id)
                                if wsl is not None:
                                    request = QgsFeatureRequest().setFilterExpression(
                                        "\"obj_id\" = '{}'".format(ws_obj_id)
                                    )
                                    rf = next(wsl.getFeatures(request))
                                if rf.isValid():
                                    # update structure condition if worse
                                    old_level = structure_condition_2_damage_level(
                                        rf["structure_condition"]
                                    )
                                    if old_level is None or old_level > "Z{}".format(
                                        structure_condition
                                    ):
                                        rf["structure_condition"] = (
                                            damage_level_2_structure_condition(structure_condition)
                                        )
                                        wsl.updateFeature(rf)

                                i += 1
                                self.progressBar.setValue(i)
                                QCoreApplication.processEvents()

        except InterruptedError:
            self.progressBar.hide()
            self.cancelButton.hide()
            self.importButton.show()
            return

        self.progressBar.hide()
        self.cancelButton.hide()
        self.importButton.show()

    def hide_progress(self):
        self.progressBar.hide()
        self.cancelButton.hide()
        self.importButton.show()
