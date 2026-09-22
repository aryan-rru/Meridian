"""API routers. Registered under ``/api`` by :mod:`app.main`."""

from __future__ import annotations

from app.routers import (
    auth,
    controls,
    derived,
    evidence,
    frameworks,
    importexport,
    risks,
    settings,
    workspaces,
)

#: Registration order controls the order of the tag sections in Swagger.
ALL_ROUTERS = [
    auth.router,
    workspaces.router,
    frameworks.router,
    controls.router,
    risks.router,
    derived.router,
    evidence.router,
    importexport.router,
    settings.router,
]

__all__ = [
    "ALL_ROUTERS",
    "auth",
    "controls",
    "derived",
    "evidence",
    "frameworks",
    "importexport",
    "risks",
    "settings",
    "workspaces",
]
