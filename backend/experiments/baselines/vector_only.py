"""Vector-only baseline: uses only semantic similarity, no SQL filters."""
from __future__ import annotations

import time

from app.metrics.aggregator import BenchmarkQuery, BenchmarkResult
from app.vector.oracle_search import get_vector_search


class VectorOnlyBaseline:
    """Retrieves using only vector similarity search. No SQL filtering."""

    def __init__(self) -> None:
        self._search = get_vector_search()

    def run(self, queries: list[BenchmarkQuery], top_k: int = 10) -> list[BenchmarkResult]:
        results: list[BenchmarkResult] = []

        for q in queries:
            started = time.perf_counter()
            try:
                vec_results = self._search.search(q.question, top_k=top_k)
                retrieved_ids = [r.paper_id for r in vec_results]
            except Exception:
                retrieved_ids = []

            elapsed = (time.perf_counter() - started) * 1000
            results.append(BenchmarkResult(
                query_id=q.query_id,
                retrieved_ids=retrieved_ids,
                latency_ms=elapsed,
            ))

        return results
