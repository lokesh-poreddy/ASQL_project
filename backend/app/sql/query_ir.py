"""SQL Intermediate Representation.

A QueryIR is the structured description of a SQL query before it is
rendered to a string. The generator builds this; the validator checks it
against the schema; the executor never sees the IR — only the final SQL
string and bind parameters.

This separation ensures no SQL string is ever built from unsanitised user input.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class JoinType(str, Enum):
    INNER = "INNER JOIN"
    LEFT  = "LEFT JOIN"


@dataclass
class JoinClause:
    join_type: JoinType
    table: str
    alias: str
    on_left_table: str
    on_left_col: str
    on_right_col: str


@dataclass
class WhereCondition:
    table_alias: str
    column: str
    operator: str   # "=", ">=", ">", etc.
    param_name: str


@dataclass
class OrderByClause:
    column: str
    direction: str = "DESC"


@dataclass
class QueryIR:
    """Full description of the SELECT to be rendered."""
    select_columns: list[str]              # ["p.paper_id", "p.title", ...]
    from_table: str                        # "papers"
    from_alias: str                        # "p"
    joins: list[JoinClause] = field(default_factory=list)
    where: list[WhereCondition] = field(default_factory=list)
    order_by: list[OrderByClause] = field(default_factory=list)
    limit: int | None = None
    bind_params: dict[str, Any] = field(default_factory=dict)
