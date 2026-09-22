"""§7.5 — the meridian itself: Risk → Control(s) → Requirement(s) → Framework(s)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    STATUS_STRENGTH,
    Control,
    ControlRequirementMapping,
    ControlStatus,
    Evidence,
    Framework,
    Requirement,
    Risk,
    RiskControlMapping,
)
from app.services.scoring import ScoringContext, assurance, risk_scores


def supporting_controls(db: Session, risk_id: uuid.UUID) -> list[Control]:
    """Controls mapped as mitigating a risk, ordered by ref."""
    return list(
        db.execute(
            select(Control)
            .join(RiskControlMapping, RiskControlMapping.control_id == Control.id)
            .where(RiskControlMapping.risk_id == risk_id)
            .order_by(Control.ref)
        )
        .scalars()
        .all()
    )


def build_traceability(db: Session, risk: Risk, ctx: ScoringContext) -> dict[str, Any]:
    """Full tree for one risk plus the aggregate that sits above it."""
    controls = supporting_controls(db, risk.id)
    control_ids = [c.id for c in controls]

    mappings: list[ControlRequirementMapping] = []
    if control_ids:
        mappings = list(
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
                .order_by(Framework.sort_order, Framework.key, Requirement.code)
            )
            .scalars()
            .all()
        )

    evidence_counts: dict[uuid.UUID, int] = {}
    if control_ids:
        for (control_id,) in db.execute(
            select(Evidence.control_id).where(Evidence.control_id.in_(control_ids))
        ).all():
            evidence_counts[control_id] = evidence_counts.get(control_id, 0) + 1

    by_control: dict[uuid.UUID, list[ControlRequirementMapping]] = {}
    for mapping in mappings:
        by_control.setdefault(mapping.control_id, []).append(mapping)

    nodes: list[dict[str, Any]] = []
    distinct_requirements: set[uuid.UUID] = set()
    distinct_frameworks: dict[str, dict[str, Any]] = {}

    for control in controls:
        requirement_nodes = []
        for mapping in by_control.get(control.id, []):
            requirement = mapping.requirement
            framework = requirement.framework
            distinct_requirements.add(requirement.id)
            distinct_frameworks.setdefault(
                framework.key,
                {
                    "framework_key": framework.key,
                    "framework_name": framework.name,
                    "color": framework.color,
                    "requirement_count": 0,
                },
            )
            distinct_frameworks[framework.key]["requirement_count"] += 1
            requirement_nodes.append(
                {
                    "requirement_id": str(requirement.id),
                    "code": requirement.code,
                    "title": requirement.title,
                    "category": requirement.category or "General",
                    "coverage_level": str(mapping.coverage_level),
                    "framework": {
                        "framework_key": framework.key,
                        "framework_name": framework.name,
                        "color": framework.color,
                    },
                }
            )
        nodes.append(
            {
                "control_id": str(control.id),
                "ref": control.ref,
                "name": control.name,
                "category": control.category or "General",
                "owner": control.owner,
                "status": str(control.status),
                "evidence_count": evidence_counts.get(control.id, 0),
                "requirements": requirement_nodes,
                "requirements_satisfied_count": len(requirement_nodes),
            }
        )

    statuses = [str(c.status) for c in controls]
    weakest = min(statuses, key=lambda s: STATUS_STRENGTH.get(s, 0)) if statuses else None
    scores = risk_scores(risk, ctx)

    return {
        "risk": {
            "id": str(risk.id),
            "ref": risk.ref,
            "title": risk.title,
            "description": risk.description,
            "category": risk.category or "General",
            "owner": risk.owner,
            "status": str(risk.status),
            "treatment": str(risk.treatment),
            **scores,
        },
        "controls": nodes,
        "assurance": assurance(risk, controls, ctx),
        "aggregate": {
            "control_count": len(controls),
            "implemented_control_count": sum(
                1 for s in statuses if s == ControlStatus.IMPLEMENTED.value
            ),
            "distinct_requirement_count": len(distinct_requirements),
            "frameworks_touched": len(distinct_frameworks),
            "frameworks": sorted(distinct_frameworks.values(), key=lambda f: f["framework_key"]),
            "weakest_control_status": weakest,
            "total_evidence_count": sum(evidence_counts.values()),
        },
    }
