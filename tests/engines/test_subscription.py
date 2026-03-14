from __future__ import annotations

from src.engines.base import EngineInput, EngineOutput


def test_engine_output_exposes_series_and_warnings() -> None:
    output = EngineOutput(
        revenue=[120000] * 5,
        variable_cost=[12000] * 5,
        gross_profit=[108000] * 5,
        warnings=["missing benchmark"],
    )

    assert output.revenue == [120000] * 5
    assert output.variable_cost == [12000] * 5
    assert output.gross_profit == [108000] * 5
    assert output.warnings == ["missing benchmark"]


def test_subscription_engine_computes_five_year_revenue_and_cost_series() -> None:
    from src.engines.subscription import SubscriptionEngine

    engine = SubscriptionEngine()
    output = engine.compute(
        EngineInput(
            config={
                "plans": [
                    {
                        "monthly_price": 1000,
                        "subscribers": [10, 20, 30, 40, 50],
                        "monthly_cost_per_subscriber": 250,
                    }
                ]
            }
        )
    )

    assert output.revenue == [120000, 240000, 360000, 480000, 600000]
    assert output.variable_cost == [30000, 60000, 90000, 120000, 150000]
    assert output.gross_profit == [90000, 180000, 270000, 360000, 450000]
    assert output.warnings == []


def test_subscription_engine_warns_when_plan_data_is_missing() -> None:
    from src.engines.subscription import SubscriptionEngine

    output = SubscriptionEngine().compute(EngineInput(config={}))

    assert output.revenue == [0, 0, 0, 0, 0]
    assert output.variable_cost == [0, 0, 0, 0, 0]
    assert output.gross_profit == [0, 0, 0, 0, 0]
    assert output.warnings == ["subscription plans are missing"]
