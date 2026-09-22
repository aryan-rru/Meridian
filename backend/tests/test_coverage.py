"""§18 — coverage classification (§7.3), gap analysis (§8.6) and remediation ranking (§7.7).

``classify`` is tested as a pure function; the roll-ups and ranking are tested against
the seeded workspace, whose expected numbers are pinned here (see the seed's §17.4 note:
two crosswalk edges are intentionally dropped so a gap and a partial exist).
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select

from app.models import CoverageStatus, Workspace
from app.models.enums import ControlStatus
from app.services.coverage import build_coverage, build_gaps, classify
from app.services.remediation import build_remediation
from app.services.scoring import ScoringContext


@dataclass
class FakeControl:
    status: str


# ---------------------------------------------------------------------------
# Pure classification (§7.3) — keyed off control STATUS, not coverage_level
# ---------------------------------------------------------------------------
def test_classify_covered_when_any_control_implemented():
    controls = [
        FakeControl(ControlStatus.NOT_IMPLEMENTED.value),
        FakeControl(ControlStatus.IMPLEMENTED.value),
    ]
    assert classify(controls) == CoverageStatus.COVERED


def test_classify_partial_when_none_implemented_but_one_partial():
    controls = [
        FakeControl(ControlStatus.NOT_IMPLEMENTED.value),
        FakeControl(ControlStatus.PARTIAL.value),
    ]
    assert classify(controls) == CoverageStatus.PARTIAL


def test_classify_gap_when_nothing_mapped():
    assert classify([]) == CoverageStatus.GAP


def test_classify_gap_when_all_not_implemented_or_not_applicable():
    controls = [
        FakeControl(ControlStatus.NOT_IMPLEMENTED.value),
        FakeControl(ControlStatus.NOT_APPLICABLE.value),
    ]
    assert classify(controls) == CoverageStatus.GAP


# ---------------------------------------------------------------------------
# Seeded roll-ups
# ---------------------------------------------------------------------------
def _workspace(db) -> Workspace:
    return db.execute(select(Workspace).where(Workspace.name == "Sample Org")).scalar_one()


def test_seeded_coverage_totals(seeded):
    db = seeded
    coverage = build_coverage(db, _workspace(db).id)
    totals = coverage["totals"]
    assert totals["total_requirements"] == 21
    assert totals["covered"] == 19
    assert totals["partial"] == 1
    assert totals["gap"] == 1
    assert totals["coverage_percent"] == 90.5


def test_seeded_gaps_have_one_gap_and_one_partial(seeded):
    db = seeded
    gaps = build_gaps(db, _workspace(db).id)
    assert gaps["gap_count"] == 1
    assert gaps["partial_count"] == 1

    by_status = {item["status"]: item for item in gaps["items"]}

    hard_gap = by_status["gap"]
    assert hard_gap["code"] == "CC6.2"
    assert hard_gap["needs_new_control"] is True
    assert hard_gap["closing_controls"] == []

    partial = by_status["partial"]
    assert partial["code"] == "A1.2"
    assert partial["needs_new_control"] is False
    assert [c["ref"] for c in partial["closing_controls"]] == ["CTL-015"]


def test_seeded_remediation_ranking_order(seeded):
    db = seeded
    result = build_remediation(db, _workspace(db).id, ScoringContext())
    assert result["candidate_count"] == 8

    items = result["items"]
    # Top two are pinned by the seed's risk/requirement leverage.
    assert items[0]["ref"] == "CTL-009"
    assert items[0]["priority"] == 47.0
    assert items[1]["ref"] == "CTL-015"
    assert items[1]["priority"] == 46.5

    # Priority is non-increasing and ranks are 1..n.
    priorities = [i["priority"] for i in items]
    assert priorities == sorted(priorities, reverse=True)
    assert [i["rank"] for i in items] == list(range(1, len(items) + 1))

    # Only unfinished controls are candidates (§7.7).
    assert all(
        i["status"] in {ControlStatus.NOT_IMPLEMENTED.value, ControlStatus.PARTIAL.value}
        for i in items
    )
