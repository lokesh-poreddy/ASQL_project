"""Vector search: Oracle VECTOR_DISTANCE (production) + in-memory cosine (test).

The Oracle search uses the HNSW index created by database/07_vector.sql.
The in-memory fallback builds a brute-force cosine similarity index over
the seed embeddings so tests requiring retrieval results still get sensible
(but non-semantic) outputs.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import numpy as np

from app.common.exceptions import VectorSearchError
from app.common.logging import get_logger
from app.vector.provider import EmbeddingProvider, get_embedding_provider

logger = get_logger("vector.search")


@dataclass
class VectorSearchResult:
    paper_id: int
    title: str
    score: float
    source: str = "vector"


class OracleVectorSearch:
    """Executes VECTOR_DISTANCE queries on Oracle 23ai paper_embeddings table."""

    def __init__(self, connection_provider, embedding_provider: EmbeddingProvider) -> None:
        self._cp = connection_provider
        self._emb = embedding_provider

    def search(
        self,
        query: str,
        top_k: int = 10,
        precision_mode: str = "FP32",
    ) -> list[VectorSearchResult]:
        query_vec = self._emb.encode(query)
        started = time.perf_counter()

        col_map = {"FP32": "embedding_f32", "INT8": "embedding_i8", "FP64": "embedding_f64"}
        col = col_map.get(precision_mode, "embedding_f32")

        sql = f"""
            SELECT pe.paper_id, p.title,
                   VECTOR_DISTANCE(pe.{col}, :query_vec, COSINE) AS dist
            FROM   paper_embeddings pe
            JOIN   papers p ON p.paper_id = pe.paper_id
            WHERE  pe.{col} IS NOT NULL
              AND  pe.precision_mode = :precision_mode
            ORDER  BY dist ASC
            FETCH  FIRST :top_k ROWS ONLY
        """

        try:
            with self._cp.get_connection() as conn:
                cursor = conn.cursor()
                try:
                    cursor.execute(
                        sql,
                        {
                            "query_vec":     query_vec.tolist(),
                            "precision_mode": precision_mode,
                            "top_k":          top_k,
                        },
                    )
                    rows = cursor.fetchall()
                finally:
                    cursor.close()
        except Exception as exc:
            raise VectorSearchError(
                f"Oracle vector search failed: {exc}"
            ) from exc

        elapsed = (time.perf_counter() - started) * 1000
        logger.debug("Oracle vector search: %d results in %.1f ms", len(rows), elapsed)

        return [
            VectorSearchResult(
                paper_id=row[0],
                title=row[1],
                score=float(1.0 - row[2]),  # convert distance to similarity
                source=f"vector_{precision_mode.lower()}",
            )
            for row in rows
        ]


class InMemoryVectorSearch:
    """Brute-force cosine search over the seed dataset.

    Used when APP_ENV=test or no Oracle connection available. Stores
    hashing-based vectors for each seed paper; results are not semantically
    meaningful but allow the full retrieval pipeline to be exercised.
    """

    # Matches the seed paper_ids in the executor
    SEED_PAPERS: list[tuple[int, str]] = [
        (1,  "Attention Is All You Need"),
        (2,  "BERT: Pre-training of Deep Bidirectional Transformers"),
        (3,  "Deep Residual Learning for Image Recognition"),
        (4,  "Transformer-Based ECG Analysis"),
        (5,  "Scalable Distributed SQL Query Processing"),
        (6,  "Neural Information Retrieval: A Survey"),
        (7,  "Hybrid Vector-SQL Retrieval for Scientific Literature"),
        (8,  "Learned Query Optimisation in Relational Databases"),
        (9,  "Quantised Vector Embeddings for Low-Memory Retrieval"),
        (10, "ECG Signal Segmentation Using Self-Supervised Transformers"),
        (12, "Retrieval-Augmented Generation"),
        (14, "Vision Transformer: An Image Is Worth 16x16 Words"),
        (16, "Dense Passage Retrieval"),
        (17, "Conversational SQL: NL to SQL"),
        (18, "Approximate Nearest Neighbour Search with HNSW"),
        (21, "Efficient Transformers: A Survey"),
        (26, "Adaptive Compression for Learned Vector Indexes"),
        (27, "Query-Aware Data Partitioning in Distributed Databases"),
        (28, "Cardiac Risk Stratification with Multi-Modal Learning"),
        (29, "Causal Inference in Machine Learning"),
        (30, "NEXUS-SQL: Adaptive Hybrid Retrieval"),
    ]

    def __init__(self, embedding_provider: EmbeddingProvider) -> None:
        self._emb = embedding_provider
        self._index: list[tuple[int, str, np.ndarray]] | None = None

    def _build_index(self) -> None:
        logger.info("Building in-memory vector index for %d papers.", len(self.SEED_PAPERS))
        self._index = []
        for pid, title in self.SEED_PAPERS:
            vec = self._emb.encode(title)
            self._index.append((pid, title, vec))

    def search(
        self,
        query: str,
        top_k: int = 10,
        precision_mode: str = "FP32",
    ) -> list[VectorSearchResult]:
        if self._index is None:
            self._build_index()

        query_vec = self._emb.encode(query)

        scores: list[tuple[int, str, float]] = []
        for pid, title, vec in self._index:
            score = float(np.dot(query_vec, vec))
            scores.append((pid, title, score))

        scores.sort(key=lambda x: x[2], reverse=True)

        return [
            VectorSearchResult(paper_id=pid, title=title, score=score, source="vector_inmem")
            for pid, title, score in scores[:top_k]
        ]


def get_vector_search():
    from app.config import get_settings
    settings = get_settings()
    provider = get_embedding_provider()
    if settings.use_oracle:
        from app.database.connection import get_pool
        return OracleVectorSearch(get_pool(), provider)
    return InMemoryVectorSearch(provider)
