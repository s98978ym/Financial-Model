from __future__ import annotations

from src.engines.base import EngineInput


def test_project_capacity_engine_computes_revenue_cost_and_capacity_hints() -> None:
    from src.engines.project_capacity import ProjectCapacityEngine

    output = ProjectCapacityEngine().compute(
        EngineInput(
            config={
                "skus": [
                    {
                        "unit_price": 2000000,
                        "quantities": [10, 12, 14, 16, 18],
                        "unit_cost": 600000,
                    }
                ],
                "headcount": [3, 3, 4, 4, 5],
                "max_projects_per_head": 4,
            }
        )
    )

    assert output.revenue == [20000000, 24000000, 28000000, 32000000, 36000000]
    assert output.variable_cost == [6000000, 7200000, 8400000, 9600000, 10800000]
    assert output.gross_profit == [14000000, 16800000, 19600000, 22400000, 25200000]
    assert output.constraint_hints == []
    assert output.warnings == []


def test_project_capacity_engine_warns_when_capacity_is_exceeded() -> None:
    from src.engines.project_capacity import ProjectCapacityEngine

    output = ProjectCapacityEngine().compute(
        EngineInput(
            config={
                "skus": [
                    {
                        "unit_price": 2000000,
                        "quantities": [20, 20, 20, 20, 20],
                        "unit_cost": 500000,
                    }
                ],
                "headcount": [3, 3, 3, 3, 3],
                "max_projects_per_head": 4,
            }
        )
    )

    assert output.revenue == [40000000, 40000000, 40000000, 40000000, 40000000]
    assert "project demand exceeds modeled capacity" in output.constraint_hints
