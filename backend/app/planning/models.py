"""Planning domain models — the intermediate representation between raw text and SQL."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.conversation.models import RetrievalMode


class FilterOperator(str, Enum):
    EQ  = "="
    NEQ = "!="
    GT  = ">"
    GTE = ">="
    LT  = "<"
    LTE = "<="
    IN  = "IN"
    LIKE = "LIKE"


@dataclass
class ColumnFilter:
    table: str
    column: str
    operator: FilterOperator
    value: Any


@dataclass
class StructuredIntent:
    """Everything the SQL generator needs — no raw text."""
    entity: str = "papers"                       # primary table
    filters: list[ColumnFilter] = field(default_factory=list)
    order_by: list[tuple[str, str]] = field(default_factory=list)  # (column, ASC|DESC)
    limit: int | None = None
    joins: list[str] = field(default_factory=list)                  # table names to join


@dataclass
class QueryPlan:
    retrieval_mode: RetrievalMode
    structured_intent: StructuredIntent
    semantic_intent: str | None
    confidence: float
    raw_query: str = ""
    needs_global_lookup: bool = False
