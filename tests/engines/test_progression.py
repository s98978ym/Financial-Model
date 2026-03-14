from __future__ import annotations

from src.engines.base import EngineInput


def test_progression_engine_computes_revenue_cost_and_profit() -> None:
    from src.engines.progression import ProgressionEngine

    output = ProgressionEngine().compute(
        EngineInput(
            config={
                "tiers": [
                    {
                        "price": 100000,
                        "students": [30, 40, 50, 60, 70],
                        "variable_cost_per_student": 15000,
                    }
                ]
            }
        )
    )

    assert output.revenue == [3000000, 4000000, 5000000, 6000000, 7000000]
    assert output.variable_cost == [450000, 600000, 750000, 900000, 1050000]
    assert output.gross_profit == [2550000, 3400000, 4250000, 5100000, 5950000]
    assert output.warnings == []


def test_progression_engine_warns_when_tiers_are_missing() -> None:
    from src.engines.progression import ProgressionEngine

    output = ProgressionEngine().compute(EngineInput(config={}))

    assert output.revenue == [0, 0, 0, 0, 0]
    assert output.warnings == ["progression tiers are missing"]
