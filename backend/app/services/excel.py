"""§10 Excel import/export and §9.5 evidence extraction.

Import is the exact inverse of export: every sheet is keyed by a natural key
(``ref`` / ``code``) and upserted, so export → import round-trips to identical data.
Unknown extra columns (the derived score/band columns we add for readability) are
ignored on the way back in.
"""

from __future__ import annotations

import io
import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Control,
    ControlRequirementMapping,
    ControlStatus,
    CoverageLevel,
    Evidence,
    Framework,
    Requirement,
    Risk,
    RiskControlMapping,
    RiskStatus,
    RiskTreatment,
)
from app.services.scoring import ScoringContext, score_and_band

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

SHEET_CONTROLS = "Controls"
SHEET_REQUIREMENTS = "Requirements"
SHEET_CROSSWALK = "Crosswalk"
SHEET_RISKS = "Risks"
SHEET_RISK_CONTROLS = "RiskControls"
SHEET_EVIDENCE = "Evidence"

CONTROL_COLUMNS = ["ref", "name", "category", "owner", "status", "description"]
REQUIREMENT_COLUMNS = ["framework_key", "code", "title", "category", "description"]
CROSSWALK_COLUMNS = ["control_ref", "requirement_code", "coverage_level"]
RISK_COLUMNS = [
    "ref",
    "title",
    "category",
    "owner",
    "inherent_likelihood",
    "inherent_impact",
    "residual_likelihood",
    "residual_impact",
    "treatment",
    "status",
    "description",
]
RISK_CONTROL_COLUMNS = ["risk_ref", "control_ref"]
EVIDENCE_COLUMNS = [
    "control_ref",
    "title",
    "source_type",
    "drive_file_name",
    "web_view_link",
    "status",
    "valid_until",
]

HEADER_FILL = PatternFill("solid", fgColor="1E293B")
HEADER_FONT = Font(bold=True, color="FFFFFF")


# ---------------------------------------------------------------------------
# Import result plumbing
# ---------------------------------------------------------------------------
@dataclass
class ImportSummary:
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[dict[str, Any]] = field(default_factory=list)
    sheets: dict[str, dict[str, int]] = field(default_factory=dict)

    def record(self, sheet: str, kind: str) -> None:
        bucket = self.sheets.setdefault(sheet, {"created": 0, "updated": 0, "skipped": 0})
        bucket[kind] += 1
        setattr(self, kind, getattr(self, kind) + 1)

    def error(self, sheet: str, row: int | None, message: str) -> None:
        self.errors.append({"sheet": sheet, "row": row, "message": message})
        self.record(sheet, "skipped")

    def as_dict(self) -> dict[str, Any]:
        return {
            "created": self.created,
            "updated": self.updated,
            "skipped": self.skipped,
            "errors": self.errors,
            "sheets": self.sheets,
        }


def _clean(value: Any) -> str:
    """Normalise a cell to a trimmed string; NaN/None become ''."""
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    if pd.isna(value) if not isinstance(value, (list, dict)) else False:
        return ""
    return str(value).strip()


def _clean_int(value: Any, default: int = 3, low: int = 1, high: int = 10) -> int | None:
    text = _clean(value)
    if not text:
        return default
    try:
        number = int(float(text))
    except ValueError:
        return None
    if not low <= number <= high:
        return None
    return number


def _clean_enum(value: Any, allowed: Iterable[str], default: str) -> str | None:
    text = _clean(value).lower().replace(" ", "_").replace("-", "_")
    if not text:
        return default
    allowed_set = {str(a) for a in allowed}
    return text if text in allowed_set else None


def _clean_datetime(value: Any) -> datetime | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    text = _clean(value)
    if not text:
        return None
    try:
        parsed = pd.to_datetime(text, errors="raise")
    except (ValueError, TypeError):
        return None
    stamp = parsed.to_pydatetime()
    return stamp if stamp.tzinfo else stamp.replace(tzinfo=UTC)


# ---------------------------------------------------------------------------
# Export (§10)
# ---------------------------------------------------------------------------
def _write_sheet(
    workbook: Workbook,
    title: str,
    columns: list[str],
    rows: list[list[Any]],
    band_column: int | None = None,
    band_colors: list[str | None] | None = None,
) -> None:
    sheet = workbook.create_sheet(title)
    sheet.append(columns)
    for cell in sheet[1]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(vertical="center")
    sheet.freeze_panes = "A2"

    for index, row in enumerate(rows):
        sheet.append(row)
        if band_column is not None and band_colors and index < len(band_colors):
            color = band_colors[index]
            if color:
                sheet.cell(row=index + 2, column=band_column).fill = PatternFill(
                    "solid", fgColor=color.lstrip("#").upper()
                )

    for column_index, name in enumerate(columns, start=1):
        longest = max(
            [len(str(name))] + [len(str(r[column_index - 1])) for r in rows if r[column_index - 1]]
            or [len(str(name))]
        )
        sheet.column_dimensions[get_column_letter(column_index)].width = min(
            max(12, longest + 2), 60
        )


def export_workspace_xlsx(db: Session, workspace_id: uuid.UUID, ctx: ScoringContext) -> bytes:
    """Build the multi-sheet workbook for a workspace."""
    workbook = Workbook()
    workbook.remove(workbook.active)  # drop the default empty sheet

    controls = list(
        db.execute(
            select(Control).where(Control.workspace_id == workspace_id).order_by(Control.ref)
        )
        .scalars()
        .all()
    )
    _write_sheet(
        workbook,
        SHEET_CONTROLS,
        CONTROL_COLUMNS,
        [[c.ref, c.name, c.category, c.owner, str(c.status), c.description] for c in controls],
    )

    requirements = list(
        db.execute(
            select(Requirement)
            .options(selectinload(Requirement.framework))
            .join(Framework, Framework.id == Requirement.framework_id)
            .order_by(Framework.sort_order, Requirement.sort_order, Requirement.code)
        )
        .scalars()
        .all()
    )
    _write_sheet(
        workbook,
        SHEET_REQUIREMENTS,
        REQUIREMENT_COLUMNS,
        [[r.framework.key, r.code, r.title, r.category, r.description] for r in requirements],
    )

    crosswalk_rows = db.execute(
        select(Control.ref, Requirement.code, ControlRequirementMapping.coverage_level)
        .join(Control, Control.id == ControlRequirementMapping.control_id)
        .join(Requirement, Requirement.id == ControlRequirementMapping.requirement_id)
        .where(Control.workspace_id == workspace_id)
        .order_by(Control.ref, Requirement.code)
    ).all()
    _write_sheet(
        workbook,
        SHEET_CROSSWALK,
        CROSSWALK_COLUMNS,
        [[ref, code, str(level)] for ref, code, level in crosswalk_rows],
    )

    risks = list(
        db.execute(select(Risk).where(Risk.workspace_id == workspace_id).order_by(Risk.ref))
        .scalars()
        .all()
    )
    # Derived columns are appended for readability; import ignores them.
    risk_columns = RISK_COLUMNS + [
        "inherent_score",
        "inherent_band",
        "residual_score",
        "residual_band",
    ]
    risk_rows: list[list[Any]] = []
    band_colors: list[str | None] = []
    for risk in risks:
        inherent_score, inherent_band = score_and_band(
            risk.inherent_likelihood, risk.inherent_impact, ctx
        )
        residual_score, residual_band = score_and_band(
            risk.residual_likelihood, risk.residual_impact, ctx
        )
        risk_rows.append(
            [
                risk.ref,
                risk.title,
                risk.category,
                risk.owner,
                risk.inherent_likelihood,
                risk.inherent_impact,
                risk.residual_likelihood,
                risk.residual_impact,
                str(risk.treatment),
                str(risk.status),
                risk.description,
                inherent_score,
                inherent_band.name,
                residual_score,
                residual_band.name,
            ]
        )
        band_colors.append(residual_band.color)
    _write_sheet(
        workbook,
        SHEET_RISKS,
        risk_columns,
        risk_rows,
        band_column=len(risk_columns),  # the residual_band cell
        band_colors=band_colors,
    )

    risk_control_rows = db.execute(
        select(Risk.ref, Control.ref)
        .join(RiskControlMapping, RiskControlMapping.risk_id == Risk.id)
        .join(Control, Control.id == RiskControlMapping.control_id)
        .where(Risk.workspace_id == workspace_id)
        .order_by(Risk.ref, Control.ref)
    ).all()
    _write_sheet(
        workbook,
        SHEET_RISK_CONTROLS,
        RISK_CONTROL_COLUMNS,
        [[risk_ref, control_ref] for risk_ref, control_ref in risk_control_rows],
    )

    evidence_rows = db.execute(
        select(
            Control.ref,
            Evidence.title,
            Evidence.source_type,
            Evidence.drive_file_name,
            Evidence.web_view_link,
            Evidence.status,
            Evidence.valid_until,
        )
        .join(Control, Control.id == Evidence.control_id)
        .where(Evidence.workspace_id == workspace_id)
        .order_by(Control.ref, Evidence.title)
    ).all()
    _write_sheet(
        workbook,
        SHEET_EVIDENCE,
        EVIDENCE_COLUMNS,
        [
            [
                ref,
                title,
                str(source_type),
                file_name or "",
                link or "",
                str(status),
                valid_until.strftime("%Y-%m-%d") if valid_until else "",
            ]
            for ref, title, source_type, file_name, link, status, valid_until in evidence_rows
        ],
    )

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Import (§10)
# ---------------------------------------------------------------------------
def _read_sheets(data: bytes) -> dict[str, pd.DataFrame]:
    try:
        return pd.read_excel(io.BytesIO(data), sheet_name=None, engine="openpyxl")
    except Exception as exc:  # noqa: BLE001 - surfaced to the user as a 400
        raise ValueError(f"Could not read the workbook: {exc}") from exc


def _normalise_columns(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame.columns = [str(c).strip().lower().replace(" ", "_") for c in frame.columns]
    return frame


def _missing_columns(frame: pd.DataFrame, required: list[str]) -> list[str]:
    return [c for c in required if c not in frame.columns]


def import_workspace_xlsx(db: Session, workspace_id: uuid.UUID, data: bytes) -> ImportSummary:
    """Upsert workspace content from a workbook, collecting row-level errors (§10)."""
    summary = ImportSummary()
    sheets = {str(k).strip(): _normalise_columns(v) for k, v in _read_sheets(data).items()}

    known = {
        SHEET_CONTROLS,
        SHEET_REQUIREMENTS,
        SHEET_CROSSWALK,
        SHEET_RISKS,
        SHEET_RISK_CONTROLS,
        SHEET_EVIDENCE,
    }
    if not known & set(sheets):
        raise ValueError(
            "No recognised sheets found. Expected at least one of: " + ", ".join(sorted(known))
        )

    _import_requirements(db, sheets.get(SHEET_REQUIREMENTS), summary)
    db.flush()
    _import_controls(db, workspace_id, sheets.get(SHEET_CONTROLS), summary)
    db.flush()
    _import_risks(db, workspace_id, sheets.get(SHEET_RISKS), summary)
    db.flush()
    _import_crosswalk(db, workspace_id, sheets.get(SHEET_CROSSWALK), summary)
    _import_risk_controls(db, workspace_id, sheets.get(SHEET_RISK_CONTROLS), summary)
    db.flush()
    return summary


def _import_requirements(db: Session, frame: pd.DataFrame | None, summary: ImportSummary) -> None:
    if frame is None or frame.empty:
        return
    missing = _missing_columns(frame, ["framework_key", "code", "title"])
    if missing:
        summary.error(SHEET_REQUIREMENTS, None, f"Missing column(s): {', '.join(missing)}")
        return

    frameworks = {f.key: f for f in db.execute(select(Framework)).scalars().all()}
    for offset, row in frame.iterrows():
        row_number = int(offset) + 2
        framework_key = _clean(row.get("framework_key"))
        code = _clean(row.get("code"))
        if not framework_key or not code:
            summary.error(SHEET_REQUIREMENTS, row_number, "framework_key and code are required.")
            continue
        framework = frameworks.get(framework_key)
        if framework is None:
            summary.error(
                SHEET_REQUIREMENTS,
                row_number,
                f"Unknown framework '{framework_key}'. Known: {', '.join(sorted(frameworks))}.",
            )
            continue

        existing = db.execute(
            select(Requirement).where(
                Requirement.framework_id == framework.id, Requirement.code == code
            )
        ).scalar_one_or_none()

        values = {
            "title": _clean(row.get("title")),
            "category": _clean(row.get("category")),
            "description": _clean(row.get("description")),
        }
        if existing:
            for key, value in values.items():
                setattr(existing, key, value)
            summary.record(SHEET_REQUIREMENTS, "updated")
        else:
            db.add(Requirement(framework_id=framework.id, code=code, **values))
            summary.record(SHEET_REQUIREMENTS, "created")


def _import_controls(
    db: Session, workspace_id: uuid.UUID, frame: pd.DataFrame | None, summary: ImportSummary
) -> None:
    if frame is None or frame.empty:
        return
    missing = _missing_columns(frame, ["ref", "name"])
    if missing:
        summary.error(SHEET_CONTROLS, None, f"Missing column(s): {', '.join(missing)}")
        return

    seen: set[str] = set()
    for offset, row in frame.iterrows():
        row_number = int(offset) + 2
        ref = _clean(row.get("ref"))
        name = _clean(row.get("name"))
        if not ref or not name:
            summary.error(SHEET_CONTROLS, row_number, "ref and name are required.")
            continue
        if ref in seen:
            summary.error(SHEET_CONTROLS, row_number, f"Duplicate control ref '{ref}' in the file.")
            continue
        seen.add(ref)

        status = _clean_enum(
            row.get("status"), [s.value for s in ControlStatus], ControlStatus.NOT_IMPLEMENTED.value
        )
        if status is None:
            summary.error(
                SHEET_CONTROLS,
                row_number,
                f"Invalid status '{_clean(row.get('status'))}'. Allowed: "
                + ", ".join(s.value for s in ControlStatus),
            )
            continue

        existing = db.execute(
            select(Control).where(Control.workspace_id == workspace_id, Control.ref == ref)
        ).scalar_one_or_none()
        values = {
            "name": name,
            "category": _clean(row.get("category")),
            "owner": _clean(row.get("owner")),
            "status": status,
            "description": _clean(row.get("description")),
        }
        if existing:
            for key, value in values.items():
                setattr(existing, key, value)
            summary.record(SHEET_CONTROLS, "updated")
        else:
            db.add(Control(workspace_id=workspace_id, ref=ref, **values))
            summary.record(SHEET_CONTROLS, "created")


def _import_risks(
    db: Session, workspace_id: uuid.UUID, frame: pd.DataFrame | None, summary: ImportSummary
) -> None:
    if frame is None or frame.empty:
        return
    missing = _missing_columns(frame, ["ref", "title"])
    if missing:
        summary.error(SHEET_RISKS, None, f"Missing column(s): {', '.join(missing)}")
        return

    seen: set[str] = set()
    for offset, row in frame.iterrows():
        row_number = int(offset) + 2
        ref = _clean(row.get("ref"))
        title = _clean(row.get("title"))
        if not ref or not title:
            summary.error(SHEET_RISKS, row_number, "ref and title are required.")
            continue
        if ref in seen:
            summary.error(SHEET_RISKS, row_number, f"Duplicate risk ref '{ref}' in the file.")
            continue
        seen.add(ref)

        scales: dict[str, int] = {}
        bad_scale = False
        for column in (
            "inherent_likelihood",
            "inherent_impact",
            "residual_likelihood",
            "residual_impact",
        ):
            value = _clean_int(row.get(column))
            if value is None:
                summary.error(
                    SHEET_RISKS,
                    row_number,
                    f"'{column}' must be a whole number between 1 and 10.",
                )
                bad_scale = True
                break
            scales[column] = value
        if bad_scale:
            continue

        treatment = _clean_enum(
            row.get("treatment"), [t.value for t in RiskTreatment], RiskTreatment.MITIGATE.value
        )
        status = _clean_enum(
            row.get("status"), [s.value for s in RiskStatus], RiskStatus.OPEN.value
        )
        if treatment is None or status is None:
            summary.error(
                SHEET_RISKS,
                row_number,
                "Invalid treatment or status value.",
            )
            continue

        existing = db.execute(
            select(Risk).where(Risk.workspace_id == workspace_id, Risk.ref == ref)
        ).scalar_one_or_none()
        values = {
            "title": title,
            "category": _clean(row.get("category")),
            "owner": _clean(row.get("owner")),
            "treatment": treatment,
            "status": status,
            "description": _clean(row.get("description")),
            **scales,
        }
        if existing:
            for key, value in values.items():
                setattr(existing, key, value)
            summary.record(SHEET_RISKS, "updated")
        else:
            db.add(Risk(workspace_id=workspace_id, ref=ref, **values))
            summary.record(SHEET_RISKS, "created")


def _import_crosswalk(
    db: Session, workspace_id: uuid.UUID, frame: pd.DataFrame | None, summary: ImportSummary
) -> None:
    if frame is None or frame.empty:
        return
    missing = _missing_columns(frame, ["control_ref", "requirement_code"])
    if missing:
        summary.error(SHEET_CROSSWALK, None, f"Missing column(s): {', '.join(missing)}")
        return

    controls = {
        c.ref: c
        for c in db.execute(select(Control).where(Control.workspace_id == workspace_id))
        .scalars()
        .all()
    }
    requirements_by_code: dict[str, list[Requirement]] = {}
    for requirement in (
        db.execute(select(Requirement).options(selectinload(Requirement.framework))).scalars().all()
    ):
        requirements_by_code.setdefault(requirement.code, []).append(requirement)

    has_framework_column = "framework_key" in frame.columns
    for offset, row in frame.iterrows():
        row_number = int(offset) + 2
        control_ref = _clean(row.get("control_ref"))
        code = _clean(row.get("requirement_code"))
        if not control_ref or not code:
            summary.error(
                SHEET_CROSSWALK, row_number, "control_ref and requirement_code are required."
            )
            continue

        control = controls.get(control_ref)
        if control is None:
            summary.error(SHEET_CROSSWALK, row_number, f"Unknown control ref '{control_ref}'.")
            continue

        candidates = requirements_by_code.get(code, [])
        if has_framework_column and _clean(row.get("framework_key")):
            wanted = _clean(row.get("framework_key"))
            candidates = [r for r in candidates if r.framework.key == wanted]
        if not candidates:
            summary.error(SHEET_CROSSWALK, row_number, f"Unknown requirement code '{code}'.")
            continue
        if len(candidates) > 1:
            summary.error(
                SHEET_CROSSWALK,
                row_number,
                f"Requirement code '{code}' exists in several frameworks — "
                "add a framework_key column to disambiguate.",
            )
            continue
        requirement = candidates[0]

        level = _clean_enum(
            row.get("coverage_level"), [c.value for c in CoverageLevel], CoverageLevel.FULL.value
        )
        if level is None:
            summary.error(
                SHEET_CROSSWALK,
                row_number,
                f"Invalid coverage_level '{_clean(row.get('coverage_level'))}'.",
            )
            continue

        existing = db.execute(
            select(ControlRequirementMapping).where(
                ControlRequirementMapping.control_id == control.id,
                ControlRequirementMapping.requirement_id == requirement.id,
            )
        ).scalar_one_or_none()
        if existing:
            if str(existing.coverage_level) != level:
                existing.coverage_level = level
                summary.record(SHEET_CROSSWALK, "updated")
            else:
                summary.record(SHEET_CROSSWALK, "updated")
        else:
            db.add(
                ControlRequirementMapping(
                    control_id=control.id, requirement_id=requirement.id, coverage_level=level
                )
            )
            summary.record(SHEET_CROSSWALK, "created")


def _import_risk_controls(
    db: Session, workspace_id: uuid.UUID, frame: pd.DataFrame | None, summary: ImportSummary
) -> None:
    if frame is None or frame.empty:
        return
    missing = _missing_columns(frame, RISK_CONTROL_COLUMNS)
    if missing:
        summary.error(SHEET_RISK_CONTROLS, None, f"Missing column(s): {', '.join(missing)}")
        return

    controls = {
        c.ref: c
        for c in db.execute(select(Control).where(Control.workspace_id == workspace_id))
        .scalars()
        .all()
    }
    risks = {
        r.ref: r
        for r in db.execute(select(Risk).where(Risk.workspace_id == workspace_id)).scalars().all()
    }

    for offset, row in frame.iterrows():
        row_number = int(offset) + 2
        risk_ref = _clean(row.get("risk_ref"))
        control_ref = _clean(row.get("control_ref"))
        if not risk_ref or not control_ref:
            summary.error(SHEET_RISK_CONTROLS, row_number, "risk_ref and control_ref are required.")
            continue
        risk = risks.get(risk_ref)
        control = controls.get(control_ref)
        if risk is None:
            summary.error(SHEET_RISK_CONTROLS, row_number, f"Unknown risk ref '{risk_ref}'.")
            continue
        if control is None:
            summary.error(SHEET_RISK_CONTROLS, row_number, f"Unknown control ref '{control_ref}'.")
            continue

        existing = db.execute(
            select(RiskControlMapping).where(
                RiskControlMapping.risk_id == risk.id,
                RiskControlMapping.control_id == control.id,
            )
        ).scalar_one_or_none()
        if existing:
            summary.record(SHEET_RISK_CONTROLS, "updated")
        else:
            db.add(RiskControlMapping(risk_id=risk.id, control_id=control.id))
            summary.record(SHEET_RISK_CONTROLS, "created")


# ---------------------------------------------------------------------------
# §9.5 Evidence extraction
# ---------------------------------------------------------------------------
MAX_SUMMARY_ROWS = 50


def extract_evidence_payload(data: bytes) -> dict[str, Any]:
    """Pull a small, well-defined payload out of an evidence workbook.

    Deliberately simple and documented rather than a general-purpose parser: sheet
    names, header row, row/column counts, and — when a two-column sheet named
    ``Summary`` exists — its key/value pairs.
    """
    frames = pd.read_excel(io.BytesIO(data), sheet_name=None, engine="openpyxl")

    sheets: list[dict[str, Any]] = []
    for name, frame in frames.items():
        sheets.append(
            {
                "name": str(name),
                "row_count": int(frame.shape[0]),
                "column_count": int(frame.shape[1]),
                "headers": [str(c) for c in frame.columns][:25],
            }
        )

    summary_values: dict[str, Any] = {}
    for name, frame in frames.items():
        if str(name).strip().lower() != "summary":
            continue
        if frame.shape[1] < 2:
            continue
        keys = frame.iloc[:MAX_SUMMARY_ROWS, 0]
        values = frame.iloc[:MAX_SUMMARY_ROWS, 1]
        for key, value in zip(keys, values, strict=False):
            key_text = _clean(key)
            if not key_text:
                continue
            if isinstance(value, (int, float)) and not pd.isna(value):
                summary_values[key_text] = float(value) if isinstance(value, float) else int(value)
            else:
                summary_values[key_text] = _clean(value)
        break

    return {
        "sheet_count": len(sheets),
        "sheets": sheets,
        "summary": summary_values,
        "extracted_with": "pandas/openpyxl",
    }
