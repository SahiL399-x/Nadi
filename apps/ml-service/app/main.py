from fastapi import FastAPI

from app.document_stub import extract
from app.schemas import DocumentRequest, SymptomRequest, TriageRequest
from app.symptom_stub import normalise
from app.triage_stub import MODEL_VERSION, run

app = FastAPI(title="NADI ML Service", version="0.1.0")


@app.get("/ml/v1/health")
def health() -> dict:
    return {"status": "ok", "modelVersions": {"triage": MODEL_VERSION}}


@app.post("/ml/v1/symptom")
def symptom(req: SymptomRequest) -> dict:
    return normalise(req.text)


@app.post("/ml/v1/document")
def document(req: DocumentRequest) -> dict:
    return {"labs": extract(req.objectKey)}


@app.post("/ml/v1/triage")
def triage(req: TriageRequest) -> dict:
    labs = [lab.model_dump() for lab in req.labs]
    return run(req.symptomText, labs, req.age, req.sex)
