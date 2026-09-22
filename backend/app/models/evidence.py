"""Evidence metadata. The files themselves live in the user's Google Drive (§3)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.enums import EvidenceSource, EvidenceStatus


class Evidence(Base):
    __tablename__ = "evidence"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    control_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("controls.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    source_type: Mapped[str] = mapped_column(
        String(32), default=EvidenceSource.DRIVE_FILE.value, nullable=False
    )

    drive_file_id: Mapped[str | None] = mapped_column(String(255), index=True)
    drive_file_name: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    web_view_link: Mapped[str | None] = mapped_column(String(1024))
    url: Mapped[str | None] = mapped_column(String(1024))

    collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(
        String(32), default=EvidenceStatus.CURRENT.value, nullable=False
    )

    #: Small, well-defined payload pulled out of an evidence workbook (§9.5).
    extracted_data: Mapped[dict | None] = mapped_column(JSON)
    extracted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    control: Mapped[Control] = relationship(back_populates="evidence")  # noqa: F821

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Evidence {self.title}>"
