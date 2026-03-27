#!/usr/bin/env bash
set -euo pipefail

if command -v docker >/dev/null 2>&1; then
  docker compose up -d postgres
fi

echo "Codespace ready. Run API with:"
echo "make dev"
