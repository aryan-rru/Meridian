"""§8.8 — Excel import, Excel export, and save-export-to-Drive."""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, File, HTTPException, Request, Response, UploadFile, status

from app.config import settings
from app.deps import AdminContext, Context, CurrentUser, DbSession, Scoring, WriteContext
from app.ratelimit import enforce
from app.schemas.settings import DriveExportResult, ImportSummaryRead
from app.services.excel import (
    XLSX_MIME,
    export_workspace_xlsx,
    import_workspace_xlsx,
)
from app.services.google import oauth as google_oauth
from app.services.google.drive import DriveClient, DriveError

logger = logging.getLogger("meridian.importexport")

router = APIRouter(tags=["import/export"])

MAX_IMPORT_BYTES = 25 * 1024 * 1024
XLSX_SUFFIXES = (".xlsx", ".xlsm")


def _workbook_name(workspace_name: str) -> str:
    # Kept ASCII: it goes into a latin-1 HTTP Content-Disposition header.
    safe = "".join(c for c in workspace_name if c.isalnum() or c in " -_").strip() or "Workspace"
    return f"Meridian - {safe} - {datetime.now().strftime('%Y-%m-%d')}.xlsx"


@router.post(
    "/import/excel",
    response_model=ImportSummaryRead,
    summary="Upsert controls, requirements, risks and mappings from a workbook",
)
def import_excel(
    request: Request,
    ctx: WriteContext,
    db: DbSession,
    file: UploadFile = File(...),
) -> dict:
    enforce(request, "import", settings.import_rate_limit_per_minute)

    filename = file.filename or ""
    if not filename.lower().endswith(XLSX_SUFFIXES):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please upload an .xlsx file (File → Save As → Excel Workbook).",
        )

    data = file.file.read()
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="That file is empty.")
    if len(data) > MAX_IMPORT_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Workbooks must be under {MAX_IMPORT_BYTES // (1024 * 1024)} MB.",
        )

    try:
        summary = import_workspace_xlsx(db, ctx.workspace_id, data)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - never leak workbook contents into the response
        db.rollback()
        logger.warning("Excel import failed: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="That workbook could not be read. Check it opens in Excel and try again.",
        ) from exc

    db.commit()
    result = summary.as_dict()
    logger.info(
        "Excel import into workspace %s: %s created, %s updated, %s errors",
        ctx.workspace_id,
        result["created"],
        result["updated"],
        len(result["errors"]),
    )
    return result


@router.get(
    "/export/excel",
    summary="Download the whole workspace as a multi-sheet .xlsx",
    response_class=Response,
    responses={200: {"content": {XLSX_MIME: {}}, "description": "Excel workbook"}},
)
def export_excel(ctx: Context, db: DbSession, scoring: Scoring) -> Response:
    data = export_workspace_xlsx(db, ctx.workspace_id, scoring)
    name = _workbook_name(ctx.workspace.name)
    return Response(
        content=data,
        media_type=XLSX_MIME,
        headers={
            "Content-Disposition": f'attachment; filename="{name}"',
            # Let the browser read the name we chose rather than guessing from the URL.
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@router.post(
    "/export/drive",
    response_model=DriveExportResult,
    summary="Save the export straight into the user's Google Drive",
)
def export_to_drive(
    ctx: AdminContext, user: CurrentUser, db: DbSession, scoring: Scoring
) -> DriveExportResult:
    try:
        credentials = google_oauth.get_google_credentials(db, user)
    except google_oauth.GoogleAuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()

    data = export_workspace_xlsx(db, ctx.workspace_id, scoring)
    name = _workbook_name(ctx.workspace.name)
    client = DriveClient(credentials=credentials)

    try:
        folder_id = ctx.workspace.evidence_folder_id
        if not folder_id:
            folder_id = client.ensure_folder(settings.evidence_folder_name)
            ctx.workspace.evidence_folder_id = folder_id
            db.flush()
        meta = client.upload_bytes(data, name=name, mime_type=XLSX_MIME, parent_id=folder_id)
    except DriveError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    db.commit()
    return DriveExportResult(
        file_id=meta["id"],
        name=meta.get("name", name),
        web_view_link=meta.get("webViewLink"),
        message=f"Saved to your Drive in '{settings.evidence_folder_name}'.",
    )
