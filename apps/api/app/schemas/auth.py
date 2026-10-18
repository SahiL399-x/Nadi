from pydantic import BaseModel


class RequestOtpIn(BaseModel):
    phone: str


class VerifyOtpIn(BaseModel):
    phone: str
    code: str
    role: str = "patient"   # ignored for privilege; new signups are always patients (see auth_service)
    name: str = ""


class TokenPair(BaseModel):
    accessToken: str
    refreshToken: str
    role: str
    userId: str


class RefreshIn(BaseModel):
    refreshToken: str
