"""Query router: decides SQL / VECTOR / HYBRID based on query features.

The routing decision is deterministic and testable (no LLM, no randomness).
The threshold weights can be tuned as research variables (see config.py).
"""
from __future__ import annotations

import re

from app.common.logging import get_logger
from app.conversation.models import RetrievalMode

logger = get_logger("planning.router")

# Terms that strongly signal semantic / vector search
SEMANTIC_TERMS: tuple[str, ...] = (
    "similar to",
    "related to",
    "like",
    "resembling",
    "about",
    "discussing",
    "concept of",
    "associated with",
    "relevant to",
    "in the field of",
    "semantic",
    "meaning",
)

# Terms that strongly signal structured / SQL filtering
STRUCTURED_TERMS: tuple[str, ...] = (
    "after",
    "before",
    "between",
    "greater than",
    "less than",
    "more than",
    "fewer than",
    "at least",
    "over",
    "under",
    "published in",
    "from",
    "citation",
    "year",
    "venue",
    "conference",
    "journal",
    "authored by",
    "written by",
    "by ",
    "in ",
)

# Bare year pattern: indicates structured intent even without explicit keywords
_YEAR_PATTERN = re.compile(r"\b20\d{2}\b")
_NUMBER_PATTERN = re.compile(r"\b\d{2,}\b")


class QueryRouter:
    """Stateless router.  Returns a (RetrievalMode, confidence) tuple."""

    def route(self, query: str) -> tuple[RetrievalMode, float]:
        text = query.lower()

        semantic_score = sum(1 for t in SEMANTIC_TERMS if t in text)
        structured_score = sum(1 for t in STRUCTURED_TERMS if t in text)

        # Bare year or large number → structured signal
        if _YEAR_PATTERN.search(text):
            structured_score += 2
        if _NUMBER_PATTERN.search(text):
            structured_score += 1

        logger.debug(
            "Router scores: semantic=%d structured=%d | query=%r",
            semantic_score, structured_score, query[:80],
        )

        if semantic_score > 0 and structured_score > 0:
            mode = RetrievalMode.HYBRID
            confidence = min(0.70 + 0.05 * min(semantic_score, structured_score), 0.95)
        elif semantic_score > 0:
            mode = RetrievalMode.VECTOR
            confidence = min(0.75 + 0.05 * semantic_score, 0.95)
        else:
            mode = RetrievalMode.SQL
            confidence = min(0.80 + 0.04 * structured_score, 0.97)

        logger.debug("Routed to %s (confidence=%.2f)", mode.value, confidence)
        return mode, confidence
