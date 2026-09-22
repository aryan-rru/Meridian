"""Session JWTs, OAuth-state signing and Fernet encryption for stored OAuth tokens."""

from __future__ import annotations

import base64
import hashlib
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from jose import JWTError, jwt

from app.config import settings

JWT_ALGORITHM = "HS256"


# ---------------------------------------------------------------------------
# Token encryption at rest (§13: OAuth tokens must never be stored in plaintext)
# ---------------------------------------------------------------------------
def _fernet() -> Fernet:
    """Build the Fernet cipher from TOKEN_ENCRYPTION_KEY.

    A real 32-byte urlsafe-base64 key is expected. To keep local dev friction low we
    derive a valid key from APP_SECRET when one is not configured — but a deployment
    must set TOKEN_ENCRYPTION_KEY explicitly.
    """
    key = settings.token_encryption_key.strip()
    if key:
        try:
            return Fernet(key.encode() if isinstance(key, str) else key)
        except (ValueError, TypeError):
            pass
    derived = base64.urlsafe_b64encode(hashlib.sha256(settings.app_secret.encode()).digest())
    return Fernet(derived)


def encrypt_token(value: str | None) -> bytes | None:
    if value is None:
        return None
    return _fernet().encrypt(value.encode("utf-8"))


def decrypt_token(value: bytes | None) -> str | None:
    if not value:
        return None
    try:
        return _fernet().decrypt(bytes(value)).decode("utf-8")
    except InvalidToken:
        return None


# ---------------------------------------------------------------------------
# Session JWT (carried in an http-only cookie)
# ---------------------------------------------------------------------------
def create_session_token(
    user_id: uuid.UUID | str,
    workspace_id: uuid.UUID | str | None = None,
    expires_minutes: int | None = None,
) -> str:
    ttl = expires_minutes if expires_minutes is not None else settings.session_ttl_minutes
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "ws": str(workspace_id) if workspace_id else None,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=ttl)).timestamp()),
    }
    return jwt.encode(payload, settings.app_secret, algorithm=JWT_ALGORITHM)


def decode_session_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, settings.app_secret, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None


# ---------------------------------------------------------------------------
# OAuth state (CSRF protection on the login round-trip, §13)
# ---------------------------------------------------------------------------
STATE_TTL_SECONDS = 600


def create_oauth_state(extra: dict[str, Any] | None = None) -> str:
    payload = {
        "nonce": uuid.uuid4().hex,
        "exp": int(time.time()) + STATE_TTL_SECONDS,
        **(extra or {}),
    }
    return jwt.encode(payload, settings.app_secret, algorithm=JWT_ALGORITHM)


def verify_oauth_state(state: str) -> dict[str, Any] | None:
    """Return the state payload if the signature is ours and it has not expired."""
    return decode_session_token(state)
