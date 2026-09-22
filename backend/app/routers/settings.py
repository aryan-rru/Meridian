"""§8.9 — scoring configuration. Changing it re-derives every score on the next read."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.deps import AdminContext, Context, DbSession, get_or_create_config
from app.schemas.settings import ScoringConfigRead, ScoringConfigUpdate
from app.services.scoring import ScoringContext, validate_bands

router = APIRouter(prefix="/settings", tags=["settings"])


def _read_model(config) -> dict:
    ctx = ScoringContext.from_model(config)
    return {
        "matrix_size": config.matrix_size,
        "score_method": str(config.score_method),
        "weights": config.weights or {},
        "likelihood_labels": config.likelihood_labels or {},
        "impact_labels": config.impact_labels or {},
        "risk_bands": config.risk_bands or [],
        "remediation_weights": config.remediation_weights or {},
        "evidence_stale_after_days": config.evidence_stale_after_days,
        "min_possible_score": ctx.min_possible_score,
        "max_possible_score": ctx.max_possible_score,
    }


@router.get("", response_model=ScoringConfigRead, summary="Current scoring configuration")
def get_settings(ctx: Context, db: DbSession) -> dict:
    config = get_or_create_config(db, ctx.workspace_id)
    db.commit()
    return _read_model(config)


@router.put("", response_model=ScoringConfigRead, summary="Update scoring configuration")
def update_settings(payload: ScoringConfigUpdate, ctx: AdminContext, db: DbSession) -> dict:
    config = get_or_create_config(db, ctx.workspace_id)
    data = payload.model_dump(exclude_unset=True)

    if "score_method" in data and data["score_method"] is not None:
        data["score_method"] = str(data["score_method"])
    if "risk_bands" in data and data["risk_bands"] is not None:
        data["risk_bands"] = [dict(b) for b in data["risk_bands"]]

    for key, value in data.items():
        if value is not None:
            setattr(config, key, value)

    # Validate bands against the *post-update* method and matrix size (§12).
    problems = validate_bands(config.risk_bands or [], ScoringContext.from_model(config))
    if problems:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Risk bands must be contiguous and cover the whole score range.",
                "problems": problems,
            },
        )

    labels_needed = config.matrix_size
    for field_name, labels in (
        ("likelihood_labels", config.likelihood_labels or {}),
        ("impact_labels", config.impact_labels or {}),
    ):
        missing = [str(i) for i in range(1, labels_needed + 1) if str(i) not in labels]
        if missing:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": f"{field_name} needs a label for every point on the scale.",
                    "problems": [f"Missing label(s) for: {', '.join(missing)}."],
                },
            )

    db.commit()
    db.refresh(config)
    return _read_model(config)
