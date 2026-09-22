"""§18 — API tests: auth guard, workspace isolation, CRUD, mappings, import
validation/errors, export→import round-trip, and settings re-derivation.
"""

from __future__ import annotations

import io

import pandas as pd
from fastapi.testclient import TestClient
from openpyxl import Workbook

from app.main import app
from app.services.google.drive import XLSX_MIME


def _xlsx(files: dict[str, list[list]]) -> bytes:
    workbook = Workbook()
    workbook.remove(workbook.active)
    for name, rows in files.items():
        sheet = workbook.create_sheet(name)
        for row in rows:
            sheet.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Health & auth guard
# ---------------------------------------------------------------------------
def test_health(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["google_configured"] is False
    assert body["dev_login_enabled"] is True


def test_protected_endpoint_requires_authentication(client):
    assert client.get("/api/controls").status_code == 401


def test_dev_login_then_me(client, seeded):
    login = client.post("/api/auth/dev-login", json={})
    assert login.status_code == 200

    me = client.get("/api/auth/me").json()
    assert me["user"]["email"] == "demo@meridian.local"
    assert me["current_workspace"]["name"] == "Sample Org"
    assert me["current_role"] == "owner"


# ---------------------------------------------------------------------------
# Workspace isolation (§13: authorization on every request)
# ---------------------------------------------------------------------------
def test_workspace_isolation(client, seeded):
    client.post("/api/auth/dev-login", json={})
    controls = client.get("/api/controls").json()
    assert len(controls) == 24
    demo_control_id = controls[0]["id"]

    # A different user lands in their own, empty workspace and cannot see A's data.
    with TestClient(app) as other:
        assert (
            other.post("/api/auth/dev-login", json={"email": "userb@meridian.local"}).status_code
            == 200
        )
        assert other.get("/api/controls").json() == []
        assert other.get(f"/api/controls/{demo_control_id}").status_code in (403, 404)


# ---------------------------------------------------------------------------
# Control CRUD and requirement mapping
# ---------------------------------------------------------------------------
def test_control_crud(auth_client):
    created = auth_client.post(
        "/api/controls",
        json={"ref": "CTL-TEST-1", "name": "Test Control", "status": "not_implemented"},
    )
    assert created.status_code == 201
    control_id = created.json()["id"]

    assert auth_client.get(f"/api/controls/{control_id}").status_code == 200

    patched = auth_client.patch(f"/api/controls/{control_id}", json={"status": "implemented"})
    assert patched.status_code == 200
    assert patched.json()["status"] == "implemented"

    deleted = auth_client.delete(f"/api/controls/{control_id}")
    assert deleted.status_code == 200
    assert auth_client.get(f"/api/controls/{control_id}").status_code == 404


def test_set_control_requirements(auth_client):
    coverage = auth_client.get("/api/coverage").json()
    requirement_id = coverage["frameworks"][0]["categories"][0]["requirements"][0]["requirement_id"]

    created = auth_client.post("/api/controls", json={"ref": "CTL-TEST-2", "name": "Mapper"})
    control_id = created.json()["id"]

    detail = auth_client.put(
        f"/api/controls/{control_id}/requirements",
        json={"items": [{"requirement_id": requirement_id, "coverage_level": "full"}]},
    )
    assert detail.status_code == 200
    # The detail payload keys each mapped requirement by its own `id`.
    mapped_ids = [str(r["id"]) for r in detail.json()["requirements"]]
    assert requirement_id in mapped_ids


# ---------------------------------------------------------------------------
# Import validation / errors
# ---------------------------------------------------------------------------
def test_import_rejects_non_xlsx(auth_client):
    response = auth_client.post(
        "/api/import/excel", files={"file": ("data.txt", b"hello", "text/plain")}
    )
    assert response.status_code == 400


def test_import_rejects_unrecognised_sheets(auth_client):
    data = _xlsx({"RandomSheet": [["a", "b"], [1, 2]]})
    response = auth_client.post("/api/import/excel", files={"file": ("junk.xlsx", data, XLSX_MIME)})
    assert response.status_code == 400
    assert "recognised" in response.json()["detail"].lower()


def test_import_reports_row_level_errors(auth_client):
    # A recognised Controls sheet with one bad status keeps going and records an error.
    data = _xlsx(
        {
            "Controls": [
                ["ref", "name", "status"],
                ["CTL-IMP-OK", "Fine", "implemented"],
                ["CTL-IMP-BAD", "Broken", "banana"],
            ]
        }
    )
    response = auth_client.post(
        "/api/import/excel", files={"file": ("controls.xlsx", data, XLSX_MIME)}
    )
    assert response.status_code == 200
    summary = response.json()
    assert summary["created"] == 1
    assert len(summary["errors"]) == 1
    assert summary["errors"][0]["sheet"] == "Controls"


# ---------------------------------------------------------------------------
# Export -> import round-trip (§10: identical data)
# ---------------------------------------------------------------------------
def test_export_import_roundtrip_is_idempotent(auth_client):
    coverage_before = auth_client.get("/api/coverage").json()["totals"]
    controls_before = len(auth_client.get("/api/controls").json())
    risks_before = len(auth_client.get("/api/risks").json())

    export = auth_client.get("/api/export/excel")
    assert export.status_code == 200
    workbook_bytes = export.content

    # Sanity check the workbook has the sheets we expect.
    sheets = pd.read_excel(io.BytesIO(workbook_bytes), sheet_name=None, engine="openpyxl")
    assert {"Controls", "Requirements", "Crosswalk", "Risks", "RiskControls"} <= set(sheets)

    reimport = auth_client.post(
        "/api/import/excel", files={"file": ("roundtrip.xlsx", workbook_bytes, XLSX_MIME)}
    )
    assert reimport.status_code == 200
    summary = reimport.json()
    assert summary["created"] == 0  # everything already existed -> only updates
    assert summary["errors"] == []

    assert auth_client.get("/api/coverage").json()["totals"] == coverage_before
    assert len(auth_client.get("/api/controls").json()) == controls_before
    assert len(auth_client.get("/api/risks").json()) == risks_before


# ---------------------------------------------------------------------------
# Derived integrity signals
# ---------------------------------------------------------------------------
def test_only_risk_009_trips_the_unearned_residual_flag(auth_client):
    risks = auth_client.get("/api/risks").json()
    flagged = [r["ref"] for r in risks if r["assurance"]["flag"] == "unsupported_residual"]
    assert flagged == ["RISK-009"]


def test_traceability_shape(auth_client):
    risks = auth_client.get("/api/risks").json()
    risk_id = next(r["id"] for r in risks if r["ref"] == "RISK-001")
    trace = auth_client.get(f"/api/risks/{risk_id}/traceability").json()
    assert {"risk", "controls", "assurance", "aggregate"} <= set(trace)


# ---------------------------------------------------------------------------
# Settings re-derivation (§8.9 / §12): a config change re-scores on the next read
# ---------------------------------------------------------------------------
def test_settings_change_rederives_scores(auth_client):
    def residual(ref):
        risks = auth_client.get("/api/risks").json()
        risk = next(r for r in risks if r["ref"] == ref)
        return risk["residual_score"], risk["residual_band"]["name"]

    # Default method is multiply: RISK-001 residual is L=2, I=5 -> 10 (High).
    assert residual("RISK-001") == (10.0, "High")

    changed = auth_client.put("/api/settings", json={"score_method": "add"})
    assert changed.status_code == 200, changed.text

    # Same stored likelihood/impact, re-derived under add: 2 + 5 = 7 (Medium).
    assert residual("RISK-001") == (7.0, "Medium")
