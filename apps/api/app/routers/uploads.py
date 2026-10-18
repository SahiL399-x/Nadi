import uuid

from fastapi import APIRouter, Depends

from app.core.deps import require_role
from app.models import User
from app.services import storage_service

router = APIRouter(prefix="/v1/uploads", tags=["uploads"])


@router.post("/sign")
def sign(user: User = Depends(require_role("patient"))) -> dict:
    key = f"reports/{user.id}/{uuid.uuid4()}.webp"
    return {"url": storage_service.presign_put(key), "objectKey": key}
