from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import create_access_token, decode_token
from app.models import User
from app.schemas.auth import RefreshIn, RequestOtpIn, TokenPair, VerifyOtpIn
from app.services.auth_service import verify_otp

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post("/request-otp")
def request_otp(body: RequestOtpIn) -> dict:
    # OTP stubbed: no SMS sent. Any phone receives the fixed dev code.
    return {"sent": True}


@router.post("/verify-otp", response_model=TokenPair)
def verify(body: VerifyOtpIn, db: Session = Depends(get_db)) -> TokenPair:
    try:
        return verify_otp(db, body.phone, body.code, body.role, body.name)
    except ValueError:
        raise HTTPException(status_code=401, detail="invalid otp") from None


@router.post("/refresh")
def refresh(body: RefreshIn, db: Session = Depends(get_db)) -> dict:
    try:
        payload = decode_token(body.refreshToken)
    except ValueError:
        raise HTTPException(status_code=401, detail="invalid token") from None
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="not a refresh token")
    user = db.get(User, payload["sub"])
    if user is None:
        raise HTTPException(status_code=401, detail="unknown user")
    return {"accessToken": create_access_token(str(user.id), user.role.value)}
