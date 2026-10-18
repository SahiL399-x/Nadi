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
