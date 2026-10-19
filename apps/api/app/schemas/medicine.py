from pydantic import BaseModel


class MedicineOut(BaseModel):
    id: str
    name: str
    strength: str
    form: str
