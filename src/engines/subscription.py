"""Subscription revenue engine."""

from __future__ import annotations

from .base import EngineInput, EngineOutput, coerce_series, zero_series


class SubscriptionEngine:
    engine_type = "subscription"

    def compute(self, engine_input: EngineInput) -> EngineOutput:
        plans = engine_input.config.get("plans", [])
        horizon_years = engine_input.horizon_years
        if not plans:
            return EngineOutput(
                revenue=zero_series(horizon_years),
                variable_cost=zero_series(horizon_years),
                gross_profit=zero_series(horizon_years),
                warnings=["subscription plans are missing"],
                required_driver_names=["monthly_price", "subscribers"],
            )

        revenue = zero_series(horizon_years)
        variable_cost = zero_series(horizon_years)

        for plan in plans:
            monthly_price = float(plan.get("monthly_price", 0) or 0)
            monthly_cost = float(plan.get("monthly_cost_per_subscriber", 0) or 0)
            subscribers = coerce_series(plan.get("subscribers"), horizon_years)
            for year in range(horizon_years):
                subs = subscribers[year]
                revenue[year] += round(subs * monthly_price * 12)
                variable_cost[year] += round(subs * monthly_cost * 12)

        gross_profit = [rev - cost for rev, cost in zip(revenue, variable_cost)]
        return EngineOutput(
            revenue=revenue,
            variable_cost=variable_cost,
            gross_profit=gross_profit,
            required_driver_names=["monthly_price", "subscribers"],
        )
