from __future__ import annotations

import pytest

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
from src.excel.template_v2 import segment_model_types_from_canonical
from src.simulation.engine import build_parameter_ranges_from_canonical
from src.solver.planner import PlannerResult
from services.api.app.routers.recalc import _canonical_to_recalc_inputs


def _canonical_model() -> CanonicalBusinessModel:
    return CanonicalBusinessModel(
        metadata=ModelMetadata(project_name="Adapter Demo"),
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
            ),
            BusinessSegment(
                segment_id="consulting",
                name="Consulting",
                engines=[
                    RevenueEngine(
                        engine_id="consulting_engine",
                        engine_type="project_capacity",
                        name="案件モデル",
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
                        ],
                    )
                ],
            ),
        ],
    )


def _ledger() -> AssumptionLedger:
    return AssumptionLedger(
        records=[
            AssumptionRecord(
                record_id="assump_subscribers",
                object_type="driver",
                object_id="subscribers",
                metric_name="契約数",
                value=20,
                unit="count",
                source_type="benchmark",
                allowed_range=ValueRange(min=10, base=20, max=30),
            ),
            AssumptionRecord(
                record_id="assump_monthly_price",
                object_type="driver",
                object_id="monthly_price",
                metric_name="月額単価",
                value=1000,
                unit="JPY",
                source_type="document",
            ),
        ]
    )


def test_canonical_to_recalc_inputs_produces_segment_payloads_and_model_configs() -> None:
    payload = _canonical_to_recalc_inputs(
        _canonical_model(),
        PlannerResult(
            feasibility="solved",
            solved_driver_values={
                "monthly_price": DriverSeries(fy1=1000),
                "subscribers": DriverSeries(fy1=20),
                "unit_price": DriverSeries(fy1=2_000_000),
                "project_count": DriverSeries(fy1=10),
            },
        ),
    )

    assert payload["parameters"]["segments"][0]["name"] == "Subscription"
    assert payload["revenue_model_configs"][0]["archetype"] == "subscription"
    assert payload["revenue_model_configs"][1]["archetype"] == "project_capacity"


def test_build_parameter_ranges_from_canonical_prefers_allowed_ranges() -> None:
    ranges = build_parameter_ranges_from_canonical(_canonical_model(), _ledger())

    assert ranges["subscribers"] == (10, 30)
    assert ranges["monthly_price"] == (800.0, 1200.0)


def test_segment_model_types_from_canonical_matches_engine_types() -> None:
    assert segment_model_types_from_canonical(_canonical_model()) == [
        "subscription",
        "project_capacity",
    ]


def test_canonical_to_recalc_inputs_maps_meal_style_unit_economics_drivers() -> None:
    model = CanonicalBusinessModel(
        metadata=ModelMetadata(project_name="Meal Demo"),
        segments=[
            BusinessSegment(
                segment_id="meal",
                name="Meal",
                engines=[
                    RevenueEngine(
                        engine_id="meal_engine",
                        engine_type="unit_economics",
                        name="Meal UE",
                        drivers=[
                            Driver(
                                driver_id="price_per_item",
                                name="価格/アイテム",
                                unit="JPY",
                                category="price",
                                series=DriverSeries(fy1=500),
                                mode="fixed",
                            ),
                            Driver(
                                driver_id="items_per_meal",
                                name="品数/食",
                                unit="count",
                                category="volume",
                                series=DriverSeries(fy1=3),
                                mode="fixed",
                            ),
                            Driver(
                                driver_id="meals_per_year",
                                name="年間提供食数",
                                unit="count",
                                category="volume",
                                series=DriverSeries(fy1=4800),
                                mode="fixed",
                            ),
                            Driver(
                                driver_id="unit_count",
                                name="ユニット数",
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

    payload = _canonical_to_recalc_inputs(model)
    sku = payload["revenue_model_configs"][0]["config"]["skus"][0]

    assert sku["price"] == 500
    assert sku["items_per_txn"] == 3
    assert sku["annual_purchases"] == 4800
    assert sku["txns_per_person"] == 1


def test_canonical_adapters_raise_when_segment_has_multiple_engines() -> None:
    model = CanonicalBusinessModel(
        metadata=ModelMetadata(project_name="Multi Engine Demo"),
        segments=[
            BusinessSegment(
                segment_id="hybrid",
                name="Hybrid",
                engines=[
                    RevenueEngine(
                        engine_id="sub_engine",
                        engine_type="subscription",
                        name="Subscription",
                    ),
                    RevenueEngine(
                        engine_id="project_engine",
                        engine_type="project_capacity",
                        name="Projects",
                    ),
                ],
            )
        ],
    )

    with pytest.raises(ValueError, match="multiple engines"):
        _canonical_to_recalc_inputs(model)

    with pytest.raises(ValueError, match="multiple engines"):
        segment_model_types_from_canonical(model)
