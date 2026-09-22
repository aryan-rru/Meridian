"""§9.4 — Google Drive: metadata, search, upload, download/export for extraction."""

from __future__ import annotations

import io
import logging
from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

logger = logging.getLogger(__name__)

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
GOOGLE_SHEET_MIME = "application/vnd.google-apps.spreadsheet"
FOLDER_MIME = "application/vnd.google-apps.folder"

FILE_FIELDS = "id,name,mimeType,webViewLink,iconLink,modifiedTime,size,owners(displayName)"


class DriveError(RuntimeError):
    """A Drive call failed in a way worth showing the user."""


class DriveFileNotFound(DriveError):
    """The Drive file no longer exists or is no longer shared with the app."""


class DriveClient:
    """Thin wrapper over the Drive v3 client.

    Kept deliberately small and injectable so tests can pass a fake ``service``.
    """

    def __init__(self, credentials: Credentials | None = None, service: Any | None = None):
        if service is not None:
            self.service = service
        else:
            if credentials is None:
                raise DriveError("Drive client requires credentials.")
            self.service = build("drive", "v3", credentials=credentials, cache_discovery=False)

    # -- reads -------------------------------------------------------------
    def get_file(self, file_id: str) -> dict[str, Any]:
        try:
            return (
                self.service.files()
                .get(fileId=file_id, fields=FILE_FIELDS, supportsAllDrives=True)
                .execute()
            )
        except HttpError as exc:
            if exc.resp.status == 404:
                raise DriveFileNotFound(f"Drive file {file_id} was not found.") from exc
            if exc.resp.status == 403:
                raise DriveError(
                    "Access to that Drive file was denied. With the drive.file scope the app "
                    "can only open files you picked or it created."
                ) from exc
            raise DriveError(f"Drive returned an error ({exc.resp.status}).") from exc

    def list_files(
        self, query: str | None = None, mime_type: str | None = None, page_size: int = 50
    ) -> list[dict[str, Any]]:
        """Search Drive.

        Requires a broad scope; with ``drive.file`` only app-visible files appear.
        """
        clauses = ["trashed = false"]
        if query:
            safe = query.replace("'", "\\'")
            clauses.append(f"name contains '{safe}'")
        if mime_type:
            clauses.append(f"mimeType = '{mime_type}'")
        try:
            response = (
                self.service.files()
                .list(
                    q=" and ".join(clauses),
                    pageSize=min(page_size, 100),
                    fields=f"files({FILE_FIELDS})",
                    orderBy="modifiedTime desc",
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                )
                .execute()
            )
        except HttpError as exc:
            raise DriveError(f"Drive search failed ({exc.resp.status}).") from exc
        return response.get("files", [])

    def download_bytes(self, file_id: str, mime_type: str | None = None) -> bytes:
        """Return workbook bytes, exporting native Google Sheets to .xlsx first (§9.4)."""
        if mime_type is None:
            mime_type = self.get_file(file_id).get("mimeType")

        try:
            if mime_type == GOOGLE_SHEET_MIME:
                request = self.service.files().export_media(fileId=file_id, mimeType=XLSX_MIME)
            else:
                request = self.service.files().get_media(fileId=file_id)

            buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(buffer, request)
            done = False
            while not done:
                _status, done = downloader.next_chunk()
            return buffer.getvalue()
        except HttpError as exc:
            if exc.resp.status == 404:
                raise DriveFileNotFound(f"Drive file {file_id} was not found.") from exc
            raise DriveError(f"Could not download the Drive file ({exc.resp.status}).") from exc

    # -- writes ------------------------------------------------------------
    def ensure_folder(self, name: str, parent_id: str | None = None) -> str:
        """Find or create the app's evidence folder and return its id."""
        clauses = [f"mimeType = '{FOLDER_MIME}'", f"name = '{name}'", "trashed = false"]
        if parent_id:
            clauses.append(f"'{parent_id}' in parents")
        try:
            existing = (
                self.service.files()
                .list(q=" and ".join(clauses), fields="files(id,name)", pageSize=1)
                .execute()
                .get("files", [])
            )
            if existing:
                return existing[0]["id"]
        except HttpError:
            # With drive.file the app cannot search pre-existing folders; just create one.
            logger.info("Folder lookup unavailable under the granted scope; creating a new folder.")

        metadata: dict[str, Any] = {"name": name, "mimeType": FOLDER_MIME}
        if parent_id:
            metadata["parents"] = [parent_id]
        try:
            created = self.service.files().create(body=metadata, fields="id").execute()
        except HttpError as exc:
            raise DriveError(f"Could not create the Drive folder ({exc.resp.status}).") from exc
        return created["id"]

    def upload_bytes(
        self,
        data: bytes,
        name: str,
        mime_type: str = XLSX_MIME,
        parent_id: str | None = None,
    ) -> dict[str, Any]:
        metadata: dict[str, Any] = {"name": name}
        if parent_id:
            metadata["parents"] = [parent_id]
        media = MediaIoBaseUpload(io.BytesIO(data), mimetype=mime_type, resumable=False)
        try:
            return (
                self.service.files()
                .create(body=metadata, media_body=media, fields=FILE_FIELDS)
                .execute()
            )
        except HttpError as exc:
            raise DriveError(f"Upload to Drive failed ({exc.resp.status}).") from exc
