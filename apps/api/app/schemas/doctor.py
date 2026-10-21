from pydantic import BaseModel


class DoctorOut(BaseModel):
    id: str
    name: str
    specialty: str
    qualifications: str
    experienceYears: int
    distanceKm: float
    lat: float
    lng: float
    feeInr: int
    rating: float
    reviewCount: int
    languages: list[str]
    nextSlot: str
    photoUrl: str
    availableSlots: list[str]
