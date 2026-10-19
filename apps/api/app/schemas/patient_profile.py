from pydantic import BaseModel


class VisitOut(BaseModel):
    visitedAt: str
    summary: str
    status: str


class PatientProfileOut(BaseModel):
    name: str
    age: int
    sex: str
    conditions: list[str]
    allergies: list[str]
    familyHistory: list[str]
    noKnownAllergies: bool
    latestVisit: VisitOut | None
    visits: list[VisitOut]
    prescriptions: list[str]  # drug summaries
