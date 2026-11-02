from pydantic import BaseModel

_STATUS_LABEL = {
    "BOOKED": "Upcoming",
    "ARRIVED": "Arrived",
    "IN_PROGRESS": "In Progress",
    "DONE": "Completed",
}


class AppointmentOut(BaseModel):
    id: str
    patientId: str
    patientName: str
    patientAge: int
    patientSex: str
    photoUrl: str
    time: str
    status: str
    complaint: str


def status_label(raw: str) -> str:
    return _STATUS_LABEL.get(raw, raw.title())
