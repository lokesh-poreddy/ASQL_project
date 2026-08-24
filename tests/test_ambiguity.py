"""Tests: ambiguity detector and resolver."""
from __future__ import annotations

import os
os.environ["APP_ENV"] = "test"

import pytest
from app.ambiguity.detector import AmbiguityDetector
from app.ambiguity.models import AmbiguityResolution, AmbiguityType
from app.ambiguity.resolver import AmbiguityResolver
from app.common.exceptions import AmbiguityUnresolvedError


@pytest.fixture
def detector() -> AmbiguityDetector:
    return AmbiguityDetector()


@pytest.fixture
def resolver() -> AmbiguityResolver:
    return AmbiguityResolver()


class TestAmbiguityDetector:
    def test_clear_query_with_year(self, detector) -> None:
        r = detector.detect("Find papers from 2022 about transformers")
        assert not r.ambiguous
        assert r.ambiguity_type == AmbiguityType.NONE

    def test_vague_time_triggers_ask_user(self, detector) -> None:
        r = detector.detect("Find recent papers about NLP")
        assert r.ambiguous
        assert r.ambiguity_type == AmbiguityType.VAGUE_TIME
        assert r.resolution == AmbiguityResolution.ASK_USER

    def test_vague_metric_triggers_ask_user(self, detector) -> None:
        r = detector.detect("Find the most popular papers")
        assert r.ambiguous
        assert r.ambiguity_type == AmbiguityType.VAGUE_METRIC
        assert r.resolution == AmbiguityResolution.ASK_USER

    def test_vague_metric_with_explicit_metric_is_clear(self, detector) -> None:
        r = detector.detect("Find the top papers by citation count")
        # "citation" is an explicit metric → CLEAR
        assert not r.ambiguous

    def test_unanswerable_future_query(self, detector) -> None:
        r = detector.detect("Which papers will be published next year?")
        assert r.ambiguous
        assert r.ambiguity_type == AmbiguityType.UNANSWERABLE_QUERY
        assert r.resolution == AmbiguityResolution.UNANSWERABLE

    def test_incomplete_followup_without_context(self, detector) -> None:
        r = detector.detect("Also filter by year", conversation_context="")
        assert r.ambiguous
        assert r.ambiguity_type == AmbiguityType.INCOMPLETE_FOLLOWUP

    def test_incomplete_followup_with_context_is_clear(self, detector) -> None:
        r = detector.detect(
            "Also filter by year",
            conversation_context="Turn 1: Find papers about NLP from 2022",
        )
        assert not r.ambiguous

    def test_vague_time_with_year_is_clear(self, detector) -> None:
        r = detector.detect("Find recent papers published in 2024")
        assert not r.ambiguous

    def test_options_provided_for_vague_time(self, detector) -> None:
        r = detector.detect("Find modern papers about machine learning")
        if r.ambiguous and r.ambiguity_type == AmbiguityType.VAGUE_TIME:
            assert r.options is not None
            assert len(r.options) >= 2


class TestAmbiguityResolver:
    def test_clear_does_not_raise(self, detector, resolver) -> None:
        r = detector.detect("Find papers from 2023")
        resolver.resolve(r)  # should not raise

    def test_ask_user_raises(self, detector, resolver) -> None:
        r = detector.detect("Find recent papers")
        with pytest.raises(AmbiguityUnresolvedError):
            resolver.resolve(r)

    def test_unanswerable_raises(self, detector, resolver) -> None:
        r = detector.detect("Which papers will be cited most next year?")
        with pytest.raises(AmbiguityUnresolvedError):
            resolver.resolve(r)

    def test_format_clarification_has_options(self, detector, resolver) -> None:
        r = detector.detect("Find recent papers about databases")
        payload = resolver.format_clarification(r)
        assert payload["status"] == "clarification_required"
        assert "ambiguity_type" in payload
