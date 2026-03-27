#!/usr/bin/env bash
set -euo pipefail

if [ ! -f ".env" ] && [ -f ".env.example" ]; then
  cp .env.example .env
fi

python -m pip install --upgrade pip
pip install -r requirements.txt
