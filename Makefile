SHELL := /usr/bin/env bash

.PHONY: install infra dev health api ingest smoke

install:
	pip install -r requirements.txt

infra:
	docker compose up -d postgres redis

health:
	bash scripts/check_health.sh

api:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev:
	bash scripts/dev.sh

ingest:
	python -m app.ingest.run --source ./data/tax_docs --recursive

smoke:
	bash scripts/smoke.sh
