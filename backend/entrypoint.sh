#!/bin/bash
set -e

ROLE=${ROLE:-backend}  # default to backend

echo "Waiting for Postgres at $POSTGRES_HOST (timeout 60s)..."
command -v pg_isready >/dev/null 2>&1 || { echo "pg_isready not found, skipping check"; }
until pg_isready -h "$POSTGRES_HOST" -U "$POSTGRES_USER" >/dev/null 2>&1; do
  sleep 2
done
echo "Postgres check complete."

echo "Waiting for MinIO at $S3_ENDPOINT (timeout 60s)..."
until curl -sf "$S3_ENDPOINT/minio/health/live" > /dev/null; do
  sleep 2
done
echo "MinIO check complete."

echo "Running migrations..."
flask db upgrade || echo "Migration step skipped or already applied."

if [ "$ROLE" = "worker" ]; then
  echo "Starting Celery worker..."
  exec celery -A app.celery_app.celery_app worker --loglevel=info
else
  echo "Starting Flask app..."
  exec python run.py
fi
