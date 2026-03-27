from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.models import Chunk, Document


class DocumentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def upsert_document(self, payload: dict[str, Any]) -> Document:
        existing = self.db.execute(
            select(Document).where(Document.source_path == payload["source_path"])
        ).scalar_one_or_none()
        if existing:
            for key, value in payload.items():
                setattr(existing, key, value)
            self.db.flush()
            return existing
        new_doc = Document(**payload)
        self.db.add(new_doc)
        self.db.flush()
        return new_doc

    def replace_chunks(self, document_id: int, chunks: Iterable[dict[str, Any]]) -> None:
        self.db.query(Chunk).filter(Chunk.document_id == document_id).delete()
        for item in chunks:
            self.db.add(Chunk(document_id=document_id, **item))
        self.db.flush()

    def fetch_candidate_chunks(
        self,
        query_terms: list[str],
        assessment_year: str | None = None,
        top_k: int = 8,
    ) -> list[Chunk]:
        stmt = select(Chunk).join(Document)
        if assessment_year:
            stmt = stmt.where(Document.assessment_year == assessment_year)
        if query_terms:
            # Use OR matching across terms to improve recall for natural queries.
            stmt = stmt.where(or_(*[Chunk.content.ilike(f"%{term}%") for term in query_terms]))
        stmt = stmt.limit(top_k)
        return list(self.db.execute(stmt).scalars().all())
