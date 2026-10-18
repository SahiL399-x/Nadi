from typing import Literal

from pydantic import BaseModel


class PharmacyOut(BaseModel):
    id: str
    name: str
    distanceKm: float
    deliversInMins: int
    isOpen: bool


class OfferOut(BaseModel):
    id: str
    prescriptionId: str
    patientName: str
    status: Literal["PENDING", "ACCEPTED", "DECLINED"]
    lines: list[dict]
