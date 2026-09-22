"""§8.2 — workspaces, switching and membership."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Response

from app.crud import workspaces as crud
from app.deps import AdminContext, Context, CurrentUser, DbSession, ensure_role_value
from app.routers.auth import set_session_cookie
from app.schemas.auth import (
    MemberInvite,
    MemberRead,
    SwitchWorkspaceResponse,
    WorkspaceCreate,
    WorkspaceMembership,
    WorkspaceRead,
)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("", response_model=list[WorkspaceMembership], summary="Workspaces you belong to")
def list_workspaces(user: CurrentUser, db: DbSession) -> list[dict]:
    return [
        {"workspace": m.workspace, "role": str(m.role)} for m in crud.memberships_for(db, user.id)
    ]


@router.post("", response_model=WorkspaceRead, status_code=201, summary="Create a workspace")
def create_workspace(payload: WorkspaceCreate, user: CurrentUser, db: DbSession) -> WorkspaceRead:
    workspace = crud.create_workspace(db, user, payload.name)
    db.commit()
    db.refresh(workspace)
    return workspace


@router.post(
    "/{workspace_id}/switch",
    response_model=SwitchWorkspaceResponse,
    summary="Set the current workspace on the session",
)
def switch_workspace(
    workspace_id: uuid.UUID, response: Response, user: CurrentUser, db: DbSession
) -> SwitchWorkspaceResponse:
    membership = crud.require_membership(db, user.id, workspace_id)
    # The current workspace lives in the signed session token, so re-issue the cookie.
    set_session_cookie(response, user.id, workspace_id)
    return SwitchWorkspaceResponse(
        current_workspace=membership.workspace,
        role=str(membership.role),
        workspace_id=workspace_id,
    )


@router.get("/{workspace_id}/members", response_model=list[MemberRead], summary="List members")
def list_members(workspace_id: uuid.UUID, user: CurrentUser, db: DbSession) -> list[MemberRead]:
    crud.require_membership(db, user.id, workspace_id)
    return crud.list_members(db, workspace_id)


@router.post(
    "/{workspace_id}/members",
    response_model=MemberRead,
    status_code=201,
    summary="Invite a member by email",
)
def invite_member(
    workspace_id: uuid.UUID, payload: MemberInvite, ctx: AdminContext, db: DbSession
) -> MemberRead:
    # AdminContext already proved the caller administers their *current* workspace;
    # confirm the path workspace is that same one.
    crud.require_membership(db, ctx.user.id, workspace_id)
    if not ctx.can_administer or ctx.workspace_id != workspace_id:
        membership = crud.require_membership(db, ctx.user.id, workspace_id)
        ensure_role_value(str(membership.role))

    member = crud.add_member(
        db, workspace_id, str(payload.email).lower(), ensure_role_value(payload.role)
    )
    db.commit()
    db.refresh(member)
    return member


@router.get("/current", response_model=WorkspaceRead, summary="The active workspace")
def current_workspace(ctx: Context) -> WorkspaceRead:
    return ctx.workspace
