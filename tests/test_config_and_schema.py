"""Tests: configuration and schema."""
from __future__ import annotations

import os

import pytest

os.environ["APP_ENV"] = "test"

from app.config import AppEnv, get_settings
from app.schema.introspector import StaticSchemaIntrospector
from app.schema.manager import SchemaManager


class TestSettings:
    def test_test_mode(self) -> None:
        settings = get_settings()
        assert settings.app_env == AppEnv.TEST

    def test_no_oracle_in_test_mode(self) -> None:
        settings = get_settings()
        assert not settings.use_oracle

    def test_is_test_mode(self) -> None:
        settings = get_settings()
        assert settings.is_test_mode

    def test_hybrid_alpha_default(self) -> None:
        settings = get_settings()
        assert 0.0 <= settings.hybrid_alpha <= 1.0


class TestStaticSchema:
    @pytest.fixture(autouse=True)
    def manager(self) -> SchemaManager:
        return SchemaManager(StaticSchemaIntrospector())

    def test_tables_present(self, manager) -> None:
        snap = manager.get_snapshot()
        assert "papers" in snap.tables
        assert "authors" in snap.tables
        assert "venues" in snap.tables

    def test_papers_has_expected_columns(self, manager) -> None:
        snap = manager.get_snapshot()
        papers = snap.get_table("papers")
        assert papers is not None
        assert papers.has_column("paper_id")
        assert papers.has_column("title")
        assert papers.has_column("year")
        assert papers.has_column("citation_count")

    def test_research_areas_loaded(self, manager) -> None:
        snap = manager.get_snapshot()
        assert len(snap.research_areas) >= 5

    def test_venues_loaded(self, manager) -> None:
        snap = manager.get_snapshot()
        assert len(snap.venues) >= 5

    def test_table_exists_case_insensitive(self, manager) -> None:
        snap = manager.get_snapshot()
        assert snap.has_table("PAPERS")
        assert snap.has_table("papers")

    def test_get_table_returns_none_for_unknown(self, manager) -> None:
        snap = manager.get_snapshot()
        assert snap.get_table("nonexistent_table_xyz") is None

    def test_snapshot_cached(self, manager) -> None:
        snap1 = manager.get_snapshot()
        snap2 = manager.get_snapshot()
        assert snap1 is snap2

    def test_12_tables_defined(self, manager) -> None:
        snap = manager.get_snapshot()
        assert len(snap.tables) == 12

    def test_paper_embeddings_has_vector_column(self, manager) -> None:
        snap = manager.get_snapshot()
        pe = snap.get_table("paper_embeddings")
        assert pe is not None
        assert pe.has_column("embedding_f32")
        assert pe.has_column("embedding_i8")

    def test_join_path_papers_to_venues(self, manager) -> None:
        path = manager.get_join_path("papers", "venues")
        assert path is not None
        assert len(path) == 1
