"""Shared risk read-model builder.

The risks list, the dashboard, the 5×5 heatmap and the Excel export all need the
same derived shape (scores, bands, assurance, supporting controls), so it is built
once here rather than three times.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Control, Risk, RiskControlMapping
from app.services.scoring import ScoringContext, assurance, risk_scores


def load_controls_by_risk(
    db: Session, workspace_id: uuid.UUID, risk_ids: Sequence[uuid.UUID] | None = None
) -> dict[uuid.UUID, list[Control]]:
    stmt = (
        select(RiskControlMapping.risk_id, Control)
        .join(Control, Control.id == RiskControlMapping.control_id)
        .where(Control.workspace_id == workspace_id)
    )
    if risk_ids is not None:
        if not risk_ids:
            return {}
        stmt = stmt.where(RiskControlMapping.risk_id.in_(list(risk_ids)))

    out: dict[uuid.UUID, list[Control]] = defaultdict(list)
    for risk_id, control in db.execute(stmt).all():
        out[risk_id].append(control)
    for controls in out.values():
        controls.sort(key=lambda c: c.ref)
    return out


def build_risk_view(risk: Risk, controls: Sequence[Control], ctx: ScoringContext) -> dict[str, Any]:
    """One risk with everything the UI needs already computed."""
    return {
        "id": str(risk.id),
        "ref": risk.ref,
        "title": risk.title,
        "description": risk.description,
        "category": risk.category or "General",
        "owner": risk.owner,
        "treatment": str(risk.treatment),
        "status": str(risk.status),
        "inherent_likelihood": risk.inherent_likelihood,
        "inherent_impact": risk.inherent_impact,
        "residual_likelihood": risk.residual_likelihood,
        "residual_impact": risk.residual_impact,
        "inherent_likelihood_label": ctx.likelihood_label(risk.inherent_likelihood),
        "inherent_impact_label": ctx.impact_label(risk.inherent_impact),
        "residual_likelihood_label": ctx.likelihood_label(risk.residual_likelihood),
        "residual_impact_label": ctx.impact_label(risk.residual_impact),
        **risk_scores(risk, ctx),
        "assurance": assurance(risk, controls, ctx),
        "controls": [
            {"id": str(c.id), "ref": c.ref, "name": c.name, "status": str(c.status)}
            for c in controls
        ],
        "control_count": len(controls),
        "created_at": risk.created_at,
        "updated_at": risk.updated_at,
    }


def build_risk_views(
    db: Session, workspace_id: uuid.UUID, risks: Sequence[Risk], ctx: ScoringContext
) -> list[dict[str, Any]]:
    by_risk = load_controls_by_risk(db, workspace_id, [r.id for r in risks])
    return [build_risk_view(risk, by_risk.get(risk.id, []), ctx) for risk in risks]
