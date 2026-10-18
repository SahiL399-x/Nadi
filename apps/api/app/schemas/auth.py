from pydantic import BaseModel


class RequestOtpIn(BaseModel):
    phone: str


class VerifyOtpIn(BaseModel):
    phone: str
    code: str
    role: str = "patient"   # dev role switcher chooses which portal to log into
    name: str = ""


class TokenPair(BaseModel):
    accessToken: str
    refreshToken: str
    role: str
    userId: str


class RefreshIn(BaseModel):
    refreshToken: str
