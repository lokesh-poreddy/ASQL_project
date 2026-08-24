"""Metrics aggregator: runs a batch of benchmark queries and writes results
to EXPERIMENT_RESULTS (Oracle) or collects them in-memory (test).
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from typing import Any

from app.common.logging import get_logger
from app.metrics.latency import LatencyStats, compute_percentiles
from app.metrics.precision_recall import (
    mean_average_precision,
    mean_reciprocal_rank,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)

logger = get_logger("metrics.aggregator")


@dataclass
class BenchmarkQuery:
    query_id: str
    question: str
    expected_mode: str
    relevant_paper_ids: list[int]


@dataclass
class BenchmarkResult:
    query_id: str
    retrieved_ids: list[int]
    latency_ms: float


@dataclass
class AggregateMetrics:
    experiment_name: str
    run_id: str
    configuration: dict[str, Any]
    k: int
    precision_at_k: float
    recall_at_k: float
    ndcg_at_k: float
    mrr: float
    map_score: float
    latency: LatencyStats
    query_count: int


class MetricsAggregator:

    def compute(
        self,
        experiment_name: str,
        configuration: dict[str, Any],
        queries: list[BenchmarkQuery],
        results: list[BenchmarkResult],
        k: int = 10,
    ) -> AggregateMetrics:
        run_id = str(uuid.uuid4())[:8]

        # Align results to queries by query_id
        result_map = {r.query_id: r for r in results}
        latencies: list[float] = []

        retrieved_lists: list[list[int]] = []
        relevant_sets: list[set[int]] = []
        relevance_scores: list[list[float]] = []

        for q in queries:
            bres = result_map.get(q.query_id)
            if bres is None:
                retrieved_lists.append([])
                relevant_sets.append(set(q.relevant_paper_ids))
                relevance_scores.append([])
                continue

            latencies.append(bres.latency_ms)
            retrieved_lists.append(bres.retrieved_ids)
            relevant_sets.append(set(q.relevant_paper_ids))

            # Binary relevance scores for NDCG
            rel_scores = [
                1.0 if pid in set(q.relevant_paper_ids) else 0.0
                for pid in bres.retrieved_ids[:k]
            ]
            relevance_scores.append(rel_scores)

        # Per-query aggregation → mean
        p_at_k = sum(
            precision_at_k(ret, rel, k)
            for ret, rel in zip(retrieved_lists, relevant_sets)
        ) / max(len(queries), 1)

        r_at_k = sum(
            recall_at_k(ret, rel, k)
            for ret, rel in zip(retrieved_lists, relevant_sets)
        ) / max(len(queries), 1)

        avg_ndcg = sum(
            ndcg_at_k(scores, k)
            for scores in relevance_scores
        ) / max(len(queries), 1)

        mrr  = mean_reciprocal_rank(retrieved_lists, relevant_sets)
        mmap = mean_average_precision(retrieved_lists, relevant_sets)

        latency_stats = compute_percentiles(latencies)

        metrics = AggregateMetrics(
            experiment_name=experiment_name,
            run_id=run_id,
            configuration=configuration,
            k=k,
            precision_at_k=p_at_k,
            recall_at_k=r_at_k,
            ndcg_at_k=avg_ndcg,
            mrr=mrr,
            map_score=mmap,
            latency=latency_stats,
            query_count=len(queries),
        )

        logger.info(
            "Metrics [%s run=%s]: P@%d=%.3f R@%d=%.3f NDCG@%d=%.3f MRR=%.3f P95=%.1f ms",
            experiment_name, run_id,
            k, p_at_k, k, r_at_k, k, avg_ndcg, mrr, latency_stats.p95_ms,
        )
        return metrics

    def to_records(
        self, metrics: AggregateMetrics, dataset_version: str = "v1"
    ) -> list[dict[str, Any]]:
        """Convert to a list of rows for insertion into EXPERIMENT_RESULTS."""
        config_json = json.dumps(metrics.configuration)
        base = dict(
            experiment_name=metrics.experiment_name,
            run_id=metrics.run_id,
            configuration=config_json,
            dataset_version=dataset_version,
            is_synthetic_smoke_test=0,
        )
        return [
            {**base, "metric_name": f"precision_at_{metrics.k}", "metric_value": metrics.precision_at_k},
            {**base, "metric_name": f"recall_at_{metrics.k}",    "metric_value": metrics.recall_at_k},
            {**base, "metric_name": f"ndcg_at_{metrics.k}",      "metric_value": metrics.ndcg_at_k},
            {**base, "metric_name": "mrr",                        "metric_value": metrics.mrr},
            {**base, "metric_name": "map",                        "metric_value": metrics.map_score},
            {**base, "metric_name": "p50_latency_ms",             "metric_value": metrics.latency.p50_ms},
            {**base, "metric_name": "p95_latency_ms",             "metric_value": metrics.latency.p95_ms},
            {**base, "metric_name": "p99_latency_ms",             "metric_value": metrics.latency.p99_ms},
            {**base, "metric_name": "mean_latency_ms",            "metric_value": metrics.latency.mean_ms},
        ]
