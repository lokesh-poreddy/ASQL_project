"""Tests: in-memory vector provider and search."""
from __future__ import annotations

import os
os.environ["APP_ENV"] = "test"

import numpy as np
import pytest

from app.vector.provider import HashingEmbeddingProvider
from app.vector.oracle_search import InMemoryVectorSearch


@pytest.fixture
def provider() -> HashingEmbeddingProvider:
    return HashingEmbeddingProvider(dim=384)


@pytest.fixture
def searcher(provider) -> InMemoryVectorSearch:
    return InMemoryVectorSearch(provider)


class TestHashingProvider:
    def test_dimension(self, provider) -> None:
        vec = provider.encode("hello world")
        assert vec.shape == (384,)

    def test_l2_normalized(self, provider) -> None:
        vec = provider.encode("test text")
        norm = float(np.linalg.norm(vec))
        assert abs(norm - 1.0) < 1e-5

    def test_deterministic(self, provider) -> None:
        v1 = provider.encode("deterministic test")
        v2 = provider.encode("deterministic test")
        np.testing.assert_array_equal(v1, v2)

    def test_different_texts_different_vectors(self, provider) -> None:
        v1 = provider.encode("paper about transformers")
        v2 = provider.encode("paper about databases")
        assert not np.allclose(v1, v2)

    def test_batch_encode_shape(self, provider) -> None:
        texts = ["text one", "text two", "text three"]
        batch = provider.encode_batch(texts)
        assert batch.shape == (3, 384)


class TestInMemoryVectorSearch:
    def test_returns_top_k_results(self, searcher) -> None:
        results = searcher.search("transformers", top_k=5)
        assert len(results) == 5

    def test_results_have_paper_ids(self, searcher) -> None:
        results = searcher.search("database systems", top_k=3)
        for r in results:
            assert r.paper_id > 0

    def test_scores_in_range(self, searcher) -> None:
        results = searcher.search("neural networks", top_k=10)
        for r in results:
            assert -1.0 <= r.score <= 1.0

    def test_source_is_vector_inmem(self, searcher) -> None:
        results = searcher.search("query", top_k=1)
        assert results[0].source == "vector_inmem"

    def test_top_k_limit_respected(self, searcher) -> None:
        results = searcher.search("NLP", top_k=2)
        assert len(results) <= 2

    def test_index_cached(self, searcher) -> None:
        searcher.search("warmup", top_k=1)
        idx1 = searcher._index
        searcher.search("second", top_k=1)
        assert searcher._index is idx1
