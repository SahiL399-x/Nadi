# ADR-0003: Harden the backend-foundation branch after a full review

## Context
A whole-branch review (verified against the running stack) found that the demo flow
and several §9/§11 contract guarantees were not actually honored: real (non-seeded)
patients never reached the doctor queue, authorization was role-only with no
resource ownership, and clients could self-assign a privileged role at signup.

## Decision
Fix the functional and security gaps now, behind the frozen §9 contract:
- Signup is patient-only; doctor/pharmacy accounts are server-provisioned (seed/admin).
  An existing user keeps its stored role.
- `intake` creates/updates the patient profile (age/sex) so the queue join resolves;
  the queue left-joins the profile defensively.
- Row-level ownership on every PHI route (consultation triage/book, prescription
  read/consent, doctor refer/prescribe, pharmacy accept/decline); unknown ids → 404.
- Persist triage `labs`; use the client's uploaded `objectKey`; filter doctors by lang
  code → stored name; return `{status:'pending'}` per contract.
- Access-token type check; migration `0002` adds uniqueness guards; `intake` rolls back
  on a failed ML call; pooled ML/S3 clients.
- The API container migrates + seeds on start, so a fresh `docker compose up` works.

## Deferred (deliberately, with rationale)
- **FK `ON DELETE` cascade** — no code path deletes rows, so cascade semantics are inert
  for the demo; reworking every constraint via Alembic is churn with no runtime payoff yet.
- **`audit_service` self-commit** — read-only endpoints have no surrounding write
  transaction, so removing the commit would silently drop their audit rows. Kept until
  audit writes are restructured to piggyback a request-scoped unit of work.
- **JWT secret / real OTP / encryption at rest** — remain per ADR-0001/0002 (demo scope).

## What we gave up
Provider self-signup convenience in the demo (providers must be seeded), and a second
hardening pass is still owed for the deferred items above.
