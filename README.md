# Nadi

Telemedicine triage + routing backend. Patients describe symptoms and (optionally)
upload reports; a triage service assigns an acuity and specialties; doctors see a
prioritised queue, prescribe or refer; prescriptions route to pharmacies for fulfilment.

The near-term goal is a live demo across three phones (patient / doctor / pharmacy)
talking to one real backend. See `ProjectPlan.md` for the full spec (the §9 API
contract is frozen) and `docs/decisions/` for ADRs.

## Stack

- **apps/api** — FastAPI + SQLAlchemy + Alembic, Postgres/PostGIS.
- **apps/ml-service** — FastAPI triage/OCR **stub** (deterministic keyword + red-flag
  rules, `model_version = stub-keyword-v0`). Swappable behind the frozen `/ml/v1/*` contract.
- **packages/shared-types** — TypeScript types generated from the API's OpenAPI schema.
- **infra/docker-compose.yml** — db, minio (S3), ml-service, api.

## Run it

```bash
docker compose -f infra/docker-compose.yml up -d --build
```

The API container runs migrations (`alembic upgrade head`) and loads demo seed data on
start, so a fresh volume comes up working. Services:

- API → http://localhost:8000  (health: `/health`, docs: `/docs`)
- ML  → http://localhost:8001  (health: `/ml/v1/health`)
- MinIO console → http://localhost:9001  (user/pass: `nadi` / `nadi12345`)
- Postgres → localhost:**5433** (mapped off 5432 to avoid a native-Postgres clash)

## Demo accounts & auth

OTP is stubbed (ADR-0002): any phone "receives" the fixed code **`123456`**.

- **Patients** self-sign-up: `POST /v1/auth/verify-otp` with a new phone creates a patient.
  The requested `role` is **not** trusted for privilege — new signups are always patients.
- **Doctors / pharmacies** are provisioned server-side (the seed creates them) and simply
  log in with their seeded phone. The demo doctor that owns the seeded queue is
  `+915000000001`; seeded doctors are `+9150000100xx`, pharmacies `+9150000200xx`.

## Tests

Tests use FastAPI's `TestClient` against the Postgres in compose. Run them in the api
container (the production image omits dev deps):

```bash
docker compose -f infra/docker-compose.yml cp apps/api/tests api:/srv/tests
docker compose -f infra/docker-compose.yml cp apps/api/pyproject.toml api:/srv/pyproject.toml
docker compose -f infra/docker-compose.yml exec api pip install -q pytest pytest-asyncio
docker compose -f infra/docker-compose.yml exec api python -m pytest -q

docker compose -f infra/docker-compose.yml exec ml-service pip install -q pytest httpx
docker compose -f infra/docker-compose.yml exec ml-service python -m pytest -q
```

## Regenerating shared types

See `packages/shared-types/gen.md`. The generated `src/types.ts` must stay compatible
with the hand-written §9 contract in `ProjectPlan.md`.
