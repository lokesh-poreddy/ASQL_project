"""Schema-aware SQL repair strategies.

Each repair strategy is a function that takes the failing SQL string and
the error category, attempts a correction, and returns the corrected SQL
or the original if no safe correction is possible.

Design rule: NEVER silently change a value. Only correct clearly wrong
identifiers by looking them up in the schema. If no confident match
exists, return the original SQL unchanged so the error propagates to the
recovery engine's failure path.
"""
from __future__ import annotations

import re

from app.common.logging import get_logger
from app.recovery.oracle_errors import OracleErrorCategory
from app.schema.manager import get_schema_manager

logger = get_logger("recovery.schema_repair")


def attempt_repair(
    sql: str,
    error_category: OracleErrorCategory,
    error_message: str,
) -> str:
    """Dispatch to the appropriate repair strategy. Returns original SQL if
    no safe correction is possible."""

    if error_category == OracleErrorCategory.INVALID_IDENTIFIER:
        return _repair_invalid_identifier(sql, error_message)

    if error_category == OracleErrorCategory.TABLE_NOT_FOUND:
        return _repair_table_not_found(sql, error_message)

    # All other categories: no automatic repair available yet.
    logger.warning(
        "No repair strategy for category=%s. Returning unchanged SQL.",
        error_category.value,
    )
    return sql


def _repair_invalid_identifier(sql: str, error_message: str) -> str:
    """ORA-00904: Extract the bad identifier from the error message and try
    to find the closest column name in the schema."""
    # Oracle error format: ORA-00904: "ALIAS"."COLNAME": invalid identifier
    m = re.search(r'"[^"]*"\."([^"]+)"', error_message)
    if not m:
        m = re.search(r'"([^"]+)":\s*invalid identifier', error_message, re.I)
    if not m:
        logger.warning("Cannot extract bad identifier from: %s", error_message[:200])
        return sql

    bad_col = m.group(1).lower()
    logger.info("Attempting repair for invalid identifier: %s", bad_col)

    schema = get_schema_manager().get_snapshot()
    best_match: str | None = None
    best_score = 0

    for table in schema.tables.values():
        for col in table.columns:
            score = _similarity(bad_col, col.name.lower())
            if score > best_score and score >= 0.7:
                best_score = score
                best_match = col.name.lower()

    if best_match and best_match != bad_col:
        logger.info("Replacing '%s' → '%s' (score=%.2f)", bad_col, best_match, best_score)
        # Replace the bad identifier in the SQL (case-insensitive)
        corrected = re.sub(
            rf"\b{re.escape(bad_col)}\b",
            best_match,
            sql,
            flags=re.IGNORECASE,
        )
        return corrected

    logger.warning("No confident replacement found for '%s'.", bad_col)
    return sql


def _repair_table_not_found(sql: str, error_message: str) -> str:
    """ORA-00942: table or view does not exist."""
    # Try to extract the table name from the message
    m = re.search(r'"([A-Z_]+)"\s+does not exist', error_message, re.I)
    if not m:
        return sql

    bad_table = m.group(1).lower()
    schema = get_schema_manager().get_snapshot()

    best_match: str | None = None
    best_score = 0
    for tname in schema.tables:
        score = _similarity(bad_table, tname.lower())
        if score > best_score and score >= 0.75:
            best_score = score
            best_match = tname.lower()

    if best_match and best_match != bad_table:
        logger.info(
            "Replacing table '%s' → '%s' (score=%.2f)",
            bad_table, best_match, best_score,
        )
        return re.sub(
            rf"\b{re.escape(bad_table)}\b",
            best_match,
            sql,
            flags=re.IGNORECASE,
        )

    return sql


def _similarity(a: str, b: str) -> float:
    """Simple character-level Jaccard similarity for identifier matching."""
    set_a = set(a)
    set_b = set(b)
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)
