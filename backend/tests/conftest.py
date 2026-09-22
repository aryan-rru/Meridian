"""Shared pytest fixtures.

The env vars below MUST be set before *anything* under ``app.*`` is imported:
``app.config`` reads settings at import time (lru-cached), and ``app.db`` builds the
engine from ``settings.database_url`` at import. pytest always imports this conftest
before collecting the test modules, so setting them here is sufficient.
"""

from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path

from cryptography.fernet import Fernet

# --- Environment (before app.* imports) --------------------------------------
_DB_PATH = Path(tempfile.gettempdir()) / f"meridian_test_{uuid.uuid4().hex}.db"
os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{_DB_PATH.as_posix()}"
os.environ["DEV_LOGIN_ENABLED"] = "true"
os.environ["APP_SECRET"] = "test-app-secret-not-for-production"
os.environ["TOKEN_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
# Force Google to look unconfigured regardless of any stray backend/.env: an empty
# OS env var still wins over a value in the .env file (env > .env in pydantic-settings).
os.environ["GOOGLE_CLIENT_ID"] = ""
os.environ["GOOGLE_CLIENT_SECRET"] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import ratelimit  # noqa: E402
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import seed  # noqa: E402


@pytest.fixture(autouse=True)
def _schema():
    """Give every test a pristine schema and an empty rate-limit window."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    ratelimit.reset()
    yield
    ratelimit.reset()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db(_schema):
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def seeded(db):
    """The seeded 'Sample Org' workspace, returning the same session used to seed it."""
    seed(db)
    return db


@pytest.fixture()
def client(_schema):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def auth_client(client, seeded):
    """A client signed in (dev-login) as the demo owner of the seeded workspace."""
    response = client.post("/api/auth/dev-login", json={})
    assert response.status_code == 200, response.text
    return client
