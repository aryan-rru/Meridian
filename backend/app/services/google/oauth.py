"""§9.1–9.3 — Google OAuth 2.0 Authorization Code flow and token lifecycle.

Google is both the identity provider (login) and the authorization source (Drive).
Tokens are Fernet-encrypted before they touch the database and are never sent to
the browser.
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from sqlalchemy.orm import Session

from app.config import settings
from app.db import utcnow
from app.models import OAuthCredential, User
from app.security import decrypt_token, encrypt_token

logger = logging.getLogger(__name__)

TOKEN_URI = "https://oauth2.googleapis.com/token"
AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


class GoogleAuthError(RuntimeError):
    """Raised when the OAuth exchange or a token refresh cannot be completed."""


def _client_config() -> dict[str, Any]:
    return {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": AUTH_URI,
            "token_uri": TOKEN_URI,
            "redirect_uris": [settings.google_redirect_uri],
        }
    }


def _build_flow(state: str | None = None, code_verifier: str | None = None) -> Flow:
    if not settings.google_configured:
        raise GoogleAuthError(
            "Google OAuth is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET "
            "in backend/.env (see README §Google Cloud Setup)."
        )
    flow = Flow.from_client_config(_client_config(), scopes=settings.scopes_list, state=state)
    flow.redirect_uri = settings.google_redirect_uri
    flow.code_verifier = code_verifier
    return flow


def build_authorization_url(state: str) -> tuple[str, str]:
    """Consent URL. ``access_type=offline`` + ``prompt=consent`` guarantee a refresh token."""
    flow = _build_flow(state=state)
    url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state,
    )
    if not flow.code_verifier:
        raise GoogleAuthError("Could not initialize the Google sign-in security challenge.")
    return url, flow.code_verifier


def exchange_code_for_credentials(code: str, code_verifier: str) -> Credentials:
    flow = _build_flow(code_verifier=code_verifier)
    try:
        # OAUTHLIB_RELAX_TOKEN_SCOPE tells oauthlib to emit a signal instead of
        # raising a Warning when Google returns canonical scope URLs in place of
        # the short aliases we requested (e.g. "email" →
        # "https://www.googleapis.com/auth/userinfo.email"). Without this the
        # Warning is raised *inside* parse_request_body_response before the token
        # is stored, which causes flow.credentials to fail with "no access token".
        os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"
        flow.fetch_token(code=code)
    except Exception as exc:  # noqa: BLE001 - surface a clean error, never the raw token payload
        logger.warning(
            "OAuth code exchange failed: %s — %s",
            type(exc).__name__,
            str(exc) or "no details provided",
        )
        raise GoogleAuthError("Could not exchange the authorization code with Google.") from exc
    finally:
        os.environ.pop("OAUTHLIB_RELAX_TOKEN_SCOPE", None)
    return flow.credentials


def fetch_userinfo(credentials: Credentials) -> dict[str, Any]:
    """Read the OpenID profile for the signed-in account."""
    try:
        response = httpx.get(
            USERINFO_URL,
            headers={"Authorization": f"Bearer {credentials.token}"},
            timeout=10.0,
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as exc:
        raise GoogleAuthError("Could not read your Google profile.") from exc


def store_credentials(db: Session, user: User, credentials: Credentials) -> OAuthCredential:
    """Persist encrypted tokens, preserving an existing refresh token if Google omits one."""
    record = user.credential or OAuthCredential(user_id=user.id)

    record.access_token_enc = encrypt_token(credentials.token)
    if credentials.refresh_token:
        record.refresh_token_enc = encrypt_token(credentials.refresh_token)
    # else: keep the refresh token we already hold — Google only returns it on first consent.

    expiry = credentials.expiry
    if expiry is not None and expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=UTC)
    record.token_expiry = expiry
    record.scopes = list(credentials.scopes or settings.scopes_list)

    if record.id is None or user.credential is None:
        db.add(record)
    db.flush()
    return record


def _to_credentials(record: OAuthCredential) -> Credentials:
    return Credentials(
        token=decrypt_token(record.access_token_enc),
        refresh_token=decrypt_token(record.refresh_token_enc),
        token_uri=TOKEN_URI,
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        scopes=list(record.scopes or []),
    )


def get_google_credentials(db: Session, user: User) -> Credentials:
    """Return usable credentials, refreshing (and re-persisting) when expired (§9.3)."""
    record = user.credential
    if record is None or not record.access_token_enc:
        raise GoogleAuthError(
            "This account has no Google authorization stored. Sign in with Google to grant access."
        )

    credentials = _to_credentials(record)
    expiry = record.token_expiry
    if expiry is not None and expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=UTC)

    expired = expiry is not None and expiry <= utcnow() + timedelta(seconds=60)
    if expired or not credentials.token:
        if not credentials.refresh_token:
            raise GoogleAuthError(
                "Your Google access has expired and no refresh token is stored. "
                "Please sign in with Google again."
            )
        try:
            credentials.refresh(GoogleRequest())
        except Exception as exc:  # noqa: BLE001
            logger.warning("Token refresh failed for user %s: %s", user.id, type(exc).__name__)
            raise GoogleAuthError(
                "Could not refresh your Google access. Please sign in with Google again."
            ) from exc
        record.access_token_enc = encrypt_token(credentials.token)
        new_expiry = credentials.expiry
        if new_expiry is not None and new_expiry.tzinfo is None:
            new_expiry = new_expiry.replace(tzinfo=UTC)
        record.token_expiry = new_expiry
        db.flush()

    return credentials


def granted_scopes(user: User) -> list[str]:
    return list(user.credential.scopes) if user.credential else []


def has_scope(user: User, scope: str) -> bool:
    return scope in granted_scopes(user)


def revoke(credentials: Credentials) -> None:  # pragma: no cover - network side-effect
    """Best-effort revocation on logout; failures are non-fatal."""
    token = credentials.token or credentials.refresh_token
    if not token:
        return
    try:
        httpx.post(
            "https://oauth2.googleapis.com/revoke",
            params={"token": token},
            timeout=5.0,
        )
    except httpx.HTTPError:
        logger.info("Token revocation call failed (ignored).")


def expiry_from_now(seconds: int) -> datetime:
    return utcnow() + timedelta(seconds=seconds)
