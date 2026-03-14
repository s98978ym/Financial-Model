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
from src.domain.evidence_ledger import AssumptionLedger, AssumptionRecord, EvidenceRef, ValueRange
from src.explain.explanation_pack import build_explanation_pack
from src.solver.constraints import ConstraintViolation
from src.solver.planner import PlannerResult


def _model() -> CanonicalBusinessModel:
    return CanonicalBusinessModel(
        metadata=ModelMetadata(project_name="FAM"),
        targets=FinancialTargets(
            revenue_targets=[YearValue(year="FY1", value=240000, source="target")]
        ),
        segments=[
            BusinessSegment(
                segment_id="saas",
                name="Subscription",
                engines=[
                    RevenueEngine(
                        engine_id="sub_engine",
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
                                series=DriverSeries(fy1=20),
                                mode="solve_for",
                            ),
                        ],
                    )
                ],
            )
        ],
    )


def _ledger(board_ready_for_subscribers: bool = True) -> AssumptionLedger:
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
                evidence_refs=[
                    EvidenceRef(
                        ref_type="document_quote",
                        source_id="pdf:fam",
                        location="page:10",
                        quote="標準価格は月額1,000円",
                    )
                ],
                review_status="grounded",
                board_ready=True,
                explanation="料金表に記載",
            ),
            AssumptionRecord(
                record_id="assump_subscribers",
                object_type="driver",
                object_id="subscribers",
                metric_name="契約数",
                value=20,
                unit="count",
                source_type="benchmark",
                evidence_refs=[
                    EvidenceRef(
                        ref_type="benchmark",
                        source_id="benchmark:saas",
                        quote="同業平均の初年度契約数レンジ",
                    )
                ],
                allowed_range=ValueRange(min=10, base=20, max=30),
                review_status="approved" if board_ready_for_subscribers else "needs_review",
                board_ready=board_ready_for_subscribers,
                explanation="ベンチマークに基づく初年度想定",
            ),
        ]
    )


def test_explanation_pack_includes_top_drivers_and_provenance() -> None:
    pack = build_explanation_pack(
        _model(),
        _ledger(),
        PlannerResult(
            feasibility="solved",
            solved_driver_values={
                "monthly_price": DriverSeries(fy1=1000),
                "subscribers": DriverSeries(fy1=20),
            },
            explanation="Planner found a feasible path.",
        ),
    )

    assert pack.headline.startswith("FAM")
    assert {driver.driver_id for driver in pack.top_drivers} == {"monthly_price", "subscribers"}
    assert any("document" in summary for summary in pack.evidence_summary)


def test_explanation_pack_includes_constraint_summary_and_sensitivity_hints() -> None:
    pack = build_explanation_pack(
        _model(),
        _ledger(),
        PlannerResult(
            feasibility="infeasible",
            solved_driver_values={},
            constraint_violations=[
                ConstraintViolation(
                    code="capacity_exceeded",
                    object_id="subscribers",
                    message="Required projects exceed modeled staffing capacity",
                )
            ],
            explanation="Planner could not satisfy the target.",
        ),
    )

    assert "Required projects exceed modeled staffing capacity" in pack.constraint_summary
    assert len(pack.sensitivity_hints) >= 1


def test_explanation_pack_is_not_board_ready_when_major_assumption_is_ungrounded() -> None:
    pack = build_explanation_pack(
        _model(),
        _ledger(board_ready_for_subscribers=False),
        PlannerResult(
            feasibility="solved",
            solved_driver_values={
                "monthly_price": DriverSeries(fy1=1000),
                "subscribers": DriverSeries(fy1=20),
            },
            explanation="Planner found a feasible path.",
        ),
    )

    assert pack.board_ready is False
