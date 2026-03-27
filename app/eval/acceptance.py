from __future__ import annotations

from dataclasses import dataclass

from app.eval.ragas_eval import EvalResult


@dataclass
class AcceptanceCriteria:
    min_retrieval_recall: float = 0.75
    min_citation_precision: float = 0.8
    max_p95_latency_ms: float = 2500.0


def check_acceptance(result: EvalResult, criteria: AcceptanceCriteria | None = None) -> dict:
    c = criteria or AcceptanceCriteria()
    return {
        "retrieval_recall_pass": result.retrieval_recall >= c.min_retrieval_recall,
        "citation_precision_pass": result.citation_precision >= c.min_citation_precision,
        "latency_pass": result.p95_latency_ms <= c.max_p95_latency_ms,
    }
