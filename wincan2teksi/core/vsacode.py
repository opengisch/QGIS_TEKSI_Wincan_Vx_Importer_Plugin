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

from qgis.core import QgsProject, QgsFeature, QgsFeatureRequest, NULL

from wincan2teksi.core.settings import Settings
from wincan2teksi.core.exceptions import W2TLayerNotFound

CODE_PREMATCH = {
    "BAG": "BAGA",
}


def damage_code_to_vl(code: str) -> str:
    """
    return pkey of vl from VSA damage code
    """
    feature = QgsFeature()

    layer_id = Settings().vl_damage_channel_layer.value()
    layer = QgsProject.instance().mapLayer(layer_id)
    if layer is None:
        raise W2TLayerNotFound(
            f"Damage channel layer with ID {layer_id} not found in the current QGIS project."
        )
    code = CODE_PREMATCH.get(code, code)
    request_text = "\"value_en\" = '{}'".format(code)
    request = QgsFeatureRequest().setFilterExpression(request_text)
    feature = next(layer.getFeatures(request), QgsFeature())

    if feature.isValid():
        return feature["code"]
    else:
        return None


def damage_level_to_vl(code):
    """
    return pkey of vl from VSA damage level
    """
    feature = QgsFeature()

    layer_id = Settings().vl_damage_single_class.value()
    layer = QgsProject.instance().mapLayer(layer_id)
    if layer is None:
        raise W2TLayerNotFound(
            f"Damage single class layer with ID {layer_id} not found in the current QGIS project."
        )
    request_text = "\"value_en\" = 'EZ{}'".format(code)
    request = QgsFeatureRequest().setFilterExpression(request_text)
    feature = next(layer.getFeatures(request), QgsFeature())

    if feature.isValid():
        return feature["code"]
    else:
        return None


def damage_level_2_structure_condition(level):
    """
    return damage code to renovation necessity pkey
    """
    feature = QgsFeature()
    layer_id = Settings().vl_wastewater_structure_structure_condition.value()
    layer = QgsProject.instance().mapLayer(layer_id)
    if layer is None:
        raise W2TLayerNotFound(
            f"Wastewater structure condition layer with ID {layer_id} not found in the current QGIS project."
        )
    request_text = "\"value_en\" = 'Z{}'".format(level)
    request = QgsFeatureRequest().setFilterExpression(request_text)
    feature = next(layer.getFeatures(request), QgsFeature())

    if feature.isValid():
        return feature["code"]
    else:
        return None


def structure_condition_2_damage_level(code):
    """
    return damage code to renovation necessity pkey
    """
    layer_id = Settings().vl_wastewater_structure_structure_condition.value()
    layer = QgsProject.instance().mapLayer(layer_id)

    if layer is None:
        raise W2TLayerNotFound(
            f"Wastewater structure condition layer with ID {layer_id} not found in the current QGIS project."
        )

    if code == NULL or code is None:
        return None

    request_text = "\"code\" = '{}'".format(code)
    request = QgsFeatureRequest().setFilterExpression(request_text)
    feature = next(layer.getFeatures(request), QgsFeature())
    # print(request_text, feature.isValid())

    if feature.isValid():
        return feature["value_en"]
    else:
        return None
