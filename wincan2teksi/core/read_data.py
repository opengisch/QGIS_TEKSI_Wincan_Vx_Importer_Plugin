#!/usr/bin/env python
# coding: utf-8 -*-
# ...existing code...
from pathlib import Path
import sqlite3

from wincan2teksi.core.objects import Project, Section, Inspection, Observation
from wincan2teksi.core.exceptions import InvalidProjectFile
from wincan2teksi.core.utils import logger

# codes which should not be imported by default
SkipCode = "BCD"


class WinCanData:
    def __init__(self):
        self.file = None
        self.meta_file = None
        self.pdf_file = None
        self.projects = {}


def __read_table(cursor: sqlite3.Cursor, table_name: str, where_clause: str = None):
    """Reads a table from the SQLite database and returns a list of dictionaries.
    Each dictionary represents a row in the table with column names as keys.
    """
    if where_clause:
        cursor.execute(f"SELECT * FROM {table_name} WHERE {where_clause}")
    else:
        cursor.execute(f"SELECT * FROM {table_name}")
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    return [dict(zip(columns, row)) for row in rows]


def read_data(file: str) -> WinCanData:
    """Reads data from a Wincan SQLite database file and returns a dictionary of projects."""
    if not Path(file).exists():
        raise FileNotFoundError(f"File {file} does not exist.")

    data = WinCanData()
    data.file = file

    file_path = Path(file)

    meta_path = file_path.with_name(file_path.stem + "_meta" + file_path.suffix)
    operators = {}
    if not meta_path.exists():
        logger.warning(f"Meta file {meta_path} does not exist.")
    else:
        data.meta_file = str(meta_path)
        conn = sqlite3.connect(meta_path)
        cursor = conn.cursor()
        logger.info(f"Read meta file: {meta_path}")
        operators = __read_table(cursor, "OPERATOR")

    conn = sqlite3.connect(file_path)
    cursor = conn.cursor()

    pdf_path = file_path.parent.parent / "Misc" / "Docu" / (file_path.stem + ".pdf")
    if not pdf_path.exists():
        logger.warning(f"PDF file {pdf_path} does not exist.")
    else:
        data.pdf_file = str(pdf_path)

    try:
        project_data = __read_table(cursor, "PROJECT", "PRJ_Deleted IS NULL")
    except sqlite3.OperationalError as e:
        raise InvalidProjectFile(f"Invalid project file: {file_path}") from e

    projects = [Project.from_dict(data) for data in project_data]

    for project in projects:
        logger.info(f"Processing project: {project.name} (PK: {project.pk})")
        sections = __read_table(
            cursor, "SECTION", f"OBJ_Project_FK = '{project.pk}' AND OBJ_Deleted IS NULL"
        )
        for section_data in sections:
            section = Section.from_dict(section_data)
            section.from_node = __read_table(
                cursor, "NODE", f"OBJ_PK = '{section.from_node}' AND OBJ_Deleted IS NULL"
            )[0]["OBJ_Key"]
            section.to_node = __read_table(
                cursor, "NODE", f"OBJ_PK = '{section.to_node}' AND OBJ_Deleted IS NULL"
            )[0]["OBJ_Key"]

            logger.debug(
                f"Found section: {section.name} (PK: {section.pk}) in project {project.name}"
            )

            inspections = __read_table(
                cursor, "SECINSP", f"INS_Section_FK = '{section.pk}' AND INS_Deleted IS NULL"
            )
            if not inspections:
                logger.warning(
                    f"No inspections found for section {section.name} (PK: {section.pk}) in project {project.name}"
                )
                continue
            for inspection_data in inspections:
                inspection = Inspection.from_dict(inspection_data)
                logger.debug(
                    f"Found inspection: {inspection.name} (PK: {inspection.pk}) in section {section.name}"
                )
                if operators:
                    for operator in operators:
                        if operator["OP_PK"] == inspection.operator:
                            # using OP_Key as OP_Name1 seems to be wrongly filled in AITV data
                            inspection.operator = operator["OP_Key"]

                observations = __read_table(
                    cursor,
                    "SECOBS",
                    f"OBS_Inspection_FK = '{inspection.pk}' AND OBS_Deleted IS NULL",
                )
                if not observations:
                    logger.warning(
                        f"No observations found for inspection {inspection.name} (PK: {inspection.pk}) in section {section.name}"
                    )
                    continue
                for observation_data in observations:
                    observation = Observation.from_dict(observation_data)
                    logger.debug(
                        f"Found observation in inspection {inspection.name} (PK: {inspection.pk})"
                    )
                    mmfiles = __read_table(
                        cursor,
                        "SECOBSMM",
                        f"OMM_Observation_FK = '{observation.pk}' AND OMM_Deleted IS NULL",
                    )
                    for mmfile in mmfiles:
                        if mmfile["OMM_Type"] in ("PI1", "PI2"):
                            observation.mmfiles.append(("picture", mmfile["OMM_FileName"]))
                        else:
                            observation.mmfiles.append(("video", mmfile["OMM_FileName"]))
                    inspection.add_observation(observation)
                section.add_inspection(inspection)
            project.add_section(section)
        logger.info(f"Found {len(project.sections)} sections in project {project.name}")

    data.projects = {project.pk: project for project in projects}
    return data
