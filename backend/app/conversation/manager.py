"""ConversationManager: multi-turn memory with progressive filter accumulation.

This is the first component in every query pipeline:
  User Query → ConversationManager → (AmbiguityDetector → ...) → Response
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from app.common.logging import get_logger
from app.config import get_settings
from app.conversation.models import ConversationState, ConversationTurn, RetrievalMode
from app.conversation.repository import (
    InMemoryConversationRepository,
    OracleConversationRepository,
)

logger = get_logger("conversation.manager")


class ConversationManager:
    def __init__(self, repository) -> None:
        self._repo = repository
        # In-process cache: avoids a DB round-trip on every turn of an active session.
        self._cache: dict[str, ConversationState] = {}

    def get_or_create(self, conversation_id: str) -> ConversationState:
        if conversation_id not in self._cache:
            self._cache[conversation_id] = self._repo.load(conversation_id)
        return self._cache[conversation_id]

    def add_turn(
        self,
        conversation_id: str,
        *,
        user_text: str,
        intent: dict[str, Any] | None = None,
        retrieval_mode: RetrievalMode | None = None,
        generated_sql: str | None = None,
        result_paper_ids: list[int] | None = None,
        clarification_question: str | None = None,
        filters: dict[str, Any] | None = None,
    ) -> ConversationTurn:
        state = self.get_or_create(conversation_id)

        turn = ConversationTurn(
            turn_id=state.next_turn_id,
            user_text=user_text,
            intent=intent,
            retrieval_mode=retrieval_mode,
            generated_sql=generated_sql,
            result_paper_ids=result_paper_ids or [],
            clarification_question=clarification_question,
            filters=filters or {},
        )

        state.add_turn(turn)
        self._repo.save_turn(state, turn)

        logger.debug(
            "Turn %d added to conversation %s | mode=%s",
            turn.turn_id,
            conversation_id,
            retrieval_mode,
        )
        return turn

    def build_context(self, conversation_id: str, max_turns: int = 5) -> str:
        """Build a plain-text context string from the last N turns.

        Used by the query planner to resolve incomplete follow-up queries
        ("Only medical ones." → needs previous filters to resolve).
        """
        state = self.get_or_create(conversation_id)
        recent = state.turns[-max_turns:]

        parts: list[str] = []
        for turn in recent:
            parts.append(f"Turn {turn.turn_id}: {turn.user_text}")
            if turn.intent:
                parts.append(f"  Intent: {turn.intent}")
            if turn.filters:
                parts.append(f"  Filters: {turn.filters}")
            if turn.retrieval_mode:
                parts.append(f"  Mode: {turn.retrieval_mode.value}")
        return "\n".join(parts)

    def accumulated_filters(self, conversation_id: str) -> dict[str, Any]:
        """Return merged filters across all turns for progressive refinement."""
        state = self.get_or_create(conversation_id)
        return state.accumulated_filters()

    def get_history(self, conversation_id: str) -> list[dict[str, Any]]:
        state = self.get_or_create(conversation_id)
        return [
            {
                "turn_id":               t.turn_id,
                "user_text":             t.user_text,
                "retrieval_mode":        t.retrieval_mode.value if t.retrieval_mode else None,
                "generated_sql":         t.generated_sql,
                "clarification_question": t.clarification_question,
                "result_count":          len(t.result_paper_ids),
            }
            for t in state.turns
        ]


@lru_cache(maxsize=1)
def get_conversation_manager() -> ConversationManager:
    settings = get_settings()
    if settings.use_oracle:
        from app.database.connection import get_pool
        repo = OracleConversationRepository(get_pool())
    else:
        repo = InMemoryConversationRepository()
    return ConversationManager(repo)
