from pydantic import BaseModel


class DoctorProfileOut(BaseModel):
    name: str
    specialty: str
    qualifications: str
    experienceYears: int
    clinicAddress: str
    about: str
    photoUrl: str
    keywords: list[str] = []


class DoctorProfileIn(BaseModel):
    clinicAddress: str | None = None
    about: str | None = None
    qualifications: str | None = None
    experienceYears: int | None = None
    keywords: list[str] | None = None
