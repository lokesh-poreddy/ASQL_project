"""Known Oracle error codes and their classification.

This is NOT an exhaustive Oracle error reference — it covers only the
errors that can realistically be triggered by NL-to-SQL generated queries
and that have known, automatable repair strategies.

Source for ORA codes: Oracle Database Error Help, docs.oracle.com/error-help
"""
from __future__ import annotations

from enum import Enum


class OracleErrorCategory(str, Enum):
    INVALID_IDENTIFIER   = "INVALID_IDENTIFIER"    # ORA-00904
    TABLE_NOT_FOUND      = "TABLE_NOT_FOUND"        # ORA-00942
    INVALID_NUMBER       = "INVALID_NUMBER"         # ORA-01722
    VALUE_TOO_LARGE      = "VALUE_TOO_LARGE"        # ORA-01401 / ORA-12899
    MISSING_EXPRESSION   = "MISSING_EXPRESSION"     # ORA-00936
    NOT_ENOUGH_VALUES    = "NOT_ENOUGH_VALUES"       # ORA-00913
    TOO_MANY_VALUES      = "TOO_MANY_VALUES"         # ORA-00913
    COLUMN_AMBIGUOUS     = "COLUMN_AMBIGUOUS"       # ORA-00918
    UNIQUE_CONSTRAINT    = "UNIQUE_CONSTRAINT"      # ORA-00001
    NO_DATA_FOUND        = "NO_DATA_FOUND"           # ORA-01403
    CONNECTION_LOST      = "CONNECTION_LOST"         # ORA-03113 / ORA-03114
    VECTOR_NOT_SUPPORTED = "VECTOR_NOT_SUPPORTED"   # ORA-62570 or similar
    UNKNOWN              = "UNKNOWN"


# ORA-NNNNN → OracleErrorCategory
ORACLE_ERROR_MAP: dict[str, OracleErrorCategory] = {
    "ORA-00904": OracleErrorCategory.INVALID_IDENTIFIER,
    "ORA-00942": OracleErrorCategory.TABLE_NOT_FOUND,
    "ORA-01722": OracleErrorCategory.INVALID_NUMBER,
    "ORA-01401": OracleErrorCategory.VALUE_TOO_LARGE,
    "ORA-12899": OracleErrorCategory.VALUE_TOO_LARGE,
    "ORA-00936": OracleErrorCategory.MISSING_EXPRESSION,
    "ORA-00913": OracleErrorCategory.NOT_ENOUGH_VALUES,
    "ORA-00918": OracleErrorCategory.COLUMN_AMBIGUOUS,
    "ORA-00001": OracleErrorCategory.UNIQUE_CONSTRAINT,
    "ORA-01403": OracleErrorCategory.NO_DATA_FOUND,
    "ORA-03113": OracleErrorCategory.CONNECTION_LOST,
    "ORA-03114": OracleErrorCategory.CONNECTION_LOST,
}


def classify(oracle_code: str | None) -> OracleErrorCategory:
    if oracle_code is None:
        return OracleErrorCategory.UNKNOWN
    return ORACLE_ERROR_MAP.get(oracle_code, OracleErrorCategory.UNKNOWN)
