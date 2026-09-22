"""Shared Pydantic pieces reused across response models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TimestampedRead(ORMModel):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class BandRead(BaseModel):
    """A named severity tier resolved from a score (§7.2)."""

    name: str
    color: str
    index: int


class AssuranceRead(BaseModel):
    """Whether a risk's residual score is backed by working controls (§7.6)."""

    supporting_count: int
    implemented_count: int
    partial_count: int
    not_implemented_count: int = 0
    not_applicable_count: int = 0
    weakest_status: str | None = None
    claims_improvement: bool = False
    flag: str | None = Field(
        default=None, description="'unsupported_residual' when the reduction is unearned."
    )
    message: str | None = None


class ControlSummary(BaseModel):
    """Compact control reference embedded in risk / traceability payloads."""

    id: uuid.UUID
    ref: str
    name: str
    status: str


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int


class MessageResponse(BaseModel):
    message: str
    detail: dict[str, Any] | None = None
