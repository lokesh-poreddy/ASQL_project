"""Structured logging.

get_logger() gives every module a logger namespaced under "nexus_sql."
so log level and format are configured in exactly one place
(configure_logging(), called once from app.main on startup).

Credentials are never logged: _RedactingFilter enforces this at the
handler level as a defense-in-depth backstop.
"""
from __future__ import annotations

import logging
import sys

_CONFIGURED = False

FORBIDDEN_LOG_FIELDS = {
    "password",
    "oracle_password",
    "db_password",
    "secret",
    "api_key",
    "token",
}


class _RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        for field in FORBIDDEN_LOG_FIELDS:
            if hasattr(record, field):
                setattr(record, field, "***REDACTED***")
        # Also scan the formatted message for accidental password leaks
        msg = record.getMessage().lower()
        for field in FORBIDDEN_LOG_FIELDS:
            if field in msg:
                record.msg = "[REDACTED — possible credential in log message]"
                record.args = ()
                break
        return True


def configure_logging(level: str = "INFO") -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    root = logging.getLogger("nexus_sql")
    root.setLevel(level.upper())
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )
    handler.addFilter(_RedactingFilter())
    root.addHandler(handler)
    root.propagate = False
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a logger under the nexus_sql namespace."""
    if not _CONFIGURED:
        configure_logging()
    return logging.getLogger(f"nexus_sql.{name}")
