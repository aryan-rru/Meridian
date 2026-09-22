"""Domain enumerations (§6). Stored as plain strings for portability and easy Excel I/O."""

from __future__ import annotations

from enum import StrEnum


class ControlStatus(StrEnum):
    NOT_IMPLEMENTED = "not_implemented"
    PARTIAL = "partial"
    IMPLEMENTED = "implemented"
    NOT_APPLICABLE = "not_applicable"


class CoverageLevel(StrEnum):
    """How completely a control answers a requirement."""

    FULL = "full"
    PARTIAL = "partial"


class CoverageStatus(StrEnum):
    """Derived per-requirement coverage (§7.3)."""

    COVERED = "covered"
    PARTIAL = "partial"
    GAP = "gap"


class RiskTreatment(StrEnum):
    MITIGATE = "mitigate"
    ACCEPT = "accept"
    TRANSFER = "transfer"
    AVOID = "avoid"


class RiskStatus(StrEnum):
    OPEN = "open"
    MONITORING = "monitoring"
    CLOSED = "closed"


class EvidenceSource(StrEnum):
    DRIVE_FILE = "drive_file"
    GOOGLE_SHEET = "google_sheet"
    UPLOAD = "upload"
    URL = "url"


class EvidenceStatus(StrEnum):
    CURRENT = "current"
    STALE = "stale"
    MISSING = "missing"


class ScoreMethod(StrEnum):
    MULTIPLY = "multiply"
    ADD = "add"
    WEIGHTED = "weighted"


class WorkspaceRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


#: Roles permitted to mutate workspace content. Viewers are read-only (§13).
WRITE_ROLES = {WorkspaceRole.OWNER, WorkspaceRole.ADMIN, WorkspaceRole.MEMBER}
#: Roles permitted to administer the workspace itself (members, settings).
ADMIN_ROLES = {WorkspaceRole.OWNER, WorkspaceRole.ADMIN}

#: Control statuses that cannot be said to reduce risk (§7.6).
UNEARNED_STATUSES = {
    ControlStatus.NOT_IMPLEMENTED,
    ControlStatus.PARTIAL,
    ControlStatus.NOT_APPLICABLE,
}

#: Ordering used to find the "weakest supporting control" (§7.5).
STATUS_STRENGTH: dict[str, int] = {
    ControlStatus.NOT_IMPLEMENTED: 0,
    ControlStatus.NOT_APPLICABLE: 1,
    ControlStatus.PARTIAL: 2,
    ControlStatus.IMPLEMENTED: 3,
}
