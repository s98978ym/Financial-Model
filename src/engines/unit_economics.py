"""Unit economics revenue engine."""

from __future__ import annotations

from .base import EngineInput, EngineOutput, coerce_series, zero_series


class UnitEconomicsEngine:
    engine_type = "unit_economics"

    def compute(self, engine_input: EngineInput) -> EngineOutput:
        skus = engine_input.config.get("skus", [])
        horizon_years = engine_input.horizon_years
        if not skus:
            return EngineOutput(
                revenue=zero_series(horizon_years),
                variable_cost=zero_series(horizon_years),
                gross_profit=zero_series(horizon_years),
                warnings=["unit economics customer series is missing"],
                required_driver_names=["price", "customers"],
            )

        revenue = zero_series(horizon_years)
        variable_cost = zero_series(horizon_years)
        has_customer_series = False

        for sku in skus:
            customers = sku.get("customers")
            if customers:
                has_customer_series = True
            customer_series = coerce_series(customers, horizon_years)
            price = float(sku.get("price", 0) or 0)
            items_per_txn = float(sku.get("items_per_txn", 1) or 1)
            txns_per_person = float(sku.get("txns_per_person", 1) or 1)
            annual_purchases = float(sku.get("annual_purchases", 12) or 12)
            unit_cost = float(sku.get("unit_cost", 0) or 0)
            annual_units_per_customer = items_per_txn * txns_per_person * annual_purchases

            for year in range(horizon_years):
                customer_count = customer_series[year]
                revenue[year] += round(customer_count * annual_units_per_customer * price)
                variable_cost[year] += round(customer_count * annual_units_per_customer * unit_cost)

        gross_profit = [rev - cost for rev, cost in zip(revenue, variable_cost)]
        warnings = [] if has_customer_series else ["unit economics customer series is missing"]
        if not has_customer_series:
            revenue = zero_series(horizon_years)
            variable_cost = zero_series(horizon_years)
            gross_profit = zero_series(horizon_years)

        return EngineOutput(
            revenue=revenue,
            variable_cost=variable_cost,
            gross_profit=gross_profit,
            warnings=warnings,
            required_driver_names=["price", "customers"],
        )
