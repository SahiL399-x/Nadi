from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routers import (
    auth, consultations, doctor_portal, doctors, medicines, pharmacies, prescriptions, uploads,
    video,
)
from app.services.storage_service import ensure_bucket


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Provision the object-storage bucket report uploads need, so a fresh stack
    # works end-to-end with no manual setup. Best-effort: the API still serves if
    # MinIO is momentarily unreachable (uploads just fail until it recovers).
    try:
        ensure_bucket()
    except Exception:
        pass
    yield


app = FastAPI(title="NADI API", version="0.1.0", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(consultations.router)
app.include_router(doctors.router)
app.include_router(doctor_portal.router)
app.include_router(prescriptions.router)
app.include_router(pharmacies.router)
app.include_router(pharmacies.list_router)
app.include_router(uploads.router)
app.include_router(medicines.router)
app.include_router(video.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
