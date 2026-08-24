"""Hybrid score fusion.

Implements weighted linear fusion: final = α × semantic + (1-α) × structured.

α is the hybrid_alpha setting (default 0.5, configurable per experiment).
The alpha value is the primary research variable for the fusion ablation.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.hybrid.score_normalizer import minmax_normalize


@dataclass
class FusionCandidate:
    paper_id: int
    title: str
    sql_score: float      # normalized [0, 1]
    semantic_score: float # normalized [0, 1]


@dataclass
class FusedResult:
    paper_id: int
    title: str
    final_score: float
    sql_score: float
    semantic_score: float
    alpha_used: float


class ScoreFusion:
    """Weighted linear combination of SQL and semantic scores."""

    def fuse(
        self,
        candidates: list[FusionCandidate],
        alpha: float,
        top_k: int,
    ) -> list[FusedResult]:
        """
        alpha ∈ [0, 1]: weight for semantic score.
        (1 - alpha):     weight for SQL/structured score.
        """
        if not 0.0 <= alpha <= 1.0:
            raise ValueError(f"alpha must be in [0, 1], got {alpha}")

        results: list[FusedResult] = []
        for c in candidates:
            final = alpha * c.semantic_score + (1.0 - alpha) * c.sql_score
            results.append(
                FusedResult(
                    paper_id=c.paper_id,
                    title=c.title,
                    final_score=final,
                    sql_score=c.sql_score,
                    semantic_score=c.semantic_score,
                    alpha_used=alpha,
                )
            )

        results.sort(key=lambda r: r.final_score, reverse=True)
        return results[:top_k]
