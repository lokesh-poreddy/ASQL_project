"""Explanation engine: produces a human-readable account of how a query was
processed, routed, executed, and corrected.

The explanation is returned alongside every query response so the user can
understand the system's reasoning. This also serves as a transparency
mechanism for the ASQL research system.
"""
from __future__ import annotations

from typing import Any


class ExplanationEngine:

    def explain(
        self,
        *,
        user_query: str,
        retrieval_mode: str,
        structured_intent: dict[str, Any] | None,
        semantic_intent: str | None,
        sql: str | None,
        sql_elapsed_ms: float | None,
        vector_elapsed_ms: float | None,
        total_elapsed_ms: float | None,
        result_count: int,
        correction_applied: bool,
        correction_count: int,
        alpha_used: float | None = None,
        optimizer_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build and return the full explanation dict."""

        # ── Intent interpretation ─────────────────────────────────────────────
        intent_summary: dict[str, Any] = {}
        if structured_intent:
            filters = structured_intent.get("filters", [])
            if filters:
                intent_summary["structured_filters"] = [
                    f"{f.get('table')}.{f.get('column')} {f.get('operator')} {f.get('value')!r}"
                    if isinstance(f, dict)
                    else str(f)
                    for f in filters
                ]
        if semantic_intent:
            intent_summary["semantic_query"] = semantic_intent

        # ── Retrieval explanation ─────────────────────────────────────────────
        retrieval_explanation: dict[str, Any] = {
            "mode": retrieval_mode,
        }
        if retrieval_mode == "HYBRID" and alpha_used is not None:
            retrieval_explanation["alpha"] = alpha_used
            retrieval_explanation["semantic_weight"] = alpha_used
            retrieval_explanation["sql_weight"] = round(1.0 - alpha_used, 4)

        # ── Timing ────────────────────────────────────────────────────────────
        timing: dict[str, Any] = {}
        if sql_elapsed_ms is not None:
            timing["sql_ms"] = round(sql_elapsed_ms, 2)
        if vector_elapsed_ms is not None:
            timing["vector_ms"] = round(vector_elapsed_ms, 2)
        if total_elapsed_ms is not None:
            timing["total_ms"] = round(total_elapsed_ms, 2)

        # ── Correction ────────────────────────────────────────────────────────
        correction: dict[str, Any] = {
            "applied": correction_applied,
            "count":   correction_count,
        }

        explanation: dict[str, Any] = {
            "user_query":         user_query,
            "intent":             intent_summary,
            "retrieval":          retrieval_explanation,
            "generated_sql":      sql,
            "result_count":       result_count,
            "timing":             timing,
            "correction":         correction,
        }

        if optimizer_config:
            explanation["optimizer"] = optimizer_config

        return explanation

    def format_for_display(self, explanation: dict[str, Any]) -> str:
        """Produce a concise human-readable summary for the UI."""
        lines: list[str] = [
            f"Query: {explanation['user_query']}",
            f"Mode:  {explanation['retrieval']['mode']}",
        ]

        intent = explanation.get("intent", {})
        if "structured_filters" in intent:
            lines.append("Filters:")
            for f in intent["structured_filters"]:
                lines.append(f"  • {f}")
        if "semantic_query" in intent:
            lines.append(f"Semantic: \"{intent['semantic_query']}\"")

        if explanation.get("generated_sql"):
            lines.append(f"SQL: {explanation['generated_sql'][:120].strip()}…")

        timing = explanation.get("timing", {})
        if "total_ms" in timing:
            lines.append(f"Time:  {timing['total_ms']} ms")

        corr = explanation.get("correction", {})
        if corr.get("applied"):
            lines.append(f"Correction: {corr['count']} correction(s) applied.")
        else:
            lines.append("Correction: None required.")

        lines.append(f"Results: {explanation['result_count']} paper(s) returned.")
        return "\n".join(lines)
