"""§7.1–7.2, §7.6 — risk scoring, band lookup and the "unearned residual" integrity check.

Everything here is a pure function over ``(config, data)`` so that a change in
Settings re-derives every number on the next read rather than requiring a backfill.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from app.models.enums import STATUS_STRENGTH, UNEARNED_STATUSES, ControlStatus, ScoreMethod
from app.models.scoring import (
    DEFAULT_IMPACT_LABELS,
    DEFAULT_LIKELIHOOD_LABELS,
    DEFAULT_REMEDIATION_WEIGHTS,
    DEFAULT_RISK_BANDS,
    DEFAULT_WEIGHTS,
)

UNSUPPORTED_RESIDUAL = "unsupported_residual"


@dataclass(frozen=True)
class Band:
    name: str
    color: str
    index: int

    def as_dict(self) -> dict[str, Any]:
        return {"name": self.name, "color": self.color, "index": self.index}


UNBANDED = Band(name="Unbanded", color="#94a3b8", index=-1)


@dataclass(frozen=True)
class ScoringContext:
    """Immutable snapshot of a workspace's scoring configuration."""

    matrix_size: int = 5
    score_method: str = ScoreMethod.MULTIPLY.value
    weights: dict[str, float] = None  # type: ignore[assignment]
    likelihood_labels: dict[str, str] = None  # type: ignore[assignment]
    impact_labels: dict[str, str] = None  # type: ignore[assignment]
    risk_bands: list[dict[str, Any]] = None  # type: ignore[assignment]
    remediation_weights: dict[str, float] = None  # type: ignore[assignment]
    evidence_stale_after_days: int = 365

    def __post_init__(self) -> None:
        # dataclass(frozen=True) still allows object.__setattr__ for defaulting.
        if self.weights is None:
            object.__setattr__(self, "weights", dict(DEFAULT_WEIGHTS))
        if self.likelihood_labels is None:
            object.__setattr__(self, "likelihood_labels", dict(DEFAULT_LIKELIHOOD_LABELS))
        if self.impact_labels is None:
            object.__setattr__(self, "impact_labels", dict(DEFAULT_IMPACT_LABELS))
        if self.risk_bands is None:
            object.__setattr__(self, "risk_bands", [dict(b) for b in DEFAULT_RISK_BANDS])
        if self.remediation_weights is None:
            object.__setattr__(self, "remediation_weights", dict(DEFAULT_REMEDIATION_WEIGHTS))

    @classmethod
    def from_model(cls, config: Any | None) -> ScoringContext:
        """Build a context from a ``ScoringConfig`` row (or defaults when absent)."""
        if config is None:
            return cls()
        return cls(
            matrix_size=config.matrix_size or 5,
            score_method=config.score_method or ScoreMethod.MULTIPLY.value,
            weights=dict(config.weights or DEFAULT_WEIGHTS),
            likelihood_labels=dict(config.likelihood_labels or DEFAULT_LIKELIHOOD_LABELS),
            impact_labels=dict(config.impact_labels or DEFAULT_IMPACT_LABELS),
            risk_bands=[dict(b) for b in (config.risk_bands or DEFAULT_RISK_BANDS)],
            remediation_weights=dict(config.remediation_weights or DEFAULT_REMEDIATION_WEIGHTS),
            evidence_stale_after_days=config.evidence_stale_after_days or 365,
        )

    # -- label helpers used by the UI and by Excel export ------------------
    def likelihood_label(self, value: int) -> str:
        return self.likelihood_labels.get(str(value), str(value))

    def impact_label(self, value: int) -> str:
        return self.impact_labels.get(str(value), str(value))

    @property
    def min_possible_score(self) -> float:
        return score(1, 1, self)

    @property
    def max_possible_score(self) -> float:
        return score(self.matrix_size, self.matrix_size, self)


# ---------------------------------------------------------------------------
# §7.1 Risk score
# ---------------------------------------------------------------------------
def score(likelihood: int, impact: int, ctx: ScoringContext) -> float:
    """Combine the two axes into a single score using the configured method."""
    likelihood = int(likelihood)
    impact = int(impact)
    if ctx.score_method == ScoreMethod.ADD:
        return float(likelihood + impact)
    if ctx.score_method == ScoreMethod.WEIGHTED:
        w_l = float(ctx.weights.get("wL", 1.0))
        w_i = float(ctx.weights.get("wI", 1.0))
        return round(w_l * likelihood + w_i * impact, 2)
    # default: multiply
    return float(likelihood * impact)


# ---------------------------------------------------------------------------
# §7.2 Risk band
# ---------------------------------------------------------------------------
def band_for(value: float, ctx: ScoringContext) -> Band:
    """Return the band whose inclusive ``[min, max]`` window contains ``value``."""
    for index, entry in enumerate(ctx.risk_bands):
        low = float(entry.get("min", 0))
        high = float(entry.get("max", 0))
        if low <= value <= high:
            return Band(
                name=str(entry.get("name", "Unnamed")),
                color=str(entry.get("color", "#94a3b8")),
                index=index,
            )
    # Out of range (e.g. bands not updated after a method change) — never raise,
    # the UI shows this as an explicit "Unbanded" chip.
    return UNBANDED


def score_and_band(likelihood: int, impact: int, ctx: ScoringContext) -> tuple[float, Band]:
    value = score(likelihood, impact, ctx)
    return value, band_for(value, ctx)


def risk_scores(risk: Any, ctx: ScoringContext) -> dict[str, Any]:
    """Inherent and residual score/band for one risk, plus the delta between them."""
    inherent, inherent_band = score_and_band(risk.inherent_likelihood, risk.inherent_impact, ctx)
    residual, residual_band = score_and_band(risk.residual_likelihood, risk.residual_impact, ctx)
    return {
        "inherent_score": inherent,
        "inherent_band": inherent_band.as_dict(),
        "residual_score": residual,
        "residual_band": residual_band.as_dict(),
        "score_reduction": round(inherent - residual, 2),
    }


# ---------------------------------------------------------------------------
# §7.6 "Unearned residual" flag — the integrity check
# ---------------------------------------------------------------------------
def assurance(risk: Any, supporting_controls: Iterable[Any], ctx: ScoringContext) -> dict[str, Any]:
    """Judge whether a risk's residual score is actually backed by working controls.

    A residual score that sits in a friendlier band than the inherent score is a
    claim: "our controls bought this improvement". If nothing is mapped, or every
    mapped control is partial / not implemented / not applicable, the claim is
    flagged ``unsupported_residual`` so the UI can say so out loud (§7.6).
    """
    controls = list(supporting_controls)
    statuses = [str(c.status) for c in controls]

    implemented_count = statuses.count(ControlStatus.IMPLEMENTED.value)
    partial_count = statuses.count(ControlStatus.PARTIAL.value)
    not_implemented_count = statuses.count(ControlStatus.NOT_IMPLEMENTED.value)
    not_applicable_count = statuses.count(ControlStatus.NOT_APPLICABLE.value)

    weakest_status: str | None = None
    if statuses:
        weakest_status = min(statuses, key=lambda s: STATUS_STRENGTH.get(s, 0))

    inherent_band = band_for(score(risk.inherent_likelihood, risk.inherent_impact, ctx), ctx)
    residual_band = band_for(score(risk.residual_likelihood, risk.residual_impact, ctx), ctx)
    # Lower index == less severe band, so a smaller residual index is an improvement.
    claims_improvement = (
        residual_band.index >= 0
        and inherent_band.index >= 0
        and residual_band.index < inherent_band.index
    )

    nothing_earned = not controls or all(s in UNEARNED_STATUSES for s in statuses)
    flag = UNSUPPORTED_RESIDUAL if (claims_improvement and nothing_earned) else None

    return {
        "supporting_count": len(controls),
        "implemented_count": implemented_count,
        "partial_count": partial_count,
        "not_implemented_count": not_implemented_count,
        "not_applicable_count": not_applicable_count,
        "weakest_status": weakest_status,
        "claims_improvement": claims_improvement,
        "flag": flag,
        "message": (
            "Residual risk is scored lower than inherent risk, but no fully implemented "
            "control supports that reduction."
            if flag
            else None
        ),
    }


# ---------------------------------------------------------------------------
# Settings validation (§12) — bands must be contiguous and span the score range
# ---------------------------------------------------------------------------
def validate_bands(bands: list[dict[str, Any]], ctx: ScoringContext) -> list[str]:
    """Return a list of human-readable problems; empty list means valid."""
    problems: list[str] = []
    if not bands:
        return ["At least one risk band is required."]

    ordered = sorted(bands, key=lambda b: float(b.get("min", 0)))
    for entry in ordered:
        if float(entry.get("min", 0)) > float(entry.get("max", 0)):
            problems.append(
                f"Band '{entry.get('name', '?')}' has a minimum greater than its maximum."
            )

    for previous, nxt in zip(ordered, ordered[1:], strict=False):
        prev_max = float(previous.get("max", 0))
        next_min = float(nxt.get("min", 0))
        if next_min > prev_max + 1:
            problems.append(
                f"Gap between '{previous.get('name')}' (max {prev_max:g}) and "
                f"'{nxt.get('name')}' (min {next_min:g}) — scores in between have no band."
            )
        elif next_min <= prev_max:
            problems.append(
                f"'{previous.get('name')}' and '{nxt.get('name')}' overlap at {next_min:g}."
            )

    lowest = float(ordered[0].get("min", 0))
    highest = float(ordered[-1].get("max", 0))
    if lowest > ctx.min_possible_score:
        problems.append(
            f"Lowest band starts at {lowest:g} but the minimum possible score is "
            f"{ctx.min_possible_score:g}."
        )
    if highest < ctx.max_possible_score:
        problems.append(
            f"Highest band ends at {highest:g} but the maximum possible score is "
            f"{ctx.max_possible_score:g}."
        )
    return problems
