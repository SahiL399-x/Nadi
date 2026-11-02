# Triage Model + Doctor Recommendation — Plan Index

Spec: `docs/superpowers/specs/2026-11-02-nadi-triage-recommendation-design.md`

The spec is one combined system but five independently-testable subsystems. Each has its own
plan file. Build order and dependencies below.

| Phase | Plan file | Depends on | Agent-buildable now? |
|---|---|---|---|
| 1 — Training notebook | `2026-11-02-nadi-triage-01-notebook.md` | — | Yes (notebook code); **training runs on Colab by the user** |
| 2 — ml-service serving | `2026-11-02-nadi-triage-02-mlservice-serving.md` | Phase 1 artifacts | Code yes; **flag-ON tests need the user's exported ONNX** |
| 3 — Doctor keywords | `2026-11-02-nadi-triage-03-doctor-keywords.md` | — | Yes, fully |
| 4 — Recommendation engine | `2026-11-02-nadi-triage-04-recommendation.md` | Phase 3 | Yes, fully (ML fallback via existing specialty path) |
| 5 — Acuity teardown | `2026-11-02-nadi-triage-05-acuity-teardown.md` | — | Yes, fully |

**Recommended execution order:** Phase 5 (teardown — clears the contract) → Phase 3 (keywords)
→ Phase 4 (recommendation) → Phase 1 (notebook) → Phase 2 (serving, after the user runs the
notebook on Colab and commits the artifacts).

Rationale: doing the acuity teardown first gives every later phase a clean specialty-only
contract to build against, instead of threading acuity through new code only to rip it out.
Phases 3–5 need no trained model. Phase 2's flag-OFF path (specialty-only stub) is testable
immediately; its flag-ON path is verified once the Colab artifacts land.

**Global constraints (apply to every phase):**
- No AI attribution in any committed artefact (ProjectPlan §14.11).
- `ML_TRIAGE_ENABLED` defaults **OFF**; flag-OFF behavior must stay byte-stable except for the
  acuity removal that Phase 5 makes universal.
- TDD throughout; commit per task.
- Reseed with `bash .superpowers/sdd/reseed.sh` if seed-dependent tests drain PENDING orders.
