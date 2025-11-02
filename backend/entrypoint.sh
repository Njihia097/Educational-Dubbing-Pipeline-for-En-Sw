#!/bin/bash
set -e

ROLE=${ROLE:-backend}
POSTGRES_HOST=${POSTGRES_HOST:-postgres}
POSTGRES_USER=${POSTGRES_USER:-postgres}
S3_ENDPOINT=${S3_ENDPOINT:-http://minio:9000}

echo "Waiting for Postgres at $POSTGRES_HOST ..."
command -v pg_isready >/dev/null 2>&1 || { echo "pg_isready not found, skipping check"; }
until pg_isready -h "$POSTGRES_HOST" -U "$POSTGRES_USER" >/dev/null 2>&1; do
  sleep 2
done
echo "Postgres check complete."

echo "Waiting for MinIO at $S3_ENDPOINT ..."
until curl -sf "$S3_ENDPOINT/minio/health/live" > /dev/null; do
  sleep 2
done
echo "MinIO check complete."

if [ "$ROLE" = "backend" ]; then
  echo "Running migrations (backend only)..."
  flask db upgrade || echo "Migration step skipped or already applied."
fi

if [ "$ROLE" = "worker" ]; then
  echo "Starting Celery worker..."
  exec celery -A app.celery_app:celery_app worker -Q gpu,default --loglevel=info --concurrency=1
else
  echo "Starting Flask app..."
  exec python run.py
fi
