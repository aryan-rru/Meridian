"""Control persistence, including the tick-box requirement mappings."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Control,
    ControlRequirementMapping,
    Evidence,
    Framework,
    Requirement,
    RiskControlMapping,
)
from app.schemas.control import ControlCreate, ControlUpdate, RequirementMappingSet
from app.services.crosswalk import control_leverage


def _conflict(ref: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=f"A control with reference '{ref}' already exists in this workspace.",
    )


def get(db: Session, workspace_id: uuid.UUID, control_id: uuid.UUID) -> Control:
    control = db.execute(
        select(Control).where(Control.id == control_id, Control.workspace_id == workspace_id)
    ).scalar_one_or_none()
    if control is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Control not found.")
    return control


def list_controls(
    db: Session,
    workspace_id: uuid.UUID,
    status_filter: str | None = None,
    category: str | None = None,
    query: str | None = None,
) -> list[Control]:
    stmt = select(Control).where(Control.workspace_id == workspace_id)
    if status_filter:
        stmt = stmt.where(Control.status == status_filter)
    if category:
        stmt = stmt.where(Control.category == category)
    if query:
        pattern = f"%{query.lower()}%"
        stmt = stmt.where(
            func.lower(Control.name).like(pattern)
            | func.lower(Control.ref).like(pattern)
            | func.lower(Control.description).like(pattern)
        )
    return list(db.execute(stmt.order_by(Control.ref)).scalars().all())


def create(db: Session, workspace_id: uuid.UUID, payload: ControlCreate) -> Control:
    existing = db.execute(
        select(Control.id).where(Control.workspace_id == workspace_id, Control.ref == payload.ref)
    ).scalar_one_or_none()
    if existing:
        raise _conflict(payload.ref)

    control = Control(
        workspace_id=workspace_id,
        ref=payload.ref,
        name=payload.name,
        description=payload.description,
        category=payload.category,
        owner=payload.owner,
        status=payload.status.value,
        implementation_notes=payload.implementation_notes,
    )
    db.add(control)
    db.flush()
    return control


def update(db: Session, control: Control, payload: ControlUpdate) -> Control:
    data = payload.model_dump(exclude_unset=True)
    new_ref = data.get("ref")
    if new_ref and new_ref != control.ref:
        clash = db.execute(
            select(Control.id).where(
                Control.workspace_id == control.workspace_id,
                Control.ref == new_ref,
                Control.id != control.id,
            )
        ).scalar_one_or_none()
        if clash:
            raise _conflict(new_ref)

    for key, value in data.items():
        setattr(control, key, value.value if hasattr(value, "value") else value)
    db.flush()
    return control


def delete(db: Session, control: Control) -> None:
    db.delete(control)
    db.flush()


# ---------------------------------------------------------------------------
# Mappings
# ---------------------------------------------------------------------------
def set_requirements(
    db: Session, control: Control, payload: RequirementMappingSet
) -> list[ControlRequirementMapping]:
    """Replace the control's crosswalk mappings with exactly what was ticked."""
    wanted = {item.requirement_id: item.coverage_level.value for item in payload.items}

    if wanted:
        found = set(
            db.execute(select(Requirement.id).where(Requirement.id.in_(list(wanted))))
            .scalars()
            .all()
        )
        unknown = set(wanted) - found
        if unknown:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown requirement id(s): {', '.join(str(u) for u in unknown)}.",
            )

    existing = list(
        db.execute(
            select(ControlRequirementMapping).where(
                ControlRequirementMapping.control_id == control.id
            )
        )
        .scalars()
        .all()
    )
    by_requirement = {m.requirement_id: m for m in existing}

    for requirement_id, level in wanted.items():
        mapping = by_requirement.get(requirement_id)
        if mapping is None:
            db.add(
                ControlRequirementMapping(
                    control_id=control.id, requirement_id=requirement_id, coverage_level=level
                )
            )
        elif str(mapping.coverage_level) != level:
            mapping.coverage_level = level

    for requirement_id, mapping in by_requirement.items():
        if requirement_id not in wanted:
            db.delete(mapping)

    db.flush()
    return list(
        db.execute(
            select(ControlRequirementMapping).where(
                ControlRequirementMapping.control_id == control.id
            )
        )
        .scalars()
        .all()
    )


def mapped_requirements(db: Session, control_id: uuid.UUID) -> list[dict[str, Any]]:
    mappings = (
        db.execute(
            select(ControlRequirementMapping)
            .options(
                selectinload(ControlRequirementMapping.requirement).selectinload(
                    Requirement.framework
                )
            )
            .join(Requirement, Requirement.id == ControlRequirementMapping.requirement_id)
            .join(Framework, Framework.id == Requirement.framework_id)
            .where(ControlRequirementMapping.control_id == control_id)
            .order_by(Framework.sort_order, Requirement.sort_order, Requirement.code)
        )
        .scalars()
        .all()
    )
    out = []
    for mapping in mappings:
        requirement = mapping.requirement
        framework = requirement.framework
        out.append(
            {
                "id": requirement.id,
                "created_at": requirement.created_at,
                "updated_at": requirement.updated_at,
                "framework_id": framework.id,
                "framework_key": framework.key,
                "framework_name": framework.name,
                "framework_color": framework.color,
                "code": requirement.code,
                "title": requirement.title,
                "description": requirement.description,
                "category": requirement.category,
                "sort_order": requirement.sort_order,
                "coverage_level": str(mapping.coverage_level),
                "mapped_control_count": 0,
            }
        )
    return out


# ---------------------------------------------------------------------------
# Read-model assembly
# ---------------------------------------------------------------------------
def counts_for(db: Session, workspace_id: uuid.UUID) -> dict[uuid.UUID, dict[str, int]]:
    """Per-control risk and evidence counts, fetched in two grouped queries."""
    risk_counts = dict(
        db.execute(
            select(RiskControlMapping.control_id, func.count())
            .join(Control, Control.id == RiskControlMapping.control_id)
            .where(Control.workspace_id == workspace_id)
            .group_by(RiskControlMapping.control_id)
        ).all()
    )
    evidence_counts = dict(
        db.execute(
            select(Evidence.control_id, func.count())
            .where(Evidence.workspace_id == workspace_id)
            .group_by(Evidence.control_id)
        ).all()
    )
    keys = set(risk_counts) | set(evidence_counts)
    return {
        key: {
            "risks_count": int(risk_counts.get(key, 0)),
            "evidence_count": int(evidence_counts.get(key, 0)),
        }
        for key in keys
    }


def build_read_models(
    db: Session, workspace_id: uuid.UUID, controls: Sequence[Control]
) -> list[dict[str, Any]]:
    leverage = control_leverage(db, workspace_id)
    counts = counts_for(db, workspace_id)
    out = []
    for control in controls:
        lev = leverage.get(
            control.id,
            {"requirements_satisfied_count": 0, "frameworks_touched": 0, "framework_breakdown": {}},
        )
        cnt = counts.get(control.id, {"risks_count": 0, "evidence_count": 0})
        out.append(
            {
                "id": control.id,
                "workspace_id": control.workspace_id,
                "ref": control.ref,
                "name": control.name,
                "description": control.description,
                "category": control.category,
                "owner": control.owner,
                "status": str(control.status),
                "implementation_notes": control.implementation_notes,
                "created_at": control.created_at,
                "updated_at": control.updated_at,
                **lev,
                **cnt,
            }
        )
    return out
