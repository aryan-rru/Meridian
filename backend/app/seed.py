"""§17 — seed / sample data.

Creates one workspace ("Sample Org"), the default scoring config, three frameworks with
21 requirements, 24 controls with a deliberate status spread, the crosswalk mappings, 10
risks with mitigating-control mappings (several designed to trip the unearned-residual flag),
and a few URL evidence placeholders so seeding needs no Google Drive.

    python -m app.seed            # create if empty (idempotent-ish; skips if Sample Org exists)
    python -m app.seed --reset    # wipe all data first, then re-create

The demo user matches DEV_LOGIN_EMAIL so `POST /api/auth/dev-login` lands in this workspace.
"""

from __future__ import annotations

import argparse
import logging

from sqlalchemy import delete, select

from app.config import settings
from app.db import SessionLocal, utcnow
from app.models import (
    Control,
    ControlRequirementMapping,
    ControlStatus,
    CoverageLevel,
    Evidence,
    EvidenceSource,
    EvidenceStatus,
    Framework,
    OAuthCredential,
    Requirement,
    Risk,
    RiskControlMapping,
    RiskStatus,
    RiskTreatment,
    ScoringConfig,
    User,
    Workspace,
    WorkspaceMember,
    WorkspaceRole,
    default_config_kwargs,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")
logger = logging.getLogger("meridian.seed")

WORKSPACE_NAME = "Sample Org"

# ---------------------------------------------------------------------------
# 17.1 Frameworks
# ---------------------------------------------------------------------------
FRAMEWORKS = [
    {
        "key": "ISO27001",
        "name": "ISO/IEC 27001:2022 (Annex A)",
        "version": "2022",
        "color": "#2563eb",
        "sort_order": 1,
        "description": "Information security management system controls (Annex A).",
    },
    {
        "key": "SOC2",
        "name": "SOC 2 Trust Services Criteria",
        "version": "2017 (rev. 2022)",
        "color": "#7c3aed",
        "sort_order": 2,
        "description": "AICPA Trust Services Criteria — Common Criteria plus Availability.",
    },
    {
        "key": "NISTCSF",
        "name": "NIST Cybersecurity Framework 2.0",
        "version": "2.0",
        "color": "#0d9488",
        "sort_order": 3,
        "description": "Outcomes across Govern, Identify, Protect, Detect, Respond, Recover.",
    },
]

# ---------------------------------------------------------------------------
# 17.2 Requirements (7 per framework). (code, title, category)
# ---------------------------------------------------------------------------
REQUIREMENTS: dict[str, list[tuple[str, str, str]]] = {
    "ISO27001": [
        ("A.5.15", "Access control", "Organizational"),
        ("A.5.17", "Authentication information", "Organizational"),
        ("A.8.5", "Secure authentication", "Technological"),
        ("A.8.7", "Protection against malware", "Technological"),
        ("A.8.13", "Information backup", "Technological"),
        ("A.5.24", "Information security incident management planning", "Organizational"),
        ("A.8.16", "Monitoring activities", "Technological"),
    ],
    "SOC2": [
        ("CC6.1", "Logical access security controls", "Common Criteria — Logical Access"),
        ("CC6.2", "User registration & authorization", "Common Criteria — Logical Access"),
        ("CC6.3", "Access modification & removal", "Common Criteria — Logical Access"),
        (
            "CC6.6",
            "Protection against external threats (boundary)",
            "Common Criteria — Logical Access",
        ),
        ("CC6.7", "Data transmission & encryption", "Common Criteria — Logical Access"),
        ("CC7.2", "Security monitoring for anomalies", "Common Criteria — System Operations"),
        ("A1.2", "Backup & recovery", "Availability"),
    ],
    "NISTCSF": [
        ("GV.RM", "Risk Management Strategy", "Govern"),
        ("ID.AM", "Asset Management", "Identify"),
        ("PR.AA", "Identity, Authentication & Access Control", "Protect"),
        ("PR.DS", "Data Security", "Protect"),
        ("DE.CM", "Continuous Monitoring", "Detect"),
        ("RS.MA", "Incident Management", "Respond"),
        ("RC.RP", "Recovery Plan Execution", "Recover"),
    ],
}

# ---------------------------------------------------------------------------
# 17.3 Controls (24). (ref, name, category, status)
# ---------------------------------------------------------------------------
_IMPL = ControlStatus.IMPLEMENTED.value
_PART = ControlStatus.PARTIAL.value
_NONE = ControlStatus.NOT_IMPLEMENTED.value

CONTROLS: list[tuple[str, str, str, str]] = [
    ("CTL-001", "Multi-Factor Authentication", "Access Management", _PART),
    ("CTL-002", "Password Policy & Management", "Access Management", _IMPL),
    ("CTL-003", "Role-Based Access Control", "Access Management", _IMPL),
    ("CTL-004", "Joiner–Mover–Leaver Process", "Access Management", _IMPL),
    ("CTL-005", "Quarterly Access Reviews", "Access Management", _PART),
    ("CTL-006", "Privileged Access Management", "Access Management", _NONE),
    ("CTL-007", "Single Sign-On", "Access Management", _IMPL),
    ("CTL-008", "Endpoint Anti-Malware / EDR", "Threat Protection", _IMPL),
    ("CTL-009", "Patch & Vulnerability Management", "Threat Protection", _PART),
    ("CTL-010", "Firewall & Network Segmentation", "Network Security", _IMPL),
    ("CTL-011", "Intrusion Detection/Prevention", "Network Security", _NONE),
    ("CTL-012", "Encryption in Transit (TLS)", "Data Protection", _IMPL),
    ("CTL-013", "Encryption at Rest", "Data Protection", _IMPL),
    ("CTL-014", "Data Backup", "Backup & Recovery", _IMPL),
    ("CTL-015", "Backup Restoration Testing", "Backup & Recovery", _PART),
    ("CTL-016", "Centralised Logging & SIEM", "Logging & Monitoring", _IMPL),
    ("CTL-017", "Security Monitoring & Alerting", "Logging & Monitoring", _IMPL),
    ("CTL-018", "Incident Response Plan", "Incident Response", _IMPL),
    ("CTL-019", "Incident Response Testing (Tabletop)", "Incident Response", _PART),
    ("CTL-020", "Asset Inventory Management", "Governance", _IMPL),
    ("CTL-021", "Risk Assessment Process", "Governance", _IMPL),
    ("CTL-022", "Security Awareness Training", "Governance", _IMPL),
    ("CTL-023", "Vendor / Third-Party Risk Management", "Governance", _PART),
    ("CTL-024", "Change Management", "Governance", _IMPL),
]

# ---------------------------------------------------------------------------
# 17.4 Crosswalk: control ref → requirement codes.
# Most mappings are 'full'; a couple are 'partial' (noted below).
#
# NOTE — two mappings from §17.4 are deliberately omitted so the seed satisfies
# acceptance criterion §20 #3 ("the coverage heatmap shows at least one `gap` and
# one `partial`"). As written, §17.4's crosswalk is dense enough that every one of
# the 21 requirements has at least one *implemented* control, which classifies them
# all as `covered` — leaving zero gaps/partials and contradicting the §17.3 note
# ("so gaps ... appear"). We drop exactly two edges, both from *implemented*
# controls, so the remediation ranking, the risk unearned-residual flags and the
# export/import round-trip are all unaffected:
#   • CTL-004 (implemented) → CC6.2 removed  ⇒ CC6.2 has no mapped control  ⇒ hard `gap`.
#   • CTL-014 (implemented) → A1.2  removed  ⇒ A1.2 answered only by CTL-015 (partial)
#     ⇒ `partial`. (CTL-015 keeps A1.2, so its remediation leverage is unchanged.)
# ---------------------------------------------------------------------------
CROSSWALK: dict[str, list[str]] = {
    "CTL-001": ["A.8.5", "A.5.17", "CC6.1", "PR.AA"],
    "CTL-002": ["A.5.17", "A.8.5", "CC6.1", "PR.AA"],
    "CTL-003": ["A.5.15", "CC6.1", "CC6.3", "PR.AA"],
    "CTL-004": ["A.5.15", "CC6.3", "PR.AA"],  # CC6.2 intentionally unmapped → gap (see note)
    "CTL-005": ["A.5.15", "CC6.3", "PR.AA"],
    "CTL-006": ["A.5.15", "CC6.1", "PR.AA"],
    "CTL-007": ["A.8.5", "CC6.1", "PR.AA"],
    "CTL-008": ["A.8.7", "CC6.6", "DE.CM", "PR.DS"],
    "CTL-009": ["A.8.7", "CC6.6", "ID.AM", "PR.DS"],
    "CTL-010": ["CC6.6", "PR.DS", "PR.AA"],
    "CTL-011": ["CC6.6", "CC7.2", "DE.CM"],
    "CTL-012": ["CC6.7", "PR.DS"],
    "CTL-013": ["CC6.7", "PR.DS"],
    "CTL-014": ["A.8.13", "RC.RP"],  # A1.2 intentionally left to CTL-015 only → partial (see note)
    "CTL-015": ["A.8.13", "A1.2", "RC.RP"],
    "CTL-016": ["A.8.16", "CC7.2", "DE.CM"],
    "CTL-017": ["A.8.16", "CC7.2", "DE.CM"],
    "CTL-018": ["A.5.24", "CC7.2", "RS.MA"],
    "CTL-019": ["A.5.24", "RS.MA"],
    "CTL-020": ["ID.AM", "CC6.1"],
    "CTL-021": ["GV.RM", "ID.AM"],
    "CTL-022": ["A.8.7", "PR.AA", "GV.RM"],
    "CTL-023": ["GV.RM", "CC6.6"],
    "CTL-024": ["CC7.2", "PR.DS"],
}

#: (control_ref, requirement_code) pairs that are only a *partial* answer (§17.4).
PARTIAL_MAPPINGS = {("CTL-005", "PR.AA"), ("CTL-022", "PR.AA")}

# ---------------------------------------------------------------------------
# 17.5 Risks. (ref, title, inh L, inh I, res L, res I, [control refs])
# ---------------------------------------------------------------------------
RISKS: list[tuple[str, str, int, int, int, int, list[str]]] = [
    (
        "RISK-001",
        "Account takeover via stolen credentials",
        4,
        5,
        2,
        5,
        ["CTL-001", "CTL-002", "CTL-006", "CTL-007"],
    ),
    (
        "RISK-002",
        "Unauthorized access from excess privilege",
        4,
        4,
        2,
        4,
        ["CTL-003", "CTL-004", "CTL-005", "CTL-006"],
    ),
    (
        "RISK-003",
        "Ransomware / malware outbreak",
        5,
        5,
        3,
        4,
        ["CTL-008", "CTL-009", "CTL-014", "CTL-015", "CTL-022"],
    ),
    ("RISK-004", "Data intercepted in transit", 3, 5, 1, 5, ["CTL-012", "CTL-010"]),
    ("RISK-005", "Data exposed at rest (lost/stolen store)", 4, 5, 2, 5, ["CTL-013", "CTL-003"]),
    (
        "RISK-006",
        "Undetected intrusion / dwell time",
        4,
        4,
        3,
        4,
        ["CTL-011", "CTL-016", "CTL-017"],
    ),
    ("RISK-007", "Prolonged outage / data loss", 4, 5, 2, 4, ["CTL-014", "CTL-015", "CTL-018"]),
    (
        "RISK-008",
        "Slow / ineffective incident response",
        4,
        4,
        3,
        3,
        ["CTL-018", "CTL-019", "CTL-016"],
    ),
    ("RISK-009", "Third-party / vendor compromise", 4, 4, 3, 4, ["CTL-023", "CTL-005"]),
    (
        "RISK-010",
        "Exploited unpatched vulnerability",
        5,
        4,
        2,
        4,
        ["CTL-009", "CTL-020", "CTL-024"],
    ),
]

RISK_CATEGORIES = {
    "RISK-001": "Access",
    "RISK-002": "Access",
    "RISK-003": "Malware",
    "RISK-004": "Data Protection",
    "RISK-005": "Data Protection",
    "RISK-006": "Detection",
    "RISK-007": "Availability",
    "RISK-008": "Incident Response",
    "RISK-009": "Third Party",
    "RISK-010": "Vulnerability",
}

# ---------------------------------------------------------------------------
# Example evidence (URL placeholders — no Drive needed at seed time).
# ---------------------------------------------------------------------------
EVIDENCE = [
    ("CTL-002", "Password Policy (Confluence)", "https://example.com/policies/password-policy"),
    ("CTL-014", "Backup Runbook & Latest Job Report", "https://example.com/runbooks/backup"),
    ("CTL-018", "Incident Response Plan v3", "https://example.com/policies/incident-response-plan"),
]

# Tables cleared by --reset, in FK-safe order (children first).
_RESET_ORDER = [
    RiskControlMapping,
    ControlRequirementMapping,
    Evidence,
    Risk,
    Control,
    Requirement,
    Framework,
    ScoringConfig,
    WorkspaceMember,
    OAuthCredential,
    Workspace,
    User,
]


def reset(db) -> None:
    logger.warning("Reset requested — deleting all existing data.")
    for model in _RESET_ORDER:
        db.execute(delete(model))
    db.commit()


def seed(db) -> None:
    existing = db.execute(
        select(Workspace).where(Workspace.name == WORKSPACE_NAME)
    ).scalar_one_or_none()
    if existing is not None:
        logger.info("'%s' already exists — nothing to do. Use --reset to rebuild.", WORKSPACE_NAME)
        return

    # Demo owner. Matches DEV_LOGIN_EMAIL so dev-login lands here (no Google needed).
    demo = User(email=settings.dev_login_email, name="Demo User")
    db.add(demo)
    db.flush()

    workspace = Workspace(name=WORKSPACE_NAME, created_by=demo.id)
    db.add(workspace)
    db.flush()
    db.add(
        WorkspaceMember(workspace_id=workspace.id, user_id=demo.id, role=WorkspaceRole.OWNER.value)
    )
    db.add(ScoringConfig(workspace_id=workspace.id, **default_config_kwargs()))

    # Frameworks + requirements.
    requirements_by_code: dict[str, Requirement] = {}
    for fw_data in FRAMEWORKS:
        framework = Framework(**fw_data)
        db.add(framework)
        db.flush()
        for order, (code, title, category) in enumerate(REQUIREMENTS[framework.key]):
            requirement = Requirement(
                framework_id=framework.id,
                code=code,
                title=title,
                category=category,
                sort_order=order,
            )
            db.add(requirement)
            db.flush()
            # Codes are unique per framework; none collide across our three, so a flat map is fine.
            requirements_by_code[code] = requirement

    # Controls.
    controls_by_ref: dict[str, Control] = {}
    for ref, name, category, status in CONTROLS:
        control = Control(
            workspace_id=workspace.id,
            ref=ref,
            name=name,
            category=category,
            status=status,
            owner="Security Team",
            description=f"{name} for {WORKSPACE_NAME}.",
        )
        db.add(control)
        db.flush()
        controls_by_ref[ref] = control

    # Crosswalk mappings.
    mapping_count = 0
    for control_ref, requirement_codes in CROSSWALK.items():
        control = controls_by_ref[control_ref]
        for code in requirement_codes:
            requirement = requirements_by_code[code]
            level = (
                CoverageLevel.PARTIAL.value
                if (control_ref, code) in PARTIAL_MAPPINGS
                else CoverageLevel.FULL.value
            )
            db.add(
                ControlRequirementMapping(
                    control_id=control.id,
                    requirement_id=requirement.id,
                    coverage_level=level,
                )
            )
            mapping_count += 1

    # Risks + mitigating-control mappings.
    for ref, title, inh_l, inh_i, res_l, res_i, control_refs in RISKS:
        risk = Risk(
            workspace_id=workspace.id,
            ref=ref,
            title=title,
            category=RISK_CATEGORIES.get(ref, ""),
            owner="Risk Owner",
            inherent_likelihood=inh_l,
            inherent_impact=inh_i,
            residual_likelihood=res_l,
            residual_impact=res_i,
            treatment=RiskTreatment.MITIGATE.value,
            status=RiskStatus.OPEN.value,
            description=f"{title}.",
        )
        db.add(risk)
        db.flush()
        for control_ref in control_refs:
            db.add(RiskControlMapping(risk_id=risk.id, control_id=controls_by_ref[control_ref].id))

    # Evidence (URL placeholders).
    for control_ref, evtitle, url in EVIDENCE:
        db.add(
            Evidence(
                workspace_id=workspace.id,
                control_id=controls_by_ref[control_ref].id,
                title=evtitle,
                description="Seeded example evidence.",
                source_type=EvidenceSource.URL.value,
                drive_file_name=evtitle,
                mime_type="text/uri-list",
                url=url,
                web_view_link=url,
                collected_at=utcnow(),
                status=EvidenceStatus.CURRENT.value,
            )
        )

    db.commit()
    logger.info(
        "Seeded '%s': %d frameworks, %d requirements, %d controls, %d crosswalk mappings, "
        "%d risks, %d evidence records.",
        WORKSPACE_NAME,
        len(FRAMEWORKS),
        sum(len(v) for v in REQUIREMENTS.values()),
        len(CONTROLS),
        mapping_count,
        len(RISKS),
        len(EVIDENCE),
    )
    logger.info(
        "Sign in at the frontend with dev-login (%s) to explore it.", settings.dev_login_email
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Meridian sample data.")
    parser.add_argument(
        "--reset", action="store_true", help="Delete all existing data before seeding."
    )
    args = parser.parse_args()

    with SessionLocal() as db:
        if args.reset:
            reset(db)
        seed(db)


if __name__ == "__main__":
    main()
