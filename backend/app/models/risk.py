"""The risk register and the risk-to-control mitigation join.

Scores and bands are deliberately *not* stored: they are derived in
``services.scoring`` from the workspace's ``ScoringConfig`` so that changing the
scoring method or bands in Settings re-derives everything on next read (§6, §12).
"""

from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.enums import RiskStatus, RiskTreatment


def _scale_check(column: str) -> CheckConstraint:
    return CheckConstraint(f"{column} >= 1 AND {column} <= 10", name=f"ck_risk_{column}_scale")


class Risk(Base):
    __tablename__ = "risks"
    __table_args__ = (
        UniqueConstraint("workspace_id", "ref", name="uq_risk_workspace_ref"),
        _scale_check("inherent_likelihood"),
        _scale_check("inherent_impact"),
        _scale_check("residual_likelihood"),
        _scale_check("residual_impact"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    ref: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    category: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    owner: Mapped[str] = mapped_column(String(255), default="", nullable=False)

    inherent_likelihood: Mapped[int] = mapped_column(default=3, nullable=False)
    inherent_impact: Mapped[int] = mapped_column(default=3, nullable=False)
    residual_likelihood: Mapped[int] = mapped_column(default=3, nullable=False)
    residual_impact: Mapped[int] = mapped_column(default=3, nullable=False)

    treatment: Mapped[str] = mapped_column(
        String(32), default=RiskTreatment.MITIGATE.value, nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), default=RiskStatus.OPEN.value, nullable=False)

    control_mappings: Mapped[list[RiskControlMapping]] = relationship(
        back_populates="risk", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Risk {self.ref}>"


class RiskControlMapping(Base):
    __tablename__ = "risk_control_mappings"
    __table_args__ = (UniqueConstraint("risk_id", "control_id", name="uq_risk_control"),)

    risk_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("risks.id", ondelete="CASCADE"), nullable=False
    )
    control_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("controls.id", ondelete="CASCADE"), nullable=False
    )

    risk: Mapped[Risk] = relationship(back_populates="control_mappings")
    control: Mapped[Control] = relationship(back_populates="risk_mappings")  # noqa: F821
