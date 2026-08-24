"""Embedding providers behind a common interface.

HashingEmbeddingProvider: deterministic, dimension-preserving, no model
  download. Used for APP_ENV=test and CI. Produces L2-normalised float32
  vectors using a seeded hash function — NOT semantically meaningful, but
  fully reproducible and fast.

SentenceTransformersProvider: production-quality semantic embeddings using
  sentence-transformers. Loaded lazily so that importing this module in a
  test environment never triggers a download.
"""
from __future__ import annotations

import hashlib
import struct
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Sequence

import numpy as np

from app.common.exceptions import EmbeddingProviderError
from app.common.logging import get_logger
from app.config import EmbeddingProviderKind, get_settings

logger = get_logger("vector.provider")


class EmbeddingProvider(ABC):
    """Common interface for all embedding providers."""

    @property
    @abstractmethod
    def dimension(self) -> int: ...

    @abstractmethod
    def encode(self, text: str) -> np.ndarray: ...

    def encode_batch(self, texts: Sequence[str]) -> np.ndarray:
        """Default: encode one by one. Override for batched providers."""
        return np.stack([self.encode(t) for t in texts])


# ── Hashing provider ──────────────────────────────────────────────────────────

class HashingEmbeddingProvider(EmbeddingProvider):
    """Deterministic, reproducible, no-model-download provider.

    For each text it:
      1. Computes SHA-256 of UTF-8 text.
      2. Expands the hash to `dimension` float32 values by seeded PRNG.
      3. L2-normalises the result.

    Useful ONLY for testing routing, retrieval pipeline wiring, and
    metric calculations. Results are NOT semantically meaningful.
    """

    def __init__(self, dim: int = 384) -> None:
        self._dim = dim

    @property
    def dimension(self) -> int:
        return self._dim

    def encode(self, text: str) -> np.ndarray:
        digest = hashlib.sha256(text.encode()).digest()
        seed = struct.unpack("<I", digest[:4])[0]
        rng = np.random.default_rng(seed)
        vec = rng.standard_normal(self._dim).astype(np.float32)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec


# ── Sentence-Transformers provider ───────────────────────────────────────────

class SentenceTransformersProvider(EmbeddingProvider):
    """Production embedding provider using sentence-transformers."""

    def __init__(self, model_name: str, dim: int) -> None:
        self._model_name = model_name
        self._dim = dim
        self._model = None  # lazy-loaded

    def _ensure_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer  # noqa
                logger.info("Loading embedding model: %s", self._model_name)
                self._model = SentenceTransformer(self._model_name)
                logger.info("Embedding model loaded.")
            except ImportError as exc:
                raise EmbeddingProviderError(
                    "sentence-transformers is not installed. "
                    "Run: pip install sentence-transformers"
                ) from exc
            except Exception as exc:
                raise EmbeddingProviderError(
                    f"Failed to load embedding model '{self._model_name}': {exc}"
                ) from exc

    @property
    def dimension(self) -> int:
        return self._dim

    def encode(self, text: str) -> np.ndarray:
        self._ensure_model()
        try:
            vec = self._model.encode(
                text,
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
            return vec.astype(np.float32)
        except Exception as exc:
            raise EmbeddingProviderError(f"Encoding failed: {exc}") from exc

    def encode_batch(self, texts: Sequence[str]) -> np.ndarray:
        self._ensure_model()
        try:
            vecs = self._model.encode(
                list(texts),
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
                batch_size=32,
            )
            return vecs.astype(np.float32)
        except Exception as exc:
            raise EmbeddingProviderError(f"Batch encoding failed: {exc}") from exc


@lru_cache(maxsize=1)
def get_embedding_provider() -> EmbeddingProvider:
    settings = get_settings()
    if settings.embedding_provider == EmbeddingProviderKind.SENTENCE_TRANSFORMERS:
        return SentenceTransformersProvider(
            model_name=settings.embedding_model_name,
            dim=settings.embedding_dimension,
        )
    return HashingEmbeddingProvider(dim=settings.embedding_dimension)
