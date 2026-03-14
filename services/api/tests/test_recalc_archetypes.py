from __future__ import annotations

from services.api.app.routers.recalc import _compute_segments


def test_compute_segments_uses_subscription_engine_variable_cost_when_available() -> None:
    segments = _compute_segments(
        parameters={
            "segments": [
                {
                    "name": "SaaS",
                    "revenue_fy1": 0,
                    "growth_rate": 0.3,
                    "cogs_rate": 0.4,
                }
            ]
        },
        revenue_model_configs=[
            {
                "segment_name": "SaaS",
                "archetype": "subscription",
                "config": {
                    "plans": [
                        {
                            "monthly_price": 1000,
                            "subscribers": [10, 20, 30, 40, 50],
                            "monthly_cost_per_subscriber": 250,
                        }
                    ]
                },
            }
        ],
    )

    assert segments[0]["revenue"] == [120000, 240000, 360000, 480000, 600000]
    assert segments[0]["cogs"] == [30000, 60000, 90000, 120000, 150000]
    assert segments[0]["gross_profit"] == [90000, 180000, 270000, 360000, 450000]


def test_compute_segments_uses_unit_economics_engine_instead_of_growth_fallback() -> None:
    segments = _compute_segments(
        parameters={
            "segments": [
                {
                    "name": "Meal",
                    "revenue_fy1": 0,
                    "growth_rate": 0.3,
                    "cogs_rate": 0.4,
                }
            ]
        },
        revenue_model_configs=[
            {
                "segment_name": "Meal",
                "archetype": "unit_economics",
                "config": {
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
                },
            }
        ],
    )

    assert segments[0]["revenue"] == [1800000, 2160000, 2520000, 2880000, 3240000]
    assert segments[0]["cogs"] == [648000, 777600, 907200, 1036800, 1166400]
    assert segments[0]["gross_profit"] == [1152000, 1382400, 1612800, 1843200, 2073600]
