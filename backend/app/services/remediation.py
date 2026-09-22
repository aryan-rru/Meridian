"""§7.7 — remediation ranking.

    "Fix the control propping up five risks before the one propping up none."

Only unfinished controls (``not_implemented`` / ``partial``) are candidates. Each is
scored by the risk it would relieve (weighted by those risks' inherent scores) plus
the number of requirements it would satisfy.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Control,
    ControlRequirementMapping,
    ControlStatus,
    Framework,
    Requirement,
    Risk,
    RiskControlMapping,
)
from app.services.scoring import ScoringContext, band_for, score

CANDIDATE_STATUSES = {ControlStatus.NOT_IMPLEMENTED.value, ControlStatus.PARTIAL.value}


def build_remediation(db: Session, workspace_id: uuid.UUID, ctx: ScoringContext) -> dict[str, Any]:
    controls = list(
        db.execute(
            select(Control)
            .where(Control.workspace_id == workspace_id, Control.status.in_(CANDIDATE_STATUSES))
            .order_by(Control.ref)
        )
        .scalars()
        .all()
    )
    if not controls:
        return {"items": [], "weights": dict(ctx.remediation_weights), "candidate_count": 0}

    control_ids = [c.id for c in controls]

    # Risks each candidate control is mapped to.
    risk_rows = db.execute(
        select(RiskControlMapping.control_id, Risk)
        .join(Risk, Risk.id == RiskControlMapping.risk_id)
        .where(RiskControlMapping.control_id.in_(control_ids), Risk.workspace_id == workspace_id)
    ).all()
    risks_by_control: dict[uuid.UUID, list[Risk]] = defaultdict(list)
    for control_id, risk in risk_rows:
        risks_by_control[control_id].append(risk)

    # Requirements each candidate control is mapped to.
    requirement_rows = (
        db.execute(
            select(ControlRequirementMapping)
            .options(
                selectinload(ControlRequirementMapping.requirement).selectinload(
                    Requirement.framework
                )
            )
            .join(Requirement, Requirement.id == ControlRequirementMapping.requirement_id)
            .join(Framework, Framework.id == Requirement.framework_id)
            .where(ControlRequirementMapping.control_id.in_(control_ids))
            .order_by(Framework.sort_order, Requirement.code)
        )
        .scalars()
        .all()
    )
    requirements_by_control: dict[uuid.UUID, list[ControlRequirementMapping]] = defaultdict(list)
    for mapping in requirement_rows:
        requirements_by_control[mapping.control_id].append(mapping)

    w_risk = float(ctx.remediation_weights.get("W_RISK", 1.0))
    w_req = float(ctx.remediation_weights.get("W_REQ", 0.5))

    items: list[dict[str, Any]] = []
    for control in controls:
        risks = risks_by_control.get(control.id, [])
        mappings = requirements_by_control.get(control.id, [])

        risk_leverage = len(risks)
        weighted_leverage = sum(score(r.inherent_likelihood, r.inherent_impact, ctx) for r in risks)
        requirement_leverage = len(mappings)
        priority = round(weighted_leverage * w_risk + requirement_leverage * w_req, 2)

        risk_entries = []
        for risk in sorted(risks, key=lambda r: r.ref):
            inherent = score(risk.inherent_likelihood, risk.inherent_impact, ctx)
            residual = score(risk.residual_likelihood, risk.residual_impact, ctx)
            risk_entries.append(
                {
                    "risk_id": str(risk.id),
                    "ref": risk.ref,
                    "title": risk.title,
                    "inherent_score": inherent,
                    "residual_score": residual,
                    "residual_band": band_for(residual, ctx).as_dict(),
                }
            )

        framework_breakdown: dict[str, int] = defaultdict(int)
        requirement_entries = []
        for mapping in mappings:
            requirement = mapping.requirement
            framework_breakdown[requirement.framework.key] += 1
            requirement_entries.append(
                {
                    "requirement_id": str(requirement.id),
                    "code": requirement.code,
                    "title": requirement.title,
                    "coverage_level": str(mapping.coverage_level),
                    "framework_key": requirement.framework.key,
                    "framework_color": requirement.framework.color,
                }
            )

        items.append(
            {
                "control_id": str(control.id),
                "ref": control.ref,
                "name": control.name,
                "category": control.category or "General",
                "owner": control.owner,
                "status": str(control.status),
                "priority": priority,
                "risk_leverage": risk_leverage,
                "weighted_leverage": round(weighted_leverage, 2),
                "requirement_leverage": requirement_leverage,
                "frameworks_touched": len(framework_breakdown),
                "framework_breakdown": dict(framework_breakdown),
                "risks": risk_entries,
                "requirements": requirement_entries,
                "rationale": _rationale(
                    control, risk_leverage, requirement_leverage, len(framework_breakdown)
                ),
            }
        )

    # Descending priority; tie-break on risk leverage then requirement leverage (§7.7).
    items.sort(
        key=lambda i: (-i["priority"], -i["risk_leverage"], -i["requirement_leverage"], i["ref"])
    )
    for position, item in enumerate(items, start=1):
        item["rank"] = position

    return {
        "items": items,
        "weights": {"W_RISK": w_risk, "W_REQ": w_req},
        "candidate_count": len(items),
    }


def _rationale(control: Control, risks: int, requirements: int, frameworks: int) -> str:
    """One plain-English sentence explaining the ranking to a non-technical reader."""
    verb = "Finishing" if str(control.status) == ControlStatus.PARTIAL.value else "Implementing"
    if risks and requirements:
        return (
            f"{verb} this control would strengthen {risks} "
            f"risk{'s' if risks != 1 else ''} and answer {requirements} "
            f"requirement{'s' if requirements != 1 else ''} across "
            f"{frameworks} framework{'s' if frameworks != 1 else ''}."
        )
    if risks:
        return f"{verb} this control would strengthen {risks} risk{'s' if risks != 1 else ''}."
    if requirements:
        return (
            f"{verb} this control would answer {requirements} "
            f"requirement{'s' if requirements != 1 else ''} across "
            f"{frameworks} framework{'s' if frameworks != 1 else ''}."
        )
    return (
        "This control is unfinished but is not yet mapped to any risk or requirement — "
        "map it to see its leverage."
    )
