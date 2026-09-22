"""§18 — unit tests for the scoring service (§7.1, §7.2, §7.6, §12).

These are pure-function tests: no database, no HTTP. Lightweight stand-in objects
provide only the attributes the functions read.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.models.enums import ControlStatus, ScoreMethod
from app.models.scoring import DEFAULT_RISK_BANDS
from app.services.scoring import (
    UNSUPPORTED_RESIDUAL,
    ScoringContext,
    assurance,
    band_for,
    score,
    score_and_band,
    validate_bands,
)


@dataclass
class FakeRisk:
    inherent_likelihood: int
    inherent_impact: int
    residual_likelihood: int
    residual_impact: int


@dataclass
class FakeControl:
    status: str


DEFAULT = ScoringContext()  # matrix 5, multiply, default bands


# ---------------------------------------------------------------------------
# §7.1 score
# ---------------------------------------------------------------------------
def test_score_multiply_is_the_default():
    assert DEFAULT.score_method == ScoreMethod.MULTIPLY.value
    assert score(4, 5, DEFAULT) == 20.0
    assert score(1, 1, DEFAULT) == 1.0
    assert score(5, 5, DEFAULT) == 25.0


def test_score_add():
    ctx = ScoringContext(score_method=ScoreMethod.ADD.value)
    assert score(4, 5, ctx) == 9.0
    assert score(1, 1, ctx) == 2.0


def test_score_weighted_rounds_to_two_dp():
    ctx = ScoringContext(score_method=ScoreMethod.WEIGHTED.value, weights={"wL": 2.0, "wI": 0.5})
    assert score(4, 5, ctx) == 10.5  # 2*4 + 0.5*5
    equal = ScoringContext(score_method=ScoreMethod.WEIGHTED.value, weights={"wL": 1.0, "wI": 1.0})
    assert score(4, 5, equal) == 9.0


def test_min_and_max_possible_scores_track_the_method():
    assert DEFAULT.min_possible_score == 1.0
    assert DEFAULT.max_possible_score == 25.0
    add = ScoringContext(score_method=ScoreMethod.ADD.value)
    assert add.min_possible_score == 2.0
    assert add.max_possible_score == 10.0


# ---------------------------------------------------------------------------
# §7.2 band lookup at the inclusive boundaries
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "value,expected_name,expected_index",
    [
        (1, "Low", 0),
        (4, "Low", 0),
        (5, "Medium", 1),
        (9, "Medium", 1),
        (10, "High", 2),
        (15, "High", 2),
        (16, "Critical", 3),
        (25, "Critical", 3),
    ],
)
def test_band_boundaries(value, expected_name, expected_index):
    band = band_for(value, DEFAULT)
    assert band.name == expected_name
    assert band.index == expected_index


@pytest.mark.parametrize("value", [0, 0.5, 26, 100])
def test_out_of_range_scores_are_unbanded(value):
    band = band_for(value, DEFAULT)
    assert band.index == -1
    assert band.name == "Unbanded"


def test_score_and_band_together():
    value, band = score_and_band(5, 5, DEFAULT)
    assert value == 25.0
    assert band.name == "Critical"


# ---------------------------------------------------------------------------
# §7.6 unearned-residual flag
# ---------------------------------------------------------------------------
def test_flag_raised_when_improvement_is_claimed_but_nothing_is_implemented():
    # inherent 20 (Critical), residual 10 (High) => claims improvement.
    risk = FakeRisk(4, 5, 2, 5)
    controls = [FakeControl(ControlStatus.PARTIAL.value)]
    result = assurance(risk, controls, DEFAULT)
    assert result["claims_improvement"] is True
    assert result["flag"] == UNSUPPORTED_RESIDUAL
    assert result["message"]


def test_flag_not_raised_when_a_control_is_implemented():
    risk = FakeRisk(4, 5, 2, 5)
    controls = [
        FakeControl(ControlStatus.IMPLEMENTED.value),
        FakeControl(ControlStatus.PARTIAL.value),
    ]
    result = assurance(risk, controls, DEFAULT)
    assert result["claims_improvement"] is True
    assert result["flag"] is None


def test_flag_not_raised_when_no_improvement_is_claimed():
    # Same band inherent and residual => no claim, so no flag even with zero controls.
    risk = FakeRisk(2, 2, 2, 2)
    result = assurance(risk, [], DEFAULT)
    assert result["claims_improvement"] is False
    assert result["flag"] is None


def test_flag_raised_when_improvement_claimed_with_no_controls_at_all():
    risk = FakeRisk(4, 5, 1, 1)
    result = assurance(risk, [], DEFAULT)
    assert result["flag"] == UNSUPPORTED_RESIDUAL


# ---------------------------------------------------------------------------
# §12 band validation
# ---------------------------------------------------------------------------
def test_default_bands_are_valid():
    bands = [dict(b) for b in DEFAULT_RISK_BANDS]
    assert validate_bands(bands, DEFAULT) == []


def test_empty_bands_are_invalid():
    problems = validate_bands([], DEFAULT)
    assert problems == ["At least one risk band is required."]


def test_gap_between_bands_is_reported():
    bands = [
        {"name": "A", "min": 1, "max": 4, "color": "#000"},
        {"name": "B", "min": 10, "max": 25, "color": "#000"},  # leaves 5..9 uncovered
    ]
    problems = validate_bands(bands, DEFAULT)
    assert any("Gap" in p for p in problems)


def test_bands_must_span_the_whole_range():
    bands = [{"name": "Only", "min": 1, "max": 10, "color": "#000"}]  # stops short of 25
    problems = validate_bands(bands, DEFAULT)
    assert any("maximum possible score" in p for p in problems)
