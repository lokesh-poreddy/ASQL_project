"""Conversation domain models."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RetrievalMode(str, Enum):
    SQL    = "SQL"
    VECTOR = "VECTOR"
    HYBRID = "HYBRID"


@dataclass
class ConversationTurn:
    turn_id: int
    user_text: str
    intent: dict[str, Any] | None = None
    retrieval_mode: RetrievalMode | None = None
    generated_sql: str | None = None
    result_paper_ids: list[int] = field(default_factory=list)
    clarification_question: str | None = None
    filters: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationState:
    conversation_id: str
    turns: list[ConversationTurn] = field(default_factory=list)

    def add_turn(self, turn: ConversationTurn) -> None:
        self.turns.append(turn)

    @property
    def last_turn(self) -> ConversationTurn | None:
        return self.turns[-1] if self.turns else None

    @property
    def next_turn_id(self) -> int:
        return len(self.turns) + 1

    def accumulated_filters(self) -> dict[str, Any]:
        """Merge filters across all turns for progressive refinement."""
        merged: dict[str, Any] = {}
        for turn in self.turns:
            merged.update(turn.filters)
        return merged
