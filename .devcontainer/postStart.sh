#!/usr/bin/env bash
set -euo pipefail

# Always run from workspace root so relative paths resolve correctly.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

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

check_api_ready() {
  python - <<'PY'
import sys
import urllib.request

try:
    with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=1) as response:
        sys.exit(0 if response.status == 200 else 1)
except Exception:
    sys.exit(1)
PY
}

print_log_excerpt() {
  python - <<'PY'
from pathlib import Path

log_path = Path(".devcontainer/api.log")
if not log_path.exists():
    print("No API log file found at .devcontainer/api.log")
else:
    lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    print("--- Last API log lines ---")
    for line in lines[-40:]:
        print(line)
PY
}

STARTED_NEW="false"
API_PID=""
if pgrep -f "uvicorn app.main:app" >/dev/null 2>&1; then
  echo "FastAPI process already exists. Checking readiness..."
else
  echo "Starting FastAPI in background..."
  nohup uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > .devcontainer/api.log 2>&1 &
  API_PID="$!"
  STARTED_NEW="true"
fi

READY="false"
for _ in {1..30}; do
  if check_api_ready; then
    READY="true"
    break
  fi
  if [ "${STARTED_NEW}" = "true" ] && [ -n "${API_PID}" ] && ! kill -0 "${API_PID}" >/dev/null 2>&1; then
    echo "FastAPI process exited during startup."
    print_log_excerpt
    exit 1
  fi
  sleep 1
done

if [ "${READY}" != "true" ]; then
  echo "FastAPI is not ready on port 8000 after startup wait."
  print_log_excerpt
  exit 1
fi

echo "Codespace ready."
echo "FastAPI: http://localhost:8000"
echo "API log: .devcontainer/api.log"
