#!/usr/bin/env python
# coding: utf-8 -*-
# ...existing code...
from pathlib import Path
import re
import sqlite3

from wincan2teksi.core.objects import Project, Section, Inspection, Observation
from wincan2teksi.core.exceptions import InvalidProjectFile

import logging

logger = logging.getLogger(__name__)

# codes which should not be imported by default
SkipCode = "BCD"


class WinCanData:
    def __init__(self):
        self.file = None
        self.meta_file = None
        self.pdf_file = None
        self.projects = {}


ALLOWED_TABLES = frozenset(
    {"PROJECT", "SECTION", "NODE", "SECINSP", "SECOBS", "SECOBSMM", "OPERATOR"}
)


def __read_table(
    cursor: sqlite3.Cursor,
    table_name: str,
    conditions: dict = None,
    extra_condition: str = None,
):
    """Reads a table from the SQLite database and returns a list of dictionaries.
    Each dictionary represents a row in the table with column names as keys.

    Args:
        cursor: SQLite cursor.
        table_name: Name of the table (must be in ALLOWED_TABLES).
        conditions: Dict of {column_name: value} for WHERE clause with parameterized queries.
        extra_condition: Additional raw SQL condition with no user-supplied values (e.g. "X IS NULL").
    """
    if table_name not in ALLOWED_TABLES:
        raise ValueError(f"Table name '{table_name}' is not allowed.")

    query = f"SELECT * FROM {table_name}"
    params = []
    where_parts = []

    if conditions:
        for col, val in conditions.items():
            where_parts.append(f"{col} = ?")
            params.append(val)

    if extra_condition:
        where_parts.append(extra_condition)

    if where_parts:
        query += " WHERE " + " AND ".join(where_parts)

    cursor.execute(query, params)
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    return [dict(zip(columns, row)) for row in rows]


def read_data(file: str) -> WinCanData:
    """Reads data from a Wincan SQLite database file and returns a dictionary of projects."""
    if not Path(file).exists():
        raise FileNotFoundError(f"File {file} does not exist.")

    logger.info(f"Reading Wincan database: {file}")

    data = WinCanData()
    data.file = file

    file_path = Path(file)

    meta_path = file_path.with_name(file_path.stem + "_meta" + file_path.suffix)
    operators = {}
    if not meta_path.exists():
        logger.warning(f"Meta file {meta_path} does not exist.")
    else:
        data.meta_file = str(meta_path)
        with sqlite3.connect(meta_path) as meta_conn:
            meta_cursor = meta_conn.cursor()
            logger.info(f"Read meta file: {meta_path}")
            operators = __read_table(meta_cursor, "OPERATOR")

    conn = sqlite3.connect(file_path)
    try:
        cursor = conn.cursor()

        pdf_path = file_path.parent.parent / "Misc" / "Docu" / (file_path.stem + ".pdf")
        if not pdf_path.exists():
            logger.warning(f"PDF file {pdf_path} does not exist.")
        else:
            data.pdf_file = str(pdf_path)

        try:
            project_data = __read_table(cursor, "PROJECT", extra_condition="PRJ_Deleted IS NULL")
        except sqlite3.OperationalError as e:
            raise InvalidProjectFile(f"Invalid project file: {file_path}") from e

        projects = [Project.from_dict(data) for data in project_data]

        for project in projects:
            logger.info(f"Processing project: {project.name} (PK: {project.pk})")
            sections = __read_table(
                cursor,
                "SECTION",
                conditions={"OBJ_Project_FK": project.pk},
                extra_condition="OBJ_Deleted IS NULL",
            )
            for section_data in sections:
                section = Section.from_dict(section_data)
                from_nodes = __read_table(
                    cursor,
                    "NODE",
                    conditions={"OBJ_PK": section.from_node},
                    extra_condition="OBJ_Deleted IS NULL",
                )
                to_nodes = __read_table(
                    cursor,
                    "NODE",
                    conditions={"OBJ_PK": section.to_node},
                    extra_condition="OBJ_Deleted IS NULL",
                )
                if not from_nodes or not to_nodes:
                    logger.warning(
                        f"Missing node data for section {section.name} (PK: {section.pk}), skipping"
                    )
                    continue
                section.from_node = from_nodes[0]["OBJ_Key"]
                section.to_node = to_nodes[0]["OBJ_Key"]
                section.original_from_node = section.from_node
                section.original_to_node = section.to_node

                logger.debug(
                    f"Found section: {section.name} (PK: {section.pk}) in project {project.name}"
                )

                inspections = __read_table(
                    cursor,
                    "SECINSP",
                    conditions={"INS_Section_FK": section.pk},
                    extra_condition="INS_Deleted IS NULL",
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
                        conditions={"OBS_Inspection_FK": inspection.pk},
                        extra_condition="OBS_Deleted IS NULL",
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
                            conditions={"OMM_Observation_FK": observation.pk},
                            extra_condition="OMM_Deleted IS NULL",
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
        logger.info(f"Loaded {len(data.projects)} project(s) from {file}")

        if data.pdf_file:
            _parse_pdf_pages(data.pdf_file, data.projects)

        return data
    finally:
        conn.close()


def _parse_pdf_pages(pdf_path: str, projects: dict) -> None:
    """Parse the PDF report's table of contents to determine the starting
    page number for each section, and store it on the Section objects."""
    try:
        import pypdf
    except ImportError:
        logger.warning(
            "pypdf is not installed — PDF page numbers will not be available. "
            "Install it with: pip install pypdf"
        )
        return

    try:
        reader = pypdf.PdfReader(pdf_path)
    except Exception as e:
        logger.warning(f"Could not read PDF {pdf_path}: {e}")
        return

    # Step 1: Extract TOC text from initial pages
    toc_text = ""
    for page_idx in range(min(len(reader.pages), 30)):
        text = reader.pages[page_idx].extract_text() or ""
        if "Table des matières" in text or re.search(r"Page\s+[A-Z]-\d+", text):
            toc_text += text + "\n"
        else:
            break

    if not toc_text:
        logger.warning("Could not find table of contents in PDF")
        return

    # Step 2: Parse section entries from TOC
    # Format: "Section: N; from - to  ...dots...  PAGE" possibly split across two lines
    toc_entries = {}
    matches = re.findall(
        r"Section:\s*(\d+);[^\n]+\n[^\d\n]*(\d+)\s*$",
        toc_text,
        re.MULTILINE,
    )
    if not matches:
        # Try single-line format
        matches = re.findall(
            r"Section:\s*(\d+);.*?(\d+)\s*$",
            toc_text,
            re.MULTILINE,
        )
    for counter_str, page_str in matches:
        toc_entries[int(counter_str)] = int(page_str)

    if not toc_entries:
        logger.warning("Could not parse section entries from PDF table of contents")
        return

    # Step 3: Determine page offset
    # Find the first content page (not TOC/legend) and its internal page number
    offset = None
    for page_idx in range(min(len(reader.pages), 30)):
        text = reader.pages[page_idx].extract_text() or ""
        if "Table des matières" in text:
            continue
        if re.search(r"Page\s+[A-Z]-\d+", text):
            continue
        m = re.search(r"\bPage\s+(\d+)\b", text)
        if m:
            internal_page = int(m.group(1))
            offset = (page_idx + 1) - internal_page
            break

    if offset is None:
        logger.warning("Could not determine PDF page offset")
        return

    logger.info(f"PDF page offset: {offset}, found {len(toc_entries)} section entries in TOC")

    # Step 4: Assign page numbers to sections
    matched = 0
    unmatched = []
    for project in projects.values():
        for section in project.sections.values():
            if section.counter in toc_entries:
                section.pdf_page = toc_entries[section.counter] + offset
                matched += 1
                logger.debug(
                    f"Section {section.name} (counter={section.counter}): "
                    f"PDF page {section.pdf_page}"
                )
            else:
                unmatched.append(section.name)
                logger.warning(
                    f"Section {section.name} (counter={section.counter}): "
                    f"no matching entry in PDF table of contents"
                )
    if unmatched:
        logger.warning(
            f"{len(unmatched)} section(s) could not be matched to a PDF page: "
            f"{', '.join(unmatched)}"
        )
    logger.info(f"PDF page matching: {matched} matched, {len(unmatched)} unmatched")
