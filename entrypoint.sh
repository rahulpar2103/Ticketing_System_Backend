#!/usr/bin/env bash
set -e

if [[ "$DATABASE_URL" == *"@db:"* ]]; then
  echo "⏳ Waiting for PostgreSQL container..."
  while ! pg_isready -h db -p 5432 -U ticket_user; do
    sleep 1
  done
  echo "✅ PostgreSQL ready"
fi

echo "🔧 Running Alembic migrations..."
alembic -c app/alembic.ini upgrade head

echo "🚀 Starting Celery worker..."
celery -A app.core.celery_app:celery_app worker --loglevel=info --concurrency=1 &

echo "🚀 Starting Uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
