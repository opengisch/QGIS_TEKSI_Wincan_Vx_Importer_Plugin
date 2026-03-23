# encoding: utf-8
#
# -----------------------------------------------------------
#
# QGIS wincan 2 TEKSI Plugin
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

import json
import os

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QVBoxLayout,
)

from qgis.core import QgsFeatureRequest, QgsProject

import logging

from wincan2teksi.core.layer_edit import edit
from wincan2teksi.core.settings import Settings

logger = logging.getLogger(__name__)

# Deletion order: dependents first, then parents.
# file_layer entries reference damage/maintenance via "object" field,
# join_layer references maintenance, damage references maintenance.
DELETION_ORDER = [
    "file_layer",
    "join_maintence_wastewaterstructure_layer",
    "damage_layer",
    "maintenance_layer",
]


class UndoImportDialog(QDialog):
    def __init__(self, log_dir, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Undo Import"))
        self.resize(500, 350)
        self.log_dir = log_dir

        layout = QVBoxLayout(self)
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        button_box = QDialogButtonBox()
        self.delete_button = button_box.addButton(
            self.tr("Delete selected import"), QDialogButtonBox.ButtonRole.DestructiveRole
        )
        self.delete_button.setEnabled(False)
        button_box.addButton(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        self.delete_button.clicked.connect(self._on_delete)
        layout.addWidget(button_box)

        self.list_widget.currentItemChanged.connect(self._on_selection_changed)

        self._load_logs()

    def _load_logs(self):
        self.list_widget.clear()
        if not os.path.isdir(self.log_dir):
            return
        files = sorted(
            (f for f in os.listdir(self.log_dir) if f.endswith(".json")),
            reverse=True,
        )
        for filename in files:
            filepath = os.path.join(self.log_dir, filename)
            try:
                with open(filepath) as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError):
                continue

            project = data.get("project", "")
            timestamp = data.get("timestamp", "?")
            user = data.get("user", "")
            features = data.get("features", {})
            total = sum(len(v.get("obj_ids", [])) for v in features.values())
            label = ""
            if project:
                label += f"{project} — "
            label += f"{timestamp}"
            if user:
                label += f" — {user}"
            label += f" ({total} features)"

            # Build tooltip with per-layer counts
            tooltip_lines = []
            for layer_name, layer_data in features.items():
                count = len(layer_data.get("obj_ids", []))
                tooltip_lines.append(f"{layer_name}: {count}")
            tooltip = "\n".join(tooltip_lines)

            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, filepath)
            item.setToolTip(tooltip)
            self.list_widget.addItem(item)

    def _on_selection_changed(self, current, _previous):
        self.delete_button.setEnabled(current is not None)

    def _on_delete(self):
        item = self.list_widget.currentItem()
        if item is None:
            return

        filepath = item.data(Qt.ItemDataRole.UserRole)
        try:
            with open(filepath) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            QMessageBox.critical(self, self.tr("Error"), str(e))
            return

        features = data.get("features", {})
        total = sum(len(v.get("obj_ids", [])) for v in features.values())

        reply = QMessageBox.warning(
            self,
            self.tr("Confirm deletion"),
            self.tr(
                "This will permanently delete {n} features from the database.\n\nAre you sure?"
            ).format(n=total),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        logger.info(f"Starting undo: deleting {total} features")

        try:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            self._delete_features(features)
        except Exception as e:
            QMessageBox.critical(
                self, self.tr("Deletion failed"), self.tr("Error during deletion:\n{e}").format(e=e)
            )
            return
        finally:
            QApplication.restoreOverrideCursor()

        # Remove log file after successful deletion
        try:
            os.remove(filepath)
        except OSError:
            pass

        logger.info(f"Undo completed: deleted {total} features")

        QMessageBox.information(
            self,
            self.tr("Import undone"),
            self.tr("Successfully deleted {n} features.").format(n=total),
        )
        self._load_logs()

    def _delete_features(self, features):
        settings = Settings()

        # Map setting key → layer id
        setting_to_layer_id = {
            "file_layer": settings.file_layer.value(),
            "join_maintence_wastewaterstructure_layer": settings.join_maintence_wastewaterstructure_layer.value(),
            "damage_layer": settings.damage_layer.value(),
            "maintenance_layer": settings.maintenance_layer.value(),
        }

        # Build layer_id → list of obj_ids from the log
        layer_id_to_obj_ids = {}
        for _layer_name, layer_data in features.items():
            layer_id = layer_data.get("layer_id")
            obj_ids = layer_data.get("obj_ids", [])
            if layer_id and obj_ids:
                layer_id_to_obj_ids[layer_id] = obj_ids

        # Determine ordered list of (layer, obj_ids) for deletion
        deletion_plan = []
        for setting_key in DELETION_ORDER:
            layer_id = setting_to_layer_id.get(setting_key)
            if layer_id and layer_id in layer_id_to_obj_ids:
                layer = QgsProject.instance().mapLayer(layer_id)
                if layer is None:
                    raise RuntimeError(
                        self.tr("Layer '{layer_id}' not found in project").format(layer_id=layer_id)
                    )
                deletion_plan.append((layer, layer_id_to_obj_ids.pop(layer_id)))

        # Any remaining layers not in the known order (shouldn't happen, but be safe)
        for layer_id, obj_ids in layer_id_to_obj_ids.items():
            layer = QgsProject.instance().mapLayer(layer_id)
            if layer is not None:
                deletion_plan.append((layer, obj_ids))

        # Execute deletion within nested edit sessions
        # We need all layers in edit mode simultaneously so we nest them
        self._delete_nested(deletion_plan, 0)

    def _delete_nested(self, plan, index):
        if index >= len(plan):
            return
        layer, obj_ids = plan[index]
        with edit(layer):
            # Open remaining layers first (deepest nesting = last layer)
            self._delete_nested(plan, index + 1)
            # Now delete features from this layer
            for obj_id in obj_ids:
                request = QgsFeatureRequest().setFilterExpression(
                    "\"obj_id\" = '{}'".format(obj_id.replace("'", "''"))
                )
                for feature in layer.getFeatures(request):
                    if not layer.deleteFeature(feature.id()):
                        raise RuntimeError(
                            self.tr("Failed to delete feature {obj_id} from {layer}").format(
                                obj_id=obj_id, layer=layer.name()
                            )
                        )
                    logger.debug(f"Deleted feature {obj_id} from {layer.name()}")
