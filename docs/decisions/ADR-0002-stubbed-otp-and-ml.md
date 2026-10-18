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
