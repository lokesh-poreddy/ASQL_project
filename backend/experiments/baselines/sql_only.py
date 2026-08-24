"""SQL-only baseline: uses only the SQL retrieval path, ignores semantic intent."""
from __future__ import annotations

import time
from typing import Any

from app.metrics.aggregator import BenchmarkQuery, BenchmarkResult
from app.planning.intent_extractor import extract_intent
from app.planning.models import QueryPlan, StructuredIntent
from app.conversation.models import RetrievalMode
from app.sql.executor import get_sql_executor
from app.sql.generator import get_sql_generator
from app.sql.validator import SQLValidator


class SQLOnlyBaseline:
    """Retrieves using only structured SQL filtering. No vector search."""

    def __init__(self) -> None:
        self._executor = get_sql_executor()
        self._generator = get_sql_generator()
        self._validator = SQLValidator()

    def run(self, queries: list[BenchmarkQuery], top_k: int = 10) -> list[BenchmarkResult]:
        results: list[BenchmarkResult] = []

        for q in queries:
            started = time.perf_counter()
            try:
                intent = extract_intent(q.question)
                plan = QueryPlan(
                    retrieval_mode=RetrievalMode.SQL,
                    structured_intent=intent,
                    semantic_intent=None,
                    confidence=1.0,
                    raw_query=q.question,
                )
                sql, params = self._generator.generate(plan)
                self._validator.validate(sql)
                result = self._executor.execute(sql, params)
                retrieved_ids = [r["paper_id"] for r in result.rows[:top_k]]
            except Exception:
                retrieved_ids = []

            elapsed = (time.perf_counter() - started) * 1000
            results.append(BenchmarkResult(
                query_id=q.query_id,
                retrieved_ids=retrieved_ids,
                latency_ms=elapsed,
            ))

        return results
