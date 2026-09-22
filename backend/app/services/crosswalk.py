"""§7.4 — the crosswalk matrix: controls (rows) × requirements (columns, by framework).

The per-control ``frameworks_touched`` / ``requirements_satisfied_count`` pair is the
leverage number the product is built around: *one* control answering N requirements
across M frameworks.
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
    Framework,
    Requirement,
)


def build_crosswalk(db: Session, workspace_id: uuid.UUID) -> dict[str, Any]:
    frameworks = list(
        db.execute(select(Framework).order_by(Framework.sort_order, Framework.key)).scalars().all()
    )
    requirements = list(
        db.execute(
            select(Requirement)
            .options(selectinload(Requirement.framework))
            .join(Framework, Framework.id == Requirement.framework_id)
            .order_by(Framework.sort_order, Framework.key, Requirement.sort_order, Requirement.code)
        )
        .scalars()
        .all()
    )
    controls = list(
        db.execute(
            select(Control).where(Control.workspace_id == workspace_id).order_by(Control.ref)
        )
        .scalars()
        .all()
    )

    mappings = (
        db.execute(
            select(ControlRequirementMapping)
            .join(Control, Control.id == ControlRequirementMapping.control_id)
            .where(Control.workspace_id == workspace_id)
        )
        .scalars()
        .all()
    )

    # (control_id, requirement_id) → coverage_level
    cells: dict[tuple[uuid.UUID, uuid.UUID], str] = {
        (m.control_id, m.requirement_id): str(m.coverage_level) for m in mappings
    }

    requirement_framework: dict[uuid.UUID, str] = {r.id: r.framework.key for r in requirements}
    per_control_frameworks: dict[uuid.UUID, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    per_requirement_controls: dict[uuid.UUID, int] = defaultdict(int)
    for control_id, requirement_id in cells:
        framework_key = requirement_framework.get(requirement_id)
        if framework_key:
            per_control_frameworks[control_id][framework_key] += 1
        per_requirement_controls[requirement_id] += 1

    column_groups = []
    for framework in frameworks:
        group_requirements = [r for r in requirements if r.framework_id == framework.id]
        if not group_requirements:
            continue
        column_groups.append(
            {
                "framework_id": str(framework.id),
                "framework_key": framework.key,
                "framework_name": framework.name,
                "color": framework.color,
                "requirements": [
                    {
                        "requirement_id": str(r.id),
                        "code": r.code,
                        "title": r.title,
                        "category": r.category or "General",
                        "mapped_control_count": per_requirement_controls.get(r.id, 0),
                    }
                    for r in group_requirements
                ],
            }
        )

    rows = []
    for control in controls:
        breakdown = dict(per_control_frameworks.get(control.id, {}))
        row_cells: dict[str, Any] = {}
        for requirement in requirements:
            level = cells.get((control.id, requirement.id))
            if level is not None:
                row_cells[str(requirement.id)] = {"coverage_level": level}
        rows.append(
            {
                "control_id": str(control.id),
                "ref": control.ref,
                "name": control.name,
                "category": control.category or "General",
                "status": str(control.status),
                "cells": row_cells,
                "requirements_satisfied_count": len(row_cells),
                "frameworks_touched": len(breakdown),
                "framework_breakdown": breakdown,
            }
        )

    total_mappings = len(cells)
    mapped_controls = sum(1 for r in rows if r["requirements_satisfied_count"] > 0)
    return {
        "column_groups": column_groups,
        "rows": rows,
        "summary": {
            "control_count": len(rows),
            "requirement_count": len(requirements),
            "mapping_count": total_mappings,
            "unmapped_control_count": len(rows) - mapped_controls,
            "unmapped_requirement_count": sum(
                1 for r in requirements if per_requirement_controls.get(r.id, 0) == 0
            ),
            "average_requirements_per_control": (
                round(total_mappings / len(rows), 2) if rows else 0.0
            ),
            # The headline overlap figure: controls that answer more than one framework.
            "multi_framework_control_count": sum(1 for r in rows if r["frameworks_touched"] > 1),
        },
    }


def control_leverage(db: Session, workspace_id: uuid.UUID) -> dict[uuid.UUID, dict[str, Any]]:
    """Lightweight per-control leverage counts, used by list endpoints."""
    rows = db.execute(
        select(ControlRequirementMapping.control_id, Framework.key)
        .join(Control, Control.id == ControlRequirementMapping.control_id)
        .join(Requirement, Requirement.id == ControlRequirementMapping.requirement_id)
        .join(Framework, Framework.id == Requirement.framework_id)
        .where(Control.workspace_id == workspace_id)
    ).all()

    out: dict[uuid.UUID, dict[str, Any]] = defaultdict(
        lambda: {"requirements_satisfied_count": 0, "framework_breakdown": defaultdict(int)}
    )
    for control_id, framework_key in rows:
        entry = out[control_id]
        entry["requirements_satisfied_count"] += 1
        entry["framework_breakdown"][framework_key] += 1
    return {
        control_id: {
            "requirements_satisfied_count": entry["requirements_satisfied_count"],
            "frameworks_touched": len(entry["framework_breakdown"]),
            "framework_breakdown": dict(entry["framework_breakdown"]),
        }
        for control_id, entry in out.items()
    }
