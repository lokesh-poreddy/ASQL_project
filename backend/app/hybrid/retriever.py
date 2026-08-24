"""HybridRetriever: orchestrates SQL + vector pipelines and fuses results.

Pipeline:
    User query + plan
         │
    ┌────┴────┐
    ▼         ▼
  SQL      Vector search
  filter   (cosine/HNSW)
    │         │
    └────┬────┘
         ▼
    Score normalization
         ▼
    Weighted fusion (α)
         ▼
      Top-K ranked results
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from app.common.logging import get_logger
from app.config import get_settings
from app.hybrid.fusion import FusionCandidate, FusedResult, ScoreFusion
from app.hybrid.score_normalizer import rank_normalize
from app.planning.models import QueryPlan
from app.sql.executor import SQLExecutionResult
from app.vector.oracle_search import VectorSearchResult

logger = get_logger("hybrid.retriever")


@dataclass
class HybridRetrievalResult:
    results: list[FusedResult]
    sql_candidate_count: int
    vector_candidate_count: int
    alpha_used: float
    elapsed_ms: float


class HybridRetriever:

    def __init__(
        self,
        sql_executor,
        sql_generator,
        vector_search,
        alpha: float | None = None,
    ) -> None:
        self._sql_executor = sql_executor
        self._sql_generator = sql_generator
        self._vector_search = vector_search
        self._fusion = ScoreFusion()
        self._default_alpha = alpha if alpha is not None else get_settings().hybrid_alpha

    def retrieve(
        self,
        plan: QueryPlan,
        top_k: int | None = None,
        alpha: float | None = None,
    ) -> HybridRetrievalResult:
        settings = get_settings()
        top_k = top_k or settings.default_top_k
        alpha = alpha if alpha is not None else self._default_alpha
        candidate_k = top_k * settings.candidate_multiplier

        started = time.perf_counter()

        # ── SQL branch ────────────────────────────────────────────────────────
        sql_rows: list[dict] = []
        from app.conversation.models import RetrievalMode
        if plan.retrieval_mode in (RetrievalMode.SQL, RetrievalMode.HYBRID):
            try:
                sql_str, params = self._sql_generator.generate(plan)
                sql_result: SQLExecutionResult = self._sql_executor.execute(sql_str, params)
                sql_rows = sql_result.rows
            except Exception as exc:
                logger.warning("SQL branch failed in hybrid retrieve: %s", exc)

        # ── Vector branch ─────────────────────────────────────────────────────
        vec_results: list[VectorSearchResult] = []
        if plan.retrieval_mode in (RetrievalMode.VECTOR, RetrievalMode.HYBRID):
            if plan.semantic_intent:
                try:
                    vec_results = self._vector_search.search(
                        plan.semantic_intent, top_k=candidate_k
                    )
                except Exception as exc:
                    logger.warning("Vector branch failed in hybrid retrieve: %s", exc)

        # ── Merge candidates ──────────────────────────────────────────────────
        candidates = self._merge(sql_rows, vec_results, candidate_k)

        # ── Fuse ──────────────────────────────────────────────────────────────
        fused = self._fusion.fuse(candidates, alpha=alpha, top_k=top_k)

        elapsed = (time.perf_counter() - started) * 1000
        logger.info(
            "Hybrid retrieve: sql=%d vector=%d → fused=%d | α=%.2f | %.1f ms",
            len(sql_rows), len(vec_results), len(fused), alpha, elapsed,
        )

        return HybridRetrievalResult(
            results=fused,
            sql_candidate_count=len(sql_rows),
            vector_candidate_count=len(vec_results),
            alpha_used=alpha,
            elapsed_ms=elapsed,
        )

    def _merge(
        self,
        sql_rows: list[dict],
        vec_results: list[VectorSearchResult],
        candidate_k: int,
    ) -> list[FusionCandidate]:
        # Index SQL by paper_id with a rank-based score
        sql_scores: dict[int, float] = {}
        for rank, row in enumerate(sql_rows[:candidate_k], start=1):
            pid = row.get("paper_id")
            if pid is not None:
                sql_scores[pid] = 1.0 / rank

        # Normalize SQL scores to [0, 1]
        if sql_scores:
            vals = list(sql_scores.values())
            lo, hi = min(vals), max(vals)
            if hi > lo:
                sql_scores = {k: (v - lo) / (hi - lo) for k, v in sql_scores.items()}

        # Index vector by paper_id
        vec_scores: dict[int, tuple[str, float]] = {}
        for vr in vec_results[:candidate_k]:
            vec_scores[vr.paper_id] = (vr.title, max(0.0, vr.score))

        # Normalize vector scores
        if vec_scores:
            vals = [v[1] for v in vec_scores.values()]
            norm = rank_normalize(vals)
            vec_scores = {
                pid: (title, norm[i])
                for i, (pid, (title, _)) in enumerate(vec_scores.items())
            }

        # Union of all candidate paper_ids
        all_ids = set(sql_scores.keys()) | set(vec_scores.keys())

        candidates: list[FusionCandidate] = []
        for pid in all_ids:
            title = ""
            if pid in vec_scores:
                title = vec_scores[pid][0]

            # Try to get title from SQL rows if missing
            if not title:
                for row in sql_rows:
                    if row.get("paper_id") == pid:
                        title = row.get("title", "")
                        break

            candidates.append(
                FusionCandidate(
                    paper_id=pid,
                    title=title,
                    sql_score=sql_scores.get(pid, 0.0),
                    semantic_score=vec_scores.get(pid, (title, 0.0))[1],
                )
            )

        return candidates
