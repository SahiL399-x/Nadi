from pydantic import BaseModel


class DoctorPrescriptionOut(BaseModel):
    id: str
    patientName: str
    issuedAt: str
    firstDrug: str
    status: str


class LabReportOut(BaseModel):
    id: str
    patientName: str
    date: str
    status: str
