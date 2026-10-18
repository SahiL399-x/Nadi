from collections.abc import Callable

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import decode_token
from app.models import User


def get_current_user(
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    try:
        payload = decode_token(authorization.removeprefix("Bearer "))
    except ValueError:
        raise HTTPException(status_code=401, detail="invalid token") from None
    if payload.get("type") != "access":
        # Refresh tokens must be exchanged at /v1/auth/refresh, not used directly.
        raise HTTPException(status_code=401, detail="invalid token")
    user = db.get(User, payload["sub"])
    if user is None:
        raise HTTPException(status_code=401, detail="unknown user")
    return user


def require_role(*roles: str) -> Callable[[User], User]:
    def _dep(user: User = Depends(get_current_user)) -> User:
        if user.role.value not in roles:
            raise HTTPException(status_code=403, detail="forbidden")
        return user

    return _dep
