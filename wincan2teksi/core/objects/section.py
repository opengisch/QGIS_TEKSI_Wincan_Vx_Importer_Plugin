from .inspection import Inspection


class Section:
    def __init__(
        self,
        pk: str,
        name: str,
        project_pk: str,
        section_length: float = None,
        section_size: float = None,
        flow_direction: int = None,
        from_node: str = None,
        to_node: str = None,
        address: str = None,
        import_: bool = True,
        counter: int = None,
    ):
        self.pk = pk
        self.name = name
        self.project_pk = project_pk
        self.inspections = {}
        self.import_ = import_

        self.teksi_channel_id_1 = None
        self.teksi_channel_id_2 = None
        self.teksi_channel_id_3 = None
        self.use_previous_section = False

        self.section_length = section_length
        self.section_size = section_size
        self.flow_direction = flow_direction
        self.from_node = from_node
        self.to_node = to_node
        self.original_from_node = from_node
        self.original_to_node = to_node
        self.address = address

        self.counter = counter
        self.pdf_page = None

        # TODO: Check if these are missing
        self.section_use = None
        self.pipe_material = None
        self.profile = None
        self.pipe_diameter = None
        self.pipe_width = None

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            pk=data["OBJ_PK"],
            name=data["OBJ_Key"],
            project_pk=data["OBJ_Project_FK"],
            section_length=data["OBJ_Length"],
            section_size=data["OBJ_Size1"],
            flow_direction=data["OBJ_FlowDir"],
            from_node=data["OBJ_FromNode_REF"],
            to_node=data["OBJ_ToNode_REF"],
            address=f"{data['OBJ_City']} {data['OBJ_Street']}",
            counter=data["OBJ_SortOrder"],
        )

    def add_inspection(self, inspection: "Inspection"):
        self.inspections[inspection.pk] = inspection
