"""The control library and the crosswalk join that maps controls to requirements."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.enums import ControlStatus, CoverageLevel


class Control(Base):
    __tablename__ = "controls"
    __table_args__ = (UniqueConstraint("workspace_id", "ref", name="uq_control_workspace_ref"),)

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    ref: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    category: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    owner: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default=ControlStatus.NOT_IMPLEMENTED.value, nullable=False
    )
    implementation_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)

    requirement_mappings: Mapped[list[ControlRequirementMapping]] = relationship(
        back_populates="control", cascade="all, delete-orphan"
    )
    risk_mappings: Mapped[list[RiskControlMapping]] = relationship(  # noqa: F821
        back_populates="control", cascade="all, delete-orphan"
    )
    evidence: Mapped[list[Evidence]] = relationship(  # noqa: F821
        back_populates="control", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Control {self.ref} {self.status}>"


class ControlRequirementMapping(Base):
    """One tick-box: "this control answers that requirement" (§7.4)."""

    __tablename__ = "control_requirement_mappings"
    __table_args__ = (
        UniqueConstraint("control_id", "requirement_id", name="uq_crosswalk_control_requirement"),
    )

    control_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("controls.id", ondelete="CASCADE"), nullable=False
    )
    requirement_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("requirements.id", ondelete="CASCADE"), nullable=False
    )
    coverage_level: Mapped[str] = mapped_column(
        String(32), default=CoverageLevel.FULL.value, nullable=False
    )

    control: Mapped[Control] = relationship(back_populates="requirement_mappings")
    requirement: Mapped[Requirement] = relationship(back_populates="control_mappings")  # noqa: F821
