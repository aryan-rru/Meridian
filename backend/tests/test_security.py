"""§18 / §13 — the security primitives behind sessions and token-at-rest storage:
Fernet token encryption, session JWTs and OAuth-state (CSRF) signing.
"""

from __future__ import annotations

import uuid

from app.security import (
    create_oauth_state,
    create_session_token,
    decode_session_token,
    decrypt_token,
    encrypt_token,
    verify_oauth_state,
)


# ---------------------------------------------------------------------------
# Token encryption at rest (§13)
# ---------------------------------------------------------------------------
def test_token_encryption_roundtrip():
    ciphertext = encrypt_token("super-secret-token")
    assert ciphertext is not None
    assert b"super-secret-token" not in ciphertext  # not stored in plaintext
    assert decrypt_token(ciphertext) == "super-secret-token"


def test_encrypt_and_decrypt_handle_none():
    assert encrypt_token(None) is None
    assert decrypt_token(None) is None


def test_decrypt_of_garbage_returns_none_not_error():
    assert decrypt_token(b"this-is-not-a-fernet-token") is None


# ---------------------------------------------------------------------------
# Session JWT (§13: short-lived token in an http-only cookie)
# ---------------------------------------------------------------------------
def test_session_token_roundtrip():
    user_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    token = create_session_token(user_id, workspace_id)
    payload = decode_session_token(token)
    assert payload is not None
    assert payload["sub"] == str(user_id)
    assert payload["ws"] == str(workspace_id)


def test_expired_session_token_is_rejected():
    token = create_session_token(uuid.uuid4(), uuid.uuid4(), expires_minutes=-1)
    assert decode_session_token(token) is None


def test_tampered_session_token_is_rejected():
    assert decode_session_token("not.a.jwt") is None


# ---------------------------------------------------------------------------
# OAuth state (§13: CSRF protection on the login round-trip)
# ---------------------------------------------------------------------------
def test_oauth_state_roundtrip():
    state = create_oauth_state()
    assert verify_oauth_state(state) is not None


def test_forged_oauth_state_is_rejected():
    assert verify_oauth_state("forged-state") is None
