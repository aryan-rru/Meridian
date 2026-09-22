"""FastAPI dependencies: session → user → workspace membership → role enforcement.

Every content endpoint depends on :func:`get_context`, which resolves the caller's
current workspace *and* verifies membership, so workspace isolation (§13) is enforced
in one place rather than per-router.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.db import get_db
from app.models import (
    ADMIN_ROLES,
    WRITE_ROLES,
    ScoringConfig,
    User,
    Workspace,
    WorkspaceMember,
    WorkspaceRole,
    default_config_kwargs,
)
from app.security import decode_session_token
from app.services.scoring import ScoringContext

DbSession = Annotated[Session, Depends(get_db)]


def _unauthenticated() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not signed in.",
        headers={"WWW-Authenticate": "Cookie"},
    )


def get_session_payload(request: Request) -> dict:
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise _unauthenticated()
    payload = decode_session_token(token)
    if not payload or not payload.get("sub"):
        raise _unauthenticated()
    return payload


def get_current_user(payload: Annotated[dict, Depends(get_session_payload)], db: DbSession) -> User:
    try:
        user_id = uuid.UUID(str(payload["sub"]))
    except (ValueError, TypeError) as exc:
        raise _unauthenticated() from exc

    user = db.execute(
        select(User).options(selectinload(User.credential)).where(User.id == user_id)
    ).scalar_one_or_none()
    if user is None:
        raise _unauthenticated()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


@dataclass
class WorkspaceContext:
    """Everything a content endpoint needs about who is asking and where."""

    user: User
    workspace: Workspace
    role: str
    db: Session

    @property
    def workspace_id(self) -> uuid.UUID:
        return self.workspace.id

    @property
    def can_write(self) -> bool:
        return self.role in {r.value for r in WRITE_ROLES}

    @property
    def can_administer(self) -> bool:
        return self.role in {r.value for r in ADMIN_ROLES}


def _membership(db: Session, user: User, workspace_id: uuid.UUID) -> WorkspaceMember | None:
    return db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.user_id == user.id,
            WorkspaceMember.workspace_id == workspace_id,
        )
    ).scalar_one_or_none()


def resolve_workspace_id(payload: dict, db: Session, user: User) -> uuid.UUID:
    """Current workspace from the session, falling back to the user's first membership."""
    raw = payload.get("ws")
    if raw:
        try:
            return uuid.UUID(str(raw))
        except (ValueError, TypeError):
            pass
    first = db.execute(
        select(WorkspaceMember)
        .where(WorkspaceMember.user_id == user.id)
        .order_by(WorkspaceMember.created_at)
        .limit(1)
    ).scalar_one_or_none()
    if first is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not belong to any workspace yet.",
        )
    return first.workspace_id


def get_context(
    payload: Annotated[dict, Depends(get_session_payload)],
    user: CurrentUser,
    db: DbSession,
) -> WorkspaceContext:
    workspace_id = resolve_workspace_id(payload, db, user)
    membership = _membership(db, user, workspace_id)
    if membership is None:
        # Either the workspace is gone or the caller was removed from it (§13).
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this workspace.",
        )
    workspace = db.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found.")
    return WorkspaceContext(user=user, workspace=workspace, role=str(membership.role), db=db)


Context = Annotated[WorkspaceContext, Depends(get_context)]


def require_write(ctx: Context) -> WorkspaceContext:
    if not ctx.can_write:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your role in this workspace is read-only.",
        )
    return ctx


def require_admin(ctx: Context) -> WorkspaceContext:
    if not ctx.can_administer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only workspace owners and admins can do this.",
        )
    return ctx


WriteContext = Annotated[WorkspaceContext, Depends(require_write)]
AdminContext = Annotated[WorkspaceContext, Depends(require_admin)]


def get_or_create_config(db: Session, workspace_id: uuid.UUID) -> ScoringConfig:
    config = db.execute(
        select(ScoringConfig).where(ScoringConfig.workspace_id == workspace_id)
    ).scalar_one_or_none()
    if config is None:
        config = ScoringConfig(workspace_id=workspace_id, **default_config_kwargs())
        db.add(config)
        db.flush()
    return config


def get_scoring_context(ctx: Context) -> ScoringContext:
    """The workspace's scoring configuration, snapshotted for this request."""
    return ScoringContext.from_model(get_or_create_config(ctx.db, ctx.workspace_id))


Scoring = Annotated[ScoringContext, Depends(get_scoring_context)]


def ensure_role_value(role: str) -> str:
    valid = {r.value for r in WorkspaceRole}
    if role not in valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role '{role}'. Allowed: {', '.join(sorted(valid))}.",
        )
    return role
