#!/bin/sh
set -eu

# One instance per client, so applying migrations at startup is safe.
alembic upgrade head

exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --proxy-headers \
    --no-server-header
