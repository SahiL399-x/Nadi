#!/bin/sh
# Bring the schema up to date and load demo data before serving, so a fresh
# `docker compose up` yields a working API against an empty volume.
set -e
alembic upgrade head
python -m seed.seed || echo "seed skipped (already present or failed, non-fatal)"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
