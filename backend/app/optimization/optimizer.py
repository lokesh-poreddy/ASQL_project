"""Resource optimizer: selects compression mode, index type, and search depth
based on the storage/latency/accuracy budget triple.

V1 policy: rule-based. This is the baseline that will be compared against
experimental observations. The policy is documented here exactly so it can be
cited in the ASQL literature review section as "proposed system behaviour".

The optimizer output (OptimizationConfig) is logged to EXPERIMENT_RESULTS
so every run produces a database record — not just a screenshot.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.common.exceptions import OptimizationError
from app.common.logging import get_logger

logger = get_logger("optimization.optimizer")


@dataclass
class OptimizationConfig:
    storage_budget_mb: float
    latency_budget_ms: float
    accuracy_target: float
    precision_mode: str       # FP32 | FP16 | INT8
    index_type: str           # HNSW | IVF | NONE
    search_depth: int         # ef_search parameter for HNSW
    candidate_count: int      # initial candidate pool size


@dataclass
class ObservedMetrics:
    storage_mb: float
    p95_latency_ms: float
    recall_at_k: float


class ResourceOptimizer:
    """Conservative rule-based policy for V1.

    Policy rationale (to be validated experimentally):
      - Storage ≤ 1024 MB → INT8 quantization (≈ 4× compression, known recall drop)
      - Storage ≤ 2048 MB → FP16 emulation (≈ 2× compression, small recall drop)
      - Storage  > 2048 MB → FP32 (baseline, no quantization loss)
      - Latency ≤  50 ms  → ef_search=32,  candidates=50  (fast, lower recall)
      - Latency ≤ 100 ms  → ef_search=64,  candidates=100 (balanced)
      - Latency  > 100 ms → ef_search=128, candidates=200 (thorough)
      - Accuracy ≥ 0.95   → double search_depth and candidate_count
    """

    def select_configuration(
        self,
        storage_budget_mb: float,
        latency_budget_ms: float,
        accuracy_target: float,
    ) -> OptimizationConfig:

        if storage_budget_mb <= 0 or latency_budget_ms <= 0 or not (0 < accuracy_target <= 1):
            raise OptimizationError(
                f"Invalid budget: storage={storage_budget_mb}, "
                f"latency={latency_budget_ms}, accuracy={accuracy_target}"
            )

        # Precision / compression
        if storage_budget_mb <= 1024:
            precision_mode = "INT8"
            index_type = "IVF"
        elif storage_budget_mb <= 2048:
            precision_mode = "FP16"
            index_type = "HNSW"
        else:
            precision_mode = "FP32"
            index_type = "HNSW"

        # Search parameters
        if latency_budget_ms <= 50:
            search_depth = 32
            candidate_count = 50
        elif latency_budget_ms <= 100:
            search_depth = 64
            candidate_count = 100
        else:
            search_depth = 128
            candidate_count = 200

        # High-accuracy multiplier
        if accuracy_target >= 0.95:
            search_depth   = min(search_depth * 2, 512)
            candidate_count = min(candidate_count * 2, 1000)

        config = OptimizationConfig(
            storage_budget_mb=storage_budget_mb,
            latency_budget_ms=latency_budget_ms,
            accuracy_target=accuracy_target,
            precision_mode=precision_mode,
            index_type=index_type,
            search_depth=search_depth,
            candidate_count=candidate_count,
        )

        logger.info(
            "Optimizer selected: precision=%s index=%s depth=%d candidates=%d",
            precision_mode, index_type, search_depth, candidate_count,
        )
        return config

    def is_feasible(
        self,
        metrics: ObservedMetrics,
        config: OptimizationConfig,
    ) -> bool:
        """Return True if the observed metrics satisfy all budget constraints."""
        return (
            metrics.storage_mb    <= config.storage_budget_mb
            and metrics.p95_latency_ms <= config.latency_budget_ms
            and metrics.recall_at_k   >= config.accuracy_target
        )

    def select_top_k(self, config: OptimizationConfig) -> int:
        """Derive the maximum Top-K that the candidate_count can support."""
        from app.config import get_settings
        return min(get_settings().default_top_k, config.candidate_count)
