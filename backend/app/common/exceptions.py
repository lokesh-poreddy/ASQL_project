"""Shared exception hierarchy.

Every module raises one of these instead of letting a raw driver exception
(oracledb.DatabaseError, KeyError, etc.) leak upward unannotated.
"""
from __future__ import annotations


class NexusSQLError(Exception):
    """Base class for every domain-level error raised by this application."""


class ConfigurationError(NexusSQLError):
    """Raised when required configuration is missing or inconsistent."""


class SchemaValidationError(NexusSQLError):
    """A generated or user-influenced query referenced an identifier that
    does not exist in the introspected database schema."""


class AmbiguityUnresolvedError(NexusSQLError):
    """Raised internally when an ambiguity cannot be auto-resolved and must
    surface as a clarification question rather than proceed to planning."""


class QueryPlanningError(NexusSQLError):
    """The query planner could not classify or route a request."""


class SQLGenerationError(NexusSQLError):
    """The SQL generator could not produce a query for the given intent."""


class SQLValidationError(NexusSQLError):
    """Generated SQL failed validation before execution."""

    def __init__(self, message: str, errors: list[str] | None = None) -> None:
        super().__init__(message)
        self.errors = errors or [message]


class SQLExecutionError(NexusSQLError):
    """A parameterized SQL statement failed at the database."""

    def __init__(
        self,
        message: str,
        *,
        oracle_error_code: str | None = None,
        sql_text: str | None = None,
    ) -> None:
        super().__init__(message)
        self.oracle_error_code = oracle_error_code
        self.sql_text = sql_text


class RecoveryExhaustedError(NexusSQLError):
    """The error-recovery loop reached MAX_RECOVERY_ATTEMPTS without success."""


class EmbeddingProviderError(NexusSQLError):
    """The configured embedding provider could not embed the given text."""


class VectorSearchError(NexusSQLError):
    """Vector index search failed (Oracle or in-memory backend)."""


class OptimizationError(NexusSQLError):
    """The resource optimizer could not produce a feasible configuration."""


class RepositoryError(NexusSQLError):
    """A repository operation failed. Wraps the underlying driver error;
    never used to silently swallow one."""
