"""Tests: SQL generator and validator."""
from __future__ import annotations

import os
os.environ["APP_ENV"] = "test"

import pytest

from app.conversation.models import RetrievalMode
from app.planning.intent_extractor import extract_intent
from app.planning.models import ColumnFilter, FilterOperator, QueryPlan, StructuredIntent
from app.schema.introspector import StaticSchemaIntrospector
from app.sql.generator import SQLGenerator
from app.sql.validator import SQLValidator
from app.common.exceptions import SQLGenerationError, SQLValidationError


@pytest.fixture
def snapshot():
    return StaticSchemaIntrospector().load_snapshot()


@pytest.fixture
def generator() -> SQLGenerator:
    return SQLGenerator()


@pytest.fixture
def validator() -> SQLValidator:
    return SQLValidator()


def _make_plan(intent: StructuredIntent) -> QueryPlan:
    return QueryPlan(
        retrieval_mode=RetrievalMode.SQL,
        structured_intent=intent,
        semantic_intent=None,
        confidence=0.9,
    )


class TestSQLGenerator:
    def test_basic_select(self, generator) -> None:
        plan = _make_plan(StructuredIntent())
        sql, params = generator.generate(plan)
        assert "SELECT" in sql
        assert "papers" in sql
        assert not params

    def test_year_filter_in_sql(self, generator, snapshot) -> None:
        intent = extract_intent("Find papers from 2022", snapshot=snapshot)
        plan = _make_plan(intent)
        sql, params = generator.generate(plan)
        assert "year" in sql.lower()
        assert any("2022" == str(v) for v in params.values())

    def test_citation_filter_in_sql(self, generator, snapshot) -> None:
        intent = extract_intent("Papers with more than 500 citations", snapshot=snapshot)
        plan = _make_plan(intent)
        sql, params = generator.generate(plan)
        assert "citation_count" in sql.lower()
        assert 500 in params.values()

    def test_venue_join_added(self, generator, snapshot) -> None:
        intent = extract_intent("Find papers from NeurIPS", snapshot=snapshot)
        plan = _make_plan(intent)
        sql, _ = generator.generate(plan)
        assert "venues" in sql.lower()

    def test_area_join_added(self, generator, snapshot) -> None:
        intent = extract_intent(
            "Papers about Natural Language Processing", snapshot=snapshot
        )
        plan = _make_plan(intent)
        sql, _ = generator.generate(plan)
        assert "research_areas" in sql.lower()

    def test_limit_in_sql(self, generator, snapshot) -> None:
        intent = extract_intent("Top 5 papers by citation", snapshot=snapshot)
        plan = _make_plan(intent)
        sql, _ = generator.generate(plan)
        assert "5" in sql

    def test_fetch_first_used_not_rownum(self, generator, snapshot) -> None:
        intent = extract_intent("Top 10 papers", snapshot=snapshot)
        plan = _make_plan(intent)
        sql, _ = generator.generate(plan)
        assert "FETCH FIRST" in sql.upper()
        assert "ROWNUM" not in sql.upper()

    def test_no_user_values_in_sql_string(self, generator, snapshot) -> None:
        """Values must be in params dict, not interpolated into the SQL."""
        intent = extract_intent("Papers with more than 300 citations", snapshot=snapshot)
        plan = _make_plan(intent)
        sql, params = generator.generate(plan)
        # 300 should NOT appear as a literal in the SQL — it goes in params
        assert "300" not in sql
        assert 300 in params.values()

    def test_invalid_table_raises(self, generator) -> None:
        intent = StructuredIntent(
            filters=[ColumnFilter("nonexistent_table", "col", FilterOperator.EQ, 1)]
        )
        plan = _make_plan(intent)
        with pytest.raises(SQLGenerationError):
            generator.generate(plan)

    def test_invalid_column_raises(self, generator) -> None:
        intent = StructuredIntent(
            filters=[ColumnFilter("papers", "nonexistent_col", FilterOperator.EQ, 1)]
        )
        plan = _make_plan(intent)
        with pytest.raises(SQLGenerationError):
            generator.generate(plan)


class TestSQLValidator:
    def test_valid_select_passes(self, validator) -> None:
        validator.validate("SELECT paper_id, title FROM papers WHERE year >= :1")

    def test_empty_raises(self, validator) -> None:
        with pytest.raises(SQLValidationError):
            validator.validate("")

    def test_drop_table_raises(self, validator) -> None:
        with pytest.raises(SQLValidationError):
            validator.validate("DROP TABLE papers")

    def test_delete_raises(self, validator) -> None:
        with pytest.raises(SQLValidationError):
            validator.validate("DELETE FROM papers WHERE paper_id = 1")

    def test_insert_raises(self, validator) -> None:
        with pytest.raises(SQLValidationError):
            validator.validate("INSERT INTO papers (title) VALUES ('x')")

    def test_multiple_statements_raises(self, validator) -> None:
        with pytest.raises(SQLValidationError):
            validator.validate("SELECT * FROM papers; DROP TABLE papers")

    def test_sql_injection_comment_raises(self, validator) -> None:
        with pytest.raises(SQLValidationError):
            validator.validate("SELECT * FROM papers -- injected")

    def test_unbalanced_parens_raises(self, validator) -> None:
        with pytest.raises(SQLValidationError):
            validator.validate("SELECT * FROM papers WHERE (year > 2020")
