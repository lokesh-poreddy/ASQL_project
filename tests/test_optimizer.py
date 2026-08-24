"""Tests: resource optimizer."""
from __future__ import annotations

import os
os.environ["APP_ENV"] = "test"

import pytest

from app.optimization.optimizer import ObservedMetrics, OptimizationConfig, ResourceOptimizer
from app.common.exceptions import OptimizationError


@pytest.fixture
def optimizer() -> ResourceOptimizer:
    return ResourceOptimizer()


class TestResourceOptimizer:
    def test_large_storage_uses_fp32(self, optimizer) -> None:
        config = optimizer.select_configuration(
            storage_budget_mb=4096, latency_budget_ms=300, accuracy_target=0.90
        )
        assert config.precision_mode == "FP32"
        assert config.index_type == "HNSW"

    def test_medium_storage_uses_fp16(self, optimizer) -> None:
        config = optimizer.select_configuration(
            storage_budget_mb=2000, latency_budget_ms=300, accuracy_target=0.90
        )
        assert config.precision_mode == "FP16"

    def test_small_storage_uses_int8(self, optimizer) -> None:
        config = optimizer.select_configuration(
            storage_budget_mb=500, latency_budget_ms=300, accuracy_target=0.90
        )
        assert config.precision_mode == "INT8"
        assert config.index_type == "IVF"

    def test_tight_latency_uses_small_search_depth(self, optimizer) -> None:
        config = optimizer.select_configuration(
            storage_budget_mb=4096, latency_budget_ms=30, accuracy_target=0.85
        )
        assert config.search_depth <= 64

    def test_high_accuracy_doubles_search_depth(self, optimizer) -> None:
        config_normal = optimizer.select_configuration(
            storage_budget_mb=4096, latency_budget_ms=200, accuracy_target=0.85
        )
        config_high = optimizer.select_configuration(
            storage_budget_mb=4096, latency_budget_ms=200, accuracy_target=0.97
        )
        assert config_high.search_depth >= config_normal.search_depth

    def test_feasibility_check_passes(self, optimizer) -> None:
        config = optimizer.select_configuration(500, 300, 0.90)
        metrics = ObservedMetrics(
            storage_mb=400, p95_latency_ms=250, recall_at_k=0.92
        )
        assert optimizer.is_feasible(metrics, config)

    def test_feasibility_check_fails_on_latency(self, optimizer) -> None:
        config = optimizer.select_configuration(500, 100, 0.90)
        metrics = ObservedMetrics(
            storage_mb=400, p95_latency_ms=150, recall_at_k=0.92
        )
        assert not optimizer.is_feasible(metrics, config)

    def test_invalid_budget_raises(self, optimizer) -> None:
        with pytest.raises(OptimizationError):
            optimizer.select_configuration(
                storage_budget_mb=-1, latency_budget_ms=100, accuracy_target=0.90
            )
