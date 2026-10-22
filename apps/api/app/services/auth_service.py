import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token
from app.models import Patient, Role, User
from app.schemas.auth import TokenPair


def verify_otp(db: Session, phone: str, code: str, role: str, name: str) -> TokenPair:
    if code != settings.otp_stub_code:
        raise ValueError("invalid otp")
    user = db.scalar(select(User).where(User.phone == phone))
    if user is None:
        # New self-service signups are always patients. The caller-supplied `role`
        # is NOT trusted for privilege: doctor/pharmacy accounts are provisioned
        # server-side (seed / admin) and an existing user keeps its stored role.
        default_name = f"Patient {phone[-4:]}" if phone else "Patient"
        user = User(id=uuid.uuid4(), phone=phone, role=Role.patient, name=name or default_name)
        db.add(user)
        db.flush()
        # Every patient gets a profile row so the doctor-queue join resolves
        # (the queue inner-joins `patients`).
        db.add(Patient(user_id=user.id))
        db.commit()
        db.refresh(user)
    return TokenPair(
        accessToken=create_access_token(str(user.id), user.role.value),
        refreshToken=create_refresh_token(str(user.id)),
        role=user.role.value,
        userId=str(user.id),
    )
