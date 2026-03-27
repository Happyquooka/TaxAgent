#!/usr/bin/env bash
set -euo pipefail

POSTGRES_OK="unknown"
REDIS_OK="unknown"

if command -v docker >/dev/null 2>&1; then
  if docker compose ps postgres >/dev/null 2>&1; then
    POSTGRES_OK="running_or_configured"
  else
    POSTGRES_OK="not_running"
  fi
  if docker compose ps redis >/dev/null 2>&1; then
    REDIS_OK="running_or_configured"
  else
    REDIS_OK="not_running"
  fi
fi

if [ -n "${REDIS_URL:-}" ]; then
  REDIS_OK="${REDIS_OK},env_configured"
else
  REDIS_OK="${REDIS_OK},missing_REDIS_URL"
fi

echo "[health] postgres=${POSTGRES_OK}"
echo "[health] redis=${REDIS_OK}"
echo "[health] note=set REDIS_URL to your Upstash rediss:// URL in .env or Codespaces secrets"
