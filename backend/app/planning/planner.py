"""QueryPlanner: orchestrates routing + intent extraction into a QueryPlan."""
from __future__ import annotations

from functools import lru_cache

from app.common.logging import get_logger
from app.planning.intent_extractor import extract_intent
from app.planning.models import QueryPlan
from app.planning.router import QueryRouter
from app.schema.manager import get_schema_manager

logger = get_logger("planning.planner")


class QueryPlanner:
    def __init__(self) -> None:
        self._router = QueryRouter()

    def plan(self, query: str, conversation_context: str = "") -> QueryPlan:
        """Produce a fully-resolved QueryPlan from a raw user query."""
        snapshot = get_schema_manager().get_snapshot()

        mode, confidence = self._router.route(query)

        structured = extract_intent(query, snapshot=snapshot)

        # For progressive refinement: merge previous turn's filters if present
        # (caller passes accumulated_filters as part of the query text via
        #  ConversationManager.build_context)

        semantic_intent: str | None = None
        from app.conversation.models import RetrievalMode
        if mode in (RetrievalMode.VECTOR, RetrievalMode.HYBRID):
            semantic_intent = query  # the raw text is the semantic query

        needs_global_lookup = (
            confidence < 0.85 and mode in (RetrievalMode.VECTOR, RetrievalMode.HYBRID)
        )

        plan = QueryPlan(
            retrieval_mode=mode,
            structured_intent=structured,
            semantic_intent=semantic_intent,
            confidence=confidence,
            raw_query=query,
            needs_global_lookup=needs_global_lookup,
        )

        logger.info(
            "Plan: mode=%s confidence=%.2f filters=%d semantic=%s global=%s",
            mode.value,
            confidence,
            len(structured.filters),
            semantic_intent is not None,
            needs_global_lookup,
        )
        return plan


@lru_cache(maxsize=1)
def get_planner() -> QueryPlanner:
    return QueryPlanner()
