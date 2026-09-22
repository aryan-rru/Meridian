"""§8.4 — the control library and its requirement tick-boxes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud import controls as crud
from app.crud import evidence as evidence_crud
from app.deps import Context, DbSession, Scoring, WriteContext
from app.models import Risk, RiskControlMapping
from app.schemas.common import MessageResponse
from app.schemas.control import (
    ControlCreate,
    ControlDetail,
    ControlRead,
    ControlUpdate,
    RequirementMappingSet,
)
from app.schemas.evidence import EvidenceRead

router = APIRouter(prefix="/controls", tags=["controls"])


def _mitigated_risks(db: Session, control_id: uuid.UUID) -> list[dict]:
    risks = (
        db.execute(
            select(Risk)
            .join(RiskControlMapping, RiskControlMapping.risk_id == Risk.id)
            .where(RiskControlMapping.control_id == control_id)
            .order_by(Risk.ref)
        )
        .scalars()
        .all()
    )
    return [
        {
            "id": str(r.id),
            "ref": r.ref,
            "title": r.title,
            "status": str(r.status),
            "inherent_likelihood": r.inherent_likelihood,
            "inherent_impact": r.inherent_impact,
            "residual_likelihood": r.residual_likelihood,
            "residual_impact": r.residual_impact,
        }
        for r in risks
    ]


def _detail(db: Session, workspace_id: uuid.UUID, control_id: uuid.UUID) -> dict:
    control = crud.get(db, workspace_id, control_id)
    read_model = crud.build_read_models(db, workspace_id, [control])[0]
    read_model["requirements"] = crud.mapped_requirements(db, control.id)
    read_model["risks"] = _mitigated_risks(db, control.id)
    read_model["evidence"] = [
        evidence_crud.to_read_model(e)
        for e in evidence_crud.list_evidence(db, workspace_id, control.id)
    ]
    return read_model


@router.get("", response_model=list[ControlRead], summary="List controls with computed counts")
def list_controls(
    ctx: Context,
    db: DbSession,
    status: str | None = Query(default=None, description="Filter by control status"),
    category: str | None = None,
    q: str | None = Query(default=None, description="Search ref, name or description"),
) -> list[dict]:
    controls = crud.list_controls(db, ctx.workspace_id, status, category, q)
    return crud.build_read_models(db, ctx.workspace_id, controls)


@router.post("", response_model=ControlRead, status_code=201, summary="Create a control")
def create_control(payload: ControlCreate, ctx: WriteContext, db: DbSession) -> dict:
    control = crud.create(db, ctx.workspace_id, payload)
    db.commit()
    db.refresh(control)
    return crud.build_read_models(db, ctx.workspace_id, [control])[0]


@router.get("/{control_id}", response_model=ControlDetail, summary="Control detail")
def get_control(control_id: uuid.UUID, ctx: Context, db: DbSession) -> dict:
    return _detail(db, ctx.workspace_id, control_id)


@router.patch("/{control_id}", response_model=ControlRead, summary="Update a control")
def update_control(
    control_id: uuid.UUID, payload: ControlUpdate, ctx: WriteContext, db: DbSession
) -> dict:
    control = crud.get(db, ctx.workspace_id, control_id)
    crud.update(db, control, payload)
    db.commit()
    db.refresh(control)
    return crud.build_read_models(db, ctx.workspace_id, [control])[0]


@router.delete("/{control_id}", response_model=MessageResponse, summary="Delete a control")
def delete_control(control_id: uuid.UUID, ctx: WriteContext, db: DbSession) -> MessageResponse:
    control = crud.get(db, ctx.workspace_id, control_id)
    ref = control.ref
    crud.delete(db, control)
    db.commit()
    return MessageResponse(message=f"Control {ref} deleted.")


@router.put(
    "/{control_id}/requirements",
    response_model=ControlDetail,
    summary="Set which requirements this control answers",
)
def set_requirements(
    control_id: uuid.UUID, payload: RequirementMappingSet, ctx: WriteContext, db: DbSession
) -> dict:
    control = crud.get(db, ctx.workspace_id, control_id)
    crud.set_requirements(db, control, payload)
    db.commit()
    return _detail(db, ctx.workspace_id, control_id)


@router.get(
    "/{control_id}/evidence",
    response_model=list[EvidenceRead],
    summary="Evidence attached to this control",
)
def control_evidence(
    control_id: uuid.UUID, ctx: Context, db: DbSession, scoring: Scoring
) -> list[dict]:
    crud.get(db, ctx.workspace_id, control_id)
    items = evidence_crud.list_evidence(db, ctx.workspace_id, control_id)
    evidence_crud.refresh_statuses(db, items, scoring.evidence_stale_after_days)
    db.commit()
    return [evidence_crud.to_read_model(e) for e in items]
