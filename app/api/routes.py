from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.schemas import (
    IngestRequest,
    IngestResponse,
    QueryRequest,
    QueryResponse,
    RecommendRequest,
    RecommendResponse,
)
from app.core.cache import get_redis_client
from app.core.settings import get_settings
from app.core.tracing import get_langfuse_client
from app.db.base import SessionLocal
from app.ingest.pipeline import ingest_path
from app.rag.recommendation import recommend_sections
from app.rag.retrieval import retrieve_citations

router = APIRouter()


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/ingest", response_model=IngestResponse)
def ingest(request: IngestRequest, db: Session = Depends(get_db)) -> IngestResponse:
    path = Path(request.source_path)
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=400, detail="source_path must be an existing file")
    return IngestResponse(**ingest_path(db, path))


@router.post("/query", response_model=QueryResponse)
def query(request: QueryRequest, db: Session = Depends(get_db)) -> QueryResponse:
    langfuse = get_langfuse_client()
    citations = retrieve_citations(db, request.query, assessment_year=request.assessment_year)
    if not citations:
        if langfuse:
            langfuse.trace(name="query", input={"query": request.query}, output={"abstained": True})
        return QueryResponse(
            answer="I do not have sufficient evidence in the indexed tax documents. Please ingest relevant source documents.",
            citations=[],
        )
    answer = "Based on retrieved tax references, review the cited sections and validate eligibility for your filing context."
    if langfuse:
        langfuse.trace(
            name="query",
            input={"query": request.query},
            output={"citation_count": len(citations)},
        )
    return QueryResponse(answer=answer, citations=[c.model_dump() for c in citations])


@router.post("/recommend-sections", response_model=RecommendResponse)
def recommend(request: RecommendRequest, db: Session = Depends(get_db)) -> RecommendResponse:
    citations = retrieve_citations(db, request.query, assessment_year=request.assessment_year)
    rec = recommend_sections(request.query, citations)
    return RecommendResponse(**rec.model_dump())


@router.get("/health/dependencies")
def dependencies_health(db: Session = Depends(get_db)) -> dict:
    settings = get_settings()
    db_ok = True
    redis_ok = True
    llm_configured = bool(settings.openai_api_key or settings.anthropic_api_key)
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    redis_client = get_redis_client()
    if redis_client is None:
        redis_ok = False
    else:
        try:
            redis_client.ping()
        except Exception:
            redis_ok = False
    return {"postgres": db_ok, "redis": redis_ok, "llm_configured": llm_configured}
