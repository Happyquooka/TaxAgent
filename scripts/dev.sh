#!/usr/bin/env bash
set -euo pipefail

echo "[dev] Starting local dependencies (Postgres only)..."
if command -v docker >/dev/null 2>&1; then
  docker compose up -d postgres
fi

if [ ! -f ".env" ] && [ -f ".env.example" ]; then
  cp .env.example .env
fi

echo "[dev] Running dependency health check..."
bash scripts/check_health.sh || true

echo "[dev] Starting FastAPI on 0.0.0.0:8000"
exec uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
