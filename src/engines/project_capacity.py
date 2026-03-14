"""Project-capacity revenue engine."""

from __future__ import annotations

from .base import EngineInput, EngineOutput, coerce_series, zero_series


class ProjectCapacityEngine:
    engine_type = "project_capacity"

    def compute(self, engine_input: EngineInput) -> EngineOutput:
        skus = engine_input.config.get("skus", [])
        horizon_years = engine_input.horizon_years
        if not skus:
            return EngineOutput(
                revenue=zero_series(horizon_years),
                variable_cost=zero_series(horizon_years),
                gross_profit=zero_series(horizon_years),
                warnings=["project capacity skus are missing"],
                required_driver_names=["unit_price", "quantities"],
            )

        revenue = zero_series(horizon_years)
        variable_cost = zero_series(horizon_years)

        for sku in skus:
            unit_price = float(sku.get("unit_price", 0) or 0)
            unit_cost = float(sku.get("unit_cost", 0) or 0)
            quantities = coerce_series(sku.get("quantities"), horizon_years)
            for year in range(horizon_years):
                quantity = quantities[year]
                revenue[year] += round(quantity * unit_price)
                variable_cost[year] += round(quantity * unit_cost)

        gross_profit = [rev - cost for rev, cost in zip(revenue, variable_cost)]

        constraint_hints = []
        headcount = engine_input.config.get("headcount")
        max_projects_per_head = engine_input.config.get("max_projects_per_head")
        if headcount and max_projects_per_head:
            capacity_series = coerce_series(headcount, horizon_years)
            max_projects = float(max_projects_per_head)
            total_quantities = zero_series(horizon_years)
            for sku in skus:
                sku_quantities = coerce_series(sku.get("quantities"), horizon_years)
                for year in range(horizon_years):
                    total_quantities[year] += round(sku_quantities[year])
            if any(total_quantities[year] > capacity_series[year] * max_projects for year in range(horizon_years)):
                constraint_hints.append("project demand exceeds modeled capacity")

        return EngineOutput(
            revenue=revenue,
            variable_cost=variable_cost,
            gross_profit=gross_profit,
            required_driver_names=["unit_price", "quantities"],
            constraint_hints=constraint_hints,
        )
