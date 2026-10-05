from qgis.PyQt.QtCore import QDateTime

from .observation import Observation


class Inspection:
    def __init__(
        self,
        pk: str,
        name: str,
        section_pk: str,
        type: str = None,
        direction: int = 1,
        inspection_length: float = None,
        highest_grade: int = None,
        start_date: QDateTime = None,
        method: str = None,
        operator: str = None,
        import_: bool = True,
    ):
        self.pk = pk
        self.name = name
        self.section_pk = section_pk
        self.type = type
        self.direction = direction
        self.inspection_length = inspection_length
        self.highest_grade = highest_grade
        self.start_date = start_date
        self.method = method
        self.operator = operator
        self.import_ = import_
        self.observations = {}

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            pk=data["INS_PK"],
            name=data["INS_Key"],
            section_pk=data["INS_Section_FK"],
            type=data["INS_Type"],
            direction=data["INS_InspectionDir"],
            inspection_length=data["INS_InspectedLength"],
            highest_grade=data["INS_HighestGrade"],
            start_date=QDateTime.fromString(data["INS_StartDate"][:23], "yyyy-MM-dd HH:mm:ss.zzz"),
            method=data["INS_Method"],
            operator=data["INS_Operator_REF"],
        )

    def add_observation(self, observation: "Observation"):
        if observation.inspection_pk != self.pk:
            raise ValueError(
                f"Observation {observation.pk} does not belong to inspection {self.pk}"
            )
        self.observations[observation.pk] = observation
