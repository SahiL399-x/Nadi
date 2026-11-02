from typing import Literal

from pydantic import BaseModel

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


class TriageInput(BaseModel):
    symptomText: str
    reportImageUris: list[str] = []
    age: int | None = None
    sex: Sex | None = None
    lang: Literal["en", "hi", "mr"] = "en"


class TriageResultOut(BaseModel):
    specialties: list[SpecialtyScore]
    labs: list[LabValueOut]
    modelVersion: str

    @classmethod
    def from_model(cls, tr) -> "TriageResultOut":
        return cls(
            specialties=tr.specialties or [],
            labs=tr.labs or [],
            modelVersion=tr.model_version,
        )
