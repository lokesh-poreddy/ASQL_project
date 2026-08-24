"""Conversation repository.

In production (Oracle available) turns are persisted to QUERY_HISTORY.
In test/dev mode the repository is in-memory only so no Oracle connection
is required.
"""
from __future__ import annotations

import json
from typing import Any

from app.common.exceptions import RepositoryError
from app.common.logging import get_logger
from app.conversation.models import ConversationState, ConversationTurn, RetrievalMode

logger = get_logger("conversation.repository")


class InMemoryConversationRepository:
    """No-Oracle fallback used when APP_ENV=test."""

    def __init__(self) -> None:
        self._store: dict[str, ConversationState] = {}

    def load(self, conversation_id: str) -> ConversationState:
        if conversation_id not in self._store:
            self._store[conversation_id] = ConversationState(
                conversation_id=conversation_id
            )
        return self._store[conversation_id]

    def save_turn(self, state: ConversationState, turn: ConversationTurn) -> None:
        # State is mutated in-place; nothing to persist.
        pass

    def list_conversations(self) -> list[str]:
        return list(self._store.keys())


class OracleConversationRepository:
    """Persists conversation turns to QUERY_HISTORY in Oracle."""

    def __init__(self, connection_provider) -> None:
        self._cp = connection_provider

    def load(self, conversation_id: str) -> ConversationState:
        try:
            with self._cp.get_connection() as conn:
                return self._load_from_db(conn, conversation_id)
        except Exception as exc:
            raise RepositoryError(
                f"Failed to load conversation {conversation_id}: {exc}"
            ) from exc

    def _load_from_db(self, conn, conversation_id: str) -> ConversationState:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT history_id, turn_id, user_query, interpreted_intent,
                       retrieval_mode, generated_sql, result_paper_ids,
                       clarification_question
                FROM   query_history
                WHERE  conversation_id = :1
                ORDER  BY turn_id
                """,
                [conversation_id],
            )
            rows = cursor.fetchall()
        finally:
            cursor.close()

        state = ConversationState(conversation_id=conversation_id)
        for row in rows:
            (_, turn_id, user_query, intent_json,
             mode_str, sql, result_ids_json, clarification) = row

            intent = json.loads(intent_json) if intent_json else None
            result_ids = json.loads(result_ids_json) if result_ids_json else []
            mode = RetrievalMode(mode_str) if mode_str else None

            turn = ConversationTurn(
                turn_id=turn_id,
                user_text=str(user_query),
                intent=intent,
                retrieval_mode=mode,
                generated_sql=str(sql) if sql else None,
                result_paper_ids=result_ids,
                clarification_question=clarification,
            )
            state.turns.append(turn)
        return state

    def save_turn(self, state: ConversationState, turn: ConversationTurn) -> None:
        try:
            with self._cp.get_connection() as conn:
                self._insert_turn(conn, state.conversation_id, turn)
        except Exception as exc:
            raise RepositoryError(
                f"Failed to save turn for {state.conversation_id}: {exc}"
            ) from exc

    def _insert_turn(self, conn, conversation_id: str, turn: ConversationTurn) -> None:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO query_history (
                    conversation_id, turn_id, user_query,
                    interpreted_intent, retrieval_mode,
                    generated_sql, result_paper_ids, clarification_question
                ) VALUES (
                    :1, :2, :3, :4, :5, :6, :7, :8
                )
                """,
                [
                    conversation_id,
                    turn.turn_id,
                    turn.user_text,
                    json.dumps(turn.intent) if turn.intent else None,
                    turn.retrieval_mode.value if turn.retrieval_mode else None,
                    turn.generated_sql,
                    json.dumps(turn.result_paper_ids),
                    turn.clarification_question,
                ],
            )
        finally:
            cursor.close()

    def list_conversations(self) -> list[str]:
        try:
            with self._cp.get_connection() as conn:
                cursor = conn.cursor()
                try:
                    cursor.execute(
                        """
                        SELECT DISTINCT conversation_id
                        FROM   query_history
                        ORDER  BY 1
                        """
                    )
                    return [r[0] for r in cursor.fetchall()]
                finally:
                    cursor.close()
        except Exception as exc:
            raise RepositoryError(f"Failed to list conversations: {exc}") from exc
