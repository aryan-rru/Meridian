"""§8.5 — the risk register, mitigating-control mappings, traceability and the heatmap."""

from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Query

from app.crud import risks as crud
from app.deps import Context, DbSession, Scoring, WriteContext
from app.schemas.common import MessageResponse
from app.schemas.risk import RiskControlSet, RiskCreate, RiskRead, RiskUpdate
from app.schemas.settings import HeatmapRead, TraceabilityRead
from app.services.dashboard import build_risk_heatmap
from app.services.risk_view import build_risk_views
from app.services.traceability import build_traceability

router = APIRouter(prefix="/risks", tags=["risks"])


@router.get("", response_model=list[RiskRead], summary="List risks with computed scores")
def list_risks(
    ctx: Context,
    db: DbSession,
    scoring: Scoring,
    status: str | None = Query(default=None, description="open | monitoring | closed"),
    band: str | None = Query(default=None, description="Filter by residual band name"),
    category: str | None = None,
    q: str | None = None,
) -> list[dict]:
    risks = crud.list_risks(db, ctx.workspace_id, status, category, q)
    views = build_risk_views(db, ctx.workspace_id, risks, scoring)
    if band:
        wanted = band.strip().lower()
        views = [v for v in views if v["residual_band"]["name"].lower() == wanted]
    return views


# Registered before /{risk_id} so "heatmap" is not parsed as an id.
@router.get("/heatmap", response_model=HeatmapRead, summary="Likelihood × impact distribution")
def heatmap(
    ctx: Context,
    db: DbSession,
    scoring: Scoring,
    basis: Literal["inherent", "residual"] = "residual",
) -> dict:
    return build_risk_heatmap(db, ctx.workspace_id, scoring, basis)


@router.post("", response_model=RiskRead, status_code=201, summary="Create a risk")
def create_risk(payload: RiskCreate, ctx: WriteContext, db: DbSession, scoring: Scoring) -> dict:
    risk = crud.create(db, ctx.workspace_id, payload)
    db.commit()
    db.refresh(risk)
    return build_risk_views(db, ctx.workspace_id, [risk], scoring)[0]


@router.get("/{risk_id}", response_model=RiskRead, summary="Risk detail")
def get_risk(risk_id: uuid.UUID, ctx: Context, db: DbSession, scoring: Scoring) -> dict:
    risk = crud.get(db, ctx.workspace_id, risk_id)
    return build_risk_views(db, ctx.workspace_id, [risk], scoring)[0]


@router.patch("/{risk_id}", response_model=RiskRead, summary="Update a risk")
def update_risk(
    risk_id: uuid.UUID,
    payload: RiskUpdate,
    ctx: WriteContext,
    db: DbSession,
    scoring: Scoring,
) -> dict:
    risk = crud.get(db, ctx.workspace_id, risk_id)
    crud.update(db, risk, payload)
    db.commit()
    db.refresh(risk)
    return build_risk_views(db, ctx.workspace_id, [risk], scoring)[0]


@router.delete("/{risk_id}", response_model=MessageResponse, summary="Delete a risk")
def delete_risk(risk_id: uuid.UUID, ctx: WriteContext, db: DbSession) -> MessageResponse:
    risk = crud.get(db, ctx.workspace_id, risk_id)
    ref = risk.ref
    crud.delete(db, risk)
    db.commit()
    return MessageResponse(message=f"Risk {ref} deleted.")


@router.put(
    "/{risk_id}/controls",
    response_model=RiskRead,
    summary="Set the controls that mitigate this risk",
)
def set_controls(
    risk_id: uuid.UUID,
    payload: RiskControlSet,
    ctx: WriteContext,
    db: DbSession,
    scoring: Scoring,
) -> dict:
    risk = crud.get(db, ctx.workspace_id, risk_id)
    crud.set_controls(db, risk, payload)
    db.commit()
    db.refresh(risk)
    return build_risk_views(db, ctx.workspace_id, [risk], scoring)[0]


@router.get(
    "/{risk_id}/traceability",
    response_model=TraceabilityRead,
    summary="Risk → Controls → Requirements → Frameworks",
)
def traceability(risk_id: uuid.UUID, ctx: Context, db: DbSession, scoring: Scoring) -> dict:
    risk = crud.get(db, ctx.workspace_id, risk_id)
    return build_traceability(db, risk, scoring)
