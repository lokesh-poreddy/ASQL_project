"""Rule-based ambiguity detection.

Intentionally rule-based for V1: deterministic, testable, and auditable.
A learned classifier would require a labelled dataset that does not exist yet.
"""
from __future__ import annotations

import re
from typing import Any

from app.ambiguity.models import AmbiguityResolution, AmbiguityResult, AmbiguityType
from app.common.logging import get_logger

logger = get_logger("ambiguity.detector")

# ── Term dictionaries ─────────────────────────────────────────────────────────

VAGUE_TIME_TERMS: frozenset[str] = frozenset({
    "recent", "recently", "latest", "old", "new", "current",
    "nowadays", "these days", "modern", "early", "historical",
})

VAGUE_METRIC_TERMS: frozenset[str] = frozenset({
    "high", "low", "best", "top", "important", "significant",
    "popular", "famous", "notable", "leading", "prominent",
})

UNANSWERABLE_TERMS: frozenset[str] = frozenset({
    "will", "predict", "future", "tomorrow", "next year",
    "forecast", "expected to",
})

# Patterns that indicate a bare follow-up (no main entity stated)
INCOMPLETE_FOLLOWUP_PATTERNS: list[re.Pattern] = [
    re.compile(r"^\s*(also|and|but|only|just|what about|how about)\b", re.I),
    re.compile(r"^\s*(filter|narrow|refine|show me|sort by)\b", re.I),
]

# Concrete year pattern: 2000-2099
YEAR_PATTERN = re.compile(r"\b20\d{2}\b")

# Explicit metric pattern
EXPLICIT_METRIC_PATTERN = re.compile(
    r"\b(citation|score|rating|count|year|rank|h.index|impact|number)\b", re.I
)


class AmbiguityDetector:
    """Stateless rule-based ambiguity detector.

    Call detect() with the raw user query text and optionally the
    current conversation context string (for follow-up detection).
    """

    def detect(
        self,
        query: str,
        *,
        conversation_context: str = "",
        schema_snapshot: Any = None,  # SchemaSnapshot | None for UNKNOWN_COLUMN check
    ) -> AmbiguityResult:
        text = query.lower().strip()

        # 1. Unanswerable (future-prediction) queries
        if any(term in text for term in UNANSWERABLE_TERMS):
            return AmbiguityResult(
                ambiguous=True,
                ambiguity_type=AmbiguityType.UNANSWERABLE_QUERY,
                resolution=AmbiguityResolution.UNANSWERABLE,
                message=(
                    "This system can only retrieve information about existing papers. "
                    "Predictive or future-oriented queries are not supported."
                ),
            )

        # 2. Incomplete follow-up (no entity in query, relies entirely on context)
        if any(p.match(text) for p in INCOMPLETE_FOLLOWUP_PATTERNS):
            if not conversation_context:
                return AmbiguityResult(
                    ambiguous=True,
                    ambiguity_type=AmbiguityType.INCOMPLETE_FOLLOWUP,
                    resolution=AmbiguityResolution.ASK_USER,
                    message=(
                        "This looks like a follow-up, but there is no previous query context. "
                        "Please provide a complete query."
                    ),
                )
            # Context exists — let the planner resolve it
            return AmbiguityResult(
                ambiguous=False,
                ambiguity_type=AmbiguityType.NONE,
                resolution=AmbiguityResolution.CLEAR,
            )

        # 3. Vague time reference without an explicit year
        if any(term in text for term in VAGUE_TIME_TERMS):
            if not YEAR_PATTERN.search(text):
                return AmbiguityResult(
                    ambiguous=True,
                    ambiguity_type=AmbiguityType.VAGUE_TIME,
                    resolution=AmbiguityResolution.ASK_USER,
                    message=(
                        "What time period should be considered? "
                        "For example: 'papers from 2022 onwards' or 'papers published in 2024'."
                    ),
                    options=["Last year (2024)", "Last 3 years (2022+)", "Last 5 years (2020+)"],
                )

        # 4. Vague metric reference without an explicit metric name
        if any(term in text for term in VAGUE_METRIC_TERMS):
            if not EXPLICIT_METRIC_PATTERN.search(text):
                return AmbiguityResult(
                    ambiguous=True,
                    ambiguity_type=AmbiguityType.VAGUE_METRIC,
                    resolution=AmbiguityResolution.ASK_USER,
                    message=(
                        "Which metric should be used for this ranking or comparison? "
                        "For example: citation count, publication year, or h-index."
                    ),
                    options=["Citation count", "Publication year", "Both"],
                )

        # 5. Clear
        return AmbiguityResult(
            ambiguous=False,
            ambiguity_type=AmbiguityType.NONE,
            resolution=AmbiguityResolution.CLEAR,
        )
