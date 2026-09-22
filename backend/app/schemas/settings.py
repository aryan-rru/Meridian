"""Settings, import/export and derived-view schemas (§8.6, §8.8, §8.9, §12)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.models.enums import ScoreMethod


class RiskBandInput(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    min: float
    max: float
    color: str = Field(default="#94a3b8", max_length=16)


class ScoringConfigRead(BaseModel):
    matrix_size: int
    score_method: str
    weights: dict[str, float]
    likelihood_labels: dict[str, str]
    impact_labels: dict[str, str]
    risk_bands: list[dict[str, Any]]
    remediation_weights: dict[str, float]
    evidence_stale_after_days: int
    #: Score range implied by the current method/matrix size, for band validation in the UI.
    min_possible_score: float
    max_possible_score: float


class ScoringConfigUpdate(BaseModel):
    matrix_size: int | None = Field(default=None, ge=2, le=10)
    score_method: ScoreMethod | None = None
    weights: dict[str, float] | None = None
    likelihood_labels: dict[str, str] | None = None
    impact_labels: dict[str, str] | None = None
    risk_bands: list[RiskBandInput] | None = None
    remediation_weights: dict[str, float] | None = None
    evidence_stale_after_days: int | None = Field(default=None, ge=1, le=3650)

    @field_validator("likelihood_labels", "impact_labels")
    @classmethod
    def _keys_are_numeric(cls, value: dict[str, str] | None) -> dict[str, str] | None:
        if value is None:
            return value
        for key in value:
            if not str(key).isdigit():
                raise ValueError("Label keys must be the scale numbers, e.g. '1'...'5'.")
        return value


class ImportError_(BaseModel):
    sheet: str
    row: int | None = None
    message: str


class ImportSummaryRead(BaseModel):
    created: int
    updated: int
    skipped: int
    errors: list[ImportError_] = []
    sheets: dict[str, dict[str, int]] = {}


class DriveExportResult(BaseModel):
    file_id: str
    name: str
    web_view_link: str | None = None
    message: str


# ---------------------------------------------------------------------------
# Derived views. The matrix payloads are intentionally loose: their shape is a
# grid built by the service layer and documented in §7, and pinning every nested
# cell as a model would duplicate that structure without adding safety.
# ---------------------------------------------------------------------------
class CoverageTotals(BaseModel):
    covered: int
    partial: int
    gap: int
    total_requirements: int
    coverage_percent: float


class CoverageRead(BaseModel):
    frameworks: list[dict[str, Any]]
    totals: CoverageTotals


class GapsRead(BaseModel):
    items: list[dict[str, Any]]
    gap_count: int
    partial_count: int


class CrosswalkRead(BaseModel):
    column_groups: list[dict[str, Any]]
    rows: list[dict[str, Any]]
    summary: dict[str, Any]


class RemediationRead(BaseModel):
    items: list[dict[str, Any]]
    weights: dict[str, float]
    candidate_count: int


class HeatmapRead(BaseModel):
    basis: Literal["inherent", "residual"]
    matrix_size: int
    rows: list[dict[str, Any]]
    impact_labels: list[dict[str, Any]]
    likelihood_labels: list[dict[str, Any]]
    total_risks: int


class TraceabilityRead(BaseModel):
    risk: dict[str, Any]
    controls: list[dict[str, Any]]
    assurance: dict[str, Any]
    aggregate: dict[str, Any]


class DashboardRead(BaseModel):
    controls: dict[str, Any]
    coverage: dict[str, Any]
    gaps: dict[str, Any]
    risks: dict[str, Any]
    remediation: dict[str, Any]
    evidence: dict[str, Any]
    leverage: dict[str, Any]
