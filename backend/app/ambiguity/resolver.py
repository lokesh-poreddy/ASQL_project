"""AmbiguityResolver: decides CLEAR / ASK_USER / UNANSWERABLE and formats
the clarification response that the API returns to the client."""
from __future__ import annotations

from app.ambiguity.models import AmbiguityResolution, AmbiguityResult
from app.common.exceptions import AmbiguityUnresolvedError
from app.common.logging import get_logger

logger = get_logger("ambiguity.resolver")


class AmbiguityResolver:

    def resolve(self, result: AmbiguityResult) -> None:
        """Raise AmbiguityUnresolvedError when the query cannot proceed.

        If CLEAR, returns normally so the caller continues to the planner.
        If ASK_USER or UNANSWERABLE, raises so the API layer can return
        the clarification message without executing any SQL.
        """
        if result.resolution == AmbiguityResolution.CLEAR:
            return

        logger.info(
            "Query blocked by ambiguity: type=%s resolution=%s",
            result.ambiguity_type.value,
            result.resolution.value,
        )
        raise AmbiguityUnresolvedError(result.message or "Ambiguous query.")

    def format_clarification(self, result: AmbiguityResult) -> dict:
        """Return the JSON-serialisable clarification payload."""
        payload: dict = {
            "status":         "clarification_required",
            "ambiguity_type": result.ambiguity_type.value,
            "message":        result.message,
        }
        if result.options:
            payload["options"] = result.options
        return payload
