from pydantic import BaseModel


class NoteIn(BaseModel):
    text: str


class NoteOut(BaseModel):
    id: str
    text: str
    createdAt: str
