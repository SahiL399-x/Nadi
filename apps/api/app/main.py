from fastapi import FastAPI

from app.routers import (
    auth, consultations, doctor_portal, doctors, medicines, pharmacies, prescriptions, uploads,
)

app = FastAPI(title="NADI API", version="0.1.0")
app.include_router(auth.router)
app.include_router(consultations.router)
app.include_router(doctors.router)
app.include_router(doctor_portal.router)
app.include_router(prescriptions.router)
app.include_router(pharmacies.router)
app.include_router(uploads.router)
app.include_router(medicines.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
