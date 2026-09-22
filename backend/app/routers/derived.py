"""§8.6 — derived views: crosswalk, coverage, gaps, remediation and the dashboard."""

from __future__ import annotations

from fastapi import APIRouter

from app.deps import Context, DbSession, Scoring
from app.schemas.settings import (
    CoverageRead,
    CrosswalkRead,
    DashboardRead,
    GapsRead,
    RemediationRead,
)
from app.services.coverage import build_coverage, build_gaps
from app.services.crosswalk import build_crosswalk
from app.services.dashboard import build_dashboard_summary
from app.services.remediation import build_remediation

router = APIRouter(tags=["derived"])


@router.get(
    "/crosswalk",
    response_model=CrosswalkRead,
    summary="Controls × requirements matrix, grouped by framework",
)
def crosswalk(ctx: Context, db: DbSession) -> dict:
    return build_crosswalk(db, ctx.workspace_id)


@router.get(
    "/coverage",
    response_model=CoverageRead,
    summary="Per-framework and per-category coverage for the heatmap",
)
def coverage(ctx: Context, db: DbSession) -> dict:
    return build_coverage(db, ctx.workspace_id)


@router.get(
    "/coverage/gaps",
    response_model=GapsRead,
    summary="Requirements that are a gap or only partially covered, and why",
)
def gaps(ctx: Context, db: DbSession) -> dict:
    return build_gaps(db, ctx.workspace_id)


@router.get(
    "/remediation",
    response_model=RemediationRead,
    summary="Unfinished controls ranked by the leverage of fixing them",
)
def remediation(ctx: Context, db: DbSession, scoring: Scoring) -> dict:
    return build_remediation(db, ctx.workspace_id, scoring)


@router.get(
    "/dashboard/summary",
    response_model=DashboardRead,
    summary="Everything the dashboard needs in one call",
)
def dashboard(ctx: Context, db: DbSession, scoring: Scoring) -> dict:
    return build_dashboard_summary(db, ctx.workspace_id, scoring)
