# TaxAgent - The way to pay less tax

Production-ready starter for a hybrid Tax RAG system:
- Managed LLM APIs (OpenAI/Anthropic)
- Self-hosted Postgres + pgvector
- Redis caching
- FastAPI endpoints for ingestion and tax-section recommendations

## Quick Start

1. Create env file:
   - Copy `.env.example` to `.env`
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Start infra:
   - `docker compose up -d postgres redis`
4. Run API:
   - `make dev`
5. Run smoke checks (in a second terminal while API is running):
   - `make smoke`

## API Endpoints

- `GET /health`
- `GET /api/v1/health/dependencies`
- `POST /api/v1/ingest`
- `POST /api/v1/query`
- `POST /api/v1/recommend-sections`

## Ingestion CLI

Run local indexing:

`python -m app.ingest.run --source ./data/tax_docs --recursive`

## GitHub Codespaces

This repo includes a ready-to-use `.devcontainer` setup.

1. Open the repository in Codespaces.
2. Add repository or Codespaces secrets:
   - `OPENAI_API_KEY`
   - `ANTHROPIC_API_KEY`
   - `LANGFUSE_PUBLIC_KEY`
   - `LANGFUSE_SECRET_KEY`
3. On first create:
   - dependencies install automatically
   - `.env` is copied from `.env.example` if missing
4. On each start:
   - `docker compose up -d postgres redis` runs automatically
5. FastAPI:
   - starts automatically on Codespace start at `http://localhost:8000`
   - logs are written to `.devcontainer/api.log`
6. Redis:
   - set `REDIS_URL` to your Upstash `rediss://...` connection string (already supported)

## Notes

- Current implementation includes robust scaffolding, typed settings, DB schema, ingestion pipeline, retrieval pipeline, and evaluation hooks.
- Connect real LLM and embedding providers by setting API keys in `.env`.
- Upstash Redis is supported directly through `REDIS_URL`.
- Langfuse tracing is wired in API query flow when Langfuse keys are configured.
- Evaluation placeholders are in `app/eval/ragas_eval.py` and acceptance checks in `app/eval/acceptance.py`.
- Smoke test script is available at `scripts/smoke.sh` (`make smoke`).
