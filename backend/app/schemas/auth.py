"""Auth, user and workspace schemas (§8.1, §8.2)."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMModel, TimestampedRead


class UserRead(TimestampedRead):
    email: str
    name: str
    picture_url: str | None = None


class WorkspaceRead(TimestampedRead):
    name: str
    evidence_folder_id: str | None = None


class WorkspaceMembership(ORMModel):
    workspace: WorkspaceRead
    role: str


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class MemberInvite(BaseModel):
    email: EmailStr
    role: str = Field(default="member")


class MemberRead(TimestampedRead):
    user: UserRead
    role: str


class GoogleStatus(BaseModel):
    """What the frontend needs to decide which Google features to show (§9.2)."""

    connected: bool
    configured: bool
    granted_scopes: list[str] = []
    can_browse_drive: bool = False
    can_read_sheets: bool = False


class MeResponse(BaseModel):
    user: UserRead
    workspaces: list[WorkspaceMembership]
    current_workspace: WorkspaceRead | None = None
    current_role: str | None = None
    google: GoogleStatus


class DevLoginRequest(BaseModel):
    """Local-development sign-in; only honoured when DEV_LOGIN_ENABLED is true."""

    email: str | None = None


class LoginUrlResponse(BaseModel):
    authorization_url: str
    state: str


class SwitchWorkspaceResponse(BaseModel):
    current_workspace: WorkspaceRead
    role: str
    workspace_id: uuid.UUID
