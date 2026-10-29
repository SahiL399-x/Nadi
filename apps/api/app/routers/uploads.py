import uuid
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.deps import require_role
from app.models import User
from app.services import storage_service

router = APIRouter(prefix="/v1/uploads", tags=["uploads"])


class SignRequest(BaseModel):
    source: Literal["scan", "upload"] = "upload"
    ext: Literal["webp", "pdf", "jpg", "png"] = "webp"


@router.post("/sign")
def sign(body: SignRequest | None = None, user: User = Depends(require_role("patient"))) -> dict:
    body = body or SignRequest()
    key = f"reports/{body.source}/{user.id}/{uuid.uuid4()}.{body.ext}"
    return {"url": storage_service.presign_put(key), "objectKey": key}
