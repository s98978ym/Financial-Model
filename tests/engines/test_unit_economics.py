from __future__ import annotations

from src.engines.base import EngineInput


def test_unit_economics_engine_computes_revenue_cost_and_profit() -> None:
    from src.engines.unit_economics import UnitEconomicsEngine

    output = UnitEconomicsEngine().compute(
        EngineInput(
            config={
                "skus": [
                    {
                        "price": 500,
                        "items_per_txn": 3,
                        "txns_per_person": 1,
                        "annual_purchases": 12,
                        "customers": [100, 120, 140, 160, 180],
                        "unit_cost": 180,
                    }
                ]
            }
        )
    )

    assert output.revenue == [1800000, 2160000, 2520000, 2880000, 3240000]
    assert output.variable_cost == [648000, 777600, 907200, 1036800, 1166400]
    assert output.gross_profit == [1152000, 1382400, 1612800, 1843200, 2073600]
    assert output.warnings == []


def test_unit_economics_engine_warns_when_customer_series_is_missing() -> None:
    from src.engines.unit_economics import UnitEconomicsEngine

    output = UnitEconomicsEngine().compute(
        EngineInput(
            config={
                "skus": [
                    {
                        "price": 500,
                        "items_per_txn": 3,
                        "annual_purchases": 12,
                    }
                ]
            }
        )
    )

    assert output.revenue == [0, 0, 0, 0, 0]
    assert output.warnings == ["unit economics customer series is missing"]
