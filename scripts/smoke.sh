#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:8000}"

echo "[smoke] checking ${BASE_URL}/health"
HEALTH_CODE="$(curl -s -o /tmp/taxagent_health.json -w "%{http_code}" "${BASE_URL}/health")"
if [ "${HEALTH_CODE}" != "200" ]; then
  echo "[smoke] /health failed with status ${HEALTH_CODE}"
  exit 1
fi
echo "[smoke] /health ok"

echo "[smoke] checking ${BASE_URL}/api/v1/health/dependencies"
DEP_CODE="$(curl -s -o /tmp/taxagent_deps.json -w "%{http_code}" "${BASE_URL}/api/v1/health/dependencies")"
if [ "${DEP_CODE}" != "200" ]; then
  echo "[smoke] /api/v1/health/dependencies failed with status ${DEP_CODE}"
  exit 1
fi
echo "[smoke] /api/v1/health/dependencies ok"
echo "[smoke] done"
