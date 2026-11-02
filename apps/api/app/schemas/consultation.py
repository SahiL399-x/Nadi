from pydantic import BaseModel

from app.schemas.common import TriageResultOut


class IntakeOut(BaseModel):
    consultationId: str
    jobId: str


class BookIn(BaseModel):
    doctorId: str
    slot: str


class QueueItemOut(BaseModel):
    id: str
    patientId: str
    patientName: str
    patientAge: int
    patientSex: str
    complaint: str
    bookedFor: str
    triage: TriageResultOut


class ConsultationDetailOut(BaseModel):
    id: str
    status: str
    doctorId: str | None = None
    bookedFor: str | None = None
    prescriptionId: str | None = None
