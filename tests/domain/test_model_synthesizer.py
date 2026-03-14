"""Tests for synthesis from business model analysis into canonical models."""

from __future__ import annotations

from src.agents.business_model_analyzer import (
    BreakevenTarget,
    BusinessModelAnalysis,
    BusinessModelProposal,
    BusinessSegment,
    CostItem,
    FinancialTargets,
    RevenueDriver,
    YearTarget,
)
from src.domain.model_synthesizer import build_assumption_ledger, synthesize_canonical_model


def _analysis_with_proposal() -> BusinessModelAnalysis:
    return BusinessModelAnalysis(
        company_name="FAM",
        document_narrative="FAM は複数サービスを持つ事業",
        proposals=[
            BusinessModelProposal(
                label="パターンA",
                industry="スポーツ栄養",
                business_model_type="B2B/B2C",
                executive_summary="複合モデル",
                segments=[
                    BusinessSegment(
                        name="ミール",
                        model_type="unit_economics",
                        revenue_formula="単価 × 食数 × ユニット数",
                        revenue_drivers=[
                            RevenueDriver(
                                name="価格/アイテム",
                                unit="円",
                                estimated_value="500",
                                evidence="価格/アイテム 500円",
                                is_from_document=True,
                            ),
                            RevenueDriver(
                                name="継続率",
                                unit="%",
                                estimated_value=None,
                                evidence="文書に記載なし",
                                is_from_document=False,
                            ),
                        ],
                        key_assumptions=["継続率は追加確認"],
                    )
                ],
                shared_costs=[
                    CostItem(
                        name="人件費",
                        category="fixed",
                        estimated_value="30000000",
                        evidence="人件費 3000万円",
                        is_from_document=True,
                    )
                ],
                growth_trajectory="5年成長",
                risk_factors=["採用難"],
                time_horizon="5年間",
                confidence=0.8,
                reasoning="文書根拠が多い",
            )
        ],
        selected_index=0,
        financial_targets=FinancialTargets(
            revenue_targets=[YearTarget(year="FY3", value=500_000_000, evidence="3年目5億円")],
            op_targets=[YearTarget(year="FY4", value=50_000_000, evidence="4年目営業利益5000万")],
            single_year_breakeven=BreakevenTarget(year="FY3", evidence="3年目単年黒字"),
        ),
    )


def test_synthesize_canonical_model_maps_segments_engines_and_targets() -> None:
    canonical = synthesize_canonical_model(_analysis_with_proposal())

    assert canonical.metadata.project_name == "FAM"
    assert canonical.targets.revenue_targets[0].value == 500_000_000
    assert canonical.targets.operating_profit_targets[0].value == 50_000_000
    assert canonical.targets.breakeven_targets[0].year == "FY3"
    assert canonical.segments[0].segment_id == "meal"
    assert canonical.segments[0].engines[0].engine_type == "unit_economics"


def test_synthesize_canonical_model_marks_missing_driver_values_as_decision_required() -> None:
    canonical = synthesize_canonical_model(_analysis_with_proposal())

    drivers = canonical.segments[0].engines[0].drivers
    retention = next(driver for driver in drivers if driver.name == "継続率")

    assert retention.decision_required is True
    assert retention.source == "inferred"


def test_build_assumption_ledger_captures_driver_and_cost_provenance() -> None:
    ledger = build_assumption_ledger(_analysis_with_proposal())

    assert len(ledger.records) >= 3
    assert any(record.metric_name == "価格/アイテム" and record.source_type == "document" for record in ledger.records)
    assert any(record.metric_name == "人件費" and record.object_type == "cost_pool" for record in ledger.records)
