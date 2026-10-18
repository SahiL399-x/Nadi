import httpx

from app.core.config import settings


def triage(payload: dict) -> dict:
    with httpx.Client(base_url=settings.ml_service_url, timeout=10) as c:
        r = c.post("/ml/v1/triage", json=payload)
        r.raise_for_status()
        return r.json()


def document(object_key: str) -> list[dict]:
    with httpx.Client(base_url=settings.ml_service_url, timeout=10) as c:
        r = c.post("/ml/v1/document", json={"objectKey": object_key})
        r.raise_for_status()
        return r.json()["labs"]
