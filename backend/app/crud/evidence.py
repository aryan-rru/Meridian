"""Evidence persistence and freshness rules (§9.5 step 4)."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import timedelta
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import utcnow
from app.models import Control, Evidence, EvidenceStatus


def get(db: Session, workspace_id: uuid.UUID, evidence_id: uuid.UUID) -> Evidence:
    evidence = db.execute(
        select(Evidence)
        .options(selectinload(Evidence.control))
        .where(Evidence.id == evidence_id, Evidence.workspace_id == workspace_id)
    ).scalar_one_or_none()
    if evidence is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found.")
    return evidence


def list_evidence(
    db: Session, workspace_id: uuid.UUID, control_id: uuid.UUID | None = None
) -> list[Evidence]:
    stmt = (
        select(Evidence)
        .options(selectinload(Evidence.control))
        .where(Evidence.workspace_id == workspace_id)
    )
    if control_id:
        stmt = stmt.where(Evidence.control_id == control_id)
    return list(db.execute(stmt.order_by(Evidence.created_at.desc())).scalars().all())


def require_control(db: Session, workspace_id: uuid.UUID, control_id: uuid.UUID) -> Control:
    control = db.execute(
        select(Control).where(Control.id == control_id, Control.workspace_id == workspace_id)
    ).scalar_one_or_none()
    if control is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Control not found in this workspace.",
        )
    return control


def freshness(evidence: Evidence, stale_after_days: int) -> str:
    """Derive current/stale from the expiry date, or from age when none is set."""
    if str(evidence.status) == EvidenceStatus.MISSING.value:
        return EvidenceStatus.MISSING.value

    now = utcnow()
    if evidence.valid_until is not None:
        valid_until = evidence.valid_until
        if valid_until.tzinfo is None:
            valid_until = valid_until.replace(tzinfo=now.tzinfo)
        return EvidenceStatus.CURRENT.value if valid_until > now else EvidenceStatus.STALE.value

    collected = evidence.collected_at or evidence.created_at
    if collected is not None:
        if collected.tzinfo is None:
            collected = collected.replace(tzinfo=now.tzinfo)
        if now - collected > timedelta(days=stale_after_days):
            return EvidenceStatus.STALE.value
    return EvidenceStatus.CURRENT.value


def refresh_statuses(
    db: Session, evidence_items: Sequence[Evidence], stale_after_days: int
) -> None:
    """Recompute freshness in place so the list view is never showing a stale claim."""
    changed = False
    for item in evidence_items:
        new_status = freshness(item, stale_after_days)
        if str(item.status) != new_status:
            item.status = new_status
            changed = True
    if changed:
        db.flush()


def to_read_model(evidence: Evidence) -> dict[str, Any]:
    control = evidence.control
    return {
        "id": evidence.id,
        "created_at": evidence.created_at,
        "updated_at": evidence.updated_at,
        "workspace_id": evidence.workspace_id,
        "control_id": evidence.control_id,
        "control_ref": control.ref if control else None,
        "control_name": control.name if control else None,
        "title": evidence.title,
        "description": evidence.description,
        "source_type": str(evidence.source_type),
        "drive_file_id": evidence.drive_file_id,
        "drive_file_name": evidence.drive_file_name,
        "mime_type": evidence.mime_type,
        "web_view_link": evidence.web_view_link,
        "url": evidence.url,
        "collected_at": evidence.collected_at,
        "valid_until": evidence.valid_until,
        "status": str(evidence.status),
        "extracted_data": evidence.extracted_data,
        "extracted_at": evidence.extracted_at,
    }
