"""SQL generator: converts a QueryPlan into a (sql_string, bind_params) pair
via an intermediate QueryIR. No string concatenation of user-supplied values.

Design rules:
  1. All user-influenced values go into bind_params, never into the SQL string.
  2. Every table and column reference is validated against the SchemaSnapshot
     before the IR is built.
  3. The generator only builds SELECT statements. INSERT/UPDATE/DELETE live in
     repository classes, never here.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from app.common.exceptions import SQLGenerationError
from app.common.logging import get_logger
from app.planning.models import ColumnFilter, FilterOperator, QueryPlan, StructuredIntent
from app.schema.manager import get_schema_manager
from app.sql.query_ir import JoinClause, JoinType, OrderByClause, QueryIR, WhereCondition

logger = get_logger("sql.generator")

# The columns we always project for paper results
_PAPER_COLUMNS = [
    "p.paper_id",
    "p.paper_code",
    "p.title",
    "p.year",
    "p.citation_count",
    "p.primary_research_area_id",
    "p.venue_id",
    "p.doi",
    "p.publication_type",
]

# Table alias map
_ALIASES: dict[str, str] = {
    "papers":          "p",
    "authors":         "a",
    "venues":          "v",
    "research_areas":  "ra",
    "paper_authors":   "pa",
    "keywords":        "k",
    "paper_keywords":  "pk",
}

# FK join paths: (parent_table, parent_col, child_table, child_col)
_JOIN_PATHS: dict[str, tuple[str, str, str, str]] = {
    "venues":         ("papers", "venue_id",                  "venues",        "venue_id"),
    "research_areas": ("papers", "primary_research_area_id",  "research_areas","area_id"),
    "authors": None,  # needs paper_authors bridge — handled specially
}


class SQLGenerator:

    def generate(self, plan: QueryPlan) -> tuple[str, dict[str, Any]]:
        """Return (sql_string, bind_params) from a QueryPlan."""
        ir = self._build_ir(plan.structured_intent)
        sql = self._render(ir)
        logger.debug("Generated SQL:\n%s\nParams: %s", sql, ir.bind_params)
        return sql, ir.bind_params

    # ── IR construction ───────────────────────────────────────────────────────

    def _build_ir(self, intent: StructuredIntent) -> QueryIR:
        schema = get_schema_manager().get_snapshot()

        ir = QueryIR(
            select_columns=list(_PAPER_COLUMNS),
            from_table="papers",
            from_alias="p",
        )

        added_joins: set[str] = set()

        for filt in intent.filters:
            self._validate_filter(filt, schema)
            self._add_join_if_needed(ir, filt.table, added_joins)
            self._add_where(ir, filt)

        for col, direction in intent.order_by:
            ir.order_by.append(OrderByClause(column=f"p.{col}", direction=direction))

        if intent.limit is not None:
            ir.limit = intent.limit

        return ir

    def _validate_filter(self, filt: ColumnFilter, schema) -> None:
        """Raise SQLGenerationError if table or column doesn't exist."""
        tbl = schema.get_table(filt.table)
        if tbl is None:
            raise SQLGenerationError(
                f"Unknown table '{filt.table}' referenced in filter."
            )
        if not tbl.has_column(filt.column):
            raise SQLGenerationError(
                f"Unknown column '{filt.column}' in table '{filt.table}'."
            )

    def _add_join_if_needed(
        self,
        ir: QueryIR,
        table: str,
        added_joins: set[str],
    ) -> None:
        if table == "papers" or table in added_joins:
            return

        alias = _ALIASES.get(table, table[:2])

        if table in ("venues", "research_areas"):
            path = _JOIN_PATHS[table]
            parent_alias = _ALIASES[path[0]]
            ir.joins.append(
                JoinClause(
                    join_type=JoinType.LEFT,
                    table=table,
                    alias=alias,
                    on_left_table=parent_alias,
                    on_left_col=path[1],
                    on_right_col=path[3],
                )
            )
            # Add the joined table's relevant column to SELECT
            if table == "venues":
                ir.select_columns.append(f"{alias}.venue_name")
            elif table == "research_areas":
                ir.select_columns.append(f"{alias}.area_name")
            added_joins.add(table)

        elif table == "authors":
            # Need paper_authors bridge table too
            if "paper_authors" not in added_joins:
                ir.joins.append(
                    JoinClause(
                        join_type=JoinType.INNER,
                        table="paper_authors",
                        alias="pa",
                        on_left_table="p",
                        on_left_col="paper_id",
                        on_right_col="paper_id",
                    )
                )
                added_joins.add("paper_authors")
            ir.joins.append(
                JoinClause(
                    join_type=JoinType.INNER,
                    table="authors",
                    alias="a",
                    on_left_table="pa",
                    on_left_col="author_id",
                    on_right_col="author_id",
                )
            )
            ir.select_columns.append("a.full_name AS author_name")
            added_joins.add("authors")

    def _add_where(self, ir: QueryIR, filt: ColumnFilter) -> None:
        alias = _ALIASES.get(filt.table, filt.table[:2])
        # Unique param name to avoid collisions when multiple filters exist
        param_name = f"{filt.table}_{filt.column}_{len(ir.bind_params)}"

        op = filt.operator.value
        if op == "LIKE":
            condition = WhereCondition(
                table_alias=alias,
                column=filt.column,
                operator="LIKE",
                param_name=param_name,
            )
        else:
            condition = WhereCondition(
                table_alias=alias,
                column=filt.column,
                operator=op,
                param_name=param_name,
            )

        ir.where.append(condition)
        ir.bind_params[param_name] = filt.value

    # ── Rendering ─────────────────────────────────────────────────────────────

    def _render(self, ir: QueryIR) -> str:
        lines: list[str] = []

        # SELECT
        lines.append("SELECT")
        cols = ",\n       ".join(ir.select_columns)
        lines.append(f"       {cols}")

        # FROM
        lines.append(f"FROM   {ir.from_table} {ir.from_alias}")

        # JOINs
        for j in ir.joins:
            lines.append(
                f"{j.join_type.value} {j.table} {j.alias}"
                f" ON {j.alias}.{j.on_right_col} = {j.on_left_table}.{j.on_left_col}"
            )

        # WHERE
        if ir.where:
            conditions = [
                f"{w.table_alias}.{w.column} {w.operator} :{w.param_name}"
                for w in ir.where
            ]
            lines.append("WHERE  " + "\n  AND  ".join(conditions))

        # ORDER BY
        if ir.order_by:
            order_parts = [f"{o.column} {o.direction}" for o in ir.order_by]
            lines.append("ORDER BY " + ", ".join(order_parts))

        # FETCH FIRST (Oracle rownum alternative)
        if ir.limit is not None:
            lines.append(f"FETCH FIRST {ir.limit} ROWS ONLY")

        return "\n".join(lines)


@lru_cache(maxsize=1)
def get_sql_generator() -> SQLGenerator:
    return SQLGenerator()
