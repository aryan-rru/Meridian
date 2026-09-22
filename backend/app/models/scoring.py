"""Per-workspace scoring configuration — the knobs behind every derived number (§12)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import JSON, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.enums import ScoreMethod

DEFAULT_LIKELIHOOD_LABELS: dict[str, str] = {
    "1": "Rare",
    "2": "Unlikely",
    "3": "Possible",
    "4": "Likely",
    "5": "Almost Certain",
}

DEFAULT_IMPACT_LABELS: dict[str, str] = {
    "1": "Insignificant",
    "2": "Minor",
    "3": "Moderate",
    "4": "Major",
    "5": "Severe",
}

DEFAULT_RISK_BANDS: list[dict[str, Any]] = [
    {"name": "Low", "min": 1, "max": 4, "color": "#16a34a"},
    {"name": "Medium", "min": 5, "max": 9, "color": "#eab308"},
    {"name": "High", "min": 10, "max": 15, "color": "#f97316"},
    {"name": "Critical", "min": 16, "max": 25, "color": "#dc2626"},
]

DEFAULT_WEIGHTS: dict[str, float] = {"wL": 1.0, "wI": 1.0}
DEFAULT_REMEDIATION_WEIGHTS: dict[str, float] = {"W_RISK": 1.0, "W_REQ": 0.5}
DEFAULT_EVIDENCE_STALE_AFTER_DAYS = 365


class ScoringConfig(Base):
    __tablename__ = "scoring_config"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    matrix_size: Mapped[int] = mapped_column(default=5, nullable=False)
    score_method: Mapped[str] = mapped_column(
        String(32), default=ScoreMethod.MULTIPLY.value, nullable=False
    )
    weights: Mapped[dict] = mapped_column(JSON, default=lambda: dict(DEFAULT_WEIGHTS))
    likelihood_labels: Mapped[dict] = mapped_column(
        JSON, default=lambda: dict(DEFAULT_LIKELIHOOD_LABELS)
    )
    impact_labels: Mapped[dict] = mapped_column(JSON, default=lambda: dict(DEFAULT_IMPACT_LABELS))
    risk_bands: Mapped[list] = mapped_column(
        JSON, default=lambda: [dict(b) for b in DEFAULT_RISK_BANDS]
    )
    remediation_weights: Mapped[dict] = mapped_column(
        JSON, default=lambda: dict(DEFAULT_REMEDIATION_WEIGHTS)
    )
    evidence_stale_after_days: Mapped[int] = mapped_column(
        default=DEFAULT_EVIDENCE_STALE_AFTER_DAYS, nullable=False
    )
    #: Reserved for §7 status weighting extensions; kept so the shape matches the spec.
    status_weights: Mapped[dict] = mapped_column(JSON, default=dict)


def default_config_kwargs() -> dict[str, Any]:
    """Field values for a brand-new workspace's scoring config."""
    return {
        "matrix_size": 5,
        "score_method": ScoreMethod.MULTIPLY.value,
        "weights": dict(DEFAULT_WEIGHTS),
        "likelihood_labels": dict(DEFAULT_LIKELIHOOD_LABELS),
        "impact_labels": dict(DEFAULT_IMPACT_LABELS),
        "risk_bands": [dict(b) for b in DEFAULT_RISK_BANDS],
        "remediation_weights": dict(DEFAULT_REMEDIATION_WEIGHTS),
        "evidence_stale_after_days": DEFAULT_EVIDENCE_STALE_AFTER_DAYS,
        "status_weights": {},
    }
