"""Tests: IR metrics (precision, recall, DCG, NDCG, MRR, MAP)."""
from __future__ import annotations

import math

import pytest

from app.metrics.precision_recall import (
    average_precision,
    dcg_at_k,
    mean_average_precision,
    mean_reciprocal_rank,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)
from app.metrics.latency import compute_percentiles


class TestPrecisionRecall:
    def test_perfect_precision(self) -> None:
        assert precision_at_k([1, 2, 3], {1, 2, 3}, k=3) == pytest.approx(1.0)

    def test_zero_precision(self) -> None:
        assert precision_at_k([4, 5, 6], {1, 2, 3}, k=3) == pytest.approx(0.0)

    def test_partial_precision(self) -> None:
        assert precision_at_k([1, 4, 2], {1, 2, 3}, k=3) == pytest.approx(2 / 3)

    def test_recall_perfect(self) -> None:
        assert recall_at_k([1, 2, 3], {1, 2, 3}, k=3) == pytest.approx(1.0)

    def test_recall_partial(self) -> None:
        assert recall_at_k([1, 4, 5], {1, 2, 3}, k=3) == pytest.approx(1 / 3)

    def test_recall_empty_relevant(self) -> None:
        assert recall_at_k([1, 2], set(), k=2) == pytest.approx(0.0)

    def test_dcg_perfect_order(self) -> None:
        rel = [1.0, 1.0, 0.0]
        dcg = dcg_at_k(rel, k=3)
        assert dcg > 0

    def test_ndcg_perfect(self) -> None:
        rel = [1.0, 1.0, 0.0]
        assert ndcg_at_k(rel, k=3) == pytest.approx(1.0)

    def test_ndcg_zero(self) -> None:
        rel = [0.0, 0.0, 0.0]
        assert ndcg_at_k(rel, k=3) == pytest.approx(0.0)

    def test_mrr(self) -> None:
        retrieved = [[1, 2, 3], [4, 1, 2]]
        relevant  = [{1}, {1}]
        mrr = mean_reciprocal_rank(retrieved, relevant)
        # First query: rank 1 → RR=1.0; Second: rank 2 → RR=0.5; MRR=(1+0.5)/2
        assert mrr == pytest.approx(0.75)

    def test_ap_perfect(self) -> None:
        assert average_precision([1, 2, 3], {1, 2, 3}) == pytest.approx(1.0)

    def test_map(self) -> None:
        retrieved = [[1, 2], [3, 4]]
        relevant  = [{1, 2}, {3}]
        assert mean_average_precision(retrieved, relevant) > 0.0


class TestLatencyStats:
    def test_empty_returns_zeros(self) -> None:
        stats = compute_percentiles([])
        assert stats.p50_ms == 0
        assert stats.p95_ms == 0

    def test_single_value(self) -> None:
        stats = compute_percentiles([42.0])
        assert stats.p50_ms == pytest.approx(42.0)
        assert stats.mean_ms == pytest.approx(42.0)

    def test_percentile_order(self) -> None:
        latencies = list(range(1, 101))
        stats = compute_percentiles([float(x) for x in latencies])
        assert stats.p50_ms <= stats.p95_ms <= stats.p99_ms

    def test_sample_count(self) -> None:
        stats = compute_percentiles([1.0, 2.0, 3.0])
        assert stats.sample_count == 3
