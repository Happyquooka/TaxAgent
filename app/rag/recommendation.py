from __future__ import annotations

import re

from app.rag.schemas import Citation, Recommendation, RecommendationResponse


SECTION_PATTERN = re.compile(r"(section|sec)\s*([0-9]{1,3}[A-Z]?)", re.IGNORECASE)


def recommend_sections(query: str, citations: list[Citation]) -> RecommendationResponse:
    sections: dict[str, Recommendation] = {}
    for citation in citations:
        for match in SECTION_PATTERN.finditer(citation.excerpt):
            sec = f"Section {match.group(2).upper()}"
            if sec not in sections:
                sections[sec] = Recommendation(
                    section=sec,
                    confidence=0.72,
                    rationale=f"Inferred from retrieved source: {citation.source_name}",
                )
    if not sections:
        return RecommendationResponse(
            recommendations=[],
            citations=citations,
            abstained=True,
        )
    ranked = sorted(sections.values(), key=lambda r: r.section)[:5]
    return RecommendationResponse(recommendations=ranked, citations=citations, abstained=False)
