# TaxSage AI — Project Documentation

## Project Overview

TaxSage AI is an AI-powered Indian tax assistant that combines Retrieval-Augmented Generation (RAG) with agentic reasoning to help individuals and tax professionals navigate the complexity of Indian taxation. Users upload their tax documents — ITR forms, Form 16, AIS (Annual Information Statement), mutual fund statements, and salary slips — and can ask natural language questions, get deduction recommendations, calculate liabilities, and receive plain-language tax summaries.

**Who it's for:**
- Salaried individuals filing their own ITR
- Freelancers and consultants managing multiple income heads
- Tax professionals handling client portfolios
- Chartered Accountants who want AI-assisted document review

**Problems it solves:**
- Indian tax documents are dense, cross-referenced, and spread across multiple PDFs
- Most people don't know which deductions they qualify for under 80C, 80D, HRA, LTA, etc.
- Tax software exists but doesn't explain *why* a number is what it is
- Manual document review is time-consuming and error-prone

TaxSage bridges the gap between raw documents and actionable understanding.

---

## Architecture Overview
```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                          │
│              (REST API client / future web UI)                  │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP / SSE
┌───────────────────────────▼─────────────────────────────────────┐
│                    FastAPI + Uvicorn                             │
│        /ingest   /query   /agent   /health   /eval              │
└────┬──────────────┬───────────────┬──────────────────────────────┘
     │              │               │
     ▼              ▼               ▼
┌─────────┐  ┌───────────┐  ┌─────────────────┐
│ Ingest  │  │ RAG Query │  │  LangGraph Agent│
│Pipeline │  │ Pipeline  │  │  (Planner +     │
│(LlamaIdx│  │(LangChain)│  │   Tools loop)   │
└────┬────┘  └─────┬─────┘  └────────┬────────┘
     │             │                  │
     ▼             ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    pgvector (Postgres)                           │
│         document_chunks table — vectors + metadata              │
└─────────────────────────────────────────────────────────────────┘
     │             │                  │
     ▼             ▼                  ▼
┌─────────────┐  ┌──────────────┐  ┌──────────────────┐
│  Anthropic  │  │ Upstash Redis│  │    Langfuse       │
│  Claude API │  │ Semantic Cache│  │ Traces/Cost/Evals │
└─────────────┘  └──────────────┘  └──────────────────┘
     │
┌────▼──────────────┐
│  Cohere Rerank    │
│  (chunk reranking)│
└───────────────────┘

Infrastructure Layer:
┌──────────────────────────────────────────────────────────┐
│  GKE (Kubernetes)  │  HashiCorp Vault  │  GitHub Actions │
│  Docker Compose    │  Trivy / tfsec    │  RAGAS Evals    │
└──────────────────────────────────────────────────────────┘
```

---

## Component Deep-Dive

### Python 3.11
**Why:** Native `asyncio` improvements, `tomllib` stdlib, performance gains over 3.10. All async FastAPI handlers and LangGraph nodes use `async/await` throughout.

**If removed:** Everything breaks. It's the runtime.

---

### FastAPI + Uvicorn
**What:** FastAPI is an async Python web framework. Uvicorn is the ASGI server that runs it.

**Why over Flask/Django:** Native async support, automatic OpenAPI docs, Pydantic request validation, streaming response support (critical for LLM token streaming via SSE).

**How used:** Three primary route groups — `/ingest` for document uploads, `/query` for RAG questions, `/agent` for agentic tasks. Streaming is enabled on `/query` via `StreamingResponse`.
```python
@router.post("/query")
async def query(request: QueryRequest) -> StreamingResponse:
    return StreamingResponse(
        rag_pipeline.stream(request.question, request.session_id),
        media_type="text/event-stream"
    )
```

**If removed:** No HTTP interface. Everything becomes a CLI script.

---

### LangChain
**What:** A framework for chaining LLM calls, prompt templates, and retrieval steps.

**Why:** Mature ecosystem, native pgvector integration, prompt hub, LCEL (LangChain Expression Language) for composable pipelines.

**How used:** Builds the RAG chain — `PromptTemplate → ChatAnthropic → StrOutputParser`. Also manages the retriever abstraction over pgvector.

**If removed:** RAG chain must be hand-written. Significant boilerplate.

---

### LlamaIndex
**What:** A data framework for ingesting, indexing, and querying documents.

**Why LlamaIndex for ingestion vs LangChain:** LlamaIndex has superior document loaders (PDF, Excel, JSON), better chunking strategies, and metadata-aware indexing. LangChain handles the query side; LlamaIndex handles the ingest side.

**How used:** `SimpleDirectoryReader` loads PDFs. `SentenceSplitter` chunks with 512 token windows and 50-token overlap. `VectorStoreIndex` pushes embeddings to pgvector.

**If removed:** Manual PDF parsing with `pdfplumber`, custom chunking logic, manual embedding calls.

---

### LangGraph
**What:** A graph-based agent framework built on top of LangChain. Agents are defined as directed graphs with typed state.

**Why over CrewAI/AutoGen:** Deterministic graph topology (you know exactly which node fires next), native human-in-the-loop checkpoints, superior debuggability — you can inspect state at every node. CrewAI is higher-level but opaque.

**How used:** The `TaxOptimiserAgent` graph has nodes: `planner → tool_executor → reviewer → human_checkpoint → report_generator`. State is a typed `TypedDict` carrying conversation history, retrieved chunks, tool outputs, and a `requires_human_approval` flag.

**If removed:** Agent logic devolves to a fragile `while True` loop with no state management.

---

### pgvector on Postgres
**What:** A Postgres extension that adds vector similarity search (cosine, L2, inner product) as native SQL operators.

**Why over Pinecone/Qdrant/Weaviate:** Free, self-hosted, no vendor lock-in, co-locates structured metadata with vectors in one database. Hybrid search (vector + BM25) is possible via `pg_trgm` and `tsvector`. At sub-100K document scale, performance is excellent.

**If removed:** Need a separate vector DB service, added cost, more operational complexity.

---

### Upstash Redis
**What:** Serverless Redis with a REST API. No persistent connection required.

**Why:** Free tier, zero infrastructure to manage, works perfectly in GitHub Codespaces where TCP Redis connections can be unreliable. Semantic caching reduces repeated Anthropic API calls.

**How used:** Before embedding a query, check if a semantically similar query has been answered before. Uses cosine similarity on cached query embeddings. Cache TTL: 1 hour for tax questions (tax laws don't change mid-session).

**If removed:** Every identical or near-identical query hits Claude. Costs multiply significantly.

---

### Langfuse
**What:** Open-source LLM observability platform. Captures traces, spans, token usage, latency, cost, and prompt versions.

**Why over LangSmith:** Open-source with self-host option, better cost tracking granularity, built-in RAGAS integration for eval score storage.

**How used:** Every `/query` and `/agent` call is wrapped in a `langfuse.trace()`. Spans are created for: embedding, retrieval, reranking, LLM call. Token cost is logged per call. Prompt versions are managed through Langfuse's prompt registry.

**If removed:** Complete observability blindness. No way to audit LLM behavior or track cost.

---

### RAGAS
**What:** An evaluation framework for RAG pipelines. Measures quality across four axes.

**Metrics used:**
| Metric | What it measures | Target |
|---|---|---|
| Faithfulness | Does the answer stay within retrieved context? | ≥ 0.75 |
| Answer Relevancy | Is the answer relevant to the question? | ≥ 0.80 |
| Context Recall | Did retrieval surface the right chunks? | ≥ 0.70 |
| Context Precision | Are retrieved chunks actually useful? | ≥ 0.65 |

**How used:** 50-question golden dataset in `eval/golden_dataset.json`. RAGAS runs in CI on every PR. A Faithfulness score below 0.75 fails the pipeline — the PR cannot merge.

---

### HashiCorp Vault
**What:** Secrets management platform. Stores API keys, DB credentials, and service tokens as dynamic or static secrets.

**How used:** Vault Agent sidecar in Kubernetes injects secrets as environment variables at pod startup. In Codespaces, secrets are injected via GitHub Secrets. Vault policies enforce least-privilege — the app service account can only read paths under `secret/taxsage/`.

**If removed:** Secrets go into `.env` files or K8s Secrets base64-encoded — a significant security regression.

---

### Trivy + tfsec + OWASP ZAP
**Trivy:** Scans Docker images for CVEs in OS packages and Python dependencies. Runs in CI before image push. HIGH/CRITICAL findings fail the build.

**tfsec:** Static analysis for Terraform IaC. Catches misconfigurations like public GCS buckets, missing encryption, overly permissive IAM.

**OWASP ZAP:** DAST (dynamic application security testing). Runs against a staging deployment to detect injection, XSS, and broken auth patterns.

---

## Complete Data Flow Walkthroughs

### (a) Document Ingestion
```
1. User POST /ingest with PDF file (multipart/form-data)
2. FastAPI validates request via Pydantic (IngestRequest schema)
3. File saved to /tmp/uploads/{uuid}.pdf
4. Langfuse trace started: langfuse.trace(name="ingest", input=filename)
5. LlamaIndex SimpleDirectoryReader loads PDF
   → pdfminer extracts text per page
   → metadata extracted: filename, page_count, doc_type (detected via classifier)
6. SentenceSplitter applied:
   → chunk_size=512 tokens, chunk_overlap=50
   → each chunk gets metadata: {source_file, page_num, chunk_index, doc_type}
7. Anthropic embeddings called for each chunk batch (batched 20 at a time)
   → model: text-embedding-3-small (or voyage-2 — configurable)
   → returns 1536-dim float vectors
8. pgvector INSERT:
   INSERT INTO document_chunks (id, content, embedding, metadata, user_id, created_at)
   VALUES ($1, $2, $3::vector, $4::jsonb, $5, NOW())
9. Langfuse span closed: logs chunk_count, embedding_tokens, latency
10. FastAPI returns: {"status": "ok", "chunks_created": 47, "trace_id": "..."}
```

### (b) RAG Query
```
1. User POST /query: {"question": "What is my HRA exemption?", "session_id": "abc"}
2. FastAPI validates via QueryRequest schema
3. Langfuse trace starts
4. Upstash Redis cache lookup:
   → query is embedded (same embedding model)
   → Redis HGETALL cache_key (cosine similarity > 0.92 = cache hit)
   → If HIT: return cached response, log "cache_hit" span, done
5. If MISS: pgvector hybrid search
   → Vector search: SELECT ... ORDER BY embedding <=> $query_vec LIMIT 20
   → BM25 search: SELECT ... WHERE to_tsvector(content) @@ plainto_tsquery($query)
   → Results merged via RRF (Reciprocal Rank Fusion)
6. Cohere Rerank API called with top-20 chunks + query
   → Returns reranked list, top-5 selected
7. Context assembled:
   → System prompt loaded from Langfuse prompt registry (versioned)
   → User question + top-5 chunks formatted into messages array
8. Claude API called (claude-haiku in dev, claude-sonnet in prod):
   → stream=True
   → tool_use definitions injected for agent mode
9. Streaming tokens forwarded via SSE to client
10. On stream close: full response assembled
11. Langfuse span: input_tokens, output_tokens, cost, latency, model
12. Response + embedding cached in Upstash Redis (TTL: 3600s)
13. Response returned with source citations [{chunk_id, page_num, source_file}]
```

### (c) Agent Task
```
1. User POST /agent: {"task": "Optimise my tax for FY 2024-25", "session_id": "abc"}
2. LangGraph TaxOptimiserAgent initialised with initial state:
   AgentState = {
     messages: [HumanMessage(task)],
     documents: [],
     tool_outputs: {},
     plan: [],
     requires_approval: False,
     final_report: None
   }
3. Node: planner
   → Claude called with task + available tools list
   → Returns JSON plan: ["retrieve_documents", "calculate_gross_income",
                         "find_deductions", "check_80C_headroom",
                         "calculate_net_liability", "generate_report"]
   → plan stored in state
4. Node: tool_executor (loops over plan)
   → tool: document_retriever → pgvector search for income docs
   → tool: tax_calculator → computes gross income from chunks
   → tool: deduction_finder → scans for 80C, 80D, HRA, LTA mentions
   → tool: slab_checker → matches income to FY24-25 tax slabs
   → All outputs stored in state.tool_outputs
5. Node: reviewer
   → Claude reviews tool_outputs for consistency
   → If recommendations involve filing changes → sets requires_approval=True
6. Conditional edge: if requires_approval → human_checkpoint node
   → Graph pauses, writes checkpoint to Postgres (LangGraph checkpointer)
   → API returns: {"status": "awaiting_approval", "checkpoint_id": "..."}
   → User reviews and calls POST /agent/resume with approval
7. Node: report_generator
   → Claude compiles final plain-language tax optimisation report
   → Includes: current liability, potential savings, recommended actions
8. Langfuse: entire graph execution logged as nested spans
9. Response: {"report": "...", "savings_identified": 45000, "trace_id": "..."}
```

---

## RAG Pipeline Internals

### Chunking Strategy
512-token chunks with 50-token overlap. Why:
- Indian tax documents have dense numerical tables — too small a chunk loses context
- 512 fits comfortably in Claude's context with 5 chunks = ~2560 tokens, leaving room for system prompt and response
- 50-token overlap ensures sentences split across chunk boundaries appear in at least one complete chunk

Chunking is done by `SentenceSplitter` (not naive character splitting) so sentence boundaries are respected.

### Embedding Model
Default: Anthropic's `voyage-2` embeddings (1024 dims). Configurable to OpenAI `text-embedding-3-small` (1536 dims). Voyage-2 is preferred because it's trained for retrieval tasks and produces superior semantic representations for financial/legal text.

### Hybrid Search
pgvector handles vector similarity. `pg_trgm` + `tsvector` handles keyword (BM25-equivalent) search. Results from both are merged using Reciprocal Rank Fusion:
```python
def reciprocal_rank_fusion(vector_results, bm25_results, k=60):
    scores = defaultdict(float)
    for rank, doc in enumerate(vector_results):
        scores[doc.id] += 1 / (k + rank + 1)
    for rank, doc in enumerate(bm25_results):
        scores[doc.id] += 1 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

### Reranking
Cohere Rerank v3 reorders the top-20 hybrid results. It uses a cross-encoder (not bi-encoder like the embedding model) — it sees the query AND each chunk together, giving more accurate relevance scoring. Top-5 after reranking go into the LLM context.

### Context Window Management
System prompt: ~400 tokens. 5 chunks × ~400 tokens each = ~2000 tokens. User question: ~50 tokens. Total input: ~2450 tokens. This leaves ~5500 tokens for Claude Haiku's 8K context for the response. For longer documents, chunk count is reduced to 3.

---

## Agent Internals

### LangGraph Graph Structure
```
START → planner → tool_executor → reviewer → [conditional]
                                              ↓ requires_approval=True
                                         human_checkpoint ← resume signal
                                              ↓
                                         report_generator → END
                                         ↑ requires_approval=False
```

### State Schema
```python
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    documents: list[Document]
    tool_outputs: dict[str, Any]
    plan: list[str]
    current_step: int
    requires_approval: bool
    approval_granted: bool
    final_report: Optional[str]
    trace_id: str
```

### Human-in-Loop
LangGraph's `interrupt_before=["human_checkpoint"]` pauses the graph. State is serialised to Postgres via `AsyncPostgresSaver`. The `/agent/resume` endpoint loads the checkpoint and continues execution. This means the user can review AI recommendations before any irreversible action (like filing a return).

### Failure Handling
Each tool node wraps execution in `try/except`. Failures are written to `state.tool_outputs[tool_name] = {"error": str(e)}`. The reviewer node detects error states and either retries (max 2) or marks the step as skipped with an explanation in the final report.

---

## Database Schema
```sql
-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Main document chunks table
CREATE TABLE document_chunks (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL,
    content     TEXT NOT NULL,
    embedding   VECTOR(1024),         -- voyage-2 dims
    metadata    JSONB NOT NULL,        -- {source_file, page_num, chunk_index, doc_type, fiscal_year}
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- HNSW index for fast approximate nearest-neighbour search
CREATE INDEX idx_chunks_embedding ON document_chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Full-text search index for BM25 hybrid search
CREATE INDEX idx_chunks_fts ON document_chunks
    USING gin(to_tsvector('english', content));

-- User + fiscal year filter index
CREATE INDEX idx_chunks_user_fy ON document_chunks (user_id, (metadata->>'fiscal_year'));

-- Agent checkpoints (LangGraph state persistence)
CREATE TABLE agent_checkpoints (
    checkpoint_id   UUID PRIMARY KEY,
    session_id      UUID NOT NULL,
    state_json      JSONB NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

**Metadata fields stored per chunk:**
| Field | Type | Example |
|---|---|---|
| source_file | string | "Form16_FY2425.pdf" |
| page_num | int | 3 |
| chunk_index | int | 12 |
| doc_type | string | "form16" / "itr" / "ais" |
| fiscal_year | string | "2024-25" |
| user_upload_id | UUID | "uuid-v4" |

---

## API Reference

### POST /ingest
Upload a tax document for processing.

**Request:** `multipart/form-data`
```
file: <PDF binary>
user_id: string
doc_type: "form16" | "itr" | "ais" | "mf_statement" | "salary_slip"
fiscal_year: string  # e.g. "2024-25"
```

**Response:**
```json
{"status": "ok", "chunks_created": 47, "trace_id": "lf-abc123"}
```

**curl:**
```bash
curl -X POST http://localhost:8000/ingest \
  -F "file=@Form16.pdf" \
  -F "user_id=user-uuid-here" \
  -F "doc_type=form16" \
  -F "fiscal_year=2024-25"
```

---

### POST /query
Ask a natural language tax question.

**Request:**
```json
{
  "question": "What is my total 80C deduction this year?",
  "session_id": "sess-uuid",
  "user_id": "user-uuid",
  "stream": true
}
```

**Response (SSE stream):**
```
data: {"token": "Your"}
data: {"token": " total"}
data: {"token": " 80C"}
...
data: {"done": true, "sources": [{"file": "Form16.pdf", "page": 2}], "trace_id": "lf-xyz"}
```

---

### POST /agent
Start an agentic tax optimisation task.

**Request:**
```json
{
  "task": "Find all deductions I'm missing and estimate my refund",
  "session_id": "sess-uuid",
  "user_id": "user-uuid"
}
```

**Response:**
```json
{
  "status": "completed" | "awaiting_approval",
  "report": "Based on your documents...",
  "checkpoint_id": "ckpt-uuid",
  "savings_identified": 45000,
  "trace_id": "lf-abc"
}
```

---

### POST /agent/resume
Resume a paused agent after human approval.
```bash
curl -X POST http://localhost:8000/agent/resume \
  -H "Content-Type: application/json" \
  -d '{"checkpoint_id": "ckpt-uuid", "approved": true}'
```

---

## Loading New Document Types

To add a new document type (e.g., Form 26AS):

1. Add the type to `app/models/schemas.py`:
```python
class DocType(str, Enum):
    FORM_26AS = "form_26as"
```

2. Create a loader in `app/rag/loaders/form_26as_loader.py`:
```python
class Form26ASLoader(BaseLoader):
    def load(self, file_path: str) -> list[Document]:
        # Custom parsing logic for Form 26AS XML/PDF structure
        ...
```

3. Register in `app/rag/ingestion_pipeline.py`:
```python
LOADER_REGISTRY = {
    "form_26as": Form26ASLoader,
    "form16": Form16Loader,
    ...
}
```

4. Add to the golden eval dataset in `eval/golden_dataset.json` with Form 26AS-specific questions.

5. Update Langfuse prompt templates if the system prompt needs document-type-specific instructions.

---

## Observability Guide

### What Langfuse Captures
Every request creates a **Trace** with nested **Spans**:
```
Trace: query (session_id, user_id, question)
  ├─ Span: cache_lookup (latency, hit/miss)
  ├─ Span: embedding (tokens, latency, model)
  ├─ Span: retrieval (chunks_returned, latency)
  ├─ Span: reranking (input_count, output_count, latency)
  └─ Span: llm_call (input_tokens, output_tokens, cost_usd, model, latency)
```

### Key Metrics to Monitor
| Metric | Alert Threshold | Dashboard |
|---|---|---|
| LLM call latency p95 | > 5s | Langfuse → Metrics |
| Daily Anthropic cost | > $5 | Langfuse → Cost |
| Cache hit rate | < 30% | Upstash console |
| RAGAS Faithfulness | < 0.75 | Langfuse → Evals |
| Retrieval chunk count | < 2 | Langfuse → Traces |

### Reading a Trace
In Langfuse UI: Project → Traces → click any trace → expand spans → check `llm_call` span for token usage. If faithfulness is low, inspect the `retrieval` span to see which chunks were passed to Claude.

---

## Eval Framework

### Running Evals
```bash
cd eval/
python run_ragas.py --dataset golden_dataset.json --env dev
```

### Golden Dataset Format
```json
[
  {
    "question": "What is the standard deduction for salaried employees in FY 2024-25?",
    "ground_truth": "The standard deduction is ₹50,000 for salaried employees under the old tax regime.",
    "context_docs": ["form16"]
  }
]
```

### Interpreting Scores
- **Faithfulness < 0.75**: Claude is hallucinating — not staying within retrieved context. Check system prompt, reduce temperature.
- **Context Recall < 0.70**: Retrieval is missing relevant chunks. Tune chunk size, embedding model, or BM25 weights.
- **Answer Relevancy < 0.80**: Claude is going off-topic. Tighten system prompt constraints.

### CI Gate
`.github/workflows/eval.yml` runs `run_ragas.py` and parses output JSON. If any metric is below threshold, the step exits with code 1, blocking the PR merge.

---

## Security Model

### Secrets Flow
```
GitHub Secrets (dev) ──→ Codespaces env vars
Vault (prod)         ──→ Vault Agent sidecar ──→ K8s pod env vars
```
No secret ever lives in code, `.env` files committed to git, or Docker images.

### OPA Data Classification
OPA policies in `infra/opa/policies/` enforce:
- Raw PII (PAN number, Aadhaar) is masked before leaving the retrieval layer
- User A cannot query User B's documents (row-level security enforced by `user_id` filter on all pgvector queries)
- External API calls (Cohere, Anthropic) receive only anonymised text — PAN/Aadhaar replaced with `[REDACTED]` via Presidio before sending

### Trivy in CI
```yaml
- name: Scan Docker image
  run: trivy image --exit-code 1 --severity HIGH,CRITICAL taxsage-ai:latest
```

Fails build on HIGH or CRITICAL CVEs in OS packages or Python deps.

---

## Known Limitations & Future Improvements

| Limitation | Planned Fix |
|---|---|
| No web UI — REST API only | React frontend (Next.js) planned |
| Single-user Codespaces dev setup | Multi-tenant auth via Clerk/Auth0 |
| Cohere free tier has rate limits | Self-hosted reranker (BGE-Reranker) |
| RAGAS evals need manual curation | LLM-assisted golden dataset generation |
| No support for Hindi/Telugu documents | Multilingual embeddings (mE5-large) |
| Agent doesn't file returns — advisory only | CA API integration (future) |
