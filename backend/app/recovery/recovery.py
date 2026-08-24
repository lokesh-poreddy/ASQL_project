"""Incremental error recovery engine.

Pipeline:
    SQL (attempt 1)
          │
     error? ──► classify ORA- code
                     │
              repair strategy
                     │
            corrected SQL (attempt 2)
                     │
             still error? ──► RecoveryExhaustedError
                     │
               SUCCESS → persist audit record

Every attempt (success or failure) is recorded in QUERY_EXECUTIONS so
we have ground-truth data for the recovery rate experiment.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

from app.common.exceptions import RecoveryExhaustedError, SQLExecutionError
from app.common.logging import get_logger
from app.config import get_settings
from app.recovery.oracle_errors import OracleErrorCategory, classify
from app.recovery.schema_repair import attempt_repair
from app.sql.executor import SQLExecutionResult
from app.sql.validator import SQLValidator

logger = get_logger("recovery.recovery")


@dataclass
class AttemptRecord:
    attempt_number: int
    sql_text: str
    status: str               # SUCCESS | FAILED
    error_code: str | None = None
    error_message: str | None = None
    error_category: str | None = None
    row_count: int | None = None
    execution_time_ms: float | None = None


@dataclass
class RecoveryResult:
    success: bool
    final_sql: str
    result: SQLExecutionResult | None
    attempts: list[AttemptRecord]
    total_elapsed_ms: float
    correction_count: int = 0

    @property
    def attempt_count(self) -> int:
        return len(self.attempts)


class ErrorRecoveryEngine:

    def __init__(self, executor, validator: SQLValidator) -> None:
        self._executor = executor
        self._validator = validator

    def execute_with_recovery(
        self,
        sql: str,
        parameters: dict[str, Any],
        history_id: int | None = None,
    ) -> RecoveryResult:
        max_attempts = get_settings().max_recovery_attempts
        current_sql = sql
        attempts: list[AttemptRecord] = []
        correction_count = 0
        started = time.perf_counter()

        for attempt_num in range(1, max_attempts + 1):
            record = AttemptRecord(
                attempt_number=attempt_num,
                sql_text=current_sql,
                status="FAILED",
            )

            try:
                # Validate before executing (catches obvious errors early)
                self._validator.validate(current_sql)
                result = self._executor.execute(current_sql, parameters)

                record.status = "SUCCESS"
                record.row_count = result.row_count
                record.execution_time_ms = result.elapsed_ms
                attempts.append(record)

                elapsed = (time.perf_counter() - started) * 1000
                logger.info(
                    "SQL succeeded on attempt %d: %d rows in %.1f ms",
                    attempt_num, result.row_count, result.elapsed_ms,
                )

                return RecoveryResult(
                    success=True,
                    final_sql=current_sql,
                    result=result,
                    attempts=attempts,
                    total_elapsed_ms=elapsed,
                    correction_count=correction_count,
                )

            except SQLExecutionError as exc:
                record.error_code    = exc.oracle_error_code
                record.error_message = str(exc)
                category = classify(exc.oracle_error_code)
                record.error_category = category.value
                attempts.append(record)

                logger.warning(
                    "SQL attempt %d failed: code=%s category=%s",
                    attempt_num, exc.oracle_error_code, category.value,
                )

                if attempt_num < max_attempts:
                    corrected = attempt_repair(current_sql, category, str(exc))
                    if corrected != current_sql:
                        logger.info(
                            "SQL repaired on attempt %d → attempting %d.",
                            attempt_num, attempt_num + 1,
                        )
                        current_sql = corrected
                        correction_count += 1
                    else:
                        logger.warning(
                            "No repair available for category=%s. "
                            "Stopping recovery after attempt %d.",
                            category.value, attempt_num,
                        )
                        break

            except Exception as exc:
                record.error_message = str(exc)[:500]
                attempts.append(record)
                logger.error("Unexpected error on attempt %d: %s", attempt_num, exc)
                break

        elapsed = (time.perf_counter() - started) * 1000
        raise RecoveryExhaustedError(
            f"SQL execution failed after {len(attempts)} attempt(s). "
            f"Last error: {attempts[-1].error_message}"
        )
