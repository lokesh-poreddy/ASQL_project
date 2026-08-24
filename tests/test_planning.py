"""Tests: query router, intent extractor, and query planner."""
from __future__ import annotations

import os
os.environ["APP_ENV"] = "test"

import pytest

from app.conversation.models import RetrievalMode
from app.planning.intent_extractor import extract_intent
from app.planning.planner import QueryPlanner
from app.planning.router import QueryRouter
from app.schema.introspector import StaticSchemaIntrospector


@pytest.fixture
def router() -> QueryRouter:
    return QueryRouter()


@pytest.fixture
def planner() -> QueryPlanner:
    return QueryPlanner()


@pytest.fixture
def snapshot():
    return StaticSchemaIntrospector().load_snapshot()


class TestQueryRouter:
    def test_year_query_routes_to_sql(self, router) -> None:
        mode, confidence = router.route("Find papers published after 2020")
        assert mode == RetrievalMode.SQL
        assert confidence >= 0.80

    def test_similarity_query_routes_to_vector(self, router) -> None:
        mode, confidence = router.route("Find papers similar to BERT")
        assert mode == RetrievalMode.VECTOR
        assert confidence >= 0.75

    def test_hybrid_query(self, router) -> None:
        mode, _ = router.route(
            "Find papers from 2022 related to transformer models"
        )
        assert mode == RetrievalMode.HYBRID

    def test_confidence_in_range(self, router) -> None:
        _, confidence = router.route("top 10 papers")
        assert 0.0 <= confidence <= 1.0

    def test_bare_year_routes_sql(self, router) -> None:
        mode, _ = router.route("Papers from 2024")
        assert mode == RetrievalMode.SQL


class TestIntentExtractor:
    def test_year_gte_filter(self, snapshot) -> None:
        intent = extract_intent("Find papers published after 2020", snapshot=snapshot)
        years = [f for f in intent.filters if f.column == "year"]
        assert any(f.operator.value == ">=" for f in years)

    def test_year_lte_filter(self, snapshot) -> None:
        intent = extract_intent("Find papers before 2023", snapshot=snapshot)
        years = [f for f in intent.filters if f.column == "year"]
        assert any(f.operator.value == "<=" for f in years)

    def test_citation_gt_filter(self, snapshot) -> None:
        intent = extract_intent("Papers with more than 500 citations", snapshot=snapshot)
        cites = [f for f in intent.filters if f.column == "citation_count"]
        assert len(cites) == 1
        assert cites[0].value == 500

    def test_area_filter_matched(self, snapshot) -> None:
        intent = extract_intent(
            "Find papers about Natural Language Processing", snapshot=snapshot
        )
        area_filters = [f for f in intent.filters if f.table == "research_areas"]
        assert len(area_filters) == 1

    def test_venue_filter_matched(self, snapshot) -> None:
        intent = extract_intent("Find papers from NeurIPS", snapshot=snapshot)
        venue_filters = [f for f in intent.filters if f.table == "venues"]
        assert len(venue_filters) == 1

    def test_top_n_limit(self, snapshot) -> None:
        intent = extract_intent("Top 5 papers by citation", snapshot=snapshot)
        assert intent.limit == 5

    def test_year_between(self, snapshot) -> None:
        intent = extract_intent("Papers between 2020 and 2023", snapshot=snapshot)
        years = [f for f in intent.filters if f.column == "year"]
        assert len(years) == 2

    def test_default_order_by_citations(self, snapshot) -> None:
        intent = extract_intent("Find papers about database systems", snapshot=snapshot)
        assert any(col == "citation_count" for col, _ in intent.order_by)


class TestQueryPlanner:
    def test_plan_returns_retrieval_mode(self, planner) -> None:
        plan = planner.plan("Find papers from 2022")
        assert plan.retrieval_mode in (RetrievalMode.SQL, RetrievalMode.HYBRID, RetrievalMode.VECTOR)

    def test_semantic_intent_populated_for_vector(self, planner) -> None:
        plan = planner.plan("Find papers similar to BERT")
        if plan.retrieval_mode in (RetrievalMode.VECTOR, RetrievalMode.HYBRID):
            assert plan.semantic_intent is not None

    def test_confidence_in_range(self, planner) -> None:
        plan = planner.plan("Papers about NLP after 2022")
        assert 0.0 <= plan.confidence <= 1.0
