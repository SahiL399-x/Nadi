import pytest
from fastapi.testclient import TestClient

from app.core.db import SessionLocal
from app.main import app


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def patient_token(client) -> str:
    client.post("/v1/auth/request-otp", json={"phone": "+919999900001"})
    r = client.post(
        "/v1/auth/verify-otp",
        json={"phone": "+919999900001", "code": "123456", "role": "patient", "name": "Test Patient"},
    )
    return r.json()["accessToken"]


@pytest.fixture
def doctor_token(client) -> str:
    # The seeded demo doctor owns the queue/appointments.
    client.post("/v1/auth/request-otp", json={"phone": "+915000000001"})
    r = client.post("/v1/auth/verify-otp", json={"phone": "+915000000001", "code": "123456"})
    return r.json()["accessToken"]
