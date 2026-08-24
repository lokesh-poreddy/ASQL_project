"""SchemaManager: cached snapshot + convenience helpers.

The manager wraps whichever introspector is active (static for tests,
Oracle-backed for production) and caches the snapshot so the data
dictionary is queried at most once per process start.
"""
from __future__ import annotations

import threading
from functools import lru_cache

from app.common.logging import get_logger
from app.config import get_settings
from app.schema.introspector import (
    OracleSchemaIntrospector,
    SchemaIntrospectorPort,
    StaticSchemaIntrospector,
)
from app.schema.models import SchemaSnapshot, TableInfo

logger = get_logger("schema.manager")


class SchemaManager:
    """Thread-safe, lazily-loaded schema snapshot cache."""

    def __init__(self, introspector: SchemaIntrospectorPort) -> None:
        self._introspector = introspector
        self._snapshot: SchemaSnapshot | None = None
        self._lock = threading.Lock()

    def get_snapshot(self) -> SchemaSnapshot:
        """Return the cached snapshot, loading it on first call."""
        if self._snapshot is None:
            with self._lock:
                if self._snapshot is None:
                    logger.info(
                        "Loading schema snapshot via %s",
                        type(self._introspector).__name__,
                    )
                    self._snapshot = self._introspector.load_snapshot()
                    logger.info(
                        "Schema snapshot loaded: %d tables, %d areas, %d venues",
                        len(self._snapshot.tables),
                        len(self._snapshot.research_areas),
                        len(self._snapshot.venues),
                    )
        return self._snapshot

    def refresh(self) -> SchemaSnapshot:
        """Force a reload (call after DDL changes)."""
        with self._lock:
            self._snapshot = None
        return self.get_snapshot()

    # ── Convenience wrappers ──────────────────────────────────────────────────

    def table_exists(self, name: str) -> bool:
        return self.get_snapshot().has_table(name)

    def column_exists(self, table: str, column: str) -> bool:
        tbl = self.get_snapshot().get_table(table)
        if tbl is None:
            return False
        return tbl.has_column(column)

    def get_table(self, name: str) -> TableInfo | None:
        return self.get_snapshot().get_table(name)

    def get_join_path(
        self,
        from_table: str,
        to_table: str,
    ) -> list[tuple[str, str, str, str]] | None:
        """Return a list of (table_a, col_a, table_b, col_b) FK hops that
        connect from_table to to_table. Returns None if no path is found
        within depth=2 (enough for the current schema)."""
        snapshot = self.get_snapshot()

        # Direct FK from_table → to_table
        src = snapshot.get_table(from_table)
        if src is None:
            return None
        for col in src.columns:
            if col.is_foreign_key and col.references_table == to_table.lower():
                return [(from_table, col.name, to_table, col.references_column)]

        # Reverse: to_table → from_table
        dst = snapshot.get_table(to_table)
        if dst is None:
            return None
        for col in dst.columns:
            if col.is_foreign_key and col.references_table == from_table.lower():
                return [(to_table, col.name, from_table, col.references_column)]

        return None


@lru_cache(maxsize=1)
def get_schema_manager() -> SchemaManager:
    """Return the process-wide SchemaManager singleton."""
    settings = get_settings()

    if settings.use_oracle:
        from app.database.connection import get_pool
        introspector: SchemaIntrospectorPort = OracleSchemaIntrospector(get_pool())
    else:
        introspector = StaticSchemaIntrospector()

    return SchemaManager(introspector)
