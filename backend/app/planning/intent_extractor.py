"""Intent and filter extraction from raw NL queries.

Produces a StructuredIntent (the IR between raw text and SQL) without
touching the database and without generating SQL directly from text.

Supported extractions (V1):
  - publication year  (year / after / before / between)
  - citation count    (more than / over / above / greater than / at least)
  - research area     (matched against known area names via substring)
  - venue             (matched against known venue names via substring)
  - author            (keyword "by <name>")
  - ORDER BY          (by citations | by year | order by)
  - LIMIT             (top N / first N / limit N)
"""
from __future__ import annotations

import re
from typing import Any

from app.common.logging import get_logger
from app.planning.models import ColumnFilter, FilterOperator, StructuredIntent
from app.schema.models import SchemaSnapshot

logger = get_logger("planning.intent_extractor")

# ── Compiled patterns ─────────────────────────────────────────────────────────

_YEAR_AFTER   = re.compile(r"\b(?:after|from|since|published\s+in|in)\s+(20\d{2})\b", re.I)
_YEAR_BEFORE  = re.compile(r"\b(?:before|until|up\s+to)\s+(20\d{2})\b", re.I)
_YEAR_EXACT   = re.compile(r"\bpublished\s+in\s+(20\d{2})\b", re.I)
_YEAR_BETWEEN = re.compile(r"\bbetween\s+(20\d{2})\s+and\s+(20\d{2})\b", re.I)

_CITE_GT = re.compile(
    r"\b(?:more\s+than|over|above|greater\s+than|at\s+least|>\s*)\s*(\d+)\s*cit", re.I
)
_CITE_LT = re.compile(
    r"\b(?:fewer\s+than|less\s+than|under|below|<\s*)\s*(\d+)\s*cit", re.I
)

_TOP_N   = re.compile(r"\b(?:top|first|limit)\s+(\d+)\b", re.I)
_BY_NAME = re.compile(r"\bby\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)", re.I)

_ORDER_CITATIONS = re.compile(r"\b(?:sort|order)\s+by\s+cit", re.I)
_ORDER_YEAR      = re.compile(r"\b(?:sort|order)\s+by\s+year", re.I)
_ORDER_TOP_CITES = re.compile(r"\bmost\s+cited\b", re.I)


def extract_intent(query: str, snapshot: SchemaSnapshot | None = None) -> StructuredIntent:
    """Return a StructuredIntent from a raw NL query string."""
    text = query.strip()
    filters: list[ColumnFilter] = []

    # ── Year filters ──────────────────────────────────────────────────────────
    m_between = _YEAR_BETWEEN.search(text)
    if m_between:
        y1, y2 = int(m_between.group(1)), int(m_between.group(2))
        filters.append(ColumnFilter("papers", "year", FilterOperator.GTE, min(y1, y2)))
        filters.append(ColumnFilter("papers", "year", FilterOperator.LTE, max(y1, y2)))
    else:
        m_after = _YEAR_AFTER.search(text)
        m_exact = _YEAR_EXACT.search(text)
        m_before = _YEAR_BEFORE.search(text)
        if m_exact:
            filters.append(ColumnFilter("papers", "year", FilterOperator.EQ, int(m_exact.group(1))))
        elif m_after:
            filters.append(ColumnFilter("papers", "year", FilterOperator.GTE, int(m_after.group(1))))
        if m_before:
            filters.append(ColumnFilter("papers", "year", FilterOperator.LTE, int(m_before.group(1))))

    # ── Citation filters ──────────────────────────────────────────────────────
    m_cite_gt = _CITE_GT.search(text)
    if m_cite_gt:
        filters.append(
            ColumnFilter("papers", "citation_count", FilterOperator.GT, int(m_cite_gt.group(1)))
        )

    m_cite_lt = _CITE_LT.search(text)
    if m_cite_lt:
        filters.append(
            ColumnFilter("papers", "citation_count", FilterOperator.LT, int(m_cite_lt.group(1)))
        )

    # ── Research area (fuzzy match against known names) ───────────────────────
    joins: list[str] = []
    if snapshot:
        lower = text.lower()
        for area in snapshot.research_areas:
            if area.area_name.lower() in lower:
                filters.append(
                    ColumnFilter(
                        "research_areas", "area_name",
                        FilterOperator.EQ, area.area_name,
                    )
                )
                if "research_areas" not in joins:
                    joins.append("research_areas")
                break

        # ── Venue ─────────────────────────────────────────────────────────────
        for venue in snapshot.venues:
            if venue.venue_name.lower() in lower:
                filters.append(
                    ColumnFilter(
                        "venues", "venue_name",
                        FilterOperator.EQ, venue.venue_name,
                    )
                )
                if "venues" not in joins:
                    joins.append("venues")
                break

    # ── Author ────────────────────────────────────────────────────────────────
    m_author = _BY_NAME.search(text)
    if m_author:
        filters.append(
            ColumnFilter(
                "authors", "full_name",
                FilterOperator.LIKE, f"%{m_author.group(1)}%",
            )
        )
        if "authors" not in joins:
            joins.append("authors")

    # ── ORDER BY ──────────────────────────────────────────────────────────────
    order_by: list[tuple[str, str]] = []
    if _ORDER_CITATIONS.search(text) or _ORDER_TOP_CITES.search(text):
        order_by.append(("citation_count", "DESC"))
    elif _ORDER_YEAR.search(text):
        order_by.append(("year", "DESC"))
    else:
        # Default: most cited first
        order_by.append(("citation_count", "DESC"))

    # ── LIMIT ─────────────────────────────────────────────────────────────────
    limit: int | None = None
    m_top = _TOP_N.search(text)
    if m_top:
        limit = int(m_top.group(1))

    return StructuredIntent(
        entity="papers",
        filters=filters,
        order_by=order_by,
        limit=limit,
        joins=joins,
    )
