"""§7.3 — per-requirement coverage classification, framework roll-ups and gap analysis."""

from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import Iterable, Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Control,
    ControlRequirementMapping,
    ControlStatus,
    CoverageStatus,
    Framework,
    Requirement,
)


# ---------------------------------------------------------------------------
# Pure classification
# ---------------------------------------------------------------------------
def classify(controls: Iterable[Any]) -> CoverageStatus:
    """Classify one requirement from the controls mapped to it.

    ``covered``  — at least one mapped control is ``implemented``.
    ``partial``  — none implemented, but at least one ``partial``.
    ``gap``      — nothing mapped, or everything is not-implemented / not-applicable.
    """
    statuses = {str(c.status) for c in controls}
    if ControlStatus.IMPLEMENTED.value in statuses:
        return CoverageStatus.COVERED
    if ControlStatus.PARTIAL.value in statuses:
        return CoverageStatus.PARTIAL
    return CoverageStatus.GAP


def _gap_reason(controls: Sequence[Any]) -> str:
    if not controls:
        return "No control in the library is mapped to this requirement."
    statuses = {str(c.status) for c in controls}
    if ControlStatus.PARTIAL.value in statuses:
        names = ", ".join(c.ref for c in controls if str(c.status) == ControlStatus.PARTIAL.value)
        return (
            f"Only partially implemented controls answer this requirement ({names}). "
            "Finish implementing them to close the gap."
        )
    if statuses <= {ControlStatus.NOT_APPLICABLE.value}:
        return "Every mapped control is marked not applicable."
    names = ", ".join(
        c.ref for c in controls if str(c.status) == ControlStatus.NOT_IMPLEMENTED.value
    )
    return f"Mapped controls exist but are not implemented ({names})."


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def load_requirement_controls(
    db: Session, workspace_id: uuid.UUID
) -> dict[uuid.UUID, list[Control]]:
    """Map every requirement id → the workspace's controls mapped to it."""
    rows = db.execute(
        select(ControlRequirementMapping.requirement_id, Control)
        .join(Control, Control.id == ControlRequirementMapping.control_id)
        .where(Control.workspace_id == workspace_id)
    ).all()
    out: dict[uuid.UUID, list[Control]] = defaultdict(list)
    for requirement_id, control in rows:
        out[requirement_id].append(control)
    return out


def load_requirements(db: Session) -> list[Requirement]:
    return list(
        db.execute(
            select(Requirement)
            .options(selectinload(Requirement.framework))
            .join(Framework, Framework.id == Requirement.framework_id)
            .order_by(Framework.sort_order, Framework.key, Requirement.sort_order, Requirement.code)
        )
        .scalars()
        .all()
    )


# ---------------------------------------------------------------------------
# §7.3 roll-ups
# ---------------------------------------------------------------------------
def build_coverage(db: Session, workspace_id: uuid.UUID) -> dict[str, Any]:
    """Per-framework and per-category coverage, plus every requirement's status.

    The frontend heatmap renders straight from this payload — grouped by framework,
    then by category, with one cell per requirement.
    """
    requirements = load_requirements(db)
    by_requirement = load_requirement_controls(db, workspace_id)

    frameworks: dict[uuid.UUID, dict[str, Any]] = {}
    totals = {"covered": 0, "partial": 0, "gap": 0}

    for requirement in requirements:
        controls = by_requirement.get(requirement.id, [])
        status = classify(controls)
        totals[status.value] += 1

        fw = requirement.framework
        entry = frameworks.setdefault(
            fw.id,
            {
                "framework_id": str(fw.id),
                "framework_key": fw.key,
                "framework_name": fw.name,
                "color": fw.color,
                "total_requirements": 0,
                "covered_count": 0,
                "partial_count": 0,
                "gap_count": 0,
                "coverage_percent": 0.0,
                "categories": {},
            },
        )
        entry["total_requirements"] += 1
        entry[f"{status.value}_count"] += 1

        category_name = requirement.category or "General"
        category = entry["categories"].setdefault(
            category_name,
            {
                "category": category_name,
                "total_requirements": 0,
                "covered_count": 0,
                "partial_count": 0,
                "gap_count": 0,
                "coverage_percent": 0.0,
                "requirements": [],
            },
        )
        category["total_requirements"] += 1
        category[f"{status.value}_count"] += 1
        category["requirements"].append(
            {
                "requirement_id": str(requirement.id),
                "code": requirement.code,
                "title": requirement.title,
                "category": category_name,
                "status": status.value,
                "control_count": len(controls),
                "controls": [
                    {"id": str(c.id), "ref": c.ref, "name": c.name, "status": str(c.status)}
                    for c in sorted(controls, key=lambda c: c.ref)
                ],
            }
        )

    framework_list = []
    for entry in frameworks.values():
        total = entry["total_requirements"] or 1
        entry["coverage_percent"] = round(100.0 * entry["covered_count"] / total, 1)
        categories = []
        for category in entry["categories"].values():
            cat_total = category["total_requirements"] or 1
            category["coverage_percent"] = round(100.0 * category["covered_count"] / cat_total, 1)
            categories.append(category)
        entry["categories"] = sorted(categories, key=lambda c: c["category"])
        framework_list.append(entry)

    grand_total = sum(totals.values()) or 1
    return {
        "frameworks": framework_list,
        "totals": {
            **totals,
            "total_requirements": sum(totals.values()),
            "coverage_percent": round(100.0 * totals["covered"] / grand_total, 1),
        },
    }


def build_gaps(db: Session, workspace_id: uuid.UUID) -> dict[str, Any]:
    """Every requirement that is a gap or only partially covered, and why (§8.6).

    ``closing_controls`` answers the UI question "what would close this?" — the
    controls already mapped but not yet implemented. When that list is empty the
    requirement needs a brand-new control.
    """
    requirements = load_requirements(db)
    by_requirement = load_requirement_controls(db, workspace_id)

    items: list[dict[str, Any]] = []
    for requirement in requirements:
        controls = by_requirement.get(requirement.id, [])
        status = classify(controls)
        if status == CoverageStatus.COVERED:
            continue
        closing = [
            {"id": str(c.id), "ref": c.ref, "name": c.name, "status": str(c.status)}
            for c in sorted(controls, key=lambda c: c.ref)
            if str(c.status) in {ControlStatus.PARTIAL.value, ControlStatus.NOT_IMPLEMENTED.value}
        ]
        items.append(
            {
                "requirement_id": str(requirement.id),
                "code": requirement.code,
                "title": requirement.title,
                "category": requirement.category or "General",
                "framework_key": requirement.framework.key,
                "framework_name": requirement.framework.name,
                "framework_color": requirement.framework.color,
                "status": status.value,
                "reason": _gap_reason(controls),
                "mapped_control_count": len(controls),
                "closing_controls": closing,
                "needs_new_control": not controls,
            }
        )

    # Hard gaps first, then partials; stable by framework then code.
    items.sort(key=lambda i: (i["status"] != "gap", i["framework_key"], i["code"]))
    return {
        "items": items,
        "gap_count": sum(1 for i in items if i["status"] == "gap"),
        "partial_count": sum(1 for i in items if i["status"] == "partial"),
    }
