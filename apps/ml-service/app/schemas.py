from typing import Literal

from pydantic import BaseModel


class LabValue(BaseModel):
    analyte: str
    value: float
    unit: str
    refRange: str
    flag: Literal["L", "N", "H"]


class TriageRequest(BaseModel):
    symptomText: str
    labs: list[LabValue] = []
    age: int | None = None
    sex: Literal["M", "F", "O"] | None = None
    lang: Literal["en", "hi", "mr"] = "en"


class SymptomRequest(BaseModel):
    text: str
    lang: Literal["en", "hi", "mr"] = "en"


class DocumentRequest(BaseModel):
    objectKey: str
