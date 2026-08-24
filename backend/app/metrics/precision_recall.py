"""IR metrics: Precision@K, Recall@K, DCG@K, NDCG@K, MRR.

All functions are pure — they take retrieved IDs and a relevant set, and
return a float. They do NOT query the database. Keep metrics independent
so experiments remain reproducible.

Reference:
  Manning, Raghavan & Schütze, Introduction to Information Retrieval (2008).
  Chapters 8 (evaluation) and 12 (language models for IR).
"""
from __future__ import annotations

import math
from typing import Iterable


def precision_at_k(
    retrieved: Iterable[int],
    relevant: set[int],
    k: int,
) -> float:
    results = list(retrieved)[:k]
    if not results:
        return 0.0
    hits = sum(1 for r in results if r in relevant)
    return hits / len(results)


def recall_at_k(
    retrieved: Iterable[int],
    relevant: set[int],
    k: int,
) -> float:
    results = list(retrieved)[:k]
    if not relevant:
        return 0.0
    hits = sum(1 for r in results if r in relevant)
    return hits / len(relevant)


def dcg_at_k(relevance: list[float], k: int) -> float:
    score = 0.0
    for i, rel in enumerate(relevance[:k]):
        rank = i + 1
        score += (2.0 ** rel - 1.0) / math.log2(rank + 1)
    return score


def ndcg_at_k(relevance: list[float], k: int) -> float:
    actual = dcg_at_k(relevance, k)
    ideal  = dcg_at_k(sorted(relevance, reverse=True), k)
    if ideal == 0:
        return 0.0
    return actual / ideal


def mean_reciprocal_rank(
    retrieved_lists: list[list[int]],
    relevant_sets: list[set[int]],
) -> float:
    """MRR over a set of queries."""
    if not retrieved_lists:
        return 0.0
    total = 0.0
    for retrieved, relevant in zip(retrieved_lists, relevant_sets):
        for rank, paper_id in enumerate(retrieved, start=1):
            if paper_id in relevant:
                total += 1.0 / rank
                break
    return total / len(retrieved_lists)


def average_precision(
    retrieved: list[int],
    relevant: set[int],
) -> float:
    """AP for a single query (used to compute MAP)."""
    if not relevant:
        return 0.0
    hits = 0
    total = 0.0
    for rank, pid in enumerate(retrieved, start=1):
        if pid in relevant:
            hits += 1
            total += hits / rank
    return total / len(relevant) if relevant else 0.0


def mean_average_precision(
    retrieved_lists: list[list[int]],
    relevant_sets: list[set[int]],
) -> float:
    if not retrieved_lists:
        return 0.0
    return sum(
        average_precision(r, rel)
        for r, rel in zip(retrieved_lists, relevant_sets)
    ) / len(retrieved_lists)
