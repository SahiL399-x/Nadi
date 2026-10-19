from pydantic import BaseModel


class OrderOut(BaseModel):
    id: str
    orderNo: str
    patientName: str
    phone: str
    itemsCount: int
    totalInr: int
    status: str
    placedAt: str
