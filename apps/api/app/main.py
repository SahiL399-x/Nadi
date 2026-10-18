from fastapi import FastAPI

from app.routers import auth, consultations, doctors

app = FastAPI(title="NADI API", version="0.1.0")
app.include_router(auth.router)
app.include_router(consultations.router)
app.include_router(doctors.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
