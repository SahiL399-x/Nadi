import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token
from app.models import Role, User
from app.schemas.auth import TokenPair


def verify_otp(db: Session, phone: str, code: str, role: str, name: str) -> TokenPair:
    if code != settings.otp_stub_code:
        raise ValueError("invalid otp")
    user = db.scalar(select(User).where(User.phone == phone))
    if user is None:
        user = User(id=uuid.uuid4(), phone=phone, role=Role(role), name=name or "User")
        db.add(user)
        db.commit()
        db.refresh(user)
    return TokenPair(
        accessToken=create_access_token(str(user.id), user.role.value),
        refreshToken=create_refresh_token(str(user.id)),
        role=user.role.value,
        userId=str(user.id),
    )
