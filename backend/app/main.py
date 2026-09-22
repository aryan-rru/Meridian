"""Meridian API — FastAPI application entry point.

One control library, mapped once, read as ISO 27001 / SOC 2 / NIST CSF at the same time.
Swagger lives at ``/docs`` (§8.9).
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.routers import ALL_ROUTERS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger("meridian")

DESCRIPTION = """
Map each control **once**, then read your posture as ISO 27001, SOC 2 and NIST CSF at the
same time — with a risk register that is honest about what the controls have actually earned.

* `/api/crosswalk` — controls × requirements, grouped by framework
* `/api/coverage` — per-framework coverage heatmap, and `/api/coverage/gaps` for the holes
* `/api/risks` — inherent vs residual scores, flagged when the reduction is unsupported
* `/api/remediation` — what to fix first, ranked by leverage
* `/api/export/excel` — the whole workspace as a workbook

Sign in with Google (`/api/auth/google/login`). The session is an http-only cookie, so
call this API from the frontend with `credentials: "include"`.
"""


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("Meridian API starting. Frontend origin: %s", settings.frontend_url)
    if not settings.google_configured:
        logger.warning(
            "Google OAuth is not configured — sign-in and Drive features are disabled. "
            "See README §Google Cloud Setup."
        )
    if settings.dev_login_enabled:
        logger.warning("DEV_LOGIN_ENABLED is true. Never do this outside local development.")
    yield


app = FastAPI(
    title="Meridian API",
    description=DESCRIPTION,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# §13 — the browser sends the session cookie, so the origin allowlist must be exact
# and `allow_origins=["*"]` is not an option when credentials are allowed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

for router in ALL_ROUTERS:
    app.include_router(router, prefix="/api")


@app.exception_handler(RequestValidationError)
async def validation_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    """Turn Pydantic's field paths into something a non-coder can act on (§3)."""
    problems = []
    for error in exc.errors():
        location = [str(p) for p in error.get("loc", []) if p not in ("body", "query", "path")]
        field = " → ".join(location) if location else "request"
        problems.append({"field": field, "message": error.get("msg", "Invalid value.")})
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": {
                "message": "Some fields need attention before this can be saved.",
                "problems": problems,
            }
        },
    )


@app.get("/api/health", tags=["meta"], summary="Liveness and configuration check")
def health() -> dict:
    return {
        "status": "ok",
        "google_configured": settings.google_configured,
        "dev_login_enabled": settings.dev_login_enabled,
    }


@app.get("/", include_in_schema=False)
def root() -> dict:
    return {"name": "Meridian API", "docs": "/docs", "health": "/api/health"}
