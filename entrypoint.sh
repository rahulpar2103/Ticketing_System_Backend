#!/usr/bin/env bash
set -e

# 1️⃣ Wait for PostgreSQL
echo "⏳ Waiting for PostgreSQL..."
while ! pg_isready -h db -p 5432 -U ticket_user; do
  sleep 1
done
echo "✅ PostgreSQL ready"

# 2️⃣ Run DB migrations
echo "🔧 Running Alembic migrations..."
alembic -c app/alembic.ini upgrade head

# 3️⃣ Start the FastAPI server
echo "🚀 Starting Uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
