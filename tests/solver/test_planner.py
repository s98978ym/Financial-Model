from __future__ import annotations

from src.domain.canonical_model import (
    BusinessSegment,
    CanonicalBusinessModel,
    Driver,
    DriverSeries,
    FinancialTargets,
    ModelMetadata,
    RevenueEngine,
    YearValue,
)
from src.domain.evidence_ledger import AssumptionLedger, AssumptionRecord, ValueRange
from src.solver.planner import plan_to_targets


def _subscription_model(target_revenue: float) -> CanonicalBusinessModel:
    return CanonicalBusinessModel(
        metadata=ModelMetadata(project_name="SaaS Demo"),
        targets=FinancialTargets(
            revenue_targets=[YearValue(year="FY1", value=target_revenue, source="target")]
        ),
        segments=[
            BusinessSegment(
                segment_id="saas",
                name="SaaS",
                engines=[
                    RevenueEngine(
                        engine_id="saas_engine",
                        engine_type="subscription",
                        name="標準プラン",
                        drivers=[
                            Driver(
                                driver_id="monthly_price",
                                name="月額単価",
                                unit="JPY",
                                category="price",
                                series=DriverSeries(fy1=1000),
                                mode="fixed",
                            ),
                            Driver(
                                driver_id="subscribers",
                                name="契約数",
                                unit="count",
                                category="volume",
                                series=DriverSeries(fy1=10),
                                mode="solve_for",
                            ),
                        ],
                    )
                ],
            )
        ],
    )


def _subscription_ledger(max_subscribers: float) -> AssumptionLedger:
    return AssumptionLedger(
        records=[
            AssumptionRecord(
                record_id="assump_monthly_price",
                object_type="driver",
                object_id="monthly_price",
                metric_name="月額単価",
                value=1000,
                unit="JPY",
                source_type="document",
                review_status="approved",
                board_ready=True,
            ),
            AssumptionRecord(
                record_id="assump_subscribers",
                object_type="driver",
                object_id="subscribers",
                metric_name="契約数",
                value=10,
                unit="count",
                source_type="benchmark",
                allowed_range=ValueRange(min=10, base=15, max=max_subscribers),
            ),
        ]
    )


def test_planner_only_moves_solve_for_and_bounded_drivers() -> None:
    result = plan_to_targets(
        _subscription_model(target_revenue=240000),
        _subscription_ledger(max_subscribers=30),
    )

    assert result.feasibility == "solved"
    assert result.solved_driver_values["subscribers"].fy1 == 20
    assert result.solved_driver_values["monthly_price"].fy1 == 1000
    assert result.constraint_violations == []


def test_planner_returns_infeasible_when_solution_exceeds_allowed_range() -> None:
    result = plan_to_targets(
        _subscription_model(target_revenue=600000),
        _subscription_ledger(max_subscribers=30),
    )

    assert result.feasibility == "infeasible"
    assert any(violation.code == "range_exceeded" for violation in result.constraint_violations)


def test_planner_writes_solution_into_target_year_series_not_only_fy1() -> None:
    model = _subscription_model(target_revenue=360000)
    model.targets.revenue_targets[0].year = "FY3"

    result = plan_to_targets(model, _subscription_ledger(max_subscribers=40))

    assert result.feasibility == "solved"
    assert result.solved_driver_values["subscribers"].fy1 == 10
    assert result.solved_driver_values["subscribers"].fy3 == 30


def test_planner_returns_capacity_violation_for_consulting_case() -> None:
    model = CanonicalBusinessModel(
        metadata=ModelMetadata(project_name="FAM Consulting"),
        targets=FinancialTargets(
            revenue_targets=[YearValue(year="FY1", value=40_000_000, source="target")]
        ),
        segments=[
            BusinessSegment(
                segment_id="consulting",
                name="コンサル",
                engines=[
                    RevenueEngine(
                        engine_id="consulting_engine",
                        engine_type="project_capacity",
                        name="案件モデル",
                        constraints={"max_projects_per_head": 4},
                        drivers=[
                            Driver(
                                driver_id="unit_price",
                                name="案件単価",
                                unit="JPY",
                                category="price",
                                series=DriverSeries(fy1=2_000_000),
                                mode="fixed",
                            ),
                            Driver(
                                driver_id="project_count",
                                name="案件数",
                                unit="count",
                                category="volume",
                                series=DriverSeries(fy1=10),
                                mode="solve_for",
                            ),
                            Driver(
                                driver_id="headcount",
                                name="担当人数",
                                unit="people",
                                category="capacity",
                                series=DriverSeries(fy1=3),
                                mode="fixed",
                            ),
                        ],
                    )
                ],
            )
        ],
    )
    ledger = AssumptionLedger(
        records=[
            AssumptionRecord(
                record_id="assump_project_count",
                object_type="driver",
                object_id="project_count",
                metric_name="案件数",
                value=10,
                unit="count",
                source_type="benchmark",
                allowed_range=ValueRange(min=10, base=12, max=25),
            )
        ]
    )

    result = plan_to_targets(model, ledger)

    assert result.feasibility == "infeasible"
    assert any(violation.code == "capacity_exceeded" for violation in result.constraint_violations)
