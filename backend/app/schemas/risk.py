"""Risk schemas (§8.5)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import RiskStatus, RiskTreatment
from app.schemas.common import AssuranceRead, BandRead, ControlSummary

SCALE = Field(ge=1, le=10, description="Position on the configured 1–N scale.")


class RiskBase(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    description: str = ""
    category: str = ""
    owner: str = ""
    inherent_likelihood: int = SCALE
    inherent_impact: int = SCALE
    residual_likelihood: int = SCALE
    residual_impact: int = SCALE
    treatment: RiskTreatment = RiskTreatment.MITIGATE
    status: RiskStatus = RiskStatus.OPEN


class RiskCreate(RiskBase):
    ref: str = Field(min_length=1, max_length=64, description="Unique within the workspace.")


class RiskUpdate(BaseModel):
    ref: str | None = Field(default=None, min_length=1, max_length=64)
    title: str | None = Field(default=None, min_length=1, max_length=512)
    description: str | None = None
    category: str | None = None
    owner: str | None = None
    inherent_likelihood: int | None = Field(default=None, ge=1, le=10)
    inherent_impact: int | None = Field(default=None, ge=1, le=10)
    residual_likelihood: int | None = Field(default=None, ge=1, le=10)
    residual_impact: int | None = Field(default=None, ge=1, le=10)
    treatment: RiskTreatment | None = None
    status: RiskStatus | None = None


class RiskRead(BaseModel):
    id: uuid.UUID
    ref: str
    title: str
    description: str
    category: str
    owner: str
    treatment: str
    status: str

    inherent_likelihood: int
    inherent_impact: int
    residual_likelihood: int
    residual_impact: int
    inherent_likelihood_label: str
    inherent_impact_label: str
    residual_likelihood_label: str
    residual_impact_label: str

    inherent_score: float
    inherent_band: BandRead
    residual_score: float
    residual_band: BandRead
    score_reduction: float

    assurance: AssuranceRead
    controls: list[ControlSummary] = []
    control_count: int = 0

    created_at: datetime
    updated_at: datetime


class RiskControlSet(BaseModel):
    """Body for ``PUT /api/risks/{id}/controls``."""

    control_ids: list[uuid.UUID] = []
