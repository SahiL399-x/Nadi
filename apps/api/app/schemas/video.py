from pydantic import BaseModel


class VideoTokenIn(BaseModel):
    consultationId: str


class VideoTokenOut(BaseModel):
    url: str
    token: str
    room: str
