from __future__ import annotations

from pydantic import BaseModel, Field


class Citation(BaseModel):
    source_name: str
    source_ref: str
    excerpt: str


class Recommendation(BaseModel):
    section: str
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str


class RecommendationResponse(BaseModel):
    recommendations: list[Recommendation]
    citations: list[Citation]
    abstained: bool = False
