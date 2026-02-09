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


from qgis.core import (
    QgsSettingsTree,
    QgsSettingsEntryBool,
    QgsSettingsEntryString,
    QgsSettingsEntryDouble,
)

PLUGIN_NAME = "wincan2teksi"


class Settings:
    instance = None

    def __new__(cls) -> "Settings":
        if cls.instance is None:
            cls.instance = super(Settings, cls).__new__(cls)

            settings_node = QgsSettingsTree.createPluginTreeNode(pluginName=PLUGIN_NAME)

            cls.remove_trailing_chars = QgsSettingsEntryBool(
                "remove_trailing_chars", settings_node, False
            )
            cls.tolerance_channel_length = QgsSettingsEntryDouble(
                "tolerance_channel_length", settings_node, 1
            )

            cls.wastewater_structure_layer = QgsSettingsEntryString(
                "wastewater_structure_layer", settings_node, "od_wastewater_structure"
            )

            cls.join_maintence_wastewaterstructure_layer = QgsSettingsEntryString(
                "join_maintence_wastewaterstructure_layer",
                settings_node,
                "re_maintenance_event_wastewater_structure",
            )

            cls.channel_layer = QgsSettingsEntryString(
                "channel_layer", settings_node, "vw_qgep_reach"
            )
            cls.cover_layer = QgsSettingsEntryString(
                "cover_layer", settings_node, "vw_qgep_wastewater_structure"
            )
            cls.maintenance_layer = QgsSettingsEntryString(
                "maintenance_layer", settings_node, "vw_qgep_maintenance"
            )
            cls.damage_layer = QgsSettingsEntryString(
                "damage_layer", settings_node, "vw_qgep_damage"
            )
            cls.file_layer = QgsSettingsEntryString(
                "file_layer", settings_node, "od_file20160921105557083"
            )
            cls.organisation_layer = QgsSettingsEntryString(
                "organisation_layer", settings_node, "od_organisation20160212172933583"
            )

            cls.vl_damage_channel_layer = QgsSettingsEntryString(
                "vl_damage_channel_layer", settings_node, "vl_damage_channel_channel_damage_code"
            )
            cls.vl_damage_single_class = QgsSettingsEntryString(
                "vl_damage_single_class", settings_node, "vl_damage_single_damage_class"
            )
            cls.vl_wastewater_structure_structure_condition = QgsSettingsEntryString(
                "vl_wastewater_structure_structure_condition",
                settings_node,
                "vl_wastewater_structure_structure_condition",
            )

            cls.db3_path = QgsSettingsEntryString("db3_path", settings_node, "")

        return cls.instance
