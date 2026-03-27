#!/usr/bin/env bash
set -euo pipefail

if [ ! -f ".env" ] && [ -f ".env.example" ]; then
  cp .env.example .env
fi

if command -v docker >/dev/null 2>&1; then
  # Docker-in-Docker can take a moment after container start.
  for _ in {1..20}; do
    if docker info >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
  docker compose up -d postgres redis
fi

if pgrep -f "uvicorn app.main:app" >/dev/null 2>&1; then
  echo "FastAPI already running."
else
  echo "Starting FastAPI in background..."
  nohup uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > .devcontainer/api.log 2>&1 &
fi

echo "Codespace ready."
echo "FastAPI: http://localhost:8000"
echo "API log: .devcontainer/api.log"
