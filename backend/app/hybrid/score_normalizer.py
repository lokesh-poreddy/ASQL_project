"""Score normalization before hybrid fusion.

SQL/structured results come with a raw citation_count or row-order score.
Vector results come with a cosine similarity in [-1, 1] (usually [0, 1]
after normalisation). Both need to be scaled to [0, 1] before fusion.
"""
from __future__ import annotations

from typing import Sequence


def minmax_normalize(scores: Sequence[float]) -> list[float]:
    """Min-max normalize to [0, 1]. Returns all 1.0s if scores are constant."""
    if not scores:
        return []
    lo, hi = min(scores), max(scores)
    if abs(hi - lo) < 1e-9:
        return [1.0] * len(scores)
    return [(s - lo) / (hi - lo) for s in scores]


def rank_normalize(scores: Sequence[float]) -> list[float]:
    """Normalize by rank position (reciprocal rank variant).

    Rank 1 → 1.0, rank N → 1/N. More robust than min-max when outliers exist.
    """
    if not scores:
        return []
    indexed = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
    result = [0.0] * len(scores)
    for rank, (orig_idx, _) in enumerate(indexed, start=1):
        result[orig_idx] = 1.0 / rank
    # Re-normalize to [0, 1]
    return minmax_normalize(result)
