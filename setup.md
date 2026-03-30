# TaxSage AI — Setup & Operations Manual

## Prerequisites

### Accounts to Create (all free tiers sufficient to start)
| Service | URL | What you'll get |
|---|---|---|
| GitHub | github.com | Repo hosting, Codespaces, Actions |
| Anthropic | console.anthropic.com | API key for Claude |
| Langfuse Cloud | cloud.langfuse.com | Public + Secret key |
| Upstash | console.upstash.com | Redis REST URL + Token |
| Cohere | dashboard.cohere.com | API key (free tier) |
| GCP | console.cloud.google.com | For GKE deployment (optional for dev) |

### What to Install Locally (minimal)
- **Cursor** — AI-native IDE. Download from cursor.sh. Used to connect to remote Codespaces.
- **Git** — for initial repo clone/push only.

### What NOT to Install Locally (and why)
- **Python** — runs inside Codespaces container. Local Python creates version conflicts.
- **Docker Desktop** — runs inside Codespaces. Your local PC doesn't need it.
- **Node.js** — not required unless building a frontend.
- **Postgres** — runs in Docker inside Codespaces. No local DB.

> **Why Codespaces?** Your local PC is low-spec. Codespaces gives you a 4-core/8GB cloud VM with a consistent, reproducible environment defined in code. Every team member gets identical tooling.

---

## Repository Setup

### Create the Repository
```bash
# On GitHub.com:
# 1. New repository → name: taxsage-ai → Private → Create

# Clone locally (first and last time you'll use local Git)
git clone https://github.com/YOUR_USERNAME/taxsage-ai.git
cd taxsage-ai
```

### Branch Strategy
```
main          ← production-ready code, protected
dev           ← integration branch, all features merge here first
feature/*     ← individual feature branches
hotfix/*      ← urgent production fixes
```

### Branch Protection Rules (set in GitHub → Settings → Branches)
- **main:** Require PR + 1 review, require status checks (lint, test, eval, scan) to pass, no direct push
- **dev:** Require status checks (lint, test) to pass

### Initial Folder Structure
```bash
mkdir -p .devcontainer .github/workflows app/{api,rag,agents,tools,models} eval infra
touch docker-compose.yml requirements.txt Dockerfile .env.example
git add . && git commit -m "chore: initial project scaffold"
git push origin main
```

---

## Codespaces Configuration

### Complete devcontainer.json
Create `.devcontainer/devcontainer.json`:
```json
{
  "name": "TaxSage AI Dev",
  "image": "mcr.microsoft.com/devcontainers/python:3.11-bullseye",
  "features": {
    "ghcr.io/devcontainers/features/docker-in-docker:2": {},
    "ghcr.io/devcontainers/features/git:1": {}
  },
  "forwardPorts": [8000, 5432, 6379, 3000],
  "portsAttributes": {
    "8000": {"label": "FastAPI", "onAutoForward": "notify"},
    "5432": {"label": "Postgres", "onAutoForward": "silent"},
    "3000": {"label": "Langfuse UI (local)", "onAutoForward": "silent"}
  },
  "postCreateCommand": "pip install -r requirements.txt && docker compose up -d",
  "remoteEnv": {
    "ANTHROPIC_API_KEY": "${localEnv:ANTHROPIC_API_KEY}",
    "LANGFUSE_PUBLIC_KEY": "${localEnv:LANGFUSE_PUBLIC_KEY}",
    "LANGFUSE_SECRET_KEY": "${localEnv:LANGFUSE_SECRET_KEY}",
    "UPSTASH_REDIS_URL": "${localEnv:UPSTASH_REDIS_URL}",
    "UPSTASH_REDIS_TOKEN": "${localEnv:UPSTASH_REDIS_TOKEN}",
    "COHERE_API_KEY": "${localEnv:COHERE_API_KEY}",
    "DATABASE_URL": "postgresql://taxsage:taxsage@localhost:5432/taxsage"
  },
  "customizations": {
    "vscode": {
      "extensions": [
        "ms-python.python",
        "ms-python.black-formatter",
        "charliermarsh.ruff",
        "mtxr.sqltools",
        "mtxr.sqltools-driver-pg"
      ],
      "settings": {
        "python.defaultInterpreterPath": "/usr/local/bin/python",
        "editor.formatOnSave": true,
        "[python]": {"editor.defaultFormatter": "ms-python.black-formatter"}
      }
    }
  }
}
```

**Field-by-field explanation:**
- `image`: Pre-built Python 3.11 Debian container — no Dockerfile needed for the dev env itself
- `features/docker-in-docker`: Enables `docker` and `docker compose` commands inside the Codespace
- `forwardPorts`: Makes these container ports accessible as localhost:PORT in your browser and Cursor
- `postCreateCommand`: Runs once when Codespace is first created — installs Python deps and starts Docker services
- `remoteEnv`: Injects GitHub Codespaces Secrets as environment variables into the container
- `extensions`: Installs VS Code extensions automatically (Black formatter, Ruff linter, SQL client)

### Setting Codespaces Secrets
GitHub → Your profile → Settings → Codespaces → Secrets → New secret. Add each key from the Environment Secrets table below.

### Rebuilding a Broken Codespace
```
Ctrl+Shift+P → "Codespaces: Rebuild Container"
```
This re-runs `postCreateCommand`. Use when `requirements.txt` changes or the container behaves unexpectedly.

### Connecting Cursor to Codespaces
1. Open Cursor
2. Ctrl+Shift+P → "Connect to Codespace"
3. Select `taxsage-ai` Codespace
4. Full IDE experience inside the cloud VM

---

## Local Services Setup (Docker Compose)

### docker-compose.yml
```yaml
version: "3.9"
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: taxsage
      POSTGRES_USER: taxsage
      POSTGRES_PASSWORD: taxsage
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U taxsage"]
      interval: 5s
      retries: 5

volumes:
  pgdata:
```

> **Note:** Redis is hosted on Upstash (serverless) — no local Redis container needed.

### Verify Services Are Running
```bash
docker compose ps
# Expected output:
# NAME                STATUS          PORTS
# taxsage-postgres    Up (healthy)    0.0.0.0:5432->5432/tcp
```

### Connect to Postgres from Terminal
```bash
docker compose exec postgres psql -U taxsage -d taxsage
# Expected: taxsage=#
\l          # list databases
\q          # quit
```

### Reset/Wipe All Data
```bash
docker compose down -v   # -v removes named volumes including pgdata
docker compose up -d     # fresh start
```

> ⚠️ **Warning:** This deletes all embeddings and document chunks. You'll need to re-ingest all documents.

---

## Environment Secrets

| Secret Name | Where to Get It | What Breaks Without It |
|---|---|---|
| `ANTHROPIC_API_KEY` | console.anthropic.com → API Keys | All LLM calls fail |
| `LANGFUSE_PUBLIC_KEY` | cloud.langfuse.com → Settings → API Keys | Observability disabled |
| `LANGFUSE_SECRET_KEY` | Same as above | Observability disabled |
| `UPSTASH_REDIS_URL` | console.upstash.com → Redis → REST URL | Semantic cache disabled, higher API cost |
| `UPSTASH_REDIS_TOKEN` | Same console | Cache auth fails |
| `COHERE_API_KEY` | dashboard.cohere.com → API Keys | Reranking disabled, retrieval quality drops |
| `DATABASE_URL` | Constructed: `postgresql://taxsage:taxsage@localhost:5432/taxsage` | All DB operations fail |

### How to Store in GitHub Secrets
GitHub → Repo → Settings → Secrets and variables → Actions → New repository secret.
Add each secret above. These are also available as Codespaces secrets if you add them under profile-level Codespaces secrets.

### Rotating Secrets
1. Generate new key on provider dashboard
2. Update GitHub Secret (same UI)
3. Rebuild Codespace (Ctrl+Shift+P → Rebuild)
4. In production: `vault kv put secret/taxsage/anthropic api_key=NEW_KEY`

---

## First Run Checklist

Run these commands **in order** from a fresh Codespace terminal:
```bash
# 1. Verify Python
python --version
# Expected: Python 3.11.x

# 2. Verify services
docker compose ps
# Expected: postgres Up (healthy)

# 3. Run database migrations
python -m alembic upgrade head
# Expected: INFO Running upgrade -> abc123, OK

# 4. Create pgvector extension (idempotent)
python scripts/init_db.py
# Expected: ✓ pgvector extension created
#           ✓ document_chunks table created
#           ✓ HNSW index created

# 5. Seed eval dataset
python eval/seed_golden_dataset.py
# Expected: ✓ 50 questions loaded

# 6. Verify Anthropic connection
python scripts/health_check.py
# Expected: ✓ Anthropic API: OK (claude-haiku-20240307)
#           ✓ Langfuse: OK
#           ✓ Upstash Redis: OK
#           ✓ Postgres pgvector: OK

# 7. Start FastAPI server
uvicorn app.main:app --reload --port 8000
# Expected: INFO:     Application startup complete.
#           INFO:     Uvicorn running on http://0.0.0.0:8000

# 8. In a new terminal: test the API
curl http://localhost:8000/health
# Expected: {"status": "ok", "version": "0.1.0"}

# 9. Ingest a test document
curl -X POST http://localhost:8000/ingest \
  -F "file=@eval/fixtures/sample_form16.pdf" \
  -F "user_id=test-user" \
  -F "doc_type=form16" \
  -F "fiscal_year=2024-25"
# Expected: {"status": "ok", "chunks_created": 23}

# 10. Ask a test question
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is my gross salary?", "user_id": "test-user", "session_id": "test-1"}'
# Expected: Streaming SSE tokens ending with {"done": true, "sources": [...]}
```

**You're live.** 🎉

---

## Database Initialisation

### scripts/init_db.py
```python
from sqlalchemy import create_engine, text
import os

engine = create_engine(os.environ["DATABASE_URL"])

with engine.connect() as conn:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS document_chunks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL,
            content TEXT NOT NULL,
            embedding VECTOR(1024),
            metadata JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """))
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_chunks_embedding
        ON document_chunks USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """))
    conn.commit()
    print("✓ Database initialised")
```

### Running Alembic Migrations
```bash
# Generate a new migration after schema changes
alembic revision --autogenerate -m "add_agent_checkpoints_table"

# Apply all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

---

## CI/CD Pipeline

### .github/workflows/ci.yml (complete)
```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main, dev]
  pull_request:
    branches: [main, dev]

env:
  IMAGE_NAME: gcr.io/${{ secrets.GCP_PROJECT_ID }}/taxsage-ai

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "3.11"}
      - run: pip install ruff black
      - run: ruff check app/ && black --check app/

  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env: {POSTGRES_DB: taxsage, POSTGRES_USER: taxsage, POSTGRES_PASSWORD: taxsage}
        ports: ["5432:5432"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "3.11"}
      - run: pip install -r requirements.txt
      - run: pytest app/tests/ -v --tb=short
    env:
      DATABASE_URL: postgresql://taxsage:taxsage@localhost:5432/taxsage
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}

  eval:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "3.11"}
      - run: pip install -r requirements.txt
      - name: Run RAGAS eval
        run: python eval/run_ragas.py --output eval_results.json
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          LANGFUSE_PUBLIC_KEY: ${{ secrets.LANGFUSE_PUBLIC_KEY }}
          LANGFUSE_SECRET_KEY: ${{ secrets.LANGFUSE_SECRET_KEY }}
      - name: Check eval thresholds
        run: python eval/check_thresholds.py eval_results.json
        # Exits with code 1 if faithfulness < 0.75

  build:
    needs: eval
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker build -t $IMAGE_NAME:${{ github.sha }} .

  scan:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Trivy image scan
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ env.IMAGE_NAME }}:${{ github.sha }}
          exit-code: 1
          severity: HIGH,CRITICAL
      - name: tfsec IaC scan
        uses: aquasecurity/tfsec-action@v1.0.0
        with:
          working_directory: infra/

  deploy:
    needs: scan
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}
      - run: gcloud container clusters get-credentials taxsage-prod --region asia-south1
      - run: |
          docker push $IMAGE_NAME:${{ github.sha }}
          helm upgrade --install taxsage ./infra/helm \
            --set image.tag=${{ github.sha }} \
            --namespace taxsage
```

**Pipeline stages explained:**
1. **lint** — Ruff (fast linter) + Black (formatter check). Fails immediately on style issues.
2. **test** — Unit + integration tests with a real Postgres/pgvector sidecar. Fast, isolated.
3. **eval** — RAGAS evaluation against the golden dataset. Gates on faithfulness ≥ 0.75. This is the quality gate.
4. **build** — Builds Docker image. Only runs if tests + evals pass.
5. **scan** — Trivy scans the built image. tfsec scans Terraform. Security gate.
6. **deploy** — Helm upgrade to GKE. Only on `main` branch pushes.

---

## Kubernetes Deployment

### GKE Cluster Setup
```bash
# Create cluster (run once)
gcloud container clusters create taxsage-prod \
  --region asia-south1 \
  --num-nodes 2 \
  --machine-type e2-standard-2

# Get credentials
gcloud container clusters get-credentials taxsage-prod --region asia-south1

# Verify
kubectl get nodes
# Expected: 2 nodes Ready
```

### Vault Agent Sidecar
The Vault Agent sidecar runs as a container alongside the FastAPI pod and writes secrets to a shared volume:
```yaml
# In Helm chart values.yaml
vault:
  enabled: true
  annotations:
    vault.hashicorp.com/agent-inject: "true"
    vault.hashicorp.com/role: "taxsage-app"
    vault.hashicorp.com/agent-inject-secret-anthropic: "secret/taxsage/anthropic"
    vault.hashicorp.com/agent-inject-template-anthropic: |
      {{- with secret "secret/taxsage/anthropic" -}}
      export ANTHROPIC_API_KEY="{{ .Data.data.api_key }}"
      {{- end }}
```

The app's entrypoint sources the injected file: `source /vault/secrets/anthropic`.

### Deploy a New Version
```bash
# CI/CD handles this automatically on main push, but for manual deploy:
helm upgrade taxsage ./infra/helm \
  --set image.tag=NEW_SHA \
  --namespace taxsage
```

### Rollback
```bash
helm rollback taxsage 0   # 0 = previous revision
# Verify
kubectl rollout status deployment/taxsage -n taxsage
```

---

## Langfuse Setup

### Project Creation
1. Go to cloud.langfuse.com → New Project → Name: `taxsage-dev`
2. Settings → API Keys → copy Public Key and Secret Key
3. Add both to GitHub Secrets and Codespaces Secrets

### Connecting to the App
```python
# app/observability.py
from langfuse import Langfuse

langfuse = Langfuse(
    public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
    secret_key=os.environ["LANGFUSE_SECRET_KEY"],
    host="https://cloud.langfuse.com"
)
```

### Reading Your First Trace
1. Ingest a document and ask a question (First Run Checklist steps 9–10)
2. Langfuse UI → Traces → click the most recent trace
3. Expand spans: you'll see `embedding → retrieval → reranking → llm_call`
4. Click `llm_call` → view input tokens, output tokens, cost in USD, latency ms

### Setting Up Alerts
Langfuse → Settings → Alerts → New Alert:
- Alert on: `llm_call.cost_usd > 0.05` (single call cost spike)
- Alert on: `faithfulness_score < 0.75` (eval regression)

---

## Adding a New Feature — Dev Loop
```bash
# 1. Create feature branch from dev
git checkout dev
git pull origin dev
git checkout -b feature/add-form-26as-support

# 2. Open Codespace (or it auto-connects if already open)
# Code in Cursor — add loader, register doc type, add tests

# 3. Run tests locally
pytest app/tests/test_ingest.py -v

# 4. Run eval locally to catch regressions
python eval/run_ragas.py --quick  # runs 10-question subset

# 5. Push
git add . && git commit -m "feat: add Form 26AS document support"
git push origin feature/add-form-26as-support

# 6. Open PR → target: dev
# CI runs: lint → test → eval → build → scan (no deploy on dev PRs)

# 7. PR approved + merged to dev
# 8. After integration testing on dev, PR: dev → main
# CI runs full pipeline including deploy to GKE
```

---

## Troubleshooting

### 1. Codespace stuck in Recovery Mode
```bash
# In Codespace terminal:
sudo systemctl restart docker
docker compose up -d
```
If still broken: Ctrl+Shift+P → "Codespaces: Rebuild Container" (takes ~3 min).

### 2. pgvector extension missing
```
Error: operator does not exist: text <=> vector
```
```bash
docker compose exec postgres psql -U taxsage -d taxsage -c "CREATE EXTENSION vector;"
python scripts/init_db.py  # recreates indexes
```

### 3. Anthropic API Rate Limit
```
Error: 429 Too Many Requests
```
In `app/rag/llm.py`, implement exponential backoff:
```python
from anthropic import RateLimitError
import time

for attempt in range(3):
    try:
        return client.messages.create(...)
    except RateLimitError:
        time.sleep(2 ** attempt)
```
Also check if Redis cache is working — cache hits bypass the API entirely.

### 4. RAGAS Eval Failure in CI
```
AssertionError: faithfulness=0.62 < threshold=0.75
```
Diagnosis steps:
```bash
python eval/run_ragas.py --output results.json
python eval/debug_failures.py results.json  # shows which questions failed
```
Common fixes: tighten system prompt to discourage hallucination, increase chunk overlap, check if golden dataset questions need updating for new tax rules.

### 5. Vault Connection Refused
```
Error: connection refused 127.0.0.1:8200
```
Vault Agent sidecar failed to start. Check:
```bash
kubectl logs <pod-name> -c vault-agent
# Common cause: wrong role name in annotation, or Vault token expired
vault token renew
```

### 6. Redis Cache Miss Storm
All queries hitting Claude simultaneously — check Upstash console for error rate. Common cause: Redis token expired.
```bash
python scripts/health_check.py  # will show Redis: FAIL
# Rotate Upstash token in console, update GitHub Secret, rebuild Codespace
```

### 7. LangGraph Infinite Loop
```
RecursionError: maximum recursion depth exceeded
```
Add a step counter to AgentState and a max_steps guard:
```python
if state["current_step"] >= 10:
    return {"final_report": "Max steps reached. Partial results: ..."}
```

### 8. pgvector HNSW Index Build Fails (OOM)
Reduce `ef_construction` for low-memory environments:
```sql
DROP INDEX idx_chunks_embedding;
CREATE INDEX idx_chunks_embedding ON document_chunks
  USING hnsw (embedding vector_cosine_ops) WITH (m=8, ef_construction=32);
```

### 9. Docker Compose Port Conflict (5432 in use)
```bash
lsof -i :5432  # find what's using the port
# If local Postgres is running:
sudo systemctl stop postgresql
docker compose up -d
```

### 10. Streaming Response Cuts Off Mid-Token
FastAPI SSE timeout. Add keepalive:
```python
async def stream_with_keepalive(generator):
    async for chunk in generator:
        yield f"data: {chunk}\n\n"
    yield "data: [DONE]\n\n"
```

---

## Cost Management

### Estimated Monthly Costs (at different usage levels)

| Usage Level | Users | Queries/day | Anthropic Cost | Total Infra |
|---|---|---|---|---|
| Dev | 1 | 20 | ~$0.50 | ~$0 (free tiers) |
| Early users | 10 | 100 | ~$3–5 | ~$30 (GKE small) |
| Growth | 100 | 1000 | ~$30–50 | ~$100 |
| Scale | 1000 | 10000 | ~$300 | ~$400 |

### Reducing Anthropic Cost
1. **Redis semantic cache** — target 40%+ cache hit rate. Check Upstash → Analytics.
2. **Use Haiku in dev, Sonnet in prod** — Haiku is ~15x cheaper per token.
3. **Reduce max_tokens** — set `max_tokens=1500` for simple Q&A (vs 4096 default).
4. **Switch model per query complexity** — simple factual queries → Haiku; complex optimisation → Sonnet.

### Switching Models Per Environment
```python
# app/config.py
import os

MODEL = (
    "claude-haiku-20240307"
    if os.environ.get("ENV") == "dev"
    else "claude-sonnet-4-20250514"
)
```

---

## Scaling Considerations

### When to Migrate from pgvector to Pinecone
- Document chunks exceed 5 million rows
- Query latency p99 > 500ms despite HNSW tuning
- Need managed scaling without Postgres expertise

### When to Move from Upstash Free to Paid
- Daily commands exceed 10,000 (Upstash free limit)
- Cache evictions are high (check Upstash → Stats → Evictions)
- Move to Upstash Pay-as-you-go: ~$0.20 per 100K commands

### How the Architecture Scales to 1000 Users
1. **GKE horizontal pod autoscaler** — FastAPI pods scale 2→10 based on CPU
2. **Postgres read replicas** — pgvector reads distributed across replicas
3. **Connection pooling** — add PgBouncer sidecar to reduce Postgres connection overhead
4. **Async everything** — FastAPI + async SQLAlchemy means each pod handles many concurrent requests
5. **Langfuse batching** — traces are batched and sent async, no per-request HTTP overhead

The architecture is designed to scale without re-platforming. The only swap at serious scale (10K+ users) is pgvector → Pinecone/Weaviate, and the retriever abstraction in LangChain makes this a one-file change.
