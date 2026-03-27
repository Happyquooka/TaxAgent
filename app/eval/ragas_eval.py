from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EvalResult:
    retrieval_recall: float
    citation_precision: float
    p95_latency_ms: float


def evaluate_baseline() -> EvalResult:
    # Placeholder hook for integrating ragas with your curated tax QA set.
    return EvalResult(retrieval_recall=0.0, citation_precision=0.0, p95_latency_ms=0.0)
