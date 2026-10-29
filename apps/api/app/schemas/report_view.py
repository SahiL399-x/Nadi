from typing import Literal

from pydantic import BaseModel


class ReportViewOut(BaseModel):
    reportId: str
    kind: Literal["image", "pdf"]
    imageUrl: str
    date: str
    needsReview: bool
    extracted: bool
    fields: list[dict]
