"""Framework and requirement schemas (§8.3)."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from app.schemas.common import TimestampedRead


class FrameworkRead(TimestampedRead):
    key: str
    name: str
    version: str
    description: str
    color: str
    sort_order: int
    requirement_count: int = 0


class RequirementRead(TimestampedRead):
    framework_id: uuid.UUID
    framework_key: str
    framework_name: str
    framework_color: str
    code: str
    title: str
    description: str
    category: str
    sort_order: int
    mapped_control_count: int = 0


class RequirementCreate(BaseModel):
    framework_id: uuid.UUID
    code: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=512)
    description: str = ""
    category: str = ""
    sort_order: int = 0


class RequirementUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=64)
    title: str | None = Field(default=None, min_length=1, max_length=512)
    description: str | None = None
    category: str | None = None
    sort_order: int | None = None
