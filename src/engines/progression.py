"""Progression-based revenue engine."""

from __future__ import annotations

from .base import EngineInput, EngineOutput, coerce_series, zero_series


class ProgressionEngine:
    engine_type = "progression"

    def compute(self, engine_input: EngineInput) -> EngineOutput:
        tiers = engine_input.config.get("tiers", [])
        horizon_years = engine_input.horizon_years
        if not tiers:
            return EngineOutput(
                revenue=zero_series(horizon_years),
                variable_cost=zero_series(horizon_years),
                gross_profit=zero_series(horizon_years),
                warnings=["progression tiers are missing"],
                required_driver_names=["price", "students"],
            )

        revenue = zero_series(horizon_years)
        variable_cost = zero_series(horizon_years)

        for tier in tiers:
            price = float(tier.get("price", 0) or 0)
            variable_cost_per_student = float(tier.get("variable_cost_per_student", 0) or 0)
            students = coerce_series(tier.get("students"), horizon_years)
            for year in range(horizon_years):
                student_count = students[year]
                revenue[year] += round(student_count * price)
                variable_cost[year] += round(student_count * variable_cost_per_student)

        gross_profit = [rev - cost for rev, cost in zip(revenue, variable_cost)]
        return EngineOutput(
            revenue=revenue,
            variable_cost=variable_cost,
            gross_profit=gross_profit,
            required_driver_names=["price", "students"],
        )
