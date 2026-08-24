"""Hybrid baseline: configurable alpha fusion of SQL + vector results."""
from __future__ import annotations

import time

from app.conversation.models import RetrievalMode
from app.hybrid.retriever import HybridRetriever
from app.metrics.aggregator import BenchmarkQuery, BenchmarkResult
from app.planning.intent_extractor import extract_intent
from app.planning.models import QueryPlan
from app.sql.executor import get_sql_executor
from app.sql.generator import get_sql_generator
from app.vector.oracle_search import get_vector_search


class HybridBaseline:
    """Full hybrid retrieval baseline with configurable alpha."""

    def __init__(self, alpha: float = 0.5) -> None:
        self._alpha = alpha
        self._retriever = HybridRetriever(
            sql_executor=get_sql_executor(),
            sql_generator=get_sql_generator(),
            vector_search=get_vector_search(),
            alpha=alpha,
        )

    def run(self, queries: list[BenchmarkQuery], top_k: int = 10) -> list[BenchmarkResult]:
        results: list[BenchmarkResult] = []

        for q in queries:
            started = time.perf_counter()
            try:
                intent = extract_intent(q.question)
                plan = QueryPlan(
                    retrieval_mode=RetrievalMode.HYBRID,
                    structured_intent=intent,
                    semantic_intent=q.question,
                    confidence=0.90,
                    raw_query=q.question,
                )
                hybrid_result = self._retriever.retrieve(plan, top_k=top_k, alpha=self._alpha)
                retrieved_ids = [r.paper_id for r in hybrid_result.results]
            except Exception:
                retrieved_ids = []

            elapsed = (time.perf_counter() - started) * 1000
            results.append(BenchmarkResult(
                query_id=q.query_id,
                retrieved_ids=retrieved_ids,
                latency_ms=elapsed,
            ))

        return results
