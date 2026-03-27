from __future__ import annotations

import re
from collections import Counter

from sqlalchemy.orm import Session

from app.db.repository import DocumentRepository
from app.rag.rerank import lexical_rerank
from app.rag.schemas import Citation


def extract_query_terms(query: str, max_terms: int = 5) -> list[str]:
    tokens = re.findall(r"[a-zA-Z0-9]+", query.lower())
    stopwords = {
        "the",
        "is",
        "a",
        "an",
        "for",
        "to",
        "and",
        "of",
        "in",
        "on",
        "with",
        "what",
        "which",
    }
    filtered = [t for t in tokens if len(t) > 2 and t not in stopwords]
    counts = Counter(filtered)
    return [term for term, _ in counts.most_common(max_terms)]


def retrieve_citations(
    db: Session, query: str, assessment_year: str | None = None, top_k: int = 6
) -> list[Citation]:
    terms = extract_query_terms(query)
    repo = DocumentRepository(db)
    chunks = repo.fetch_candidate_chunks(
        terms[:2] or terms, assessment_year=assessment_year, top_k=max(top_k * 2, 8)
    )
    ranked_indices = lexical_rerank(terms, [c.content for c in chunks], top_k=top_k)
    citations: list[Citation] = []
    for idx in ranked_indices:
        chunk = chunks[idx]
        citations.append(
            Citation(
                source_name=chunk.document.source_name,
                source_ref=chunk.source_ref,
                excerpt=chunk.content[:300],
            )
        )
    return citations
