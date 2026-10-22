from pydantic import BaseModel


class MyAppointmentOut(BaseModel):
    consultationId: str
    doctorName: str
    specialty: str
    status: str
    slot: str


class MyPrescriptionOut(BaseModel):
    id: str
    doctorName: str
    status: str
    items: int


class MyReportOut(BaseModel):
    id: str
    objectKey: str
