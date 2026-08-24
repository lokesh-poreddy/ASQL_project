"""Experiment runner: CLI entry point for running baselines and ablations.

Usage:
    python -m backend.experiments.runner --experiment sql_only --top-k 10
    python -m backend.experiments.runner --experiment vector_only --top-k 10
    python -m backend.experiments.runner --experiment hybrid --top-k 10 --alpha 0.5
    python -m backend.experiments.runner --experiment all --top-k 10
    python -m backend.experiments.runner --experiment ablation --top-k 10

Results are written to evaluation/results/<experiment_name>.json and logged
to EXPERIMENT_RESULTS in Oracle (if available).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Ensure backend is on the path when run as a module
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.common.logging import configure_logging, get_logger

configure_logging()
logger = get_logger("experiments.runner")


def load_benchmark_queries() -> list:
    """Load benchmark queries from data/benchmark_queries.json."""
    from app.metrics.aggregator import BenchmarkQuery
    data_path = Path(__file__).parent.parent.parent / "data" / "benchmark_queries.json"
    if not data_path.exists():
        logger.warning("benchmark_queries.json not found at %s. Using minimal defaults.", data_path)
        return _minimal_benchmark()

    with open(data_path) as f:
        raw = json.load(f)

    return [
        BenchmarkQuery(
            query_id=q["id"],
            question=q["question"],
            expected_mode=q.get("expected_mode", "HYBRID"),
            relevant_paper_ids=q.get("relevant_ids", []),
        )
        for q in raw
    ]


def _minimal_benchmark():
    from app.metrics.aggregator import BenchmarkQuery
    return [
        BenchmarkQuery("Q001", "Find papers after 2024 with more than 100 citations", "SQL", [8, 27]),
        BenchmarkQuery("Q002", "Find papers similar to transformer ECG analysis", "VECTOR", [4, 10]),
        BenchmarkQuery("Q003", "Find papers after 2024 similar to transformer ECG analysis", "HYBRID", [4, 7, 10]),
    ]


def run_experiment(
    name: str,
    queries: list,
    top_k: int = 10,
    alpha: float = 0.5,
    output_dir: Path | None = None,
) -> dict:
    from app.metrics.aggregator import MetricsAggregator

    aggregator = MetricsAggregator()
    results = []
    config: dict = {"top_k": top_k, "experiment": name}

    if name == "sql_only":
        from backend.experiments.baselines.sql_only import SQLOnlyBaseline
        results = SQLOnlyBaseline().run(queries, top_k=top_k)
        config["baseline"] = "sql_only"

    elif name == "vector_only":
        from backend.experiments.baselines.vector_only import VectorOnlyBaseline
        results = VectorOnlyBaseline().run(queries, top_k=top_k)
        config["baseline"] = "vector_only"

    elif name == "hybrid":
        from backend.experiments.baselines.hybrid import HybridBaseline
        results = HybridBaseline(alpha=alpha).run(queries, top_k=top_k)
        config.update({"baseline": "hybrid", "alpha": alpha})

    else:
        raise ValueError(f"Unknown experiment: {name}")

    metrics = aggregator.compute(
        experiment_name=name,
        configuration=config,
        queries=queries,
        results=results,
        k=top_k,
    )

    summary = {
        "experiment": name,
        "run_id": metrics.run_id,
        "queries": metrics.query_count,
        f"precision_at_{top_k}": round(metrics.precision_at_k, 4),
        f"recall_at_{top_k}":    round(metrics.recall_at_k, 4),
        f"ndcg_at_{top_k}":      round(metrics.ndcg_at_k, 4),
        "mrr":                   round(metrics.mrr, 4),
        "map":                   round(metrics.map_score, 4),
        "p50_ms":                round(metrics.latency.p50_ms, 2),
        "p95_ms":                round(metrics.latency.p95_ms, 2),
        "p99_ms":                round(metrics.latency.p99_ms, 2),
    }

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        out_file = output_dir / f"{name}.json"
        with open(out_file, "w") as f:
            json.dump(summary, f, indent=2)
        logger.info("Results written to %s", out_file)

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="NEXUS-SQL Experiment Runner")
    parser.add_argument("--experiment", default="hybrid",
                        choices=["sql_only", "vector_only", "hybrid", "all", "ablation"])
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--alpha", type=float, default=0.5)
    parser.add_argument("--output-dir", default="evaluation/results")
    args = parser.parse_args()

    queries = load_benchmark_queries()
    output_dir = Path(args.output_dir)

    experiments = (
        ["sql_only", "vector_only", "hybrid"]
        if args.experiment == "all"
        else [args.experiment]
    )

    for exp in experiments:
        logger.info("Running experiment: %s", exp)
        try:
            summary = run_experiment(
                name=exp,
                queries=queries,
                top_k=args.top_k,
                alpha=args.alpha,
                output_dir=output_dir,
            )
            print(f"\n{'='*60}")
            print(f"Experiment: {exp}")
            for k, v in summary.items():
                print(f"  {k}: {v}")
        except Exception as exc:
            logger.error("Experiment %s failed: %s", exp, exc)


if __name__ == "__main__":
    main()
