from __future__ import annotations

from collections import Counter


def lexical_rerank(query_terms: list[str], texts: list[str], top_k: int = 6) -> list[int]:
    scored: list[tuple[int, int]] = []
    query_counter = Counter(query_terms)
    for idx, text in enumerate(texts):
        tokens = text.lower().split()
        token_counter = Counter(tokens)
        score = sum(min(token_counter[t], query_counter[t]) for t in query_terms)
        scored.append((idx, score))
    scored.sort(key=lambda item: item[1], reverse=True)
    return [idx for idx, _ in scored[:top_k]]
