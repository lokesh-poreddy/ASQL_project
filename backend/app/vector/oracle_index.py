"""Oracle vector index management.

Provides:
  - Version detection (requires Oracle 23ai for native VECTOR)
  - Index existence check
  - Index creation and recreation (controlled experiment operation only)
  - Storage size measurement for experiment_results

IMPORTANT: Do not rebuild indexes automatically at query time. Index changes
are controlled experiment operations that must be explicitly invoked.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.common.exceptions import RepositoryError
from app.common.logging import get_logger

logger = get_logger("vector.oracle_index")


@dataclass
class IndexInfo:
    index_name: str
    table_name: str
    column_name: str
    index_type: str       # HNSW | IVF
    precision_mode: str   # FP32 | INT8 | FP64
    size_mb: float | None = None


class OracleVectorIndexManager:

    # Maps precision_mode → (column_name, index_name, index_sql)
    INDEX_CONFIGS = {
        "FP32": (
            "embedding_f32",
            "IX_PAPER_EMBEDDINGS_F32_HNSW",
            """CREATE VECTOR INDEX IX_PAPER_EMBEDDINGS_F32_HNSW
               ON paper_embeddings(embedding_f32)
               ORGANIZATION INMEMORY NEIGHBOR GRAPH
               DISTANCE COSINE
               WITH TARGET ACCURACY 90
               PARAMETERS (type HNSW, neighbors 32, efconstruction 200)""",
        ),
        "INT8": (
            "embedding_i8",
            "IX_PAPER_EMBEDDINGS_I8_IVF",
            """CREATE VECTOR INDEX IX_PAPER_EMBEDDINGS_I8_IVF
               ON paper_embeddings(embedding_i8)
               ORGANIZATION NEIGHBOR PARTITIONS
               DISTANCE COSINE
               WITH TARGET ACCURACY 85
               PARAMETERS (type IVF, neighbor_partitions 64)""",
        ),
    }

    def __init__(self, connection_provider) -> None:
        self._cp = connection_provider
        self._oracle_version: int | None = None

    def check_oracle_version(self) -> int:
        """Return Oracle major version (23 for 23ai). Caches result."""
        if self._oracle_version is not None:
            return self._oracle_version
        try:
            with self._cp.get_connection() as conn:
                cursor = conn.cursor()
                try:
                    cursor.execute(
                        "SELECT TO_NUMBER(REGEXP_SUBSTR(version, '^\\d+')) FROM v$instance"
                    )
                    major = int(cursor.fetchone()[0])
                finally:
                    cursor.close()
            self._oracle_version = major
            logger.info("Oracle major version: %d", major)
            return major
        except Exception as exc:
            raise RepositoryError(f"Cannot determine Oracle version: {exc}") from exc

    def supports_vector(self) -> bool:
        """True only for Oracle 23ai (version >= 23)."""
        try:
            return self.check_oracle_version() >= 23
        except RepositoryError:
            return False

    def index_exists(self, index_name: str) -> bool:
        try:
            with self._cp.get_connection() as conn:
                cursor = conn.cursor()
                try:
                    cursor.execute(
                        "SELECT COUNT(*) FROM user_indexes WHERE index_name = :1",
                        [index_name.upper()],
                    )
                    return cursor.fetchone()[0] > 0
                finally:
                    cursor.close()
        except Exception as exc:
            raise RepositoryError(f"Index existence check failed: {exc}") from exc

    def measure_index_size_mb(self, index_name: str) -> float | None:
        """Return estimated index size in MB from dba_segments (may require DBA privilege)."""
        try:
            with self._cp.get_connection() as conn:
                cursor = conn.cursor()
                try:
                    cursor.execute(
                        """
                        SELECT NVL(SUM(bytes) / (1024*1024), 0)
                        FROM   user_segments
                        WHERE  segment_name = :1
                        """,
                        [index_name.upper()],
                    )
                    return float(cursor.fetchone()[0])
                finally:
                    cursor.close()
        except Exception:
            return None

    def list_indexes(self) -> list[IndexInfo]:
        results: list[IndexInfo] = []
        for precision, (col, idx_name, _) in self.INDEX_CONFIGS.items():
            size = self.measure_index_size_mb(idx_name)
            exists = self.index_exists(idx_name)
            if exists:
                results.append(
                    IndexInfo(
                        index_name=idx_name,
                        table_name="paper_embeddings",
                        column_name=col,
                        index_type="HNSW" if precision == "FP32" else "IVF",
                        precision_mode=precision,
                        size_mb=size,
                    )
                )
        return results
