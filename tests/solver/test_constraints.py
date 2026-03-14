from __future__ import annotations

from src.domain.evidence_ledger import AssumptionRecord, ValueRange
from src.solver.constraints import check_allowed_range, check_project_capacity


def test_check_allowed_range_returns_none_within_bounds() -> None:
    record = AssumptionRecord(
        record_id="assump_subscribers",
        object_type="driver",
        object_id="subscribers",
        metric_name="契約数",
        value=10,
        unit="count",
        source_type="benchmark",
        allowed_range=ValueRange(min=10, base=15, max=30),
    )

    assert check_allowed_range(record, 20) is None


def test_check_allowed_range_returns_violation_outside_bounds() -> None:
    record = AssumptionRecord(
        record_id="assump_subscribers",
        object_type="driver",
        object_id="subscribers",
        metric_name="契約数",
        value=10,
        unit="count",
        source_type="benchmark",
        allowed_range=ValueRange(min=10, base=15, max=30),
    )

    violation = check_allowed_range(record, 40)

    assert violation is not None
    assert violation.code == "range_exceeded"
    assert violation.object_id == "subscribers"


def test_check_project_capacity_returns_violation_when_projects_exceed_capacity() -> None:
    violation = check_project_capacity(
        object_id="consulting_projects",
        required_projects=20,
        headcount=3,
        max_projects_per_head=4,
    )

    assert violation is not None
    assert violation.code == "capacity_exceeded"
    assert violation.limit_value == 12
