"""Workspace, membership and user persistence."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.deps import get_or_create_config
from app.models import User, Workspace, WorkspaceMember, WorkspaceRole


def memberships_for(db: Session, user_id: uuid.UUID) -> list[WorkspaceMember]:
    return list(
        db.execute(
            select(WorkspaceMember)
            .options(selectinload(WorkspaceMember.workspace))
            .where(WorkspaceMember.user_id == user_id)
            .order_by(WorkspaceMember.created_at)
        )
        .scalars()
        .all()
    )


def create_workspace(db: Session, user: User, name: str) -> Workspace:
    """Create a workspace, make the creator its owner, and seed default settings."""
    workspace = Workspace(name=name, created_by=user.id)
    db.add(workspace)
    db.flush()

    db.add(
        WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role=WorkspaceRole.OWNER.value)
    )
    get_or_create_config(db, workspace.id)
    db.flush()
    return workspace


def get_membership(
    db: Session, user_id: uuid.UUID, workspace_id: uuid.UUID
) -> WorkspaceMember | None:
    return db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.user_id == user_id, WorkspaceMember.workspace_id == workspace_id
        )
    ).scalar_one_or_none()


def require_membership(db: Session, user_id: uuid.UUID, workspace_id: uuid.UUID) -> WorkspaceMember:
    membership = get_membership(db, user_id, workspace_id)
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this workspace.",
        )
    return membership


def list_members(db: Session, workspace_id: uuid.UUID) -> list[WorkspaceMember]:
    return list(
        db.execute(
            select(WorkspaceMember)
            .options(selectinload(WorkspaceMember.user))
            .where(WorkspaceMember.workspace_id == workspace_id)
            .order_by(WorkspaceMember.created_at)
        )
        .scalars()
        .all()
    )


def upsert_user(
    db: Session,
    email: str,
    name: str = "",
    google_sub: str | None = None,
    picture_url: str | None = None,
) -> User:
    """Find a user by Google subject then email, creating one if neither matches."""
    user: User | None = None
    if google_sub:
        user = db.execute(
            select(User).options(selectinload(User.credential)).where(User.google_sub == google_sub)
        ).scalar_one_or_none()
    if user is None:
        user = db.execute(
            select(User).options(selectinload(User.credential)).where(User.email == email)
        ).scalar_one_or_none()

    if user is None:
        user = User(email=email, name=name or email, google_sub=google_sub, picture_url=picture_url)
        db.add(user)
        db.flush()
        return user

    if google_sub and not user.google_sub:
        user.google_sub = google_sub
    if name:
        user.name = name
    if picture_url:
        user.picture_url = picture_url
    db.flush()
    return user


def add_member(db: Session, workspace_id: uuid.UUID, email: str, role: str) -> WorkspaceMember:
    """Invite by email. The user row is created ahead of their first sign-in."""
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None:
        user = User(email=email, name=email)
        db.add(user)
        db.flush()

    existing = get_membership(db, user.id, workspace_id)
    if existing:
        existing.role = role
        db.flush()
        return existing

    membership = WorkspaceMember(workspace_id=workspace_id, user_id=user.id, role=role)
    db.add(membership)
    db.flush()
    return membership


def ensure_default_workspace(db: Session, user: User) -> Workspace:
    """Give a brand-new user somewhere to work."""
    memberships = memberships_for(db, user.id)
    if memberships:
        return memberships[0].workspace
    return create_workspace(db, user, f"{user.name or user.email}'s Workspace")
