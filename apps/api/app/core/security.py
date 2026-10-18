from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.core.config import settings


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(sub: str, role: str) -> str:
    payload = {"sub": sub, "role": role, "type": "access",
               "exp": _now() + timedelta(minutes=settings.access_ttl_min)}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_alg)


def create_refresh_token(sub: str) -> str:
    payload = {"sub": sub, "type": "refresh",
               "exp": _now() + timedelta(days=settings.refresh_ttl_days)}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_alg)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_alg])
    except JWTError as exc:
        raise ValueError("invalid token") from exc
