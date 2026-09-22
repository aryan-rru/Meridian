"""§9.4 — optional live read of native Google Sheets (needs `spreadsheets.readonly`).

When that scope has not been granted the app falls back to exporting the sheet as
.xlsx through :class:`~app.services.google.drive.DriveClient`, so this module is a
nice-to-have rather than a dependency.
"""

from __future__ import annotations

from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SHEETS_READONLY_SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"


class SheetsError(RuntimeError):
    pass


class SheetsClient:
    def __init__(self, credentials: Credentials | None = None, service: Any | None = None):
        if service is not None:
            self.service = service
        else:
            if credentials is None:
                raise SheetsError("Sheets client requires credentials.")
            self.service = build("sheets", "v4", credentials=credentials, cache_discovery=False)

    def get_metadata(self, spreadsheet_id: str) -> dict[str, Any]:
        try:
            return (
                self.service.spreadsheets()
                .get(spreadsheetId=spreadsheet_id, fields="properties.title,sheets.properties")
                .execute()
            )
        except HttpError as exc:
            raise SheetsError(f"Could not read the spreadsheet ({exc.resp.status}).") from exc

    def get_values(self, spreadsheet_id: str, range_: str = "A1:Z1000") -> list[list[Any]]:
        try:
            response = (
                self.service.spreadsheets()
                .values()
                .get(spreadsheetId=spreadsheet_id, range=range_)
                .execute()
            )
        except HttpError as exc:
            raise SheetsError(f"Could not read sheet values ({exc.resp.status}).") from exc
        return response.get("values", [])
