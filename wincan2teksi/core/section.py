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

from qgis.core import QgsProject, QgsFeature, QgsFeatureRequest

from wincan2teksi.core.exceptions import W2TLayerNotFound
from wincan2teksi.core.settings import Settings

from wincan2teksi.core.utils import logger


def find_section(channel, start_node, end_node):
    logger.debug(
        f"Finding section for channel {channel}, start node {start_node}, end node {end_node}"
    )
    feature = QgsFeature()

    layerid = Settings().channel_layer.value()
    layer = QgsProject.instance().mapLayer(layerid)
    if layer is None:
        raise W2TLayerNotFound(
            f"Channel layer with ID {layerid} not found in the current QGIS project."
        )

    if channel:
        request_text = f"\"rp_from_identifier\" LIKE '{channel}-{start_node}%' and \"rp_to_identifier\" LIKE '{channel}-{end_node}%'"
    else:
        request_text = f"\"rp_from_identifier\" LIKE '{start_node}%' and \"rp_to_identifier\" LIKE '{end_node}%'"

    request = QgsFeatureRequest().setFilterExpression(request_text)
    feature = next(layer.getFeatures(request), QgsFeature())
    if feature.isValid():
        logger.debug(f"Found section: {feature.attribute('obj_id')} for {start_node} → {end_node}")
    else:
        logger.debug(f"No section found for {start_node} → {end_node}")
    return feature


def section_at_id(obj_id):
    feature = QgsFeature()
    if obj_id is not None:
        layer_id = Settings().channel_layer.value()
        layer = QgsProject.instance().mapLayer(layer_id)
        if layer is None:
            raise W2TLayerNotFound(
                f"Channel layer with ID {layer_id} not found in the current QGIS project."
            )
        request = QgsFeatureRequest().setFilterExpression("\"obj_id\" = '{}'".format(obj_id))
        feature = next(layer.getFeatures(request), QgsFeature())
    return feature
