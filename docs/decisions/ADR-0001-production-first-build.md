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
