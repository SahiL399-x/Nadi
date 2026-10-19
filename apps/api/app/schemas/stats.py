from pydantic import BaseModel


class DoctorStatsOut(BaseModel):
    appointmentsToday: int
    pending: int
    completed: int
    prescriptionsIssued: int
    newPatients: int
