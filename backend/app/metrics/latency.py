"""Latency measurement and percentile computation.

Measures wall-clock execution time for the full retrieval pipeline and
computes P50, P95, P99 over a batch of query latencies.

These are the latency metrics that directly feed into the resource
optimizer's feasibility check and the experiment_results table.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, TypeVar

T = TypeVar("T")


@dataclass
class LatencyStats:
    p50_ms: float
    p95_ms: float
    p99_ms: float
    mean_ms: float
    min_ms: float
    max_ms: float
    sample_count: int


def measure_ms(fn: Callable[[], T]) -> tuple[T, float]:
    """Call fn(), return (result, elapsed_ms)."""
    start = time.perf_counter()
    result = fn()
    elapsed = (time.perf_counter() - start) * 1000.0
    return result, elapsed


def compute_percentiles(latencies_ms: list[float]) -> LatencyStats:
    """Compute P50/P95/P99 from a list of measured latencies (in ms)."""
    if not latencies_ms:
        return LatencyStats(0, 0, 0, 0, 0, 0, 0)

    sorted_lats = sorted(latencies_ms)
    n = len(sorted_lats)

    def percentile(p: float) -> float:
        idx = max(0, int(p / 100.0 * n) - 1)
        return sorted_lats[min(idx, n - 1)]

    return LatencyStats(
        p50_ms=percentile(50),
        p95_ms=percentile(95),
        p99_ms=percentile(99),
        mean_ms=sum(sorted_lats) / n,
        min_ms=sorted_lats[0],
        max_ms=sorted_lats[-1],
        sample_count=n,
    )
