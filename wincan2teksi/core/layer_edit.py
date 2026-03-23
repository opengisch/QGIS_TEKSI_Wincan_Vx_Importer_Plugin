# encoding: utf-8
#
# #-----------------------------------------------------------
#
# QGIS wincan 2 QGEP Plugin
# Copyright (C) 2019 Denis Rouzaud
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

from qgis.core import QgsEditError

from wincan2teksi.core.utils import logger


class edit(object):
    """
    This is a modification of qgis.core.edit
    It can be used both in transaction and standard mode
    """

    def __init__(self, layer):
        self.layer = layer

    def __enter__(self):
        # allow combination of nested `with edit(layer)`
        # startEditing returns false in case of transaction groups
        if not self.layer.isEditable():
            logger.debug("making {} editable".format(self.layer.id()))
            assert self.layer.startEditing()
        return self.layer

    def __exit__(self, ex_type, ex_value, traceback):
        logger.debug(
            "exiting edit for layer {}: is editable: {} excep: {}({})".format(
                self.layer.id(), self.layer.isEditable(), ex_type, ex_value
            )
        )
        if ex_type is None:
            # allow combination of nested `with edit(layer)`
            # in case of transaction groups, commit might have been achieved before
            if self.layer.isEditable():
                logger.debug("committing changes")
                if not self.layer.commitChanges():
                    raise QgsEditError(self.layer.commitErrors())
            return True
        else:
            self.layer.rollBack()
            return False
