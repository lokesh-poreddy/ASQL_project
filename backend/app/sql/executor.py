"""SQL executor: runs parameterized SELECT statements against Oracle.

Responsibilities:
  - Measure wall-clock execution time (for P50/P95/P99 benchmarking).
  - Map cursor rows to list[dict] with lowercase column names.
  - Wrap oracledb exceptions in SQLExecutionError with the ORA- code preserved.
  - Never construct SQL strings — receives them from the generator.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from app.common.exceptions import SQLExecutionError
from app.common.logging import get_logger

logger = get_logger("sql.executor")


@dataclass
class SQLExecutionResult:
    rows: list[dict[str, Any]]
    row_count: int
    elapsed_ms: float
    sql_text: str


class SQLExecutor:

    def __init__(self, connection_provider) -> None:
        self._cp = connection_provider

    def execute(
        self,
        sql: str,
        parameters: dict[str, Any] | None = None,
    ) -> SQLExecutionResult:
        parameters = parameters or {}
        started = time.perf_counter()

        try:
            with self._cp.get_connection() as conn:
                cursor = conn.cursor()
                try:
                    cursor.execute(sql, parameters)
                    columns = [desc[0].lower() for desc in cursor.description]
                    rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
                finally:
                    cursor.close()

            elapsed_ms = (time.perf_counter() - started) * 1000.0

            logger.debug(
                "SQL executed: %d rows in %.1f ms", len(rows), elapsed_ms
            )

            return SQLExecutionResult(
                rows=rows,
                row_count=len(rows),
                elapsed_ms=elapsed_ms,
                sql_text=sql,
            )

        except Exception as exc:
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            error_str = str(exc)

            # Extract ORA-XXXXX code if present
            import re
            m = re.search(r"ORA-(\d+)", error_str)
            oracle_code = f"ORA-{m.group(1)}" if m else None

            logger.error(
                "SQL execution failed after %.1f ms: %s | ORA=%s",
                elapsed_ms, error_str[:200], oracle_code,
            )

            raise SQLExecutionError(
                f"SQL execution failed: {error_str}",
                oracle_error_code=oracle_code,
                sql_text=sql,
            ) from exc


class InMemorySQLExecutor:
    """Offline executor used when APP_ENV=test. Runs against the in-memory
    seed dataset without an Oracle connection."""

    # Minimal seed matching the seed SQL (paper_id, title, year, citation_count, area_id)
    SEED_ROWS: list[dict[str, Any]] = [
        {"paper_id": 1,  "paper_code": "P-00001", "title": "Attention Is All You Need",                             "year": 2017, "citation_count": 15000, "primary_research_area_id": 1},
        {"paper_id": 2,  "paper_code": "P-00002", "title": "BERT: Pre-training of Deep Bidirectional Transformers", "year": 2019, "citation_count": 12000, "primary_research_area_id": 1},
        {"paper_id": 3,  "paper_code": "P-00003", "title": "Deep Residual Learning for Image Recognition",          "year": 2016, "citation_count": 18000, "primary_research_area_id": 2},
        {"paper_id": 4,  "paper_code": "P-00004", "title": "Transformer-Based ECG Analysis",                        "year": 2023, "citation_count": 340,   "primary_research_area_id": 5},
        {"paper_id": 5,  "paper_code": "P-00005", "title": "Scalable Distributed SQL Query Processing",              "year": 2022, "citation_count": 89,    "primary_research_area_id": 3},
        {"paper_id": 6,  "paper_code": "P-00006", "title": "Neural Information Retrieval: A Survey",                "year": 2021, "citation_count": 450,   "primary_research_area_id": 7},
        {"paper_id": 7,  "paper_code": "P-00007", "title": "Hybrid Vector-SQL Retrieval for Scientific Literature", "year": 2024, "citation_count": 22,    "primary_research_area_id": 7},
        {"paper_id": 8,  "paper_code": "P-00008", "title": "Learned Query Optimisation in Relational Databases",    "year": 2024, "citation_count": 130,   "primary_research_area_id": 3},
        {"paper_id": 9,  "paper_code": "P-00009", "title": "Quantised Vector Embeddings for Low-Memory Retrieval",  "year": 2025, "citation_count": 18,    "primary_research_area_id": 6},
        {"paper_id": 10, "paper_code": "P-00010", "title": "ECG Signal Segmentation Using Self-Supervised Transformers", "year": 2024, "citation_count": 77,   "primary_research_area_id": 5},
        {"paper_id": 12, "paper_code": "P-00012", "title": "Retrieval-Augmented Generation",                        "year": 2020, "citation_count": 6200,  "primary_research_area_id": 1},
        {"paper_id": 14, "paper_code": "P-00014", "title": "Vision Transformer: An Image Is Worth 16x16 Words",     "year": 2021, "citation_count": 9800,  "primary_research_area_id": 2},
        {"paper_id": 16, "paper_code": "P-00016", "title": "Dense Passage Retrieval",                               "year": 2020, "citation_count": 5100,  "primary_research_area_id": 7},
        {"paper_id": 17, "paper_code": "P-00017", "title": "Conversational SQL: NL to SQL",                         "year": 2023, "citation_count": 210,   "primary_research_area_id": 1},
        {"paper_id": 18, "paper_code": "P-00018", "title": "Approximate Nearest Neighbour Search with HNSW",        "year": 2018, "citation_count": 3400,  "primary_research_area_id": 7},
        {"paper_id": 21, "paper_code": "P-00021", "title": "Efficient Transformers: A Survey",                      "year": 2022, "citation_count": 2300,  "primary_research_area_id": 6},
        {"paper_id": 26, "paper_code": "P-00026", "title": "Adaptive Compression for Learned Vector Indexes",       "year": 2025, "citation_count": 5,     "primary_research_area_id": 7},
        {"paper_id": 27, "paper_code": "P-00027", "title": "Query-Aware Data Partitioning in Distributed Databases","year": 2024, "citation_count": 102,   "primary_research_area_id": 3},
        {"paper_id": 28, "paper_code": "P-00028", "title": "Cardiac Risk Stratification with Multi-Modal Learning", "year": 2025, "citation_count": 3,     "primary_research_area_id": 5},
        {"paper_id": 29, "paper_code": "P-00029", "title": "Causal Inference in Machine Learning",                  "year": 2024, "citation_count": 198,   "primary_research_area_id": 6},
        {"paper_id": 30, "paper_code": "P-00030", "title": "NEXUS-SQL: Adaptive Hybrid Retrieval",                 "year": 2025, "citation_count": 1,     "primary_research_area_id": 7},
    ]

    def execute(
        self,
        sql: str,
        parameters: dict[str, Any] | None = None,
    ) -> SQLExecutionResult:
        parameters = parameters or {}
        started = time.perf_counter()

        rows = list(self.SEED_ROWS)  # always work on a copy

        # Apply year filters
        year_gte = parameters.get("papers_year_0") or parameters.get("papers_year_1")
        year_lte = None
        citation_gt = None

        for key, val in parameters.items():
            if "year" in key and ">=" in sql:
                rows = [r for r in rows if r["year"] >= int(val)]
            elif "year" in key and ">" in sql and "<=" not in sql:
                rows = [r for r in rows if r["year"] > int(val)]
            elif "year" in key and "<=" in sql:
                rows = [r for r in rows if r["year"] <= int(val)]
            elif "citation_count" in key and "> :" in sql:
                rows = [r for r in rows if r["citation_count"] > int(val)]
            elif "citation_count" in key and "< :" in sql:
                rows = [r for r in rows if r["citation_count"] < int(val)]

        # Sort by citation_count DESC (default)
        rows.sort(key=lambda r: r["citation_count"], reverse=True)

        elapsed_ms = (time.perf_counter() - started) * 1000.0
        return SQLExecutionResult(
            rows=rows,
            row_count=len(rows),
            elapsed_ms=elapsed_ms,
            sql_text=sql,
        )


def get_sql_executor() -> "SQLExecutor | InMemorySQLExecutor":
    from app.config import get_settings
    settings = get_settings()
    if settings.use_oracle:
        from app.database.connection import get_pool
        return SQLExecutor(get_pool())
    return InMemorySQLExecutor()
