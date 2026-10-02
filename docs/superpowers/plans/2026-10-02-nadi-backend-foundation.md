# NADI Backend Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A running, tested FastAPI backend + separate ML stub service that serve the frozen NADI §9 API contract over real Postgres+PostGIS, with seed data, so the three portals can be built against a live backend.

**Architecture:** Two FastAPI deployables. `apps/api` owns auth, data, and business logic (routers stay thin, logic in `services/`); `apps/ml-service` is a separate app serving `/ml/v1/*` with deterministic keyword + red-flag logic (swapped for trained ONNX models in a later phase). PostgreSQL 16 + PostGIS via Docker Compose locally. The API calls the ML service over internal HTTP.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2.x, GeoAlchemy2, Alembic, PostgreSQL 16 + PostGIS, pydantic v2 / pydantic-settings, python-jose (JWT), httpx, pytest, ruff, black, Docker Compose, MinIO (local S3).

## Global Constraints

- Python 3.11; type hints everywhere; `ruff` + `black`; pydantic at all boundaries. No bare `Any`.
- Routers stay thin — validate, call a service, return. All logic in `services/`.
- API contract is FROZEN (ProjectPlan.md §9). Response shapes must match exactly. Any change requires an ADR.
- The system ROUTES, it does not DIAGNOSE. No field name, enum, or string may imply a diagnosis.
- Red-flag rules run FIRST and bypass the triage model entirely; biased toward false positives.
- `triage_results.model_version` is mandatory on every row (stub writes `stub-keyword-v0`).
- Prescriptions are immutable — corrections create a new prescription superseding the old; never UPDATE clinical content.
- Pharmacy consent is mandatory, unticked, patient-chosen. No commission on medicine sales.
- `audit_log` is append-only; every patient-record access is logged.
- All inference is server-side. No LLMs/VLMs/third-party AI APIs.
- No AI attribution in any committed artefact (commits, comments, files). Commit messages: short, imperative, lowercase.
- Acuity enum values exactly: `ROUTINE | PRIORITY | URGENT | EMERGENCY`.
- PostGIS: all locations are `geography(Point, 4326)`; GiST index on every location column.

---

## File Structure

```
infra/
  docker-compose.yml            # postgres+postgis, minio, api, ml-service
apps/
  api/
    pyproject.toml              # deps + ruff/black/pytest config
    alembic.ini
    .env.example
    Dockerfile
    app/
      main.py                   # FastAPI app, router registration, /health
      core/
        config.py               # pydantic-settings
        db.py                   # engine, SessionLocal, get_db dependency
        security.py             # JWT encode/decode, password-free OTP helpers
        deps.py                 # current_user, require_role RBAC deps
      models/                   # SQLAlchemy ORM (one module per aggregate)
        base.py                 # DeclarativeBase + common columns
        user.py                 # User, Patient, Doctor, Pharmacy
        consultation.py         # Consultation, Report, LabValue
        triage.py               # TriageResult, Referral
        prescription.py         # Prescription, PrescriptionLine, PharmacyConsent, PharmacyOffer
        audit.py                # AuditLog
      schemas/                  # pydantic request/response (mirror §9)
        common.py               # Acuity, LabValue, TriageResult, Doctor, QueueItem, Prescription...
        auth.py
        consultation.py
        doctor.py
        prescription.py
        pharmacy.py
      services/                 # business logic
        auth_service.py
        ml_client.py            # httpx client to ml-service
        consultation_service.py
        doctor_service.py       # PostGIS search
        prescription_service.py
        pharmacy_service.py
        audit_service.py
      routers/
        auth.py consultations.py doctors.py doctor_portal.py
        prescriptions.py pharmacies.py uploads.py
    migrations/                 # alembic
      env.py
      versions/
    seed/
      doctor_headshots.json     # ALREADY EXISTS — curated Unsplash URLs
      seed.py                   # inserts 10 doctors, 6 queue items, 5 pharmacies, lab panels
    tests/
      conftest.py               # test db + client fixtures
      test_health.py test_auth.py test_consultations.py test_doctors.py
      test_doctor_portal.py test_prescriptions.py test_pharmacies.py test_seed.py
  ml-service/
    pyproject.toml
    Dockerfile
    app/
      main.py                   # FastAPI app, /ml/v1/* , /ml/v1/health
      redflags.py               # deterministic red-flag rules
      triage_stub.py            # keyword→TriageResult logic
      symptom_stub.py           # normalised entities
      document_stub.py          # LabValue fixtures by panel keyword
      schemas.py                # MUST match apps/api/schemas/common.py
    tests/
      test_redflags.py test_triage_stub.py test_symptom_stub.py test_document_stub.py
packages/
  shared-types/
    package.json
    gen.md                      # how to regenerate from OpenAPI
    src/types.ts                # generated TS types (checked in)
```

---

## Task 1: Repo scaffold, tooling, Docker Compose, API skeleton

**Files:**
- Create: `infra/docker-compose.yml`
- Create: `apps/api/pyproject.toml`
- Create: `apps/api/.env.example`
- Create: `apps/api/app/__init__.py`, `apps/api/app/main.py`
- Create: `apps/api/app/core/__init__.py`, `apps/api/app/core/config.py`, `apps/api/app/core/db.py`
- Test: `apps/api/tests/conftest.py`, `apps/api/tests/test_health.py`

**Interfaces:**
- Produces: `app.main.app` (FastAPI instance); `app.core.config.settings`; `app.core.db.get_db` (yields `Session`), `app.core.db.engine`, `app.core.db.SessionLocal`.

- [ ] **Step 1: Create `infra/docker-compose.yml`**

```yaml
services:
  db:
    image: postgis/postgis:16-3.4
    environment:
      POSTGRES_USER: nadi
      POSTGRES_PASSWORD: nadi
      POSTGRES_DB: nadi
    ports: ["5432:5432"]
    volumes: ["nadi_db:/var/lib/postgresql/data"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U nadi"]
      interval: 5s
      timeout: 5s
      retries: 10
  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: nadi
      MINIO_ROOT_PASSWORD: nadi12345
    ports: ["9000:9000", "9001:9001"]
    volumes: ["nadi_minio:/data"]
volumes:
  nadi_db:
  nadi_minio:
```

- [ ] **Step 2: Create `apps/api/pyproject.toml`**

```toml
[project]
name = "nadi-api"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.115",
  "uvicorn[standard]>=0.30",
  "sqlalchemy>=2.0",
  "geoalchemy2>=0.15",
  "psycopg[binary]>=3.2",
  "alembic>=1.13",
  "pydantic>=2.7",
  "pydantic-settings>=2.3",
  "python-jose[cryptography]>=3.3",
  "httpx>=0.27",
  "boto3>=1.34",
]

[project.optional-dependencies]
dev = ["pytest>=8", "ruff>=0.5", "black>=24", "pytest-asyncio>=0.23"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.black]
line-length = 100

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 3: Create `apps/api/.env.example`**

```
DATABASE_URL=postgresql+psycopg://nadi:nadi@localhost:5432/nadi
ML_SERVICE_URL=http://localhost:8001
JWT_SECRET=dev-secret-change-me
JWT_ALG=HS256
ACCESS_TTL_MIN=30
REFRESH_TTL_DAYS=30
S3_ENDPOINT=http://localhost:9000
S3_KEY=nadi
S3_SECRET=nadi12345
S3_BUCKET=nadi-reports
OTP_STUB_CODE=123456
```

- [ ] **Step 4: Create `apps/api/app/core/config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://nadi:nadi@localhost:5432/nadi"
    ml_service_url: str = "http://localhost:8001"
    jwt_secret: str = "dev-secret-change-me"
    jwt_alg: str = "HS256"
    access_ttl_min: int = 30
    refresh_ttl_days: int = 30
    s3_endpoint: str = "http://localhost:9000"
    s3_key: str = "nadi"
    s3_secret: str = "nadi12345"
    s3_bucket: str = "nadi-reports"
    otp_stub_code: str = "123456"


settings = Settings()
```

- [ ] **Step 5: Create `apps/api/app/core/db.py`**

```python
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 6: Create `apps/api/app/main.py`**

```python
from fastapi import FastAPI

app = FastAPI(title="NADI API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 7: Create `apps/api/tests/conftest.py`**

```python
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
```

- [ ] **Step 8: Write the failing test `apps/api/tests/test_health.py`**

```python
def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
```

- [ ] **Step 9: Install deps and run the test**

Run (from `apps/api`): `pip install -e ".[dev]" && pytest tests/test_health.py -v`
Expected: PASS (1 passed).

- [ ] **Step 10: Commit**

```bash
git add infra apps/api/pyproject.toml apps/api/.env.example apps/api/app apps/api/tests
git commit -m "scaffold api app, tooling, docker compose"
```

---

## Task 2: ORM base + models for the full §8 data model + Alembic migration

**Files:**
- Create: `apps/api/app/models/base.py`, `user.py`, `consultation.py`, `triage.py`, `prescription.py`, `audit.py`, `__init__.py`
- Create: `apps/api/alembic.ini`, `apps/api/migrations/env.py`, `apps/api/migrations/script.py.mako`
- Create migration: `apps/api/migrations/versions/0001_initial.py`
- Test: `apps/api/tests/test_models.py`

**Interfaces:**
- Produces ORM classes: `User, Patient, Doctor, Pharmacy, Consultation, Report, LabValue, TriageResult, Referral, Prescription, PrescriptionLine, PharmacyConsent, PharmacyOffer, AuditLog`. All inherit `Base` from `models/base.py`. `Base.metadata` is the Alembic target.
- Enums produced: `Role(patient|doctor|pharmacy)`, `Acuity(ROUTINE|PRIORITY|URGENT|EMERGENCY)`, `ConsultationStatus(PENDING|TRIAGED|BOOKED|IN_PROGRESS|DONE)`, `PrescriptionStatus(PENDING|ACCEPTED|DECLINED|DELIVERED)`, `OfferStatus(PENDING|ACCEPTED|DECLINED)`, `Flag(L|N|H)`.

- [ ] **Step 1: Create `apps/api/app/models/base.py`**

```python
import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def created_at_col() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 2: Create `apps/api/app/models/user.py`**

```python
import enum
import uuid

from geoalchemy2 import Geography
from sqlalchemy import ARRAY, Boolean, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at_col, uuid_pk


class Role(str, enum.Enum):
    patient = "patient"
    doctor = "doctor"
    pharmacy = "pharmacy"


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = uuid_pk()
    phone: Mapped[str] = mapped_column(String, unique=True, index=True)
    role: Mapped[Role] = mapped_column(Enum(Role, name="role"))
    name: Mapped[str] = mapped_column(String)
    lang: Mapped[str] = mapped_column(String, default="en")
    created_at = created_at_col()


class Patient(Base):
    __tablename__ = "patients"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sex: Mapped[str | None] = mapped_column(String, nullable=True)
    location = mapped_column(Geography(geometry_type="POINT", srid=4326), nullable=True)


class Doctor(Base):
    __tablename__ = "doctors"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    specialty: Mapped[str] = mapped_column(String, index=True)
    qualifications: Mapped[str] = mapped_column(String)
    reg_number: Mapped[str] = mapped_column(String)
    experience_years: Mapped[int] = mapped_column(Integer, default=0)
    fee_inr: Mapped[int] = mapped_column(Integer, default=0)
    languages: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    location = mapped_column(Geography(geometry_type="POINT", srid=4326), nullable=True)
    rating: Mapped[float] = mapped_column(Float, default=0.0)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=True)
    photo_url: Mapped[str] = mapped_column(String, default="")


class Pharmacy(Base):
    __tablename__ = "pharmacies"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    name: Mapped[str] = mapped_column(String)
    licence_number: Mapped[str] = mapped_column(String)
    location = mapped_column(Geography(geometry_type="POINT", srid=4326), nullable=True)
    delivers: Mapped[bool] = mapped_column(Boolean, default=True)
    open_hours: Mapped[str] = mapped_column(String, default="09:00-21:00")
    is_open: Mapped[bool] = mapped_column(Boolean, default=True)
```

- [ ] **Step 3: Create `apps/api/app/models/consultation.py`**

```python
import enum
import uuid

from sqlalchemy import Enum, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at_col, uuid_pk


class ConsultationStatus(str, enum.Enum):
    PENDING = "PENDING"
    TRIAGED = "TRIAGED"
    BOOKED = "BOOKED"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"


class Flag(str, enum.Enum):
    L = "L"
    N = "N"
    H = "H"


class Consultation(Base):
    __tablename__ = "consultations"
    id: Mapped[uuid.UUID] = uuid_pk()
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    doctor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[ConsultationStatus] = mapped_column(
        Enum(ConsultationStatus, name="consultation_status"),
        default=ConsultationStatus.PENDING,
    )
    booked_for: Mapped[str | None] = mapped_column(String, nullable=True)
    symptom_text_raw: Mapped[str] = mapped_column(String, default="")
    symptom_text_normalised: Mapped[str] = mapped_column(String, default="")
    created_at = created_at_col()


class Report(Base):
    __tablename__ = "reports"
    id: Mapped[uuid.UUID] = uuid_pk()
    consultation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("consultations.id"))
    object_key: Mapped[str] = mapped_column(String)
    ocr_status: Mapped[str] = mapped_column(String, default="pending")


class LabValue(Base):
    __tablename__ = "lab_values"
    id: Mapped[uuid.UUID] = uuid_pk()
    report_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("reports.id"))
    analyte: Mapped[str] = mapped_column(String)
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String)
    ref_range: Mapped[str] = mapped_column(String)
    flag: Mapped[Flag] = mapped_column(Enum(Flag, name="lab_flag"))
```

- [ ] **Step 4: Create `apps/api/app/models/triage.py`**

```python
import enum
import uuid

from sqlalchemy import Enum, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at_col, uuid_pk


class Acuity(str, enum.Enum):
    ROUTINE = "ROUTINE"
    PRIORITY = "PRIORITY"
    URGENT = "URGENT"
    EMERGENCY = "EMERGENCY"


class TriageResult(Base):
    __tablename__ = "triage_results"
    id: Mapped[uuid.UUID] = uuid_pk()
    consultation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("consultations.id"))
    acuity: Mapped[Acuity] = mapped_column(Enum(Acuity, name="acuity"))
    acuity_confidence: Mapped[float] = mapped_column(Float)
    specialties = mapped_column(JSONB)      # [{name, score}]
    drivers = mapped_column(JSONB)          # [{feature, contribution}]
    red_flags = mapped_column(JSONB)        # [str]
    model_version: Mapped[str] = mapped_column(String)   # MANDATORY
    created_at = created_at_col()


class Referral(Base):
    __tablename__ = "referrals"
    id: Mapped[uuid.UUID] = uuid_pk()
    consultation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("consultations.id"))
    from_doctor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    to_specialty: Mapped[str] = mapped_column(String)
    reason: Mapped[str] = mapped_column(String)
    created_at = created_at_col()
```

- [ ] **Step 5: Create `apps/api/app/models/prescription.py`**

```python
import enum
import uuid

from sqlalchemy import Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at_col, uuid_pk


class PrescriptionStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    DELIVERED = "DELIVERED"


class OfferStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"


class Prescription(Base):
    __tablename__ = "prescriptions"
    id: Mapped[uuid.UUID] = uuid_pk()
    consultation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("consultations.id"))
    status: Mapped[PrescriptionStatus] = mapped_column(
        Enum(PrescriptionStatus, name="prescription_status"),
        default=PrescriptionStatus.PENDING,
    )
    superseded_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("prescriptions.id"), nullable=True
    )
    issued_at = created_at_col()


class PrescriptionLine(Base):
    __tablename__ = "prescription_lines"
    id: Mapped[uuid.UUID] = uuid_pk()
    prescription_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("prescriptions.id"))
    drug: Mapped[str] = mapped_column(String)
    strength: Mapped[str] = mapped_column(String)
    frequency: Mapped[str] = mapped_column(String)
    duration_days: Mapped[int] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)


class PharmacyConsent(Base):
    __tablename__ = "pharmacy_consents"
    id: Mapped[uuid.UUID] = uuid_pk()
    prescription_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("prescriptions.id"))
    pharmacy_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    rank: Mapped[int] = mapped_column(Integer, default=0)  # routing order chosen by patient
    granted_at = created_at_col()


class PharmacyOffer(Base):
    __tablename__ = "pharmacy_offers"
    id: Mapped[uuid.UUID] = uuid_pk()
    prescription_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("prescriptions.id"))
    pharmacy_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    status: Mapped[OfferStatus] = mapped_column(
        Enum(OfferStatus, name="offer_status"), default=OfferStatus.PENDING
    )
    rank: Mapped[int] = mapped_column(Integer, default=0)
    responded_at: Mapped[str | None] = mapped_column(String, nullable=True)
```

- [ ] **Step 6: Create `apps/api/app/models/audit.py`**

```python
import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at_col, uuid_pk


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[uuid.UUID] = uuid_pk()
    actor_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String)
    entity: Mapped[str] = mapped_column(String)
    entity_id: Mapped[str] = mapped_column(String)
    at = created_at_col()
```

- [ ] **Step 7: Create `apps/api/app/models/__init__.py`** (re-export for Alembic autogenerate)

```python
from app.models.audit import AuditLog
from app.models.base import Base
from app.models.consultation import Consultation, ConsultationStatus, Flag, LabValue, Report
from app.models.prescription import (
    OfferStatus,
    PharmacyConsent,
    PharmacyOffer,
    Prescription,
    PrescriptionLine,
    PrescriptionStatus,
)
from app.models.triage import Acuity, Referral, TriageResult
from app.models.user import Doctor, Patient, Pharmacy, Role, User

__all__ = [
    "Base", "User", "Patient", "Doctor", "Pharmacy", "Role",
    "Consultation", "ConsultationStatus", "Report", "LabValue", "Flag",
    "TriageResult", "Referral", "Acuity",
    "Prescription", "PrescriptionLine", "PharmacyConsent", "PharmacyOffer",
    "PrescriptionStatus", "OfferStatus", "AuditLog",
]
```

- [ ] **Step 8: Initialise Alembic**

Run (from `apps/api`): `alembic init migrations`
Then edit `alembic.ini` line `sqlalchemy.url =` to be empty (URL comes from env), and replace `migrations/env.py` with:

```python
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings
from app.models import Base

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)
if config.config_file_name:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
```

- [ ] **Step 9: Create the initial migration enabling PostGIS**

Create `apps/api/migrations/versions/0001_initial.py` manually with a first line enabling the extension, then autogenerate the rest. First bring the DB up: `docker compose -f ../../infra/docker-compose.yml up -d db`. Then run:
`alembic revision --autogenerate -m "initial schema"`
Open the generated version file and ensure its `upgrade()` begins with:

```python
op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
```

(before any `create_table`). Then add GiST indexes at the end of `upgrade()`:

```python
op.execute("CREATE INDEX IF NOT EXISTS ix_doctors_location ON doctors USING gist (location)")
op.execute("CREATE INDEX IF NOT EXISTS ix_pharmacies_location ON pharmacies USING gist (location)")
op.execute("CREATE INDEX IF NOT EXISTS ix_patients_location ON patients USING gist (location)")
op.execute(
    "CREATE INDEX IF NOT EXISTS ix_consult_doctor_status_booked "
    "ON consultations (doctor_id, status, booked_for)"
)
```

- [ ] **Step 10: Write the failing test `apps/api/tests/test_models.py`**

```python
from sqlalchemy import inspect

from app.core.db import engine


def test_core_tables_exist():
    tables = set(inspect(engine).get_table_names())
    expected = {
        "users", "patients", "doctors", "pharmacies", "consultations",
        "reports", "lab_values", "triage_results", "referrals",
        "prescriptions", "prescription_lines", "pharmacy_consents",
        "pharmacy_offers", "audit_log",
    }
    assert expected.issubset(tables)
```

- [ ] **Step 11: Apply migration and run the test**

Run (from `apps/api`): `alembic upgrade head && pytest tests/test_models.py -v`
Expected: PASS. (If autogenerate missed geography columns, GeoAlchemy2 needs importing in env — it is, via models.)

- [ ] **Step 12: Commit**

```bash
git add apps/api/app/models apps/api/alembic.ini apps/api/migrations apps/api/tests/test_models.py
git commit -m "add data model and initial postgis migration"
```

---

## Task 3: Pydantic schemas mirroring the §9 contract

**Files:**
- Create: `apps/api/app/schemas/__init__.py`, `common.py`, `auth.py`, `consultation.py`, `doctor.py`, `prescription.py`, `pharmacy.py`
- Test: `apps/api/tests/test_schemas.py`

**Interfaces:**
- Produces pydantic models matching §9 exactly: `Acuity` (Literal), `LabValueOut`, `TriageInput`, `TriageResultOut`, `DoctorOut`, `QueueItemOut`, `PrescriptionLineIn/Out`, `PrescriptionOut`, `PharmacyOut`; auth: `RequestOtpIn`, `VerifyOtpIn`, `TokenPair`; `IntakeOut{consultationId, jobId}`, `BookIn{doctorId, slot}`, `ReferIn{toSpecialty, reason}`, `PrescribeIn{lines}`, `ConsentIn{pharmacyIds}`.

- [ ] **Step 1: Create `apps/api/app/schemas/common.py`**

```python
from typing import Literal

from pydantic import BaseModel

Acuity = Literal["ROUTINE", "PRIORITY", "URGENT", "EMERGENCY"]
Sex = Literal["M", "F", "O"]
LabFlag = Literal["L", "N", "H"]


class LabValueOut(BaseModel):
    analyte: str
    value: float
    unit: str
    refRange: str
    flag: LabFlag


class SpecialtyScore(BaseModel):
    name: str
    score: float


class Driver(BaseModel):
    feature: str
    contribution: float


class TriageInput(BaseModel):
    symptomText: str
    reportImageUris: list[str] = []
    age: int | None = None
    sex: Sex | None = None
    lang: Literal["en", "hi", "mr"] = "en"


class TriageResultOut(BaseModel):
    acuity: Acuity
    acuityConfidence: float
    specialties: list[SpecialtyScore]
    drivers: list[Driver]
    labs: list[LabValueOut]
    redFlags: list[str]
    modelVersion: str
```

- [ ] **Step 2: Create `apps/api/app/schemas/doctor.py`**

```python
from pydantic import BaseModel


class DoctorOut(BaseModel):
    id: str
    name: str
    specialty: str
    qualifications: str
    experienceYears: int
    distanceKm: float
    feeInr: int
    rating: float
    reviewCount: int
    languages: list[str]
    nextSlot: str
    photoUrl: str
    availableSlots: list[str]
```

- [ ] **Step 3: Create `apps/api/app/schemas/consultation.py`**

```python
from pydantic import BaseModel

from app.schemas.common import Acuity, TriageResultOut


class IntakeOut(BaseModel):
    consultationId: str
    jobId: str


class BookIn(BaseModel):
    doctorId: str
    slot: str


class QueueItemOut(BaseModel):
    id: str
    patientName: str
    patientAge: int
    patientSex: str
    acuity: Acuity
    complaint: str
    bookedFor: str
    triage: TriageResultOut
```

- [ ] **Step 4: Create `apps/api/app/schemas/prescription.py`**

```python
from typing import Literal

from pydantic import BaseModel


class PrescriptionLineIn(BaseModel):
    drug: str
    strength: str
    frequency: str
    durationDays: int
    notes: str | None = None


class PrescriptionLineOut(PrescriptionLineIn):
    pass


class PrescribeIn(BaseModel):
    lines: list[PrescriptionLineIn]


class ReferIn(BaseModel):
    toSpecialty: str
    reason: str


class ConsentIn(BaseModel):
    pharmacyIds: list[str]


class PrescriptionOut(BaseModel):
    id: str
    patientName: str
    doctorName: str
    issuedAt: str
    lines: list[PrescriptionLineOut]
    status: Literal["PENDING", "ACCEPTED", "DECLINED", "DELIVERED"]
```

- [ ] **Step 5: Create `apps/api/app/schemas/pharmacy.py`**

```python
from typing import Literal

from pydantic import BaseModel


class PharmacyOut(BaseModel):
    id: str
    name: str
    distanceKm: float
    deliversInMins: int
    isOpen: bool


class OfferOut(BaseModel):
    id: str
    prescriptionId: str
    patientName: str
    status: Literal["PENDING", "ACCEPTED", "DECLINED"]
    lines: list[dict]
```

- [ ] **Step 6: Create `apps/api/app/schemas/auth.py`**

```python
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
```

- [ ] **Step 7: Create `apps/api/app/schemas/__init__.py`** (empty re-export module)

```python
```

- [ ] **Step 8: Write the failing test `apps/api/tests/test_schemas.py`**

```python
from app.schemas.common import TriageResultOut
from app.schemas.doctor import DoctorOut


def test_triage_result_shape():
    t = TriageResultOut(
        acuity="ROUTINE", acuityConfidence=0.8, specialties=[],
        drivers=[], labs=[], redFlags=[], modelVersion="stub-keyword-v0",
    )
    assert t.model_dump()["acuity"] == "ROUTINE"


def test_doctor_requires_camelcase_fields():
    d = DoctorOut(
        id="1", name="Dr A", specialty="Cardiology", qualifications="MBBS",
        experienceYears=5, distanceKm=3.2, feeInr=400, rating=4.5,
        reviewCount=12, languages=["Hindi"], nextSlot="10:00",
        photoUrl="x", availableSlots=["10:00", "10:30"],
    )
    assert d.model_dump()["distanceKm"] == 3.2
```

- [ ] **Step 9: Run the test**

Run (from `apps/api`): `pytest tests/test_schemas.py -v`
Expected: PASS (2 passed).

- [ ] **Step 10: Commit**

```bash
git add apps/api/app/schemas apps/api/tests/test_schemas.py
git commit -m "add pydantic schemas mirroring the api contract"
```

---

## Task 4: ML service — red-flag rules + keyword triage/symptom/document stubs

**Files:**
- Create: `apps/ml-service/pyproject.toml`, `Dockerfile`, `app/__init__.py`, `app/schemas.py`, `app/redflags.py`, `app/triage_stub.py`, `app/symptom_stub.py`, `app/document_stub.py`, `app/main.py`
- Test: `apps/ml-service/tests/test_redflags.py`, `test_triage_stub.py`, `test_symptom_stub.py`, `test_document_stub.py`, `conftest.py`

**Interfaces:**
- Produces HTTP endpoints `POST /ml/v1/symptom {text, lang}`, `POST /ml/v1/document {objectKey}`, `POST /ml/v1/triage {symptomText, labs, age, sex, lang}` → `TriageResultOut`, `GET /ml/v1/health`.
- Produces `redflags.check(text: str) -> list[str]`, `triage_stub.run(text, labs, age, sex) -> dict` (TriageResult shape), `document_stub.extract(object_key) -> list[dict]` (LabValue shape), `symptom_stub.normalise(text) -> dict{entities, normalised}`.
- `MODEL_VERSION = "stub-keyword-v0"`.

- [ ] **Step 1: Create `apps/ml-service/pyproject.toml`**

```toml
[project]
name = "nadi-ml-service"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["fastapi>=0.115", "uvicorn[standard]>=0.30", "pydantic>=2.7"]

[project.optional-dependencies]
dev = ["pytest>=8", "ruff>=0.5", "black>=24", "httpx>=0.27"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Write failing test `apps/ml-service/tests/test_redflags.py`**

```python
from app.redflags import check


def test_chest_pain_with_breathlessness_fires():
    assert check("mujhe chest pain aur breathlessness ho raha hai")


def test_seizure_fires():
    assert "seizure" in " ".join(check("patient had a seizure")).lower()


def test_plain_fever_does_not_fire():
    assert check("mild fever since morning") == []
```

- [ ] **Step 3: Implement `apps/ml-service/app/redflags.py`**

```python
RULES: list[tuple[str, list[list[str]]]] = [
    ("chest pain with breathlessness", [["chest", "breath"], ["seene", "saans"]]),
    ("one-sided weakness or slurred speech", [["one-sided", "weak"], ["slurred"], ["paralysis"]]),
    ("seizure", [["seizure"], ["convulsion"], ["fit", "jhatka"]]),
    ("severe bleeding", [["severe", "bleeding"], ["heavy", "blood"]]),
    ("unresponsiveness", [["unconscious"], ["unresponsive"], ["behosh"]]),
    ("bleeding during pregnancy", [["pregnan", "bleed"], ["garbh", "khoon"]]),
    ("high fever in an infant", [["infant", "fever"], ["newborn", "fever"], ["baby", "high fever"]]),
]


def check(text: str) -> list[str]:
    t = text.lower()
    fired: list[str] = []
    for label, groups in RULES:
        for group in groups:
            if all(token in t for token in group):
                fired.append(label)
                break
    return fired
```

- [ ] **Step 4: Run red-flag test**

Run (from `apps/ml-service`): `pip install -e ".[dev]" && pytest tests/test_redflags.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Write failing test `apps/ml-service/tests/test_triage_stub.py`**

```python
from app.triage_stub import run


def test_chest_breath_is_emergency_with_redflag():
    r = run("chest pain and breathlessness", [], 50, "M")
    assert r["acuity"] == "EMERGENCY"
    assert r["redFlags"]
    assert r["modelVersion"] == "stub-keyword-v0"


def test_chakkar_is_priority_general_medicine():
    r = run("mujhe chakkar aa raha hai", [], 30, "F")
    assert r["acuity"] == "PRIORITY"
    assert r["specialties"][0]["name"] == "General Medicine"


def test_fever_is_routine():
    r = run("fever and cough", [], 25, "M")
    assert r["acuity"] == "ROUTINE"


def test_specialties_always_length_three_descending():
    r = run("something unmapped", [], 40, "M")
    scores = [s["score"] for s in r["specialties"]]
    assert len(r["specialties"]) == 3
    assert scores == sorted(scores, reverse=True)
```

- [ ] **Step 6: Implement `apps/ml-service/app/triage_stub.py`**

```python
from app.redflags import check

MODEL_VERSION = "stub-keyword-v0"


def _specialties(primary: str, alts: list[str]) -> list[dict]:
    names = [primary, *alts][:3]
    scores = [0.82, 0.11, 0.07][: len(names)]
    return [{"name": n, "score": s} for n, s in zip(names, scores, strict=False)]


def run(symptom_text: str, labs: list[dict], age: int | None, sex: str | None) -> dict:
    t = symptom_text.lower()
    red_flags = check(symptom_text)
    if red_flags or ("chest" in t and "breath" in t):
        return {
            "acuity": "EMERGENCY",
            "acuityConfidence": 0.97,
            "specialties": _specialties("Emergency Medicine", ["Cardiology", "General Medicine"]),
            "drivers": [{"feature": "red_flag_rule", "contribution": 1.0}],
            "labs": labs,
            "redFlags": red_flags or ["chest pain with breathlessness"],
            "modelVersion": MODEL_VERSION,
        }
    if any(k in t for k in ("chakkar", "dizzy", "weak", "weakness")):
        return {
            "acuity": "PRIORITY",
            "acuityConfidence": 0.74,
            "specialties": _specialties("General Medicine", ["Haematology", "Cardiology"]),
            "drivers": [
                {"feature": "dizziness", "contribution": 0.44},
                {"feature": "low_haemoglobin", "contribution": 0.31},
            ],
            "labs": labs,
            "redFlags": [],
            "modelVersion": MODEL_VERSION,
        }
    if any(k in t for k in ("fever", "cough", "cold", "bukhar", "khansi")):
        return {
            "acuity": "ROUTINE",
            "acuityConfidence": 0.81,
            "specialties": _specialties("General Physician", ["ENT", "General Medicine"]),
            "drivers": [{"feature": "fever", "contribution": 0.52}],
            "labs": labs,
            "redFlags": [],
            "modelVersion": MODEL_VERSION,
        }
    return {
        "acuity": "ROUTINE",
        "acuityConfidence": 0.6,
        "specialties": _specialties("General Physician", ["General Medicine", "ENT"]),
        "drivers": [{"feature": "unspecified_symptom", "contribution": 0.3}],
        "labs": labs,
        "redFlags": [],
        "modelVersion": MODEL_VERSION,
    }
```

- [ ] **Step 7: Run triage-stub test**

Run: `pytest tests/test_triage_stub.py -v`
Expected: PASS (4 passed).

- [ ] **Step 8: Write failing test `apps/ml-service/tests/test_document_stub.py`**

```python
from app.document_stub import extract


def test_anaemia_panel_returns_low_haemoglobin():
    labs = extract("anaemia/report1.webp")
    hb = next(x for x in labs if x["analyte"] == "Haemoglobin")
    assert hb["flag"] == "L"


def test_unknown_key_defaults_to_anaemia_panel():
    labs = extract("random.webp")
    assert any(x["analyte"] == "Haemoglobin" for x in labs)
```

- [ ] **Step 9: Implement `apps/ml-service/app/document_stub.py`**

```python
_ANAEMIA = [
    {"analyte": "Haemoglobin", "value": 9.1, "unit": "g/dL", "refRange": "12.0 - 15.5", "flag": "L"},
    {"analyte": "RBC Count", "value": 3.8, "unit": "mill/cu.mm", "refRange": "4.2 - 5.4", "flag": "L"},
    {"analyte": "MCV", "value": 72.0, "unit": "fL", "refRange": "80 - 100", "flag": "L"},
]
_THYROID = [
    {"analyte": "TSH", "value": 7.8, "unit": "uIU/mL", "refRange": "0.4 - 4.0", "flag": "H"},
    {"analyte": "Free T4", "value": 0.7, "unit": "ng/dL", "refRange": "0.8 - 1.8", "flag": "L"},
]
_DIABETES = [
    {"analyte": "Fasting Glucose", "value": 148.0, "unit": "mg/dL", "refRange": "70 - 100", "flag": "H"},
    {"analyte": "HbA1c", "value": 7.9, "unit": "%", "refRange": "4.0 - 5.6", "flag": "H"},
]


def extract(object_key: str) -> list[dict]:
    k = object_key.lower()
    if "thyroid" in k:
        return _THYROID
    if "diabet" in k or "glucose" in k or "sugar" in k:
        return _DIABETES
    return _ANAEMIA
```

- [ ] **Step 10: Write failing test `apps/ml-service/tests/test_symptom_stub.py`**

```python
from app.symptom_stub import normalise


def test_normalise_returns_entities_and_string():
    out = normalise("mujhe pet me jalan ho rahi hai")
    assert "entities" in out
    assert isinstance(out["normalised"], str)
    assert out["normalised"]
```

- [ ] **Step 11: Implement `apps/ml-service/app/symptom_stub.py`**

```python
_LEXICON = {
    "chakkar": "dizziness", "dizzy": "dizziness",
    "jalan": "burning", "pet": "abdomen",
    "bukhar": "fever", "fever": "fever",
    "khansi": "cough", "cough": "cough",
    "sar": "head", "dard": "pain",
    "saans": "breathlessness", "breath": "breathlessness",
}


def normalise(text: str) -> dict:
    t = text.lower()
    entities = sorted({canon for token, canon in _LEXICON.items() if token in t})
    normalised = ", ".join(entities) if entities else t.strip()
    return {"entities": entities, "normalised": normalised}
```

- [ ] **Step 12: Create `apps/ml-service/app/schemas.py`** (mirror of api common schemas)

```python
from typing import Literal

from pydantic import BaseModel


class LabValue(BaseModel):
    analyte: str
    value: float
    unit: str
    refRange: str
    flag: Literal["L", "N", "H"]


class TriageRequest(BaseModel):
    symptomText: str
    labs: list[LabValue] = []
    age: int | None = None
    sex: Literal["M", "F", "O"] | None = None
    lang: Literal["en", "hi", "mr"] = "en"


class SymptomRequest(BaseModel):
    text: str
    lang: Literal["en", "hi", "mr"] = "en"


class DocumentRequest(BaseModel):
    objectKey: str
```

- [ ] **Step 13: Implement `apps/ml-service/app/main.py`**

```python
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
```

- [ ] **Step 14: Create `apps/ml-service/tests/conftest.py`**

```python
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
```

- [ ] **Step 15: Run the full ML service suite**

Run (from `apps/ml-service`): `pytest -v`
Expected: all pass.

- [ ] **Step 16: Create `apps/ml-service/Dockerfile`**

```dockerfile
FROM python:3.11-slim
WORKDIR /srv
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .
COPY app ./app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

- [ ] **Step 17: Commit**

```bash
git add apps/ml-service
git commit -m "add ml service stub with red-flag rules and keyword triage"
```

---

## Task 5: Auth — stubbed OTP, JWT issuance, RBAC dependencies

**Files:**
- Create: `apps/api/app/core/security.py`, `apps/api/app/core/deps.py`
- Create: `apps/api/app/services/auth_service.py`, `apps/api/app/routers/auth.py`
- Modify: `apps/api/app/main.py` (register auth router)
- Test: `apps/api/tests/test_auth.py`
- Modify: `apps/api/tests/conftest.py` (add db-backed client + db fixtures)

**Interfaces:**
- Consumes: `models.User, Role`; `schemas.auth.*`; `core.db.get_db`.
- Produces: `security.create_access_token(sub, role) -> str`, `security.create_refresh_token(sub) -> str`, `security.decode_token(token) -> dict`; `deps.get_current_user(...) -> User`, `deps.require_role(*roles) -> Callable`; `auth_service.verify_otp(db, phone, code, role, name) -> TokenPair`.
- Routes: `POST /v1/auth/request-otp`, `/v1/auth/verify-otp`, `/v1/auth/refresh`.

- [ ] **Step 1: Implement `apps/api/app/core/security.py`**

```python
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.core.config import settings


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(sub: str, role: str) -> str:
    payload = {"sub": sub, "role": role, "type": "access",
               "exp": _now() + timedelta(minutes=settings.access_ttl_min)}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_alg)


def create_refresh_token(sub: str) -> str:
    payload = {"sub": sub, "type": "refresh",
               "exp": _now() + timedelta(days=settings.refresh_ttl_days)}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_alg)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_alg])
    except JWTError as exc:
        raise ValueError("invalid token") from exc
```

- [ ] **Step 2: Implement `apps/api/app/services/auth_service.py`**

```python
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token
from app.models import Role, User
from app.schemas.auth import TokenPair


def verify_otp(db: Session, phone: str, code: str, role: str, name: str) -> TokenPair:
    if code != settings.otp_stub_code:
        raise ValueError("invalid otp")
    user = db.scalar(select(User).where(User.phone == phone))
    if user is None:
        user = User(id=uuid.uuid4(), phone=phone, role=Role(role), name=name or "User")
        db.add(user)
        db.commit()
        db.refresh(user)
    return TokenPair(
        accessToken=create_access_token(str(user.id), user.role.value),
        refreshToken=create_refresh_token(str(user.id)),
        role=user.role.value,
        userId=str(user.id),
    )
```

- [ ] **Step 3: Implement `apps/api/app/core/deps.py`**

```python
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
```

- [ ] **Step 4: Implement `apps/api/app/routers/auth.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import create_access_token, decode_token
from app.models import User
from app.schemas.auth import RefreshIn, RequestOtpIn, TokenPair, VerifyOtpIn
from app.services.auth_service import verify_otp

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post("/request-otp")
def request_otp(body: RequestOtpIn) -> dict:
    # OTP stubbed: no SMS sent. Any phone receives the fixed dev code.
    return {"sent": True}


@router.post("/verify-otp", response_model=TokenPair)
def verify(body: VerifyOtpIn, db: Session = Depends(get_db)) -> TokenPair:
    try:
        return verify_otp(db, body.phone, body.code, body.role, body.name)
    except ValueError:
        raise HTTPException(status_code=401, detail="invalid otp") from None


@router.post("/refresh")
def refresh(body: RefreshIn, db: Session = Depends(get_db)) -> dict:
    try:
        payload = decode_token(body.refreshToken)
    except ValueError:
        raise HTTPException(status_code=401, detail="invalid token") from None
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="not a refresh token")
    user = db.get(User, payload["sub"])
    if user is None:
        raise HTTPException(status_code=401, detail="unknown user")
    return {"accessToken": create_access_token(str(user.id), user.role.value)}
```

- [ ] **Step 5: Register router in `apps/api/app/main.py`**

```python
from fastapi import FastAPI

from app.routers import auth

app = FastAPI(title="NADI API", version="0.1.0")
app.include_router(auth.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 6: Replace `apps/api/tests/conftest.py` with db-aware fixtures**

```python
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
```

- [ ] **Step 7: Write the failing test `apps/api/tests/test_auth.py`**

```python
def test_verify_otp_with_stub_code_issues_tokens(client):
    client.post("/v1/auth/request-otp", json={"phone": "+919000000001"})
    r = client.post(
        "/v1/auth/verify-otp",
        json={"phone": "+919000000001", "code": "123456", "role": "patient", "name": "A"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["accessToken"] and body["role"] == "patient"


def test_wrong_code_rejected(client):
    r = client.post(
        "/v1/auth/verify-otp",
        json={"phone": "+919000000002", "code": "000000", "role": "patient", "name": "A"},
    )
    assert r.status_code == 401
```

- [ ] **Step 8: Run tests against the running DB**

Ensure DB is up and migrated (`alembic upgrade head`). Run: `pytest tests/test_auth.py -v`
Expected: PASS (2 passed).

- [ ] **Step 9: Commit**

```bash
git add apps/api/app/core/security.py apps/api/app/core/deps.py apps/api/app/services/auth_service.py apps/api/app/routers/auth.py apps/api/app/main.py apps/api/tests/conftest.py apps/api/tests/test_auth.py
git commit -m "add stubbed otp auth with jwt and rbac deps"
```

---

## Task 6: ML client + consultations (intake → triage → get → book)

**Files:**
- Create: `apps/api/app/services/ml_client.py`, `apps/api/app/services/audit_service.py`, `apps/api/app/services/consultation_service.py`, `apps/api/app/routers/consultations.py`
- Modify: `apps/api/app/main.py` (register router)
- Test: `apps/api/tests/test_consultations.py`

**Interfaces:**
- Consumes: `schemas.common.TriageInput/TriageResultOut`, `schemas.consultation.IntakeOut/BookIn`, models, `deps`.
- Produces: `ml_client.triage(payload) -> dict`, `ml_client.document(object_key) -> list[dict]`; `audit_service.log(db, actor, action, entity, entity_id)`; `consultation_service.intake(db, patient, inp) -> Consultation`, `.get_triage(db, cid) -> TriageResult|None`, `.book(db, cid, doctor_id, slot)`.
- Routes: `POST /v1/consultations/intake`, `GET /v1/consultations/{id}/triage`, `GET /v1/consultations/{id}`, `POST /v1/consultations/{id}/book`.

- [ ] **Step 1: Implement `apps/api/app/services/ml_client.py`**

```python
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
```

- [ ] **Step 2: Implement `apps/api/app/services/audit_service.py`**

```python
import uuid

from sqlalchemy.orm import Session

from app.models import AuditLog


def log(db: Session, actor_user_id, action: str, entity: str, entity_id: str) -> None:
    db.add(
        AuditLog(
            id=uuid.uuid4(), actor_user_id=actor_user_id,
            action=action, entity=entity, entity_id=entity_id,
        )
    )
    db.commit()
```

- [ ] **Step 3: Implement `apps/api/app/services/consultation_service.py`**

```python
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Consultation, ConsultationStatus, Report, TriageResult
from app.schemas.common import TriageInput
from app.services import ml_client


def intake(db: Session, patient_id, inp: TriageInput) -> Consultation:
    consult = Consultation(
        id=uuid.uuid4(), patient_id=patient_id,
        status=ConsultationStatus.PENDING, symptom_text_raw=inp.symptomText,
    )
    db.add(consult)
    db.flush()

    labs: list[dict] = []
    for i, uri in enumerate(inp.reportImageUris):
        key = f"consult/{consult.id}/report{i}"
        db.add(Report(id=uuid.uuid4(), consultation_id=consult.id, object_key=key, ocr_status="done"))
        labs.extend(ml_client.document(key))

    result = ml_client.triage(
        {"symptomText": inp.symptomText, "labs": labs, "age": inp.age, "sex": inp.sex, "lang": inp.lang}
    )
    db.add(
        TriageResult(
            id=uuid.uuid4(), consultation_id=consult.id,
            acuity=result["acuity"], acuity_confidence=result["acuityConfidence"],
            specialties=result["specialties"], drivers=result["drivers"],
            red_flags=result["redFlags"], model_version=result["modelVersion"],
        )
    )
    consult.status = ConsultationStatus.TRIAGED
    consult.symptom_text_normalised = inp.symptomText
    db.commit()
    db.refresh(consult)
    return consult


def get_triage(db: Session, consultation_id) -> TriageResult | None:
    return db.scalar(
        select(TriageResult).where(TriageResult.consultation_id == consultation_id)
    )


def book(db: Session, consultation_id, doctor_id, slot: str) -> Consultation:
    consult = db.get(Consultation, consultation_id)
    consult.doctor_id = doctor_id
    consult.booked_for = slot
    consult.status = ConsultationStatus.BOOKED
    db.commit()
    db.refresh(consult)
    return consult
```

- [ ] **Step 4: Implement `apps/api/app/routers/consultations.py`**

```python
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_role
from app.models import TriageResult, User
from app.schemas.common import TriageInput, TriageResultOut
from app.schemas.consultation import BookIn, IntakeOut
from app.services import audit_service, consultation_service

router = APIRouter(prefix="/v1/consultations", tags=["consultations"])


def _triage_out(tr: TriageResult, labs: list | None = None) -> TriageResultOut:
    return TriageResultOut(
        acuity=tr.acuity.value if hasattr(tr.acuity, "value") else tr.acuity,
        acuityConfidence=tr.acuity_confidence,
        specialties=tr.specialties, drivers=tr.drivers,
        labs=labs or [], redFlags=tr.red_flags, modelVersion=tr.model_version,
    )


@router.post("/intake", response_model=IntakeOut)
def intake(body: TriageInput, user: User = Depends(require_role("patient")),
           db: Session = Depends(get_db)) -> IntakeOut:
    consult = consultation_service.intake(db, user.id, body)
    audit_service.log(db, user.id, "intake", "consultation", str(consult.id))
    return IntakeOut(consultationId=str(consult.id), jobId=str(uuid.uuid4()))


@router.get("/{consultation_id}/triage", response_model=TriageResultOut)
def get_triage(consultation_id: str, user: User = Depends(require_role("patient")),
               db: Session = Depends(get_db)) -> TriageResultOut:
    tr = consultation_service.get_triage(db, consultation_id)
    if tr is None:
        raise HTTPException(status_code=202, detail="pending")
    return _triage_out(tr)


@router.post("/{consultation_id}/book")
def book(consultation_id: str, body: BookIn, user: User = Depends(require_role("patient")),
         db: Session = Depends(get_db)) -> dict:
    consultation_service.book(db, consultation_id, body.doctorId, body.slot)
    audit_service.log(db, user.id, "book", "consultation", consultation_id)
    return {"booked": True}
```

- [ ] **Step 5: Register router in `apps/api/app/main.py`**

Add `from app.routers import auth, consultations` and `app.include_router(consultations.router)`.

- [ ] **Step 6: Write the failing test `apps/api/tests/test_consultations.py`**

```python
import httpx


def _stub_ml(monkeypatch):
    from app.services import ml_client

    def fake_triage(payload):
        return {
            "acuity": "EMERGENCY" if "chest" in payload["symptomText"] else "ROUTINE",
            "acuityConfidence": 0.9,
            "specialties": [{"name": "Emergency Medicine", "score": 0.8},
                            {"name": "Cardiology", "score": 0.1},
                            {"name": "General Medicine", "score": 0.1}],
            "drivers": [{"feature": "f", "contribution": 1.0}],
            "labs": payload["labs"],
            "redFlags": ["chest pain with breathlessness"] if "chest" in payload["symptomText"] else [],
            "modelVersion": "stub-keyword-v0",
        }

    monkeypatch.setattr(ml_client, "triage", fake_triage)
    monkeypatch.setattr(ml_client, "document", lambda k: [])


def test_intake_then_triage_emergency(client, patient_token, monkeypatch):
    _stub_ml(monkeypatch)
    h = {"Authorization": f"Bearer {patient_token}"}
    r = client.post("/v1/consultations/intake",
                    json={"symptomText": "chest pain and breath", "reportImageUris": [],
                          "age": 50, "sex": "M", "lang": "en"}, headers=h)
    assert r.status_code == 200
    cid = r.json()["consultationId"]
    t = client.get(f"/v1/consultations/{cid}/triage", headers=h)
    assert t.status_code == 200
    assert t.json()["acuity"] == "EMERGENCY"
    assert t.json()["redFlags"]
    assert t.json()["modelVersion"] == "stub-keyword-v0"
```

- [ ] **Step 7: Run the test**

Run: `pytest tests/test_consultations.py -v`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add apps/api/app/services apps/api/app/routers/consultations.py apps/api/app/main.py apps/api/tests/test_consultations.py
git commit -m "add consultations intake triage and booking"
```

---

## Task 7: Doctors — PostGIS search + detail

**Files:**
- Create: `apps/api/app/services/doctor_service.py`, `apps/api/app/routers/doctors.py`
- Modify: `apps/api/app/main.py`
- Test: `apps/api/tests/test_doctors.py`

**Interfaces:**
- Consumes: `models.Doctor, User`, `schemas.doctor.DoctorOut`.
- Produces: `doctor_service.search(db, specialty, lat, lng, radius_km, lang) -> list[DoctorOut]`, `doctor_service.get(db, doctor_id) -> DoctorOut`. Distance computed with `ST_Distance` over `geography`; results ordered by distance ascending.
- Routes: `GET /v1/doctors?specialty=&lat=&lng=&radiusKm=&lang=`, `GET /v1/doctors/{id}`.

- [ ] **Step 1: Implement `apps/api/app/services/doctor_service.py`**

```python
from geoalchemy2.functions import ST_Distance, ST_DWithin, ST_SetSRID, ST_MakePoint
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Doctor, User
from app.schemas.doctor import DoctorOut

_SLOTS = ["09:00", "09:30", "10:00", "11:00", "14:00", "16:30"]


def _point(lat: float, lng: float):
    return func.cast(ST_SetSRID(ST_MakePoint(lng, lat), 4326), type_=Doctor.location.type)


def _to_out(doctor: Doctor, name: str, distance_km: float) -> DoctorOut:
    return DoctorOut(
        id=str(doctor.user_id), name=name, specialty=doctor.specialty,
        qualifications=doctor.qualifications, experienceYears=doctor.experience_years,
        distanceKm=round(distance_km, 1), feeInr=doctor.fee_inr, rating=doctor.rating,
        reviewCount=doctor.review_count, languages=list(doctor.languages),
        nextSlot=_SLOTS[0], photoUrl=doctor.photo_url, availableSlots=_SLOTS,
    )


def search(db: Session, specialty: str | None, lat: float, lng: float,
           radius_km: float, lang: str | None) -> list[DoctorOut]:
    pt = _point(lat, lng)
    dist = ST_Distance(Doctor.location, pt)
    stmt = select(Doctor, User.name, dist).join(User, User.id == Doctor.user_id)
    stmt = stmt.where(ST_DWithin(Doctor.location, pt, radius_km * 1000))
    if specialty:
        stmt = stmt.where(Doctor.specialty == specialty)
    if lang:
        stmt = stmt.where(Doctor.languages.any(lang))
    stmt = stmt.order_by(dist.asc())
    rows = db.execute(stmt).all()
    return [_to_out(d, name, d_m / 1000.0) for (d, name, d_m) in rows]


def get(db: Session, doctor_id: str) -> DoctorOut | None:
    row = db.execute(
        select(Doctor, User.name).join(User, User.id == Doctor.user_id)
        .where(Doctor.user_id == doctor_id)
    ).first()
    if row is None:
        return None
    doctor, name = row
    return _to_out(doctor, name, 0.0)
```

- [ ] **Step 2: Implement `apps/api/app/routers/doctors.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.doctor import DoctorOut
from app.services import doctor_service

router = APIRouter(prefix="/v1/doctors", tags=["doctors"])


@router.get("", response_model=list[DoctorOut])
def search(specialty: str | None = None, lat: float = 19.9975, lng: float = 73.7898,
           radiusKm: float = 50.0, lang: str | None = None,
           db: Session = Depends(get_db)) -> list[DoctorOut]:
    return doctor_service.search(db, specialty, lat, lng, radiusKm, lang)


@router.get("/{doctor_id}", response_model=DoctorOut)
def get(doctor_id: str, db: Session = Depends(get_db)) -> DoctorOut:
    out = doctor_service.get(db, doctor_id)
    if out is None:
        raise HTTPException(status_code=404, detail="not found")
    return out
```

(Default lat/lng are Nashik, Maharashtra — where seed doctors are located.)

- [ ] **Step 3: Register router in `apps/api/app/main.py`** (`from app.routers import auth, consultations, doctors` + include).

- [ ] **Step 4: Write the failing test `apps/api/tests/test_doctors.py`**

```python
import uuid

from geoalchemy2.elements import WKTElement

from app.models import Doctor, Role, User


def _make_doctor(db, name, specialty, lat, lng, fee):
    uid = uuid.uuid4()
    db.add(User(id=uid, phone=f"+91{uuid.uuid4().int % 10**10:010d}", role=Role.doctor, name=name))
    db.add(Doctor(user_id=uid, specialty=specialty, qualifications="MBBS", reg_number="R1",
                  experience_years=5, fee_inr=fee, languages=["Hindi", "English"],
                  location=WKTElement(f"POINT({lng} {lat})", srid=4326),
                  rating=4.5, review_count=10, is_verified=True, photo_url="x"))
    db.commit()
    return uid


def test_search_orders_by_distance(client, db):
    # near Nashik centre 19.9975,73.7898
    _make_doctor(db, "Dr Near", "Cardiology", 19.99, 73.79, 400)
    _make_doctor(db, "Dr Far", "Cardiology", 20.30, 74.20, 500)
    r = client.get("/v1/doctors", params={"specialty": "Cardiology",
                                           "lat": 19.9975, "lng": 73.7898, "radiusKm": 100})
    assert r.status_code == 200
    names = [d["name"] for d in r.json()]
    assert names.index("Dr Near") < names.index("Dr Far")
```

- [ ] **Step 5: Run the test**

Run: `pytest tests/test_doctors.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/api/app/services/doctor_service.py apps/api/app/routers/doctors.py apps/api/app/main.py apps/api/tests/test_doctors.py
git commit -m "add postgis doctor search and detail"
```

---

## Task 8: Doctor portal — queue, patient file, refer, prescribe

**Files:**
- Create: `apps/api/app/routers/doctor_portal.py`, `apps/api/app/services/prescription_service.py`
- Modify: `apps/api/app/main.py`
- Test: `apps/api/tests/test_doctor_portal.py`

**Interfaces:**
- Consumes: models, `schemas.consultation.QueueItemOut`, `schemas.prescription.ReferIn/PrescribeIn`.
- Produces: `prescription_service.create(db, consultation_id, lines) -> Prescription`, `prescription_service.refer(db, consultation_id, from_doctor_id, to_specialty, reason) -> Referral`.
- Routes: `GET /v1/doctor/queue`, `GET /v1/doctor/consultations/{id}`, `POST /v1/doctor/consultations/{id}/refer`, `POST /v1/doctor/consultations/{id}/prescribe`.
- Acuity ordering for the queue: EMERGENCY > URGENT > PRIORITY > ROUTINE.

- [ ] **Step 1: Implement `apps/api/app/services/prescription_service.py`**

```python
import uuid

from sqlalchemy.orm import Session

from app.models import Prescription, PrescriptionLine, Referral
from app.schemas.prescription import PrescriptionLineIn


def create(db: Session, consultation_id, lines: list[PrescriptionLineIn]) -> Prescription:
    pres = Prescription(id=uuid.uuid4(), consultation_id=consultation_id)
    db.add(pres)
    db.flush()
    for ln in lines:
        db.add(PrescriptionLine(
            id=uuid.uuid4(), prescription_id=pres.id, drug=ln.drug, strength=ln.strength,
            frequency=ln.frequency, duration_days=ln.durationDays, notes=ln.notes,
        ))
    db.commit()
    db.refresh(pres)
    return pres


def refer(db: Session, consultation_id, from_doctor_id, to_specialty: str, reason: str) -> Referral:
    ref = Referral(id=uuid.uuid4(), consultation_id=consultation_id,
                   from_doctor_id=from_doctor_id, to_specialty=to_specialty, reason=reason)
    db.add(ref)
    db.commit()
    db.refresh(ref)
    return ref
```

- [ ] **Step 2: Implement `apps/api/app/routers/doctor_portal.py`**

```python
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_role
from app.models import Consultation, ConsultationStatus, Patient, TriageResult, User
from app.schemas.common import TriageResultOut
from app.schemas.consultation import QueueItemOut
from app.schemas.prescription import PrescribeIn, ReferIn
from app.services import audit_service, prescription_service

router = APIRouter(prefix="/v1/doctor", tags=["doctor"])

_ORDER = {"EMERGENCY": 0, "URGENT": 1, "PRIORITY": 2, "ROUTINE": 3}


@router.get("/queue", response_model=list[QueueItemOut])
def queue(user: User = Depends(require_role("doctor")), db: Session = Depends(get_db)):
    rows = db.execute(
        select(Consultation, TriageResult, User, Patient)
        .join(TriageResult, TriageResult.consultation_id == Consultation.id)
        .join(User, User.id == Consultation.patient_id)
        .join(Patient, Patient.user_id == Consultation.patient_id)
        .where(Consultation.doctor_id == user.id)
        .where(Consultation.status == ConsultationStatus.BOOKED)
    ).all()
    items = []
    for consult, tr, patient_user, patient in rows:
        acuity = tr.acuity.value if hasattr(tr.acuity, "value") else tr.acuity
        items.append(QueueItemOut(
            id=str(consult.id), patientName=patient_user.name, patientAge=patient.age or 0,
            patientSex=patient.sex or "O", acuity=acuity, complaint=consult.symptom_text_raw,
            bookedFor=consult.booked_for or "",
            triage=TriageResultOut(
                acuity=acuity, acuityConfidence=tr.acuity_confidence,
                specialties=tr.specialties, drivers=tr.drivers, labs=[],
                redFlags=tr.red_flags, modelVersion=tr.model_version,
            ),
        ))
    items.sort(key=lambda i: _ORDER[i.acuity])
    audit_service.log(db, user.id, "view_queue", "doctor", str(user.id))
    return items


@router.post("/consultations/{consultation_id}/refer")
def refer(consultation_id: str, body: ReferIn,
          user: User = Depends(require_role("doctor")), db: Session = Depends(get_db)) -> dict:
    prescription_service.refer(db, consultation_id, user.id, body.toSpecialty, body.reason)
    audit_service.log(db, user.id, "refer", "consultation", consultation_id)
    return {"referred": True}


@router.post("/consultations/{consultation_id}/prescribe")
def prescribe(consultation_id: str, body: PrescribeIn,
              user: User = Depends(require_role("doctor")), db: Session = Depends(get_db)) -> dict:
    pres = prescription_service.create(db, consultation_id, body.lines)
    audit_service.log(db, user.id, "prescribe", "consultation", consultation_id)
    return {"prescriptionId": str(pres.id)}
```

- [ ] **Step 3: Register router in `apps/api/app/main.py`**.

- [ ] **Step 4: Write the failing test `apps/api/tests/test_doctor_portal.py`**

```python
import uuid

from app.models import (
    Consultation, ConsultationStatus, Patient, Role, TriageResult, User,
)


def _doctor_token(client):
    client.post("/v1/auth/request-otp", json={"phone": "+918000000001"})
    r = client.post("/v1/auth/verify-otp",
                    json={"phone": "+918000000001", "code": "123456", "role": "doctor", "name": "Dr Q"})
    return r.json()["accessToken"], r.json()["userId"]


def test_queue_sorted_emergency_first(client, db):
    token, doctor_id = _doctor_token(client)
    pid = uuid.uuid4()
    db.add(User(id=pid, phone=f"+91{uuid.uuid4().int % 10**10:010d}", role=Role.patient, name="P"))
    db.add(Patient(user_id=pid, age=40, sex="M"))
    for acuity in ("ROUTINE", "EMERGENCY"):
        cid = uuid.uuid4()
        db.add(Consultation(id=cid, patient_id=pid, doctor_id=doctor_id,
                            status=ConsultationStatus.BOOKED, symptom_text_raw="x", booked_for="10:00"))
        db.add(TriageResult(id=uuid.uuid4(), consultation_id=cid, acuity=acuity,
                            acuity_confidence=0.9, specialties=[], drivers=[], red_flags=[],
                            model_version="stub-keyword-v0"))
    db.commit()
    r = client.get("/v1/doctor/queue", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()[0]["acuity"] == "EMERGENCY"
```

- [ ] **Step 5: Run the test**

Run: `pytest tests/test_doctor_portal.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/api/app/routers/doctor_portal.py apps/api/app/services/prescription_service.py apps/api/app/main.py apps/api/tests/test_doctor_portal.py
git commit -m "add doctor portal queue refer and prescribe"
```

---

## Task 9: Prescriptions + mandatory pharmacy consent + pharmacy routing

**Files:**
- Create: `apps/api/app/routers/prescriptions.py`, `apps/api/app/routers/pharmacies.py`, `apps/api/app/services/pharmacy_service.py`
- Modify: `apps/api/app/main.py`
- Test: `apps/api/tests/test_prescriptions.py`, `apps/api/tests/test_pharmacies.py`

**Interfaces:**
- Consumes: models, `schemas.prescription.ConsentIn/PrescriptionOut`, `schemas.pharmacy.OfferOut`.
- Produces: `pharmacy_service.grant_consent(db, prescription_id, pharmacy_ids) -> None` (creates ranked `PharmacyConsent` rows + a PENDING `PharmacyOffer` for the first-ranked pharmacy only), `pharmacy_service.decline(db, offer_id) -> PharmacyOffer|None` (marks declined, opens the next-ranked offer; returns the new offer or None if exhausted), `pharmacy_service.accept(db, offer_id)`.
- Routes: `GET /v1/prescriptions/{id}`, `POST /v1/prescriptions/{id}/consent`, `GET /v1/pharmacy/inbox`, `POST /v1/pharmacy/offers/{id}/accept`, `POST /v1/pharmacy/offers/{id}/decline`.
- Consent invariant: order of `pharmacyIds` in the request IS the routing order (patient-chosen). First pharmacy gets the only open offer; routing advances on decline.

- [ ] **Step 1: Implement `apps/api/app/services/pharmacy_service.py`**

```python
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    OfferStatus, PharmacyConsent, PharmacyOffer, Prescription, PrescriptionStatus,
)


def grant_consent(db: Session, prescription_id, pharmacy_ids: list[str]) -> None:
    if not pharmacy_ids:
        raise ValueError("at least one pharmacy must be chosen")
    for rank, pid in enumerate(pharmacy_ids):
        db.add(PharmacyConsent(id=uuid.uuid4(), prescription_id=prescription_id,
                               pharmacy_id=pid, rank=rank))
    # open an offer for the first-ranked pharmacy only
    db.add(PharmacyOffer(id=uuid.uuid4(), prescription_id=prescription_id,
                         pharmacy_id=pharmacy_ids[0], status=OfferStatus.PENDING, rank=0))
    db.commit()


def _next_consent(db: Session, prescription_id, after_rank: int) -> PharmacyConsent | None:
    return db.scalar(
        select(PharmacyConsent).where(PharmacyConsent.prescription_id == prescription_id)
        .where(PharmacyConsent.rank > after_rank).order_by(PharmacyConsent.rank.asc())
    )


def decline(db: Session, offer_id) -> PharmacyOffer | None:
    offer = db.get(PharmacyOffer, offer_id)
    offer.status = OfferStatus.DECLINED
    nxt = _next_consent(db, offer.prescription_id, offer.rank)
    new_offer = None
    if nxt is not None:
        new_offer = PharmacyOffer(id=uuid.uuid4(), prescription_id=offer.prescription_id,
                                  pharmacy_id=nxt.pharmacy_id, status=OfferStatus.PENDING,
                                  rank=nxt.rank)
        db.add(new_offer)
    else:
        pres = db.get(Prescription, offer.prescription_id)
        pres.status = PrescriptionStatus.DECLINED
    db.commit()
    return new_offer


def accept(db: Session, offer_id) -> None:
    offer = db.get(PharmacyOffer, offer_id)
    offer.status = OfferStatus.ACCEPTED
    pres = db.get(Prescription, offer.prescription_id)
    pres.status = PrescriptionStatus.ACCEPTED
    db.commit()
```

- [ ] **Step 2: Implement `apps/api/app/routers/prescriptions.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user, require_role
from app.models import Consultation, Prescription, PrescriptionLine, User
from app.schemas.prescription import ConsentIn, PrescriptionLineOut, PrescriptionOut
from app.services import audit_service, pharmacy_service

router = APIRouter(prefix="/v1/prescriptions", tags=["prescriptions"])


@router.get("/{prescription_id}", response_model=PrescriptionOut)
def get(prescription_id: str, user: User = Depends(get_current_user),
        db: Session = Depends(get_db)) -> PrescriptionOut:
    pres = db.get(Prescription, prescription_id)
    if pres is None:
        raise HTTPException(status_code=404, detail="not found")
    lines = db.scalars(
        select(PrescriptionLine).where(PrescriptionLine.prescription_id == pres.id)
    ).all()
    consult = db.get(Consultation, pres.consultation_id)
    patient = db.get(User, consult.patient_id)
    doctor = db.get(User, consult.doctor_id) if consult.doctor_id else None
    audit_service.log(db, user.id, "view_prescription", "prescription", prescription_id)
    return PrescriptionOut(
        id=str(pres.id), patientName=patient.name if patient else "",
        doctorName=doctor.name if doctor else "", issuedAt=str(pres.issued_at),
        lines=[PrescriptionLineOut(drug=ln.drug, strength=ln.strength, frequency=ln.frequency,
                                   durationDays=ln.duration_days, notes=ln.notes) for ln in lines],
        status=pres.status.value if hasattr(pres.status, "value") else pres.status,
    )


@router.post("/{prescription_id}/consent")
def consent(prescription_id: str, body: ConsentIn, user: User = Depends(require_role("patient")),
            db: Session = Depends(get_db)) -> dict:
    if not body.pharmacyIds:
        raise HTTPException(status_code=400, detail="at least one pharmacy required")
    pharmacy_service.grant_consent(db, prescription_id, body.pharmacyIds)
    audit_service.log(db, user.id, "consent", "prescription", prescription_id)
    return {"consented": True, "routedTo": body.pharmacyIds[0]}
```

- [ ] **Step 3: Implement `apps/api/app/routers/pharmacies.py`**

```python
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_role
from app.models import (
    Consultation, OfferStatus, PharmacyOffer, Prescription, PrescriptionLine, User,
)
from app.services import audit_service, pharmacy_service

router = APIRouter(prefix="/v1/pharmacy", tags=["pharmacy"])


@router.get("/inbox")
def inbox(user: User = Depends(require_role("pharmacy")), db: Session = Depends(get_db)) -> list[dict]:
    offers = db.scalars(
        select(PharmacyOffer).where(PharmacyOffer.pharmacy_id == user.id)
        .where(PharmacyOffer.status == OfferStatus.PENDING)
    ).all()
    out = []
    for offer in offers:
        pres = db.get(Prescription, offer.prescription_id)
        consult = db.get(Consultation, pres.consultation_id)
        patient = db.get(User, consult.patient_id)
        lines = db.scalars(
            select(PrescriptionLine).where(PrescriptionLine.prescription_id == pres.id)
        ).all()
        out.append({
            "id": str(offer.id), "prescriptionId": str(pres.id),
            "patientName": patient.name if patient else "", "status": offer.status.value,
            "lines": [{"drug": ln.drug, "strength": ln.strength, "frequency": ln.frequency,
                       "durationDays": ln.duration_days} for ln in lines],
        })
    return out


@router.post("/offers/{offer_id}/accept")
def accept(offer_id: str, user: User = Depends(require_role("pharmacy")),
           db: Session = Depends(get_db)) -> dict:
    pharmacy_service.accept(db, offer_id)
    audit_service.log(db, user.id, "accept_offer", "offer", offer_id)
    return {"accepted": True}


@router.post("/offers/{offer_id}/decline")
def decline(offer_id: str, user: User = Depends(require_role("pharmacy")),
            db: Session = Depends(get_db)) -> dict:
    nxt = pharmacy_service.decline(db, offer_id)
    audit_service.log(db, user.id, "decline_offer", "offer", offer_id)
    return {"declined": True, "forwarded": nxt is not None}
```

- [ ] **Step 4: Register both routers in `apps/api/app/main.py`**.

- [ ] **Step 5: Write failing test `apps/api/tests/test_pharmacies.py`**

```python
import uuid

from app.models import (
    Consultation, Prescription, Role, User,
)


def _pharmacy_token(client, phone):
    client.post("/v1/auth/request-otp", json={"phone": phone})
    r = client.post("/v1/auth/verify-otp",
                    json={"phone": phone, "code": "123456", "role": "pharmacy", "name": "Ph"})
    return r.json()["accessToken"], r.json()["userId"]


def test_decline_forwards_to_next_pharmacy(client, db):
    t1, ph1 = _pharmacy_token(client, "+917000000001")
    t2, ph2 = _pharmacy_token(client, "+917000000002")
    pat = uuid.uuid4()
    db.add(User(id=pat, phone=f"+91{uuid.uuid4().int % 10**10:010d}", role=Role.patient, name="P"))
    cid, prid = uuid.uuid4(), uuid.uuid4()
    db.add(Consultation(id=cid, patient_id=pat))
    db.add(Prescription(id=prid, consultation_id=cid))
    db.commit()
    from app.services import pharmacy_service
    pharmacy_service.grant_consent(db, prid, [ph1, ph2])

    inbox1 = client.get("/v1/pharmacy/inbox", headers={"Authorization": f"Bearer {t1}"}).json()
    assert len(inbox1) == 1
    offer_id = inbox1[0]["id"]
    r = client.post(f"/v1/pharmacy/offers/{offer_id}/decline",
                    headers={"Authorization": f"Bearer {t1}"})
    assert r.json()["forwarded"] is True
    inbox2 = client.get("/v1/pharmacy/inbox", headers={"Authorization": f"Bearer {t2}"}).json()
    assert len(inbox2) == 1
```

- [ ] **Step 6: Write failing test `apps/api/tests/test_prescriptions.py`**

```python
def test_consent_requires_at_least_one_pharmacy(client, patient_token):
    # craft a prescription id that does not exist is fine; validation happens before lookup
    h = {"Authorization": f"Bearer {patient_token}"}
    r = client.post("/v1/prescriptions/00000000-0000-0000-0000-000000000000/consent",
                    json={"pharmacyIds": []}, headers=h)
    assert r.status_code == 400
```

- [ ] **Step 7: Run both tests**

Run: `pytest tests/test_pharmacies.py tests/test_prescriptions.py -v`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add apps/api/app/routers/prescriptions.py apps/api/app/routers/pharmacies.py apps/api/app/services/pharmacy_service.py apps/api/app/main.py apps/api/tests/test_pharmacies.py apps/api/tests/test_prescriptions.py
git commit -m "add prescriptions consent and pharmacy routing"
```

---

## Task 10: Uploads — pre-signed URLs (MinIO/R2)

**Files:**
- Create: `apps/api/app/routers/uploads.py`, `apps/api/app/services/storage_service.py`
- Modify: `apps/api/app/main.py`
- Test: `apps/api/tests/test_uploads.py`

**Interfaces:**
- Produces: `storage_service.presign_put(object_key) -> str` using boto3 against the S3-compatible endpoint.
- Route: `POST /v1/uploads/sign {contentType?} -> {url, objectKey}`.

- [ ] **Step 1: Implement `apps/api/app/services/storage_service.py`**

```python
import boto3
from botocore.client import Config

from app.core.config import settings


def _client():
    return boto3.client(
        "s3", endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_key, aws_secret_access_key=settings.s3_secret,
        config=Config(signature_version="s3v4"), region_name="us-east-1",
    )


def presign_put(object_key: str) -> str:
    return _client().generate_presigned_url(
        "put_object",
        Params={"Bucket": settings.s3_bucket, "Key": object_key},
        ExpiresIn=300,
    )
```

- [ ] **Step 2: Implement `apps/api/app/routers/uploads.py`**

```python
import uuid

from fastapi import APIRouter, Depends

from app.core.deps import require_role
from app.models import User
from app.services import storage_service

router = APIRouter(prefix="/v1/uploads", tags=["uploads"])


@router.post("/sign")
def sign(user: User = Depends(require_role("patient"))) -> dict:
    key = f"reports/{user.id}/{uuid.uuid4()}.webp"
    return {"url": storage_service.presign_put(key), "objectKey": key}
```

- [ ] **Step 3: Register router in `apps/api/app/main.py`**.

- [ ] **Step 4: Write the failing test `apps/api/tests/test_uploads.py`**

```python
def test_sign_returns_url_and_key(client, patient_token, monkeypatch):
    from app.services import storage_service
    monkeypatch.setattr(storage_service, "presign_put", lambda key: f"http://minio/{key}?sig=x")
    r = client.post("/v1/uploads/sign", headers={"Authorization": f"Bearer {patient_token}"})
    assert r.status_code == 200
    assert r.json()["url"].startswith("http")
    assert r.json()["objectKey"].startswith("reports/")
```

- [ ] **Step 5: Run the test**

Run: `pytest tests/test_uploads.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/api/app/routers/uploads.py apps/api/app/services/storage_service.py apps/api/app/main.py apps/api/tests/test_uploads.py
git commit -m "add presigned upload url endpoint"
```

---

## Task 11: Seed script — 10 doctors, 6 queue items, 5 pharmacies, lab panels

**Files:**
- Create: `apps/api/seed/seed.py`
- Test: `apps/api/tests/test_seed.py`
- Uses: `apps/api/seed/doctor_headshots.json` (already in repo)

**Interfaces:**
- Consumes: all models; `seed/doctor_headshots.json`.
- Produces: `seed.run(db)` — idempotent (skips if a known seed phone already exists). Inserts 10 doctors with real Nashik-area coordinates, authentic Indian names, specialties, fees ₹200–800, ratings 3.8–4.9, languages; 5 pharmacies (some `is_open=False`); a demo patient with 6 booked consultations + triage rows spanning all four acuity levels.

- [ ] **Step 1: Implement `apps/api/seed/seed.py`**

```python
import json
import pathlib
import uuid

from geoalchemy2.elements import WKTElement
from sqlalchemy import select

from app.core.db import SessionLocal
from app.models import (
    Consultation, ConsultationStatus, Doctor, Patient, Pharmacy, Role, TriageResult, User,
)

HEADSHOTS = json.loads((pathlib.Path(__file__).parent / "doctor_headshots.json").read_text())
_TMPL = HEADSHOTS["url_template"]
_PHOTOS = [_TMPL.replace("{id}", h["id"]) for h in HEADSHOTS["headshots"]]

# (name, specialty, qual, exp, fee, rating, reviews, langs, lat, lng)
DOCTORS = [
    ("Dr. Anjali Deshmukh", "Cardiology", "MBBS, MD, DM", 14, 800, 4.9, 212, ["Hindi", "Marathi", "English"], 19.9975, 73.7898),
    ("Dr. Rohan Kulkarni", "General Physician", "MBBS", 6, 300, 4.3, 88, ["Hindi", "Marathi"], 20.0110, 73.7900),
    ("Dr. Sneha Patil", "General Medicine", "MBBS, MD", 9, 450, 4.6, 134, ["Marathi", "English"], 19.9600, 73.8300),
    ("Dr. Imran Shaikh", "ENT", "MBBS, MS", 11, 500, 4.5, 156, ["Hindi", "English"], 20.0300, 73.7700),
    ("Dr. Priya Nair", "Dermatology", "MBBS, MD", 8, 600, 4.7, 190, ["English", "Hindi"], 19.9400, 73.7600),
    ("Dr. Vikram Jadhav", "Orthopaedics", "MBBS, MS", 16, 700, 4.8, 203, ["Marathi", "Hindi"], 20.0500, 73.8100),
    ("Dr. Meera Joshi", "Gynaecology", "MBBS, MD", 12, 650, 4.6, 171, ["Marathi", "English", "Hindi"], 19.9700, 73.8000),
    ("Dr. Sameer Pawar", "Paediatrics", "MBBS, MD", 7, 400, 4.4, 97, ["Hindi", "Marathi"], 20.0200, 73.8200),
    ("Dr. Kavita Rao", "General Physician", "MBBS", 5, 250, 4.2, 61, ["Marathi"], 19.9300, 73.7500),
    ("Dr. Arjun Menon", "Haematology", "MBBS, MD, DM", 13, 750, 4.7, 145, ["English", "Hindi"], 20.0400, 73.7950),
]

PHARMACIES = [
    ("Nashik Medico", "MH-PH-1001", 19.9980, 73.7905, True, True),
    ("Godavari Pharmacy", "MH-PH-1002", 20.0100, 73.7890, True, True),
    ("Shree Medical Store", "MH-PH-1003", 19.9650, 73.8250, False, False),
    ("Panchavati Chemists", "MH-PH-1004", 20.0350, 73.7720, True, True),
    ("Trimurti Pharma", "MH-PH-1005", 19.9450, 73.7650, False, True),
]

QUEUE = [
    ("Ramesh Pawar", 58, "M", "EMERGENCY", "chest pain and breathlessness"),
    ("Sunita Jadhav", 34, "F", "URGENT", "severe abdominal pain"),
    ("Imran Khan", 41, "M", "PRIORITY", "mujhe chakkar aa raha hai"),
    ("Lata More", 29, "F", "ROUTINE", "fever and cough for two days"),
    ("Vijay Shinde", 63, "M", "PRIORITY", "weakness and dizziness"),
    ("Pooja Deshpande", 7, "F", "ROUTINE", "mild cold"),
]


def _wkt(lat, lng):
    return WKTElement(f"POINT({lng} {lat})", srid=4326)


def run(db) -> None:
    if db.scalar(select(User).where(User.phone == "+915000000001")):
        return  # already seeded

    for i, (name, spec, qual, exp, fee, rating, reviews, langs, lat, lng) in enumerate(DOCTORS):
        uid = uuid.uuid4()
        db.add(User(id=uid, phone=f"+9150000100{i:02d}", role=Role.doctor, name=name, lang="mr"))
        db.add(Doctor(user_id=uid, specialty=spec, qualifications=qual, reg_number=f"MH{10000+i}",
                      experience_years=exp, fee_inr=fee, languages=langs, location=_wkt(lat, lng),
                      rating=rating, review_count=reviews, is_verified=True,
                      photo_url=_PHOTOS[i % len(_PHOTOS)]))

    for i, (name, lic, lat, lng, delivers, is_open) in enumerate(PHARMACIES):
        uid = uuid.uuid4()
        db.add(User(id=uid, phone=f"+9150000200{i:02d}", role=Role.pharmacy, name=name, lang="mr"))
        db.add(Pharmacy(user_id=uid, name=name, licence_number=lic, location=_wkt(lat, lng),
                        delivers=delivers, is_open=is_open))

    # a demo doctor to own the queue
    doc_uid = uuid.uuid4()
    db.add(User(id=doc_uid, phone="+915000000001", role=Role.doctor, name="Dr. Demo Queue", lang="en"))
    db.add(Doctor(user_id=doc_uid, specialty="General Medicine", qualifications="MBBS, MD",
                  reg_number="MH99999", experience_years=10, fee_inr=400, languages=["Hindi", "English"],
                  location=_wkt(19.9975, 73.7898), rating=4.5, review_count=100,
                  is_verified=True, photo_url=_PHOTOS[0]))
    db.flush()

    for i, (pname, age, sex, acuity, complaint) in enumerate(QUEUE):
        pat_uid = uuid.uuid4()
        db.add(User(id=pat_uid, phone=f"+9150000300{i:02d}", role=Role.patient, name=pname, lang="hi"))
        db.add(Patient(user_id=pat_uid, age=age, sex=sex, location=_wkt(19.99, 73.79)))
        cid = uuid.uuid4()
        db.add(Consultation(id=cid, patient_id=pat_uid, doctor_id=doc_uid,
                            status=ConsultationStatus.BOOKED, symptom_text_raw=complaint,
                            symptom_text_normalised=complaint, booked_for="10:00"))
        db.add(TriageResult(id=uuid.uuid4(), consultation_id=cid, acuity=acuity,
                            acuity_confidence=0.9,
                            specialties=[{"name": "General Medicine", "score": 0.8},
                                         {"name": "Cardiology", "score": 0.1},
                                         {"name": "ENT", "score": 0.1}],
                            drivers=[{"feature": "symptom", "contribution": 0.5}],
                            red_flags=["chest pain with breathlessness"] if acuity == "EMERGENCY" else [],
                            model_version="stub-keyword-v0"))
    db.commit()


if __name__ == "__main__":
    session = SessionLocal()
    try:
        run(session)
        print("seeded")
    finally:
        session.close()
```

- [ ] **Step 2: Write the failing test `apps/api/tests/test_seed.py`**

```python
from sqlalchemy import select

from app.models import Doctor, Pharmacy, TriageResult
from seed.seed import run


def test_seed_inserts_doctors_pharmacies_and_all_acuities(db):
    run(db)
    doctors = db.scalars(select(Doctor)).all()
    pharmacies = db.scalars(select(Pharmacy)).all()
    acuities = {
        (t.acuity.value if hasattr(t.acuity, "value") else t.acuity)
        for t in db.scalars(select(TriageResult)).all()
    }
    assert len(doctors) >= 10
    assert len(pharmacies) >= 5
    assert {"ROUTINE", "PRIORITY", "URGENT", "EMERGENCY"}.issubset(acuities)


def test_seed_is_idempotent(db):
    run(db)
    first = len(db.scalars(select(Doctor)).all())
    run(db)
    assert len(db.scalars(select(Doctor)).all()) == first
```

- [ ] **Step 3: Run the seed test**

Run (from `apps/api`, DB migrated): `pytest tests/test_seed.py -v`
Expected: PASS (ensure `apps/api` is on `sys.path` so `import seed.seed` resolves; add `pythonpath = ["."]` under `[tool.pytest.ini_options]` in `pyproject.toml` if needed).

- [ ] **Step 4: Commit**

```bash
git add apps/api/seed/seed.py apps/api/tests/test_seed.py apps/api/pyproject.toml
git commit -m "add seed data for doctors pharmacies and demo queue"
```

---

## Task 12: Full-stack wiring — Dockerfile, compose services, OpenAPI → shared TS types

**Files:**
- Create: `apps/api/Dockerfile`
- Modify: `infra/docker-compose.yml` (add `api` and `ml-service` services)
- Create: `packages/shared-types/package.json`, `packages/shared-types/gen.md`, `packages/shared-types/src/types.ts`
- Test: `apps/api/tests/test_openapi.py`

**Interfaces:**
- Produces: a `docker compose up` that brings up db, minio, ml-service, api together; a checked-in `packages/shared-types/src/types.ts` for the frontends; the api `/openapi.json` reflecting all routes.

- [ ] **Step 1: Create `apps/api/Dockerfile`**

```dockerfile
FROM python:3.11-slim
WORKDIR /srv
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini .
COPY seed ./seed
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Add `api` and `ml-service` to `infra/docker-compose.yml`**

```yaml
  ml-service:
    build: ../apps/ml-service
    ports: ["8001:8001"]
  api:
    build: ../apps/api
    depends_on:
      db: {condition: service_healthy}
    environment:
      DATABASE_URL: postgresql+psycopg://nadi:nadi@db:5432/nadi
      ML_SERVICE_URL: http://ml-service:8001
      S3_ENDPOINT: http://minio:9000
    ports: ["8000:8000"]
```

- [ ] **Step 3: Write the failing test `apps/api/tests/test_openapi.py`**

```python
def test_openapi_lists_core_routes(client):
    spec = client.get("/openapi.json").json()
    paths = spec["paths"].keys()
    for p in ["/v1/auth/verify-otp", "/v1/consultations/intake",
              "/v1/doctors", "/v1/doctor/queue",
              "/v1/prescriptions/{prescription_id}/consent", "/v1/pharmacy/inbox"]:
        assert p in paths
```

- [ ] **Step 4: Run the test**

Run: `pytest tests/test_openapi.py -v`
Expected: PASS.

- [ ] **Step 5: Generate shared TS types**

Create `packages/shared-types/package.json`:

```json
{
  "name": "@nadi/shared-types",
  "version": "0.1.0",
  "types": "src/types.ts",
  "scripts": {
    "gen": "openapi-typescript http://localhost:8000/openapi.json -o src/types.ts"
  },
  "devDependencies": { "openapi-typescript": "^7" }
}
```

Create `packages/shared-types/gen.md`:

```md
# Regenerating shared types
1. Start the API: `docker compose -f infra/docker-compose.yml up -d api`
2. From `packages/shared-types`: `npm install && npm run gen`
3. Commit the updated `src/types.ts`.
The frozen hand-written contract types also live in ProjectPlan.md §9; the generated
file must stay compatible with them.
```

Create `packages/shared-types/src/types.ts` with the §9 hand-authored types as the initial checked-in version:

```ts
export type Acuity = 'ROUTINE' | 'PRIORITY' | 'URGENT' | 'EMERGENCY';

export interface LabValue {
  analyte: string; value: number; unit: string; refRange: string; flag: 'L' | 'N' | 'H';
}
export interface TriageInput {
  symptomText: string; reportImageUris: string[]; age?: number;
  sex?: 'M' | 'F' | 'O'; lang: 'en' | 'hi' | 'mr';
}
export interface TriageResult {
  acuity: Acuity; acuityConfidence: number;
  specialties: { name: string; score: number }[];
  drivers: { feature: string; contribution: number }[];
  labs: LabValue[]; redFlags: string[]; modelVersion: string;
}
export interface Doctor {
  id: string; name: string; specialty: string; qualifications: string;
  experienceYears: number; distanceKm: number; feeInr: number; rating: number;
  reviewCount: number; languages: string[]; nextSlot: string;
  photoUrl: string; availableSlots: string[];
}
export interface QueueItem {
  id: string; patientName: string; patientAge: number; patientSex: 'M' | 'F' | 'O';
  acuity: Acuity; complaint: string; bookedFor: string; triage: TriageResult;
}
export interface PrescriptionLine {
  drug: string; strength: string; frequency: string; durationDays: number; notes?: string;
}
export interface Prescription {
  id: string; patientName: string; doctorName: string; issuedAt: string;
  lines: PrescriptionLine[]; status: 'PENDING' | 'ACCEPTED' | 'DECLINED' | 'DELIVERED';
}
export interface Pharmacy {
  id: string; name: string; distanceKm: number; deliversInMins: number; isOpen: boolean;
}
```

- [ ] **Step 6: Run the whole api suite once**

Run (from `apps/api`): `pytest -v`
Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add apps/api/Dockerfile infra/docker-compose.yml packages/shared-types apps/api/tests/test_openapi.py
git commit -m "add full-stack compose wiring and shared types"
```

---

## Task 13: End-to-end smoke test + ADRs

**Files:**
- Create: `apps/api/tests/test_e2e_flow.py`
- Create: `docs/decisions/ADR-0001-production-first-build.md`, `docs/decisions/ADR-0002-stubbed-otp-and-ml.md`

**Interfaces:**
- Consumes: the full running api + ml-service. Produces: one test that walks patient intake → doctor queue/prescribe → patient consent → pharmacy accept.

- [ ] **Step 1: Write the end-to-end test `apps/api/tests/test_e2e_flow.py`**

```python
import uuid

from app.models import Patient, User


def _token(client, phone, role, name):
    client.post("/v1/auth/request-otp", json={"phone": phone})
    r = client.post("/v1/auth/verify-otp",
                    json={"phone": phone, "code": "123456", "role": role, "name": name})
    return r.json()["accessToken"], r.json()["userId"]


def test_full_patient_doctor_pharmacy_loop(client, db, monkeypatch):
    from app.services import ml_client
    monkeypatch.setattr(ml_client, "document", lambda k: [])
    monkeypatch.setattr(ml_client, "triage", lambda p: {
        "acuity": "PRIORITY", "acuityConfidence": 0.8,
        "specialties": [{"name": "General Medicine", "score": 0.8},
                        {"name": "Cardiology", "score": 0.1}, {"name": "ENT", "score": 0.1}],
        "drivers": [{"feature": "x", "contribution": 0.5}], "labs": [],
        "redFlags": [], "modelVersion": "stub-keyword-v0"})

    pt, patient_id = _token(client, "+916000000001", "patient", "E2E Patient")
    db.add(Patient(user_id=uuid.UUID(patient_id), age=40, sex="M"))
    db.commit()
    dt, doctor_id = _token(client, "+916000000002", "doctor", "E2E Doctor")
    pht, pharmacy_id = _token(client, "+916000000003", "pharmacy", "E2E Pharmacy")
    ph = {"Authorization": f"Bearer {pt}"}
    dh = {"Authorization": f"Bearer {dt}"}
    phh = {"Authorization": f"Bearer {pht}"}

    cid = client.post("/v1/consultations/intake",
                      json={"symptomText": "weakness", "reportImageUris": [],
                            "age": 40, "sex": "M", "lang": "en"}, headers=ph).json()["consultationId"]
    client.post(f"/v1/consultations/{cid}/book",
                json={"doctorId": doctor_id, "slot": "10:00"}, headers=ph)
    pres_id = client.post(f"/v1/doctor/consultations/{cid}/prescribe",
                          json={"lines": [{"drug": "Iron", "strength": "100mg",
                                           "frequency": "OD", "durationDays": 30}]},
                          headers=dh).json()["prescriptionId"]
    r = client.post(f"/v1/prescriptions/{pres_id}/consent",
                    json={"pharmacyIds": [pharmacy_id]}, headers=ph)
    assert r.status_code == 200
    inbox = client.get("/v1/pharmacy/inbox", headers=phh).json()
    assert len(inbox) == 1
    offer_id = inbox[0]["id"]
    acc = client.post(f"/v1/pharmacy/offers/{offer_id}/accept", headers=phh)
    assert acc.status_code == 200
```

- [ ] **Step 2: Run the e2e test**

Run: `pytest tests/test_e2e_flow.py -v`
Expected: PASS.

- [ ] **Step 3: Write `docs/decisions/ADR-0001-production-first-build.md`**

```md
# ADR-0001: Build production-first instead of a mock-only prototype

## Context
ProjectPlan.md §13 sequenced a mock-only Phase 1 before any backend. The near-term goal is a
live demo across three physical Android phones showing the workflow move between devices.

## Decision
Build the real FastAPI backend + Postgres/PostGIS now; all three portals talk to it over HTTP.
The §9 contract stays frozen.

## Options considered
- Mock-only per-device layer (plan default) — cannot show genuine cross-device sync.
- Thin real-time relay (e.g. Firestore) bolted onto mocks — throwaway, still not the real system.
- Real backend now (chosen) — genuine sync, and it is the Phase 2 system we need anyway.

## What we gave up
More upfront work than mock screens; some backend hardening (encryption at rest, cert pinning)
deferred to a later phase.
```

- [ ] **Step 4: Write `docs/decisions/ADR-0002-stubbed-otp-and-ml.md`**

```md
# ADR-0002: Stub OTP and ML behind the frozen contract for the demo

## Context
Trained models M1/M2/M3 require the annotated dataset and months of training (Phases 3–4).
Live SMS OTP to Indian numbers is subject to the TRAI DLT framework and can be filtered/delayed.

## Decision
Serve `/ml/v1/*` with deterministic keyword + red-flag logic (`model_version = stub-keyword-v0`),
and issue real JWTs after accepting a fixed stub OTP code. Both sit behind the frozen contract.

## Options considered
- Real SMS now — regulatory + reliability risk during a live demo.
- Firebase Phone Auth now — viable free path, deferred to post-demo as an isolated swap.
- Stubs (chosen) — zero cost, reproducible demo, swap-in later changes no contract.

## What we gave up
No real model accuracy or real SMS yet; these arrive in later phases without contract changes.
```

- [ ] **Step 5: Commit**

```bash
git add apps/api/tests/test_e2e_flow.py docs/decisions
git commit -m "add end-to-end smoke test and adrs"
```

---

## Self-Review

**Spec coverage:** §2 architecture → Tasks 1,4,12; §3 infra → Tasks 1,12; §4 design tokens → (frontend plans, not backend); §5 screens → backend endpoints feeding them covered Tasks 5–10; §6 data/API/invariants → Tasks 2,3 + immutability (prescriptions never updated) + model_version (Tasks 2,4,6) + append-only audit (Task 6); §7 stubbed ML → Task 4; §8 seed → Task 11; §9 demo flow → Task 13 e2e; §11 non-negotiables → Global Constraints + ADRs Task 13. Frontend (patient/doctor/pharmacy UI) is explicitly out of scope for THIS plan — separate plans follow.

**Placeholder scan:** no TBD/TODO; every code step shows complete code; every run step shows the command and expected result.

**Type consistency:** `TriageResultOut` fields (acuity, acuityConfidence, specialties, drivers, labs, redFlags, modelVersion) consistent across schemas (Task 3), ml stub (Task 4), consultations (Task 6), doctor queue (Task 8). `model_version` DB column ↔ `modelVersion` API field consistent. `pharmacy_service.grant_consent/decline/accept` signatures consistent between Task 9 service and its router + tests. Doctor `user_id` used as the public `id` consistently (doctor_service, seed, tests).

**Note for executor:** tests need a live migrated Postgres+PostGIS (`docker compose up -d db` then `alembic upgrade head`) and, for non-monkeypatched paths, the ml-service running (`uvicorn app.main:app --port 8001`). Most tests monkeypatch `ml_client`, so only Task 4 and manual e2e need the ml-service live.

---

## Execution Handoff

Next plans (separate files, after this one is green): `2026-10-03-nadi-mobile-patient-app.md`, `...doctor-portal.md`, `...pharmacy-portal.md`.
