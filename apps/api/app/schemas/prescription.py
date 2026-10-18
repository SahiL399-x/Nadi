from typing import Literal

from pydantic import BaseModel


class PrescriptionLineIn(BaseModel):
    drug: str
    strength: str
    frequency: str
    durationDays: int
    notes: str | None = None


class PrescriptionLineOut(PrescriptionLineIn):
    pass


class PrescribeIn(BaseModel):
    lines: list[PrescriptionLineIn]


class ReferIn(BaseModel):
    toSpecialty: str
    reason: str


class ConsentIn(BaseModel):
    pharmacyIds: list[str]


class PrescriptionOut(BaseModel):
    id: str
    patientName: str
    doctorName: str
    issuedAt: str
    lines: list[PrescriptionLineOut]
    status: Literal["PENDING", "ACCEPTED", "DECLINED", "DELIVERED"]
