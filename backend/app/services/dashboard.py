"""§7.8 dashboard aggregates and the §8.5 likelihood × impact heatmap distribution."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Control,
    ControlStatus,
    Evidence,
    EvidenceStatus,
    Risk,
)
from app.services.coverage import build_coverage, build_gaps
from app.services.crosswalk import build_crosswalk
from app.services.remediation import build_remediation
from app.services.risk_view import build_risk_views
from app.services.scoring import UNSUPPORTED_RESIDUAL, ScoringContext, band_for, score


def _counts_by(db: Session, column, where) -> dict[str, int]:
    rows = db.execute(select(column, func.count()).where(where).group_by(column)).all()
    return {str(value): int(count) for value, count in rows}


def build_dashboard_summary(
    db: Session, workspace_id: uuid.UUID, ctx: ScoringContext
) -> dict[str, Any]:
    control_counts = _counts_by(db, Control.status, Control.workspace_id == workspace_id)
    control_status_counts = {
        status.value: control_counts.get(status.value, 0) for status in ControlStatus
    }
    total_controls = sum(control_status_counts.values())

    evidence_counts = _counts_by(db, Evidence.status, Evidence.workspace_id == workspace_id)
    evidence_status_counts = {
        status.value: evidence_counts.get(status.value, 0) for status in EvidenceStatus
    }

    coverage = build_coverage(db, workspace_id)
    gaps = build_gaps(db, workspace_id)
    crosswalk = build_crosswalk(db, workspace_id)
    remediation = build_remediation(db, workspace_id, ctx)

    risks = list(db.execute(select(Risk).where(Risk.workspace_id == workspace_id)).scalars().all())
    risk_views = build_risk_views(db, workspace_id, risks, ctx)
    risk_views.sort(key=lambda r: r["residual_score"], reverse=True)

    unsupported = [r for r in risk_views if r["assurance"]["flag"] == UNSUPPORTED_RESIDUAL]

    return {
        "controls": {
            "total": total_controls,
            "by_status": control_status_counts,
            "implemented_percent": (
                round(
                    100.0 * control_status_counts[ControlStatus.IMPLEMENTED.value] / total_controls,
                    1,
                )
                if total_controls
                else 0.0
            ),
        },
        "coverage": {
            "frameworks": [
                {
                    "framework_key": f["framework_key"],
                    "framework_name": f["framework_name"],
                    "color": f["color"],
                    "coverage_percent": f["coverage_percent"],
                    "covered_count": f["covered_count"],
                    "partial_count": f["partial_count"],
                    "gap_count": f["gap_count"],
                    "total_requirements": f["total_requirements"],
                }
                for f in coverage["frameworks"]
            ],
            "totals": coverage["totals"],
        },
        "gaps": {
            "gap_count": gaps["gap_count"],
            "partial_count": gaps["partial_count"],
            "top_gaps": gaps["items"][:5],
        },
        "risks": {
            "total": len(risk_views),
            "open": sum(1 for r in risk_views if r["status"] == "open"),
            "unsupported_residual_count": len(unsupported),
            "top_by_residual": risk_views[:5],
            "unsupported_residual": unsupported[:5],
        },
        "remediation": {
            "candidate_count": remediation["candidate_count"],
            "top_items": remediation["items"][:5],
        },
        "evidence": {
            "total": sum(evidence_status_counts.values()),
            "by_status": evidence_status_counts,
        },
        "leverage": crosswalk["summary"],
    }


def build_risk_heatmap(
    db: Session,
    workspace_id: uuid.UUID,
    ctx: ScoringContext,
    basis: Literal["inherent", "residual"] = "residual",
) -> dict[str, Any]:
    """Counts (and the risks themselves) for every likelihood × impact cell.

    Likelihood is the Y axis with the highest value at the top; impact is the X axis
    running low → high left → right (§11.4). The grid is emitted rows-first in that
    display order so the frontend can render it without re-sorting.
    """
    size = max(2, int(ctx.matrix_size or 5))
    risks = list(db.execute(select(Risk).where(Risk.workspace_id == workspace_id)).scalars().all())
    views = build_risk_views(db, workspace_id, risks, ctx)

    buckets: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for view in views:
        likelihood = int(view[f"{basis}_likelihood"])
        impact = int(view[f"{basis}_impact"])
        buckets.setdefault((likelihood, impact), []).append(
            {
                "id": view["id"],
                "ref": view["ref"],
                "title": view["title"],
                "status": view["status"],
                "score": view[f"{basis}_score"],
                "band": view[f"{basis}_band"],
                "flag": view["assurance"]["flag"],
            }
        )

    rows: list[dict[str, Any]] = []
    for likelihood in range(size, 0, -1):  # 5 at the top
        cells = []
        for impact in range(1, size + 1):  # 1 → 5 left to right
            cell_score = score(likelihood, impact, ctx)
            contained = buckets.get((likelihood, impact), [])
            cells.append(
                {
                    "likelihood": likelihood,
                    "impact": impact,
                    "likelihood_label": ctx.likelihood_label(likelihood),
                    "impact_label": ctx.impact_label(impact),
                    "score": cell_score,
                    "band": band_for(cell_score, ctx).as_dict(),
                    "count": len(contained),
                    "risks": sorted(contained, key=lambda r: r["ref"]),
                }
            )
        rows.append(
            {
                "likelihood": likelihood,
                "likelihood_label": ctx.likelihood_label(likelihood),
                "cells": cells,
            }
        )

    return {
        "basis": basis,
        "matrix_size": size,
        "rows": rows,
        "impact_labels": [{"value": i, "label": ctx.impact_label(i)} for i in range(1, size + 1)],
        "likelihood_labels": [
            {"value": i, "label": ctx.likelihood_label(i)} for i in range(size, 0, -1)
        ],
        "total_risks": len(views),
    }
