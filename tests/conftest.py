"""Shared pytest fixtures for the NEXUS-SQL test suite.

All fixtures that touch settings force APP_ENV=test so no Oracle connection
is ever required. The StaticSchemaIntrospector is used throughout.
"""
from __future__ import annotations

import os
# Force test mode before anything imports app code
os.environ.setdefault("APP_ENV", "test")

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings, Settings
from app.schema.introspector import StaticSchemaIntrospector
from app.schema.manager import SchemaManager


@pytest.fixture(scope="session")
def settings() -> Settings:
    return get_settings()


@pytest.fixture(scope="session")
def schema_manager() -> SchemaManager:
    return SchemaManager(StaticSchemaIntrospector())


@pytest.fixture(scope="session")
def app_client() -> TestClient:
    from app.main import app
    return TestClient(app)
