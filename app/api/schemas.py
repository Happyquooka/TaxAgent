from __future__ import annotations

from pydantic import BaseModel, Field

from app.rag.schemas import RecommendationResponse


class IngestRequest(BaseModel):
    source_path: str


class IngestResponse(BaseModel):
    file: str
    status: str
    chunks: int | None = None
    reason: str | None = None


class QueryRequest(BaseModel):
    query: str = Field(min_length=5)
    assessment_year: str | None = None


class QueryResponse(BaseModel):
    answer: str
    citations: list[dict]


class RecommendRequest(BaseModel):
    query: str = Field(min_length=5)
    assessment_year: str | None = None


class RecommendResponse(RecommendationResponse):
    pass
