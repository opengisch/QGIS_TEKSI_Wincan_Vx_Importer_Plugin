from pathlib import Path

from qgis.PyQt.QtCore import QDateTime

from .section import Section


class Project:
    def __init__(self, pk: str, name: str, date: QDateTime, root_path: Path = None):
        self.pk = pk
        self.name = name
        self.date = date
        self.root_path = root_path
        self.channel = None
        self.sections = {}

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            pk=data["PRJ_PK"],
            name=data["PRJ_Key"],
            date=QDateTime.fromString(data["PRJ_Date"], "yyyy-MM-dd HH:mm:ss"),
        )

    def add_section(self, section: "Section"):
        if section.project_pk != self.pk:
            raise ValueError(f"Section {section.pk} does not belong to project {self.pk}")
        self.sections[section.pk] = section
