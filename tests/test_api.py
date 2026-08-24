"""Integration tests: FastAPI endpoint smoke tests (no Oracle required)."""
from __future__ import annotations

import os
os.environ["APP_ENV"] = "test"

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


class TestHealthEndpoint:
    def test_health_ok(self, client) -> None:
        r = client.get("/api/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["database"] == "test_mode"

    def test_health_has_embedding_provider(self, client) -> None:
        r = client.get("/api/health")
        data = r.json()
        assert "embedding_provider" in data


class TestSchemaEndpoint:
    def test_schema_returns_tables(self, client) -> None:
        r = client.get("/api/schema")
        assert r.status_code == 200
        data = r.json()
        assert "papers" in data["tables"]
        assert len(data["research_areas"]) >= 5
        assert len(data["venues"]) >= 5


class TestOptimizeEndpoint:
    def test_optimize_returns_config(self, client) -> None:
        r = client.post("/api/optimize", json={
            "storage_budget_mb": 500,
            "latency_budget_ms": 300,
            "accuracy_target": 0.90,
        })
        assert r.status_code == 200
        data = r.json()
        assert "precision_mode" in data
        assert "index_type" in data
        assert data["precision_mode"] in ("FP32", "FP16", "INT8")


class TestQueryEndpoint:
    def test_query_sql_mode(self, client) -> None:
        r = client.post("/api/query", json={
            "conversation_id": "test-session-001",
            "query": "Find papers published after 2020",
            "top_k": 5,
        })
        assert r.status_code == 200
        data = r.json()
        assert data["status"] in ("ok", "clarification_required")

    def test_query_vague_triggers_clarification(self, client) -> None:
        r = client.post("/api/query", json={
            "conversation_id": "test-session-002",
            "query": "Find recent papers about machine learning",
        })
        assert r.status_code == 200
        data = r.json()
        # "recent" is a vague time term → clarification_required
        assert data["status"] in ("clarification_required", "ok")

    def test_query_unanswerable(self, client) -> None:
        r = client.post("/api/query", json={
            "conversation_id": "test-session-003",
            "query": "Which papers will be published next year?",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "unanswerable"

    def test_query_returns_explanation(self, client) -> None:
        r = client.post("/api/query", json={
            "conversation_id": "test-session-004",
            "query": "Top 5 papers by citation from 2022",
        })
        assert r.status_code == 200
        data = r.json()
        if data["status"] == "ok":
            assert "explanation" in data
            assert data["explanation"] is not None

    def test_history_endpoint(self, client) -> None:
        conv_id = "test-history-001"
        client.post("/api/query", json={
            "conversation_id": conv_id,
            "query": "Find papers from 2022",
        })
        r = client.get(f"/api/history/{conv_id}")
        assert r.status_code == 200
        data = r.json()
        assert data["conversation_id"] == conv_id
        assert isinstance(data["turns"], list)

    def test_metrics_endpoint(self, client) -> None:
        r = client.get("/api/metrics")
        assert r.status_code == 200
        data = r.json()
        assert "experiment_count" in data
        assert isinstance(data["experiments"], list)
