from typing import Literal

from pydantic import BaseModel

Acuity = Literal["ROUTINE", "PRIORITY", "URGENT", "EMERGENCY"]
Sex = Literal["M", "F", "O"]
LabFlag = Literal["L", "N", "H"]


class LabValueOut(BaseModel):
    analyte: str
    value: float
    unit: str
    refRange: str
    flag: LabFlag


class SpecialtyScore(BaseModel):
    name: str
    score: float


class Driver(BaseModel):
    feature: str
    contribution: float


class TriageInput(BaseModel):
    symptomText: str
    reportImageUris: list[str] = []
    age: int | None = None
    sex: Sex | None = None
    lang: Literal["en", "hi", "mr"] = "en"


class TriageResultOut(BaseModel):
    acuity: Acuity
    acuityConfidence: float
    specialties: list[SpecialtyScore]
    drivers: list[Driver]
    labs: list[LabValueOut]
    redFlags: list[str]
    modelVersion: str

    @classmethod
    def from_model(cls, tr) -> "TriageResultOut":
        return cls(
            acuity=tr.acuity.value,
            acuityConfidence=tr.acuity_confidence,
            specialties=tr.specialties or [],
            drivers=tr.drivers or [],
            labs=tr.labs or [],
            redFlags=tr.red_flags or [],
            modelVersion=tr.model_version,
        )
