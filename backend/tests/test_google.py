"""§18 — Google layer: Drive client against a fake service, OAuth token refresh,
and evidence extraction parsing against an in-memory fixture workbook.

No network and no real Google credentials are used.
"""

from __future__ import annotations

import io
from datetime import UTC, datetime, timedelta

import pytest
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError
from openpyxl import Workbook

from app.models import OAuthCredential, User
from app.security import decrypt_token, encrypt_token
from app.services.excel import extract_evidence_payload
from app.services.google import oauth as google_oauth
from app.services.google.drive import DriveClient, DriveError, DriveFileNotFound


# ---------------------------------------------------------------------------
# Fake Drive service
# ---------------------------------------------------------------------------
class _Resp:
    def __init__(self, status: int):
        self.status = status
        self.reason = "Error"


class _Exec:
    def __init__(self, result=None, error: Exception | None = None):
        self._result = result
        self._error = error

    def execute(self):
        if self._error is not None:
            raise self._error
        return self._result


class _FakeFiles:
    def __init__(self, *, get_result=None, get_error=None, list_result=None, create_result=None):
        self._get_result = get_result
        self._get_error = get_error
        self._list_result = list_result if list_result is not None else {"files": []}
        self._create_result = (
            create_result if create_result is not None else {"id": "new", "name": "x"}
        )

    def get(self, **_kwargs):
        return _Exec(self._get_result, self._get_error)

    def list(self, **_kwargs):
        return _Exec(self._list_result)

    def create(self, **_kwargs):
        return _Exec(self._create_result)


class _FakeService:
    def __init__(self, files: _FakeFiles):
        self._files = files

    def files(self) -> _FakeFiles:
        return self._files


def _client(files: _FakeFiles) -> DriveClient:
    return DriveClient(service=_FakeService(files))


# ---------------------------------------------------------------------------
# DriveClient
# ---------------------------------------------------------------------------
def test_drive_requires_credentials_or_service():
    with pytest.raises(DriveError):
        DriveClient()


def test_drive_get_file_ok():
    client = _client(_FakeFiles(get_result={"id": "f1", "name": "Doc"}))
    assert client.get_file("f1")["name"] == "Doc"


def test_drive_get_file_404_maps_to_not_found():
    error = HttpError(_Resp(404), b"{}")
    client = _client(_FakeFiles(get_error=error))
    with pytest.raises(DriveFileNotFound):
        client.get_file("missing")


def test_drive_get_file_403_maps_to_drive_error():
    error = HttpError(_Resp(403), b"{}")
    client = _client(_FakeFiles(get_error=error))
    with pytest.raises(DriveError):
        client.get_file("forbidden")


def test_drive_list_files():
    client = _client(_FakeFiles(list_result={"files": [{"id": "a"}, {"id": "b"}]}))
    assert [f["id"] for f in client.list_files(query="report")] == ["a", "b"]


def test_drive_ensure_folder_reuses_existing():
    client = _client(_FakeFiles(list_result={"files": [{"id": "fld", "name": "Evidence"}]}))
    assert client.ensure_folder("Evidence") == "fld"


def test_drive_upload_bytes():
    client = _client(_FakeFiles(create_result={"id": "up1", "name": "wb.xlsx"}))
    meta = client.upload_bytes(b"payload", name="wb.xlsx")
    assert meta["id"] == "up1"


# ---------------------------------------------------------------------------
# OAuth token refresh (§9.3)
# ---------------------------------------------------------------------------
def _user_with_credential(db, *, refresh_token: str | None) -> User:
    user = User(email="oauth@example.com", name="OAuth User")
    db.add(user)
    db.flush()
    db.add(
        OAuthCredential(
            user_id=user.id,
            access_token_enc=encrypt_token("stale-access"),
            refresh_token_enc=encrypt_token(refresh_token) if refresh_token else None,
            token_expiry=datetime.now(UTC) - timedelta(hours=1),  # expired
            scopes=["https://www.googleapis.com/auth/drive.file"],
        )
    )
    db.flush()
    db.refresh(user)
    return user


def test_expired_token_is_refreshed_and_re_persisted(db, monkeypatch):
    user = _user_with_credential(db, refresh_token="refresh-token")

    def fake_refresh(self, _request):
        self.token = "fresh-access"
        self.expiry = datetime(2999, 1, 1)  # naive, as the google lib returns

    monkeypatch.setattr(Credentials, "refresh", fake_refresh)

    credentials = google_oauth.get_google_credentials(db, user)
    assert credentials.token == "fresh-access"
    # The new access token is written back encrypted.
    assert decrypt_token(user.credential.access_token_enc) == "fresh-access"


def test_expired_token_without_refresh_token_raises(db):
    user = _user_with_credential(db, refresh_token=None)
    with pytest.raises(google_oauth.GoogleAuthError):
        google_oauth.get_google_credentials(db, user)


def test_no_stored_credential_raises(db):
    user = User(email="nocreds@example.com", name="No Creds")
    db.add(user)
    db.flush()
    with pytest.raises(google_oauth.GoogleAuthError):
        google_oauth.get_google_credentials(db, user)


# ---------------------------------------------------------------------------
# Evidence extraction parsing (§9.5)
# ---------------------------------------------------------------------------
def test_extract_evidence_payload_parses_sheets_and_summary():
    workbook = Workbook()
    data_sheet = workbook.active
    data_sheet.title = "Data"
    data_sheet.append(["control", "result"])
    data_sheet.append(["CTL-1", "pass"])
    data_sheet.append(["CTL-2", "fail"])

    summary_sheet = workbook.create_sheet("Summary")
    summary_sheet.append(["metric", "value"])
    summary_sheet.append(["passed", 1])
    summary_sheet.append(["owner", "SecOps"])

    buffer = io.BytesIO()
    workbook.save(buffer)

    payload = extract_evidence_payload(buffer.getvalue())
    assert payload["extracted_with"] == "pandas/openpyxl"
    assert payload["sheet_count"] == 2
    assert {s["name"] for s in payload["sheets"]} == {"Data", "Summary"}
    assert float(payload["summary"]["passed"]) == 1.0
    assert payload["summary"]["owner"] == "SecOps"
