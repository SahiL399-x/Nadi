from pydantic import BaseModel


class AvailabilityOut(BaseModel):
    weekday: int
    morning: str
    evening: str
    isOpen: bool


class AvailabilityIn(BaseModel):
    days: list[AvailabilityOut]
