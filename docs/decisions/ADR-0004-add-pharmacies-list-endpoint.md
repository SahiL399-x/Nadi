# ADR-0004: Add GET /v1/pharmacies

## Status
Accepted (2026-10-19)

## Context
The frozen §9 API contract has no endpoint listing pharmacies, yet the pharmacy-
consent flow legally requires the patient to choose their own pharmacy from a list
(Telemedicine Practice Guidelines 2020; ProjectPlan §11). Hard-coding pharmacy IDs
in the client is not acceptable for a real cross-device demo.

## Decision
Add `GET /v1/pharmacies?lat=&lng=&radiusKm=` returning `PharmacyOut[]` sorted by
PostGIS distance, mirroring the existing `GET /v1/doctors` pattern. Additive and
backward-compatible. `deliversInMins` is derived (no such column exists): 0 when the
pharmacy does not deliver, else 15 + round(distanceKm * 3).

## Consequences
The §9 contract gains one additive read endpoint. No existing shape changes.
