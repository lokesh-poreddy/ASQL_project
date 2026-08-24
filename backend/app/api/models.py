"""Pydantic request/response models for all API endpoints."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ── Request models ────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    conversation_id: str = Field(min_length=1, description="Unique conversation session ID")
    query: str = Field(min_length=2, description="Natural language query")
    top_k: int = Field(default=10, ge=1, le=100)
    alpha: float | None = Field(default=None, ge=0.0, le=1.0,
                                description="Hybrid fusion weight override (0=SQL, 1=vector)")


class ClarifyRequest(BaseModel):
    conversation_id: str = Field(min_length=1)
    original_query: str = Field(min_length=2)
    clarification: str = Field(min_length=1, description="User's answer to clarification question")


class OptimizeRequest(BaseModel):
    storage_budget_mb: float = Field(default=500.0, gt=0)
    latency_budget_ms: float = Field(default=300.0, gt=0)
    accuracy_target:   float = Field(default=0.90, gt=0, le=1.0)


# ── Response models ───────────────────────────────────────────────────────────

class PaperResult(BaseModel):
    paper_id: int
    title: str
    year: int | None = None
    citation_count: int | None = None
    score: float | None = None
    source: str = "unknown"


class QueryResponse(BaseModel):
    status: str
    conversation_id: str
    retrieval_mode: str | None = None
    results: list[PaperResult] = []
    result_count: int = 0
    sql: str | None = None
    latency_ms: float | None = None
    explanation: dict[str, Any] | None = None
    message: str | None = None
    ambiguity_type: str | None = None
    options: list[str] | None = None


class HealthResponse(BaseModel):
    status: str
    database: str
    embedding_provider: str
    oracle_version: int | None = None


class SchemaResponse(BaseModel):
    tables: list[str]
    research_areas: list[str]
    venues: list[str]


class MetricsResponse(BaseModel):
    experiment_count: int
    experiments: list[dict[str, Any]]


class OptimizeResponse(BaseModel):
    precision_mode: str
    index_type: str
    search_depth: int
    candidate_count: int
    storage_budget_mb: float
    latency_budget_ms: float
    accuracy_target: float
