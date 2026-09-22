"""§8.7 — evidence records backed by Google Drive files, uploads, links and extraction."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status

from app.config import settings
from app.crud import evidence as crud
from app.db import utcnow
from app.deps import Context, CurrentUser, DbSession, Scoring, WriteContext
from app.models import Evidence, EvidenceSource, EvidenceStatus
from app.schemas.common import MessageResponse
from app.schemas.evidence import (
    DriveFileList,
    EvidenceLinkCreate,
    EvidenceRead,
    EvidenceUpdate,
    ExtractionResult,
)
from app.services.excel import extract_evidence_payload
from app.services.google import oauth as google_oauth
from app.services.google.drive import (
    GOOGLE_SHEET_MIME,
    XLSX_MIME,
    DriveClient,
    DriveError,
    DriveFileNotFound,
)

logger = logging.getLogger("meridian.evidence")

router = APIRouter(tags=["evidence"])

DRIVE_READONLY = "https://www.googleapis.com/auth/drive.readonly"
#: Types the extractor understands. Anything else can still be linked, just not parsed.
EXTRACTABLE_MIMES = {XLSX_MIME, GOOGLE_SHEET_MIME, "application/vnd.ms-excel"}
MAX_UPLOAD_BYTES = 25 * 1024 * 1024


def _drive_client(db, user) -> DriveClient:
    """Authorised Drive client for the caller, with a plain-English failure message."""
    try:
        credentials = google_oauth.get_google_credentials(db, user)
    except google_oauth.GoogleAuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()  # persist a refreshed access token
    return DriveClient(credentials=credentials)


def _drive_source(mime_type: str) -> EvidenceSource:
    return (
        EvidenceSource.GOOGLE_SHEET if mime_type == GOOGLE_SHEET_MIME else EvidenceSource.DRIVE_FILE
    )


# ---------------------------------------------------------------------------
# Drive browsing (only useful when the broad scope was granted — otherwise the
# frontend uses the Google Picker, which works under drive.file. §9.2)
# ---------------------------------------------------------------------------
@router.get("/drive/files", response_model=DriveFileList, summary="Search the user's Drive")
def list_drive_files(
    ctx: Context,
    user: CurrentUser,
    db: DbSession,
    q: str | None = Query(default=None, description="Substring of the file name"),
    mimeType: str | None = Query(default=None, alias="mimeType"),  # noqa: N803
    page_size: int = Query(default=50, ge=1, le=100),
) -> DriveFileList:
    client = _drive_client(db, user)
    scope_limited = not google_oauth.has_scope(user, DRIVE_READONLY)
    try:
        files = client.list_files(query=q, mime_type=mimeType, page_size=page_size)
    except DriveError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return DriveFileList(files=files, scope_limited=scope_limited)


# ---------------------------------------------------------------------------
# Evidence records
# ---------------------------------------------------------------------------
@router.get("/evidence", response_model=list[EvidenceRead], summary="List evidence")
def list_evidence(
    ctx: Context,
    db: DbSession,
    scoring: Scoring,
    control_id: uuid.UUID | None = None,
) -> list[dict]:
    items = crud.list_evidence(db, ctx.workspace_id, control_id)
    crud.refresh_statuses(db, items, scoring.evidence_stale_after_days)
    db.commit()
    return [crud.to_read_model(e) for e in items]


@router.post(
    "/evidence",
    response_model=EvidenceRead,
    status_code=201,
    summary="Link a Drive file (or URL) to a control",
)
def create_evidence(
    payload: EvidenceLinkCreate, ctx: WriteContext, user: CurrentUser, db: DbSession
) -> dict:
    crud.require_control(db, ctx.workspace_id, payload.control_id)

    if payload.source_type == EvidenceSource.URL:
        if not payload.url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A link needs a url.",
            )
        evidence = Evidence(
            workspace_id=ctx.workspace_id,
            control_id=payload.control_id,
            title=payload.title or payload.url,
            description=payload.description,
            source_type=EvidenceSource.URL.value,
            drive_file_name=payload.title or payload.url,
            mime_type="text/uri-list",
            url=payload.url,
            web_view_link=payload.url,
            collected_at=utcnow(),
            valid_until=payload.valid_until,
            status=EvidenceStatus.CURRENT.value,
        )
        db.add(evidence)
        db.commit()
        db.refresh(evidence)
        return crud.to_read_model(evidence)

    if not payload.drive_file_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pick a Drive file first — drive_file_id is required.",
        )

    client = _drive_client(db, user)
    try:
        meta = client.get_file(payload.drive_file_id)
    except DriveFileNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DriveError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    mime_type = meta.get("mimeType", "")
    evidence = Evidence(
        workspace_id=ctx.workspace_id,
        control_id=payload.control_id,
        title=payload.title or meta.get("name", "Evidence"),
        description=payload.description,
        source_type=_drive_source(mime_type).value,
        drive_file_id=meta.get("id"),
        drive_file_name=meta.get("name", ""),
        mime_type=mime_type,
        web_view_link=meta.get("webViewLink"),
        collected_at=utcnow(),
        valid_until=payload.valid_until,
        status=EvidenceStatus.CURRENT.value,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    logger.info(
        "Evidence linked to control %s in workspace %s", payload.control_id, ctx.workspace_id
    )
    return crud.to_read_model(evidence)


@router.post(
    "/evidence/upload",
    response_model=EvidenceRead,
    status_code=201,
    summary="Upload a file to the app's Drive folder and attach it",
)
def upload_evidence(
    ctx: WriteContext,
    user: CurrentUser,
    db: DbSession,
    control_id: uuid.UUID = Form(...),
    title: str | None = Form(default=None),
    description: str = Form(default=""),
    valid_until: datetime | None = Form(default=None),
    file: UploadFile = File(...),
) -> dict:
    crud.require_control(db, ctx.workspace_id, control_id)

    data = file.file.read()
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="That file is empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Files must be under {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.",
        )

    client = _drive_client(db, user)
    try:
        folder_id = ctx.workspace.evidence_folder_id
        if not folder_id:
            folder_id = client.ensure_folder(settings.evidence_folder_name)
            ctx.workspace.evidence_folder_id = folder_id
            db.flush()
        meta = client.upload_bytes(
            data,
            name=file.filename or "evidence",
            mime_type=file.content_type or "application/octet-stream",
            parent_id=folder_id,
        )
    except DriveError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    evidence = Evidence(
        workspace_id=ctx.workspace_id,
        control_id=control_id,
        title=title or meta.get("name", file.filename or "Evidence"),
        description=description,
        source_type=EvidenceSource.UPLOAD.value,
        drive_file_id=meta.get("id"),
        drive_file_name=meta.get("name", file.filename or ""),
        mime_type=meta.get("mimeType", file.content_type or ""),
        web_view_link=meta.get("webViewLink"),
        collected_at=utcnow(),
        valid_until=valid_until,
        status=EvidenceStatus.CURRENT.value,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    return crud.to_read_model(evidence)


@router.get("/evidence/{evidence_id}", response_model=EvidenceRead, summary="Evidence detail")
def get_evidence(evidence_id: uuid.UUID, ctx: Context, db: DbSession, scoring: Scoring) -> dict:
    evidence = crud.get(db, ctx.workspace_id, evidence_id)
    crud.refresh_statuses(db, [evidence], scoring.evidence_stale_after_days)
    db.commit()
    return crud.to_read_model(evidence)


@router.patch("/evidence/{evidence_id}", response_model=EvidenceRead, summary="Edit evidence")
def update_evidence(
    evidence_id: uuid.UUID, payload: EvidenceUpdate, ctx: WriteContext, db: DbSession
) -> dict:
    evidence = crud.get(db, ctx.workspace_id, evidence_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(evidence, key, value)
    db.commit()
    db.refresh(evidence)
    return crud.to_read_model(evidence)


@router.delete(
    "/evidence/{evidence_id}",
    response_model=MessageResponse,
    summary="Unlink evidence (the Drive file itself is kept)",
)
def delete_evidence(evidence_id: uuid.UUID, ctx: WriteContext, db: DbSession) -> MessageResponse:
    evidence = crud.get(db, ctx.workspace_id, evidence_id)
    title = evidence.title
    db.delete(evidence)
    db.commit()
    # §8.7: deleting the link never deletes the user's Drive file.
    return MessageResponse(
        message=f"'{title}' was unlinked. The file is still in your Google Drive."
    )


@router.post(
    "/evidence/{evidence_id}/extract",
    response_model=ExtractionResult,
    summary="Read the spreadsheet and store a small summary (§9.5)",
)
def extract_evidence(
    evidence_id: uuid.UUID,
    ctx: WriteContext,
    user: CurrentUser,
    db: DbSession,
    scoring: Scoring,
) -> ExtractionResult:
    evidence = crud.get(db, ctx.workspace_id, evidence_id)

    if not evidence.drive_file_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This evidence is a plain link, so there is no file to read.",
        )
    if evidence.mime_type and evidence.mime_type not in EXTRACTABLE_MIMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Only Excel workbooks and Google Sheets can be read automatically. "
                f"This file is {evidence.mime_type}."
            ),
        )

    client = _drive_client(db, user)
    try:
        data = client.download_bytes(evidence.drive_file_id, evidence.mime_type or None)
    except DriveFileNotFound:
        # §9.5 step 4 — a vanished file is 'missing', not an error page.
        evidence.status = EvidenceStatus.MISSING.value
        db.commit()
        return ExtractionResult(
            evidence_id=evidence.id,
            status=str(evidence.status),
            extracted_at=evidence.extracted_at,
            extracted_data=evidence.extracted_data,
            message="That file is no longer in Drive, so the evidence is marked missing.",
        )
    except DriveError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    try:
        payload = extract_evidence_payload(data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    evidence.extracted_data = payload
    evidence.extracted_at = utcnow()
    # The file was readable, so clear any earlier 'missing' before re-deriving freshness.
    evidence.status = EvidenceStatus.CURRENT.value
    evidence.status = crud.freshness(evidence, scoring.evidence_stale_after_days)
    db.commit()
    db.refresh(evidence)

    sheet_count = len(payload.get("sheets", []))
    return ExtractionResult(
        evidence_id=evidence.id,
        status=str(evidence.status),
        extracted_at=evidence.extracted_at,
        extracted_data=evidence.extracted_data,
        message=f"Read {sheet_count} sheet(s) from '{evidence.drive_file_name}'.",
    )
