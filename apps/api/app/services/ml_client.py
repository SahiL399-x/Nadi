import httpx

from app.core.config import settings

# One pooled client reused across calls (keep-alive), instead of per-request setup.
_client = httpx.Client(base_url=settings.ml_service_url, timeout=10)


def _post(path: str, payload: dict) -> dict:
    r = _client.post(path, json=payload)
    r.raise_for_status()
    return r.json()


def triage(payload: dict) -> dict:
    return _post("/ml/v1/triage", payload)


def document(object_key: str) -> list[dict]:
    return _post("/ml/v1/document", {"objectKey": object_key})["labs"]
