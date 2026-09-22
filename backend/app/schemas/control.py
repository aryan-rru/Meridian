"""Control schemas (§8.4)."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from app.models.enums import ControlStatus, CoverageLevel
from app.schemas.common import TimestampedRead
from app.schemas.framework import RequirementRead


class ControlBase(BaseModel):
    name: str = Field(min_length=1, max_length=512)
    description: str = ""
    category: str = ""
    owner: str = ""
    status: ControlStatus = ControlStatus.NOT_IMPLEMENTED
    implementation_notes: str = ""


class ControlCreate(ControlBase):
    ref: str = Field(min_length=1, max_length=64, description="Unique within the workspace.")


class ControlUpdate(BaseModel):
    ref: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=512)
    description: str | None = None
    category: str | None = None
    owner: str | None = None
    status: ControlStatus | None = None
    implementation_notes: str | None = None


class ControlRead(TimestampedRead):
    workspace_id: uuid.UUID
    ref: str
    name: str
    description: str
    category: str
    owner: str
    status: str
    implementation_notes: str

    # Computed (§8.4) so the frontend never recomputes.
    requirements_satisfied_count: int = 0
    frameworks_touched: int = 0
    framework_breakdown: dict[str, int] = {}
    risks_count: int = 0
    evidence_count: int = 0


class MappedRequirement(RequirementRead):
    coverage_level: str


class ControlDetail(ControlRead):
    requirements: list[MappedRequirement] = []
    risks: list[dict] = []
    evidence: list[dict] = []


class RequirementMappingItem(BaseModel):
    requirement_id: uuid.UUID
    coverage_level: CoverageLevel = CoverageLevel.FULL


class RequirementMappingSet(BaseModel):
    """Body for ``PUT /api/controls/{id}/requirements`` — the full tick-box state."""

    items: list[RequirementMappingItem] = []
