# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Copyright (C) 2019 Denis Rouzaud
 ***************************************************************************/
/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

from qgis.PyQt.QtCore import QObject, pyqtSignal
import logging
from logging import LogRecord

PLUGIN_LOGGER_NAME = "wincan2teksi"


class LoggingBridge(logging.Handler, QObject):
    loggedLine = pyqtSignal(LogRecord, str)

    def __init__(self, level=logging.NOTSET, excluded_modules=None):
        QObject.__init__(self)
        logging.Handler.__init__(self, level)
        self.formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
        self.excluded_modules = excluded_modules or []

    def filter(self, record):
        return record.name not in self.excluded_modules

    def emit(self, record):
        log_entry = self.format(record)
        self.loggedLine.emit(record, log_entry)
