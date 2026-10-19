# ADR-0005: v2 API contract — doctor/pharmacy portal endpoints

## Status
Accepted (2026-10-19)

## Context
ProjectPlan §9 froze the API contract. The doctor and pharmacy portals require a
substantial, additive expansion (medicine catalog, appointments, notes, stats,
order lifecycle, patient history, availability, profile). See
docs/superpowers/specs/2026-10-19-nadi-backend-expansion-design.md.

## Decision
Lift the §9 freeze for ADDITIVE growth only. The v2 contract adds the endpoints in
the expansion spec. No existing endpoint or response shape changes, so the merged
mobile core keeps working. Heavy subsystems (messaging, inventory, delivery/rider)
are out of scope here and will have their own ADR when built.

## Consequences
The contract grows; `packages/shared-types` is regenerated. Existing clients unaffected.
