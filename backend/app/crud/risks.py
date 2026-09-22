"""Risk persistence and the risk↔control mitigation mappings."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Control, Risk, RiskControlMapping
from app.schemas.risk import RiskControlSet, RiskCreate, RiskUpdate


def _conflict(ref: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=f"A risk with reference '{ref}' already exists in this workspace.",
    )


def get(db: Session, workspace_id: uuid.UUID, risk_id: uuid.UUID) -> Risk:
    risk = db.execute(
        select(Risk).where(Risk.id == risk_id, Risk.workspace_id == workspace_id)
    ).scalar_one_or_none()
    if risk is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Risk not found.")
    return risk


def list_risks(
    db: Session,
    workspace_id: uuid.UUID,
    status_filter: str | None = None,
    category: str | None = None,
    query: str | None = None,
) -> list[Risk]:
    stmt = select(Risk).where(Risk.workspace_id == workspace_id)
    if status_filter:
        stmt = stmt.where(Risk.status == status_filter)
    if category:
        stmt = stmt.where(Risk.category == category)
    if query:
        pattern = f"%{query.lower()}%"
        stmt = stmt.where(
            func.lower(Risk.title).like(pattern)
            | func.lower(Risk.ref).like(pattern)
            | func.lower(Risk.description).like(pattern)
        )
    return list(db.execute(stmt.order_by(Risk.ref)).scalars().all())


def create(db: Session, workspace_id: uuid.UUID, payload: RiskCreate) -> Risk:
    existing = db.execute(
        select(Risk.id).where(Risk.workspace_id == workspace_id, Risk.ref == payload.ref)
    ).scalar_one_or_none()
    if existing:
        raise _conflict(payload.ref)

    risk = Risk(
        workspace_id=workspace_id,
        ref=payload.ref,
        title=payload.title,
        description=payload.description,
        category=payload.category,
        owner=payload.owner,
        inherent_likelihood=payload.inherent_likelihood,
        inherent_impact=payload.inherent_impact,
        residual_likelihood=payload.residual_likelihood,
        residual_impact=payload.residual_impact,
        treatment=payload.treatment.value,
        status=payload.status.value,
    )
    db.add(risk)
    db.flush()
    return risk


def update(db: Session, risk: Risk, payload: RiskUpdate) -> Risk:
    data = payload.model_dump(exclude_unset=True)
    new_ref = data.get("ref")
    if new_ref and new_ref != risk.ref:
        clash = db.execute(
            select(Risk.id).where(
                Risk.workspace_id == risk.workspace_id,
                Risk.ref == new_ref,
                Risk.id != risk.id,
            )
        ).scalar_one_or_none()
        if clash:
            raise _conflict(new_ref)

    for key, value in data.items():
        setattr(risk, key, value.value if hasattr(value, "value") else value)
    db.flush()
    return risk


def delete(db: Session, risk: Risk) -> None:
    db.delete(risk)
    db.flush()


def set_controls(db: Session, risk: Risk, payload: RiskControlSet) -> list[RiskControlMapping]:
    """Replace the risk's mitigating controls with exactly the ids supplied."""
    wanted = set(payload.control_ids)

    if wanted:
        found = set(
            db.execute(
                select(Control.id).where(
                    Control.id.in_(list(wanted)), Control.workspace_id == risk.workspace_id
                )
            )
            .scalars()
            .all()
        )
        unknown = wanted - found
        if unknown:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Unknown control id(s) for this workspace: "
                    + ", ".join(str(u) for u in unknown)
                ),
            )

    existing = list(
        db.execute(select(RiskControlMapping).where(RiskControlMapping.risk_id == risk.id))
        .scalars()
        .all()
    )
    by_control = {m.control_id: m for m in existing}

    for control_id in wanted - set(by_control):
        db.add(RiskControlMapping(risk_id=risk.id, control_id=control_id))
    for control_id in set(by_control) - wanted:
        db.delete(by_control[control_id])

    db.flush()
    return list(
        db.execute(select(RiskControlMapping).where(RiskControlMapping.risk_id == risk.id))
        .scalars()
        .all()
    )
