"""§8.1 — Google sign-in, session cookie and the current-user endpoint."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.crud import workspaces as workspaces_crud
from app.deps import (
    CurrentUser,
    DbSession,
    get_session_payload,
    resolve_workspace_id,
)
from app.models import User
from app.ratelimit import enforce
from app.schemas.auth import (
    DevLoginRequest,
    GoogleStatus,
    MeResponse,
)
from app.schemas.common import MessageResponse
from app.security import create_oauth_state, create_session_token, verify_oauth_state
from app.services.google import oauth as google_oauth

logger = logging.getLogger("meridian.auth")
router = APIRouter(prefix="/auth", tags=["auth"])

STATE_COOKIE = "meridian_oauth_state"
CODE_VERIFIER_COOKIE = "meridian_oauth_code_verifier"
DRIVE_READONLY = "https://www.googleapis.com/auth/drive.readonly"
SHEETS_READONLY = "https://www.googleapis.com/auth/spreadsheets.readonly"


# ---------------------------------------------------------------------------
# Session cookie helpers
# ---------------------------------------------------------------------------
def set_session_cookie(
    response: Response, user_id: uuid.UUID, workspace_id: uuid.UUID | None
) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=create_session_token(user_id, workspace_id),
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        max_age=settings.session_ttl_minutes * 60,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(settings.session_cookie_name, path="/")


def _google_status(user: User) -> GoogleStatus:
    scopes = google_oauth.granted_scopes(user)
    return GoogleStatus(
        connected=bool(user.credential and user.credential.access_token_enc),
        configured=settings.google_configured,
        granted_scopes=scopes,
        can_browse_drive=DRIVE_READONLY in scopes,
        can_read_sheets=SHEETS_READONLY in scopes,
    )


def build_me(db: Session, user: User, workspace_id: uuid.UUID | None) -> MeResponse:
    memberships = workspaces_crud.memberships_for(db, user.id)
    current = None
    current_role = None
    for membership in memberships:
        if workspace_id and membership.workspace_id == workspace_id:
            current = membership.workspace
            current_role = str(membership.role)
    if current is None and memberships:
        current = memberships[0].workspace
        current_role = str(memberships[0].role)

    return MeResponse(
        user=user,
        workspaces=[{"workspace": m.workspace, "role": str(m.role)} for m in memberships],
        current_workspace=current,
        current_role=current_role,
        google=_google_status(user),
    )


# ---------------------------------------------------------------------------
# Google OAuth
# ---------------------------------------------------------------------------
@router.get("/google/login", summary="Redirect to Google consent")
def google_login(request: Request) -> RedirectResponse:
    enforce(request, "auth", settings.auth_rate_limit_per_minute)
    if not settings.google_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Google sign-in is not configured on the server. Add GOOGLE_CLIENT_ID and "
                "GOOGLE_CLIENT_SECRET to backend/.env — see README §Google Cloud Setup."
            ),
        )

    state = create_oauth_state()
    url, code_verifier = google_oauth.build_authorization_url(state)
    response = RedirectResponse(url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    # The state is echoed back by Google and compared against this cookie (§13 CSRF).
    response.set_cookie(
        STATE_COOKIE,
        state,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        max_age=600,
        path="/",
    )
    response.set_cookie(
        CODE_VERIFIER_COOKIE,
        code_verifier,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        max_age=600,
        path="/",
    )
    return response


@router.get("/google/callback", summary="Exchange the code and start a session")
def google_callback(
    request: Request,
    db: DbSession,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    enforce(request, "auth", settings.auth_rate_limit_per_minute)
    failure = RedirectResponse(
        f"{settings.frontend_url}/login?error=", status_code=status.HTTP_307_TEMPORARY_REDIRECT
    )

    def fail(reason: str) -> RedirectResponse:
        logger.info("OAuth callback rejected: %s", reason)
        failure.headers["location"] = f"{settings.frontend_url}/login?error={reason}"
        failure.delete_cookie(STATE_COOKIE, path="/")
        failure.delete_cookie(CODE_VERIFIER_COOKIE, path="/")
        return failure

    if error:
        return fail("access_denied")
    if not code or not state:
        return fail("missing_code")

    cookie_state = request.cookies.get(STATE_COOKIE)
    code_verifier = request.cookies.get(CODE_VERIFIER_COOKIE)
    if (
        not cookie_state
        or cookie_state != state
        or verify_oauth_state(state) is None
        or not code_verifier
    ):
        return fail("invalid_state")

    try:
        credentials = google_oauth.exchange_code_for_credentials(code, code_verifier)
        profile = google_oauth.fetch_userinfo(credentials)
    except google_oauth.GoogleAuthError:
        return fail("exchange_failed")

    email = profile.get("email")
    if not email:
        return fail("no_email")

    user = workspaces_crud.upsert_user(
        db,
        email=email,
        name=profile.get("name", ""),
        google_sub=profile.get("sub"),
        picture_url=profile.get("picture"),
    )
    google_oauth.store_credentials(db, user, credentials)
    workspace = workspaces_crud.ensure_default_workspace(db, user)
    db.commit()

    logger.info("Sign-in succeeded for user %s", user.id)
    response = RedirectResponse(
        f"{settings.frontend_url}/", status_code=status.HTTP_307_TEMPORARY_REDIRECT
    )
    response.delete_cookie(STATE_COOKIE, path="/")
    response.delete_cookie(CODE_VERIFIER_COOKIE, path="/")
    set_session_cookie(response, user.id, workspace.id)
    return response


# ---------------------------------------------------------------------------
# Local development sign-in
# ---------------------------------------------------------------------------
@router.post(
    "/dev-login",
    response_model=MeResponse,
    summary="Local-only sign-in (requires DEV_LOGIN_ENABLED=true)",
)
def dev_login(
    request: Request, response: Response, payload: DevLoginRequest, db: DbSession
) -> MeResponse:
    """Sign in without Google so the seeded workspace is demoable before GCP setup.

    Guarded by ``DEV_LOGIN_ENABLED`` which must be false in any deployed environment.
    Google-backed features (Picker, Drive evidence, save-to-Drive) stay unavailable
    because no OAuth credential is created.
    """
    enforce(request, "auth", settings.auth_rate_limit_per_minute)
    if not settings.dev_login_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")

    email = (payload.email or settings.dev_login_email).strip().lower()
    user = workspaces_crud.upsert_user(db, email=email, name=email.split("@")[0])
    workspace = workspaces_crud.ensure_default_workspace(db, user)
    db.commit()

    logger.warning("DEV LOGIN used for %s — do not enable this outside local dev.", email)
    set_session_cookie(response, user.id, workspace.id)
    return build_me(db, user, workspace.id)


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------
@router.post("/logout", response_model=MessageResponse, summary="Clear the session")
def logout(response: Response) -> MessageResponse:
    clear_session_cookie(response)
    return MessageResponse(message="Signed out.")


@router.get("/me", response_model=MeResponse, summary="Current user, workspaces and scopes")
def me(request: Request, user: CurrentUser, db: DbSession) -> MeResponse:
    payload = get_session_payload(request)
    try:
        workspace_id = resolve_workspace_id(payload, db, user)
    except HTTPException:
        workspace_id = None
    return build_me(db, user, workspace_id)
