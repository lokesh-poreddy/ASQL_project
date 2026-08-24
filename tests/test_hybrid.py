"""Tests: hybrid fusion, score normalization, and retriever."""
from __future__ import annotations

import os
os.environ["APP_ENV"] = "test"

import pytest

from app.conversation.models import RetrievalMode
from app.hybrid.fusion import FusionCandidate, ScoreFusion
from app.hybrid.retriever import HybridRetriever
from app.hybrid.score_normalizer import minmax_normalize, rank_normalize
from app.planning.models import QueryPlan, StructuredIntent
from app.sql.executor import InMemorySQLExecutor
from app.sql.generator import get_sql_generator
from app.vector.oracle_search import InMemoryVectorSearch
from app.vector.provider import HashingEmbeddingProvider


@pytest.fixture
def fusion() -> ScoreFusion:
    return ScoreFusion()


@pytest.fixture
def retriever() -> HybridRetriever:
    provider = HashingEmbeddingProvider(dim=384)
    return HybridRetriever(
        sql_executor=InMemorySQLExecutor(),
        sql_generator=get_sql_generator(),
        vector_search=InMemoryVectorSearch(provider),
        alpha=0.5,
    )


def _candidates(n: int = 5) -> list[FusionCandidate]:
    return [
        FusionCandidate(
            paper_id=i,
            title=f"Paper {i}",
            sql_score=1.0 / i,
            semantic_score=1.0 / (i + 1),
        )
        for i in range(1, n + 1)
    ]


class TestScoreNormalizer:
    def test_minmax_all_same_returns_ones(self) -> None:
        result = minmax_normalize([3.0, 3.0, 3.0])
        assert all(v == 1.0 for v in result)

    def test_minmax_range(self) -> None:
        result = minmax_normalize([0.0, 5.0, 10.0])
        assert result[0] == pytest.approx(0.0)
        assert result[-1] == pytest.approx(1.0)

    def test_rank_normalize_output_in_unit_range(self) -> None:
        result = rank_normalize([0.9, 0.5, 0.1])
        assert all(0.0 <= v <= 1.0 for v in result)

    def test_empty_normalizer(self) -> None:
        assert minmax_normalize([]) == []
        assert rank_normalize([]) == []


class TestScoreFusion:
    def test_fuse_returns_top_k(self, fusion) -> None:
        candidates = _candidates(10)
        result = fusion.fuse(candidates, alpha=0.5, top_k=5)
        assert len(result) == 5

    def test_alpha_one_uses_only_semantic(self, fusion) -> None:
        c1 = FusionCandidate(1, "A", sql_score=0.1, semantic_score=0.9)
        c2 = FusionCandidate(2, "B", sql_score=0.9, semantic_score=0.1)
        result = fusion.fuse([c1, c2], alpha=1.0, top_k=2)
        assert result[0].paper_id == 1  # highest semantic score wins

    def test_alpha_zero_uses_only_sql(self, fusion) -> None:
        c1 = FusionCandidate(1, "A", sql_score=0.1, semantic_score=0.9)
        c2 = FusionCandidate(2, "B", sql_score=0.9, semantic_score=0.1)
        result = fusion.fuse([c1, c2], alpha=0.0, top_k=2)
        assert result[0].paper_id == 2  # highest sql score wins

    def test_alpha_out_of_range_raises(self, fusion) -> None:
        with pytest.raises(ValueError):
            fusion.fuse(_candidates(2), alpha=1.5, top_k=2)

    def test_sorted_descending(self, fusion) -> None:
        candidates = _candidates(5)
        result = fusion.fuse(candidates, alpha=0.5, top_k=5)
        scores = [r.final_score for r in result]
        assert scores == sorted(scores, reverse=True)


class TestHybridRetriever:
    def test_hybrid_retrieval_returns_results(self, retriever) -> None:
        plan = QueryPlan(
            retrieval_mode=RetrievalMode.HYBRID,
            structured_intent=StructuredIntent(),
            semantic_intent="papers about neural networks",
            confidence=0.9,
        )
        result = retriever.retrieve(plan, top_k=5)
        assert len(result.results) <= 5

    def test_sql_only_mode(self, retriever) -> None:
        plan = QueryPlan(
            retrieval_mode=RetrievalMode.SQL,
            structured_intent=StructuredIntent(),
            semantic_intent=None,
            confidence=0.9,
        )
        result = retriever.retrieve(plan, top_k=5)
        assert result.vector_candidate_count == 0

    def test_vector_only_mode(self, retriever) -> None:
        plan = QueryPlan(
            retrieval_mode=RetrievalMode.VECTOR,
            structured_intent=StructuredIntent(),
            semantic_intent="neural networks",
            confidence=0.9,
        )
        result = retriever.retrieve(plan, top_k=5)
        assert result.sql_candidate_count == 0

    def test_alpha_is_recorded(self, retriever) -> None:
        plan = QueryPlan(
            retrieval_mode=RetrievalMode.HYBRID,
            structured_intent=StructuredIntent(),
            semantic_intent="deep learning",
            confidence=0.9,
        )
        result = retriever.retrieve(plan, top_k=5, alpha=0.7)
        assert result.alpha_used == pytest.approx(0.7)
