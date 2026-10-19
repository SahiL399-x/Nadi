# NADI Backend Expansion — Plan B: Core Pharmacy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax. Implements Stage B of `docs/superpowers/specs/2026-10-19-nadi-backend-expansion-design.md`. **Depends on Plan A.**

**Goal:** The Core pharmacy backend — a full order-status lifecycle, an orders board, status transitions, and pharmacy dashboard stats — seeded so the pharmacy dashboard reads as a busy, real operation.

**Architecture:** Extend the existing `PharmacyOffer`/`OfferStatus` with a richer lifecycle + a human `order_no`; new orders-board and status-transition endpoints alongside the existing `/v1/pharmacy/inbox` (which stays for the core consent flow). Thin routers → `pharmacy_service`/`stats_service`. Additive migrations chained after `0005`.

**Tech Stack:** As Plan A (FastAPI/SQLAlchemy/Alembic/pytest). Commands from `apps/api` via `.venv/Scripts/python`.

## Global Constraints

- Python type hints; `ruff`+`black`; pydantic at boundaries; routers thin, logic in `services/`.
- RBAC: a pharmacy sees only its own orders; it sees the prescription only, **never medical history** (§11).
- **No AI/tool attribution**; commits short, imperative, lowercase.
- Additive only; every endpoint has a response model + pytest; migrations chained/reversible; seed idempotent.
- Postgres enum additions via `op.get_context().autocommit_block()`.
- `totalInr` is a **deterministic demo-derived** figure (no pricing engine exists) — documented in code, never random.

## Conventions

- Migrations continue the chain: latest after Plan A is `0005_consultation_notes`. Add `0006_order_lifecycle`.
- Add a `pharmacy_token` test fixture (Task 1) for the seeded demo pharmacy `+915000020000`.

---

### Task 1: Order lifecycle (status enum + order_no) and the orders board

**Files:**
- Modify: `apps/api/app/models/prescription.py`
- Create: `apps/api/migrations/versions/0006_order_lifecycle.py`
- Create: `apps/api/app/schemas/order.py`
- Modify: `apps/api/app/services/pharmacy_service.py`
- Modify: `apps/api/app/routers/pharmacies.py`
- Modify: `apps/api/seed/seed.py`
- Modify: `apps/api/tests/conftest.py`
- Create: `apps/api/tests/test_orders.py`

**Interfaces:**
- Produces: expanded `OfferStatus` (`TO_VERIFY, PENDING, PREPARING, VERIFIED, OUT_FOR_DELIVERY, DELIVERED, COMPLETED, CANCELLED, DECLINED`); `PharmacyOffer.order_no`; `GET /v1/pharmacy/orders?status=` → `OrderOut[]` `{ id, orderNo, patientName, phone, itemsCount, totalInr, status, placedAt }`; a `pharmacy_token` fixture; seeded lifecycle orders.

- [ ] **Step 1: Add the `pharmacy_token` fixture**

Append to `apps/api/tests/conftest.py`:
```python
@pytest.fixture
def pharmacy_token(client) -> str:
    client.post("/v1/auth/request-otp", json={"phone": "+915000020000"})
    r = client.post("/v1/auth/verify-otp", json={"phone": "+915000020000", "code": "123456"})
    return r.json()["accessToken"]
```

- [ ] **Step 2: Write the failing test**

`apps/api/tests/test_orders.py`:
```python
def test_orders_requires_pharmacy(client):
    assert client.get("/v1/pharmacy/orders").status_code == 401

def test_orders_board_returns_seeded_orders(client, pharmacy_token):
    h = {"Authorization": f"Bearer {pharmacy_token}"}
    r = client.get("/v1/pharmacy/orders", headers=h)
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) >= 10
    assert {"id", "orderNo", "patientName", "itemsCount", "totalInr", "status", "placedAt"} <= set(rows[0].keys())
    assert all(o["orderNo"].startswith("NP") for o in rows)
```

- [ ] **Step 3: Run to verify it fails** → `pytest tests/test_orders.py -v` FAIL (404).

- [ ] **Step 4: Model change + migration**

In `apps/api/app/models/prescription.py`, expand `OfferStatus`:
```python
class OfferStatus(str, enum.Enum):
    TO_VERIFY = "TO_VERIFY"
    PENDING = "PENDING"
    PREPARING = "PREPARING"
    VERIFIED = "VERIFIED"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
```
Add to `PharmacyOffer`:
```python
    order_no: Mapped[str] = mapped_column(String, default="", index=True)
```

`apps/api/migrations/versions/0006_order_lifecycle.py`:
```python
"""pharmacy order lifecycle

Revision ID: 0006_order_lifecycle
Revises: 0005_consultation_notes
Create Date: 2026-10-19
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_order_lifecycle"
down_revision: str | None = "0005_consultation_notes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NEW = ["TO_VERIFY", "PREPARING", "VERIFIED", "OUT_FOR_DELIVERY", "DELIVERED", "COMPLETED", "CANCELLED"]


def upgrade() -> None:
    op.add_column("pharmacy_offers",
                  sa.Column("order_no", sa.String(), nullable=False, server_default=""))
    op.create_index("ix_pharmacy_offers_order_no", "pharmacy_offers", ["order_no"])
    with op.get_context().autocommit_block():
        for v in _NEW:
            op.execute(f"ALTER TYPE offer_status ADD VALUE IF NOT EXISTS '{v}'")


def downgrade() -> None:
    op.drop_index("ix_pharmacy_offers_order_no", table_name="pharmacy_offers")
    op.drop_column("pharmacy_offers", "order_no")
    # Postgres cannot drop enum values; the added labels remain.
```
Run: `alembic upgrade head`.

- [ ] **Step 5: Schema + service**

`apps/api/app/schemas/order.py`:
```python
from pydantic import BaseModel


class OrderOut(BaseModel):
    id: str
    orderNo: str
    patientName: str
    phone: str
    itemsCount: int
    totalInr: int
    status: str
    placedAt: str
```
In `apps/api/app/services/pharmacy_service.py` add (imports: `PrescriptionLine` already imported; add `OrderOut` from `app.schemas.order`, `func`):
```python
def _demo_total(lines: list) -> int:
    # Deterministic demo figure — no pricing engine exists. Stable per line set.
    return sum(40 + 10 * ln.duration_days for ln in lines)

def orders(db: Session, pharmacy_id, status: str | None) -> list[OrderOut]:
    stmt = (select(PharmacyOffer, Prescription, User)
            .join(Prescription, Prescription.id == PharmacyOffer.prescription_id)
            .join(Consultation, Consultation.id == Prescription.consultation_id)
            .join(User, User.id == Consultation.patient_id)
            .where(PharmacyOffer.pharmacy_id == pharmacy_id))
    if status and status != "all":
        stmt = stmt.where(PharmacyOffer.status == OfferStatus(status.upper()))
    rows = db.execute(stmt).all()
    out: list[OrderOut] = []
    for offer, pres, patient in rows:
        lines = list(db.scalars(select(PrescriptionLine)
                                .where(PrescriptionLine.prescription_id == pres.id)))
        out.append(OrderOut(
            id=str(offer.id), orderNo=offer.order_no or f"NP{str(offer.id)[:4].upper()}",
            patientName=patient.name if patient else "", phone=patient.phone if patient else "",
            itemsCount=len(lines), totalInr=_demo_total(lines),
            status=offer.status.value, placedAt=str(pres.issued_at)))
    return out
```

- [ ] **Step 6: Route**

In `apps/api/app/routers/pharmacies.py` add to the existing `/v1/pharmacy` router (import `OrderOut`):
```python
@router.get("/orders", response_model=list[OrderOut])
def orders(status: str | None = None, user: User = Depends(require_role("pharmacy")),
           db: Session = Depends(get_db)):
    return pharmacy_service.orders(db, user.id, status)
```

- [ ] **Step 7: Seed lifecycle orders**

In `apps/api/seed/seed.py`, add a helper that generates orders in each state for the demo pharmacy (`+915000020000`). It creates a lightweight patient + consultation + prescription + offer chain per order:
```python
ORDER_SEED = {  # status -> count (dashboard targets; stats compute from these)
    "PENDING": 12, "PREPARING": 5, "VERIFIED": 3,
    "OUT_FOR_DELIVERY": 5, "DELIVERED": 15, "COMPLETED": 13,
}

def _seed_orders(db, pharmacy_uid):
    from app.models import (Consultation, ConsultationStatus, OfferStatus, PharmacyOffer,
                            Prescription, PrescriptionLine, Patient, Role, User)
    n = 4500
    for status, count in ORDER_SEED.items():
        for _ in range(count):
            pid = uuid.uuid4()
            db.add(User(id=pid, phone=f"+9199{n:08d}", role=Role.patient, name=f"Patient {n}", lang="hi"))
            db.flush()
            db.add(Patient(user_id=pid, age=30 + (n % 40), sex="M" if n % 2 else "F",
                           location=_wkt(19.99, 73.79)))
            cid = uuid.uuid4()
            db.add(Consultation(id=cid, patient_id=pid, status=ConsultationStatus.DONE,
                                symptom_text_raw="follow-up", symptom_text_normalised="follow-up"))
            db.flush()
            pres = uuid.uuid4()
            db.add(Prescription(id=pres, consultation_id=cid))
            db.flush()
            db.add(PrescriptionLine(id=uuid.uuid4(), prescription_id=pres, drug="Paracetamol",
                                    strength="500mg", frequency="BD", duration_days=5, notes=None))
            db.add(PharmacyOffer(id=uuid.uuid4(), prescription_id=pres, pharmacy_id=pharmacy_uid,
                                 status=OfferStatus[status], rank=0, order_no=f"NP{n}"))
            n += 1
```
Call `_seed_orders(db, first_pharmacy_uid)` inside `run()` — capture the first pharmacy's `user_id` when seeding `PHARMACIES` (store `demo_pharmacy_uid = uid` on `i == 0`). Commit at the end as the existing seed does.

- [ ] **Step 8: Run tests + reseed** → reseed, then `pytest tests/test_orders.py tests/test_pharmacies.py -v` → PASS.

- [ ] **Step 9: Commit**

```bash
git add apps/api/app/models/prescription.py apps/api/migrations/versions/0006_order_lifecycle.py apps/api/app/schemas/order.py apps/api/app/services/pharmacy_service.py apps/api/app/routers/pharmacies.py apps/api/seed/seed.py apps/api/tests/conftest.py apps/api/tests/test_orders.py
git commit -m "add pharmacy order lifecycle and orders board"
```

---

### Task 2: Order status transitions

**Files:**
- Modify: `apps/api/app/services/pharmacy_service.py`
- Modify: `apps/api/app/routers/pharmacies.py`
- Modify: `apps/api/tests/test_orders.py`

**Interfaces:**
- Produces: `POST /v1/pharmacy/orders/{offerId}/status` `{ status }` → `{ status }`. Validates allowed forward transitions; rejects illegal ones with 400; `CANCELLED` allowed from any non-terminal state.

- [ ] **Step 1: Write the failing test**

Append to `apps/api/tests/test_orders.py`:
```python
def _first_order_in(client, h, status):
    rows = client.get("/v1/pharmacy/orders", params={"status": status}, headers=h).json()
    return rows[0]["id"] if rows else None

def test_advance_order_status(client, pharmacy_token):
    h = {"Authorization": f"Bearer {pharmacy_token}"}
    oid = _first_order_in(client, h, "pending")
    assert oid
    r = client.post(f"/v1/pharmacy/orders/{oid}/status", json={"status": "PREPARING"}, headers=h)
    assert r.status_code == 200 and r.json()["status"] == "PREPARING"

def test_illegal_transition_rejected(client, pharmacy_token):
    h = {"Authorization": f"Bearer {pharmacy_token}"}
    oid = _first_order_in(client, h, "delivered")
    if oid:
        r = client.post(f"/v1/pharmacy/orders/{oid}/status", json={"status": "PENDING"}, headers=h)
        assert r.status_code == 400
```

- [ ] **Step 2: Run to verify it fails** → `pytest tests/test_orders.py -k status -v` FAIL.

- [ ] **Step 3: Service — transition rules**

In `apps/api/app/services/pharmacy_service.py`:
```python
_ALLOWED: dict[str, set[str]] = {
    "PENDING": {"TO_VERIFY", "VERIFIED", "PREPARING", "CANCELLED"},
    "TO_VERIFY": {"VERIFIED", "PREPARING", "CANCELLED"},
    "VERIFIED": {"PREPARING", "CANCELLED"},
    "PREPARING": {"OUT_FOR_DELIVERY", "CANCELLED"},
    "OUT_FOR_DELIVERY": {"DELIVERED", "CANCELLED"},
    "DELIVERED": {"COMPLETED"},
    "COMPLETED": set(), "CANCELLED": set(), "DECLINED": set(), "ACCEPTED": {"PREPARING", "CANCELLED"},
}

def set_status(db: Session, offer_id, pharmacy_id, new_status: str) -> tuple[bool, bool]:
    """Returns (found, allowed)."""
    offer = _owned_offer(db, offer_id, pharmacy_id)
    if offer is None:
        return (False, False)
    target = new_status.upper()
    if target not in _ALLOWED.get(offer.status.value, set()):
        return (True, False)
    offer.status = OfferStatus(target)
    db.commit()
    return (True, True)
```

- [ ] **Step 4: Route**

In `apps/api/app/routers/pharmacies.py` (import a small body model inline or reuse):
```python
from pydantic import BaseModel

class _StatusIn(BaseModel):
    status: str

@router.post("/orders/{offer_id}/status")
def set_order_status(offer_id: str, body: _StatusIn, user: User = Depends(require_role("pharmacy")),
                     db: Session = Depends(get_db)) -> dict:
    found, allowed = pharmacy_service.set_status(db, offer_id, user.id, body.status)
    if not found:
        raise HTTPException(status_code=404, detail="not found")
    if not allowed:
        raise HTTPException(status_code=400, detail="illegal transition")
    return {"status": body.status.upper()}
```

- [ ] **Step 5: Run to verify it passes** → `pytest tests/test_orders.py -v` PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/api/app/services/pharmacy_service.py apps/api/app/routers/pharmacies.py apps/api/tests/test_orders.py
git commit -m "add pharmacy order status transitions"
```

---

### Task 3: Pharmacy dashboard stats

**Files:**
- Modify: `apps/api/app/schemas/stats.py`
- Modify: `apps/api/app/services/stats_service.py`
- Modify: `apps/api/app/routers/pharmacies.py`
- Create: `apps/api/tests/test_pharmacy_stats.py`

**Interfaces:**
- Produces: `GET /v1/pharmacy/stats` → `PharmacyStatsOut` `{ newOrders, inProgress, outForDelivery, completedToday }`, computed from seeded order statuses.

- [ ] **Step 1: Write the failing test**

`apps/api/tests/test_pharmacy_stats.py`:
```python
def test_pharmacy_stats(client, pharmacy_token):
    h = {"Authorization": f"Bearer {pharmacy_token}"}
    r = client.get("/v1/pharmacy/stats", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert {"newOrders", "inProgress", "outForDelivery", "completedToday"} == set(body)
    assert body["newOrders"] >= 1
```

- [ ] **Step 2: Run to verify it fails** → `pytest tests/test_pharmacy_stats.py -v` FAIL (404).

- [ ] **Step 3: Schema + service**

Append to `apps/api/app/schemas/stats.py`:
```python
class PharmacyStatsOut(BaseModel):
    newOrders: int
    inProgress: int
    outForDelivery: int
    completedToday: int
```
Append to `apps/api/app/services/stats_service.py` (imports: `OfferStatus`, `PharmacyOffer`):
```python
def pharmacy_stats(db: Session, pharmacy_id) -> PharmacyStatsOut:
    rows = list(db.scalars(select(PharmacyOffer).where(PharmacyOffer.pharmacy_id == pharmacy_id)))
    def count(*states):
        return sum(1 for o in rows if o.status in states)
    return PharmacyStatsOut(
        newOrders=count(OfferStatus.PENDING, OfferStatus.TO_VERIFY),
        inProgress=count(OfferStatus.PREPARING, OfferStatus.VERIFIED, OfferStatus.ACCEPTED),
        outForDelivery=count(OfferStatus.OUT_FOR_DELIVERY),
        completedToday=count(OfferStatus.DELIVERED, OfferStatus.COMPLETED),
    )
```
(Add `PharmacyStatsOut` to the stats schema import.)

- [ ] **Step 4: Route**

In `apps/api/app/routers/pharmacies.py` (import `PharmacyStatsOut`, `stats_service`):
```python
@router.get("/stats", response_model=PharmacyStatsOut)
def pharmacy_stats(user: User = Depends(require_role("pharmacy")), db: Session = Depends(get_db)):
    return stats_service.pharmacy_stats(db, user.id)
```

- [ ] **Step 5: Run to verify it passes** → `pytest tests/test_pharmacy_stats.py -v` PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/api/app/schemas/stats.py apps/api/app/services/stats_service.py apps/api/app/routers/pharmacies.py apps/api/tests/test_pharmacy_stats.py
git commit -m "add pharmacy dashboard stats"
```

---

## Verification (end of Plan B)

- `alembic upgrade head` clean; reseed clean.
- `.venv/Scripts/python -m pytest` — all green.
- Manual: as the demo pharmacy, `GET /v1/pharmacy/stats` (~12 new / 8 in-progress / 5 out-for-delivery / 28 completed from seed), `/orders?status=pending`, and a status transition all return real data.

**Next plan:** `backend-C-medium-doctor` — patient profile + history, prescriptions list, lab-reports list, availability, profile.
