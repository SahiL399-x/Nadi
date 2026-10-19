from pydantic import BaseModel


class DoctorProfileOut(BaseModel):
    name: str
    specialty: str
    qualifications: str
    experienceYears: int
    clinicAddress: str
    about: str
    photoUrl: str


class DoctorProfileIn(BaseModel):
    clinicAddress: str | None = None
    about: str | None = None
