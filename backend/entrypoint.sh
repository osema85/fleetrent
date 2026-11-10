#!/bin/sh
set -eu

echo "Applying database migrations..."
alembic upgrade head

echo "Bootstrapping admin / demo data..."
python -m app.initial_data

echo "Starting API..."
# --forwarded-allow-ips '*' is safe here: the API is only reachable through nginx on a private network
exec uvicorn app.main:app \
  --host 0.0.0.0 --port 8000 \
  --workers "${WEB_CONCURRENCY:-2}" \
  --proxy-headers --forwarded-allow-ips '*' \
  --no-server-header
