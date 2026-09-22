"""§8.3 — frameworks and requirements (seeded reference data, read-mostly)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.deps import AdminContext, Context, DbSession
from app.models import Control, ControlRequirementMapping, Framework, Requirement
from app.schemas.common import MessageResponse
from app.schemas.framework import (
    FrameworkRead,
    RequirementCreate,
    RequirementRead,
    RequirementUpdate,
)

router = APIRouter(tags=["frameworks"])


@router.get("/frameworks", response_model=list[FrameworkRead], summary="List frameworks")
def list_frameworks(db: DbSession, _ctx: Context) -> list[dict]:
    counts = dict(
        db.execute(
            select(Requirement.framework_id, func.count()).group_by(Requirement.framework_id)
        ).all()
    )
    frameworks = (
        db.execute(select(Framework).order_by(Framework.sort_order, Framework.key)).scalars().all()
    )
    return [
        {
            "id": f.id,
            "created_at": f.created_at,
            "updated_at": f.updated_at,
            "key": f.key,
            "name": f.name,
            "version": f.version,
            "description": f.description,
            "color": f.color,
            "sort_order": f.sort_order,
            "requirement_count": int(counts.get(f.id, 0)),
        }
        for f in frameworks
    ]


@router.get("/requirements", response_model=list[RequirementRead], summary="List requirements")
def list_requirements(
    db: DbSession,
    ctx: Context,
    framework: str | None = Query(default=None, description="Framework key, e.g. ISO27001"),
    category: str | None = None,
    q: str | None = Query(default=None, description="Search code or title"),
) -> list[dict]:
    stmt = (
        select(Requirement)
        .options(selectinload(Requirement.framework))
        .join(Framework, Framework.id == Requirement.framework_id)
    )
    if framework:
        stmt = stmt.where(Framework.key == framework)
    if category:
        stmt = stmt.where(Requirement.category == category)
    if q:
        pattern = f"%{q.lower()}%"
        stmt = stmt.where(
            func.lower(Requirement.code).like(pattern)
            | func.lower(Requirement.title).like(pattern)
            | func.lower(Requirement.description).like(pattern)
        )

    requirements = (
        db.execute(
            stmt.order_by(
                Framework.sort_order, Framework.key, Requirement.sort_order, Requirement.code
            )
        )
        .scalars()
        .all()
    )

    # How many of *this workspace's* controls answer each requirement.
    mapped_counts = dict(
        db.execute(
            select(ControlRequirementMapping.requirement_id, func.count())
            .join(Control, Control.id == ControlRequirementMapping.control_id)
            .where(Control.workspace_id == ctx.workspace_id)
            .group_by(ControlRequirementMapping.requirement_id)
        ).all()
    )

    return [_read_model(r, int(mapped_counts.get(r.id, 0))) for r in requirements]


def _read_model(requirement: Requirement, mapped_count: int = 0) -> dict:
    framework = requirement.framework
    return {
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
        "mapped_control_count": mapped_count,
    }


def _get_requirement(db, requirement_id: uuid.UUID) -> Requirement:
    requirement = db.execute(
        select(Requirement)
        .options(selectinload(Requirement.framework))
        .where(Requirement.id == requirement_id)
    ).scalar_one_or_none()
    if requirement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requirement not found.")
    return requirement


@router.get("/requirements/{requirement_id}", response_model=RequirementRead)
def get_requirement(requirement_id: uuid.UUID, db: DbSession, _ctx: Context) -> dict:
    return _read_model(_get_requirement(db, requirement_id))


@router.post(
    "/requirements",
    response_model=RequirementRead,
    status_code=201,
    summary="Add a requirement (admin)",
)
def create_requirement(payload: RequirementCreate, db: DbSession, _ctx: AdminContext) -> dict:
    framework = db.get(Framework, payload.framework_id)
    if framework is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Framework not found.")

    clash = db.execute(
        select(Requirement.id).where(
            Requirement.framework_id == payload.framework_id, Requirement.code == payload.code
        )
    ).scalar_one_or_none()
    if clash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"'{payload.code}' already exists in {framework.key}.",
        )

    requirement = Requirement(**payload.model_dump())
    db.add(requirement)
    db.commit()
    db.refresh(requirement)
    return _read_model(_get_requirement(db, requirement.id))


@router.put("/requirements/{requirement_id}", response_model=RequirementRead)
def update_requirement(
    requirement_id: uuid.UUID, payload: RequirementUpdate, db: DbSession, _ctx: AdminContext
) -> dict:
    requirement = _get_requirement(db, requirement_id)
    data = payload.model_dump(exclude_unset=True)
    if "code" in data and data["code"] != requirement.code:
        clash = db.execute(
            select(Requirement.id).where(
                Requirement.framework_id == requirement.framework_id,
                Requirement.code == data["code"],
                Requirement.id != requirement.id,
            )
        ).scalar_one_or_none()
        if clash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="That code is already in use."
            )
    for key, value in data.items():
        setattr(requirement, key, value)
    db.commit()
    db.refresh(requirement)
    return _read_model(_get_requirement(db, requirement.id))


@router.delete("/requirements/{requirement_id}", response_model=MessageResponse)
def delete_requirement(
    requirement_id: uuid.UUID, db: DbSession, _ctx: AdminContext
) -> MessageResponse:
    requirement = _get_requirement(db, requirement_id)
    db.delete(requirement)
    db.commit()
    return MessageResponse(message="Requirement deleted.")
