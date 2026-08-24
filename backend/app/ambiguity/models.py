"""Ambiguity domain models."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AmbiguityType(str, Enum):
    NONE                    = "NONE"
    VAGUE_TIME              = "VAGUE_TIME"
    VAGUE_METRIC            = "VAGUE_METRIC"
    MISSING_THRESHOLD       = "MISSING_THRESHOLD"
    UNKNOWN_COLUMN          = "UNKNOWN_COLUMN"
    UNKNOWN_VALUE           = "UNKNOWN_VALUE"
    MULTIPLE_POSSIBLE_COLUMNS = "MULTIPLE_POSSIBLE_COLUMNS"
    INCOMPLETE_FOLLOWUP     = "INCOMPLETE_FOLLOWUP"
    AMBIGUOUS_ENTITY        = "AMBIGUOUS_ENTITY"
    UNANSWERABLE_QUERY      = "UNANSWERABLE_QUERY"


class AmbiguityResolution(str, Enum):
    CLEAR          = "CLEAR"
    ASK_USER       = "ASK_USER"
    UNANSWERABLE   = "UNANSWERABLE"


@dataclass
class AmbiguityResult:
    ambiguous: bool
    ambiguity_type: AmbiguityType
    resolution: AmbiguityResolution
    message: str | None = None
    options: list[str] | None = None  # Suggested options to present to the user
