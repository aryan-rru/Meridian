"""Evidence and Drive schemas (§8.7)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import EvidenceSource
from app.schemas.common import TimestampedRead


class EvidenceRead(TimestampedRead):
    workspace_id: uuid.UUID
    control_id: uuid.UUID
    control_ref: str | None = None
    control_name: str | None = None
    title: str
    description: str
    source_type: str
    drive_file_id: str | None = None
    drive_file_name: str
    mime_type: str
    web_view_link: str | None = None
    url: str | None = None
    collected_at: datetime | None = None
    valid_until: datetime | None = None
    status: str
    extracted_data: dict[str, Any] | None = None
    extracted_at: datetime | None = None


class EvidenceLinkCreate(BaseModel):
    """Attach a Drive file the user picked with the Google Picker."""

    control_id: uuid.UUID
    drive_file_id: str | None = Field(
        default=None, description="Required unless source_type is 'url'."
    )
    title: str | None = None
    description: str = ""
    source_type: EvidenceSource = EvidenceSource.DRIVE_FILE
    url: str | None = None
    valid_until: datetime | None = None


class EvidenceUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    valid_until: datetime | None = None


class DriveFile(BaseModel):
    id: str
    name: str
    mimeType: str  # noqa: N815 - mirrors the Drive API field name
    webViewLink: str | None = None  # noqa: N815
    iconLink: str | None = None  # noqa: N815
    modifiedTime: str | None = None  # noqa: N815
    size: str | None = None  # noqa: N815


class DriveFileList(BaseModel):
    files: list[DriveFile]
    scope_limited: bool = Field(
        default=False,
        description="True when only drive.file was granted, so search sees app files only.",
    )


class ExtractionResult(BaseModel):
    evidence_id: uuid.UUID
    status: str
    extracted_at: datetime | None = None
    extracted_data: dict[str, Any] | None = None
    message: str
