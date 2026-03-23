def _format_obs_value(quantity, unit):
    parts = [str(v) for v in (quantity, unit) if v is not None]
    return " ".join(parts) if parts else None


class Observation:
    def __init__(
        self,
        pk: str,
        inspection_pk: str,
        distance: float,
        code: str = None,
        text: str = None,
        time: str = None,
        clock_position_1: str = None,
        clock_position_2: str = None,
        obs_value_1: str = None,
        obs_value_2: str = None,
        obs_value_3: str = None,
        rate: int = None,
        memo: str = None,
    ):
        self.pk = pk
        self.inspection_pk = inspection_pk
        self.distance = distance
        self.code = code
        self.text = text
        self.time = time
        self.clock_position_1 = clock_position_1
        self.clock_position_2 = clock_position_2
        self.obs_value_1 = obs_value_1
        self.obs_value_2 = obs_value_2
        self.obs_value_3 = obs_value_3
        self.rate = rate
        self.memo = memo
        self.mmfiles = []
        self.mpeg_position = None  # TODO
        self.import_ = True
        self.force_import = False

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            pk=data["OBS_PK"],
            inspection_pk=data["OBS_Inspection_FK"],
            distance=data["OBS_Distance"],
            code=data["OBS_OpCode"],
            text=data["OBS_Observation"],
            time=data["OBS_TimeCtr"],
            clock_position_1=data["OBS_ClockPos1"],
            clock_position_2=data["OBS_ClockPos2"],
            obs_value_1=_format_obs_value(data["OBS_Q1_Value"], data["OBS_U1_Value"]),
            obs_value_2=_format_obs_value(data["OBS_Q2_Value"], data["OBS_U2_Value"]),
            obs_value_3=_format_obs_value(data["OBS_Q3_Value"], data["OBS_U3_Value"]),
            rate=data["OBS_RateValue"],
            memo=data["OBS_Memo"],
        )
