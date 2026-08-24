"""Oracle connection pool.

Provides a single OracleConnectionPool instance that is shared across the
whole application lifetime. The pool is created lazily on first use (not at
import time) so that test suites that set APP_ENV=test never attempt to open
a real database connection.

Usage:
    from app.database.connection import get_pool

    with get_pool().get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM dual")
        row = cursor.fetchone()
"""
from __future__ import annotations

import contextlib
from contextlib import contextmanager
from typing import Any, Generator

from app.common.exceptions import RepositoryError
from app.common.logging import get_logger
from app.config import get_settings

logger = get_logger("database.connection")

# Module-level singleton; populated by _init_pool() on first call.
_pool: Any = None


def _init_pool() -> Any:
    """Create and return the oracledb connection pool. Never called in test mode."""
    import oracledb  # noqa: PLC0415 – deferred so tests without the driver still work

    settings = get_settings()

    kwargs: dict[str, Any] = dict(
        user=settings.oracle_user,
        password=settings.oracle_password,
        dsn=settings.oracle_dsn,
        min=settings.oracle_pool_min,
        max=settings.oracle_pool_max,
        increment=settings.oracle_pool_increment,
    )

    if settings.oracle_wallet_location:
        kwargs["wallet_location"] = settings.oracle_wallet_location
        kwargs["wallet_password"] = ""

    logger.info(
        "Creating Oracle connection pool: dsn=%s min=%d max=%d",
        settings.oracle_dsn,
        settings.oracle_pool_min,
        settings.oracle_pool_max,
    )

    try:
        pool = oracledb.create_pool(**kwargs)
        logger.info("Oracle connection pool created.")
        return pool
    except Exception as exc:
        raise RepositoryError(
            f"Failed to create Oracle connection pool: {exc}"
        ) from exc


class OracleConnectionPool:
    """Thin wrapper around the oracledb pool that provides a context-manager
    interface and a health-check helper."""

    def __init__(self) -> None:
        self._pool: Any = None

    def _ensure_pool(self) -> Any:
        if self._pool is None:
            self._pool = _init_pool()
        return self._pool

    @contextmanager
    def get_connection(self) -> Generator[Any, None, None]:
        pool = self._ensure_pool()
        conn = pool.acquire()
        try:
            yield conn
            conn.commit()
        except Exception:
            with contextlib.suppress(Exception):
                conn.rollback()
            raise
        finally:
            pool.release(conn)

    def health_check(self) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM dual")
                return cursor.fetchone()[0] == 1
        except Exception:
            return False

    def close(self) -> None:
        if self._pool is not None:
            with contextlib.suppress(Exception):
                self._pool.close()
            self._pool = None
            logger.info("Oracle connection pool closed.")


# Module-level singleton used via dependency injection
_connection_pool: OracleConnectionPool | None = None


def get_pool() -> OracleConnectionPool:
    """Return the process-wide pool singleton. Safe to call from any thread."""
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = OracleConnectionPool()
    return _connection_pool
