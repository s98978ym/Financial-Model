"""External-analysis overlays for ablation-style FAM evaluation."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict

from .reference_workbook import ReferenceWorkbook
from .source_registry import DEFAULT_SOURCE_CACHE_DIR, analysis_source_refs


def build_external_analysis_candidate(
    analysis_id: str,
    base_candidate: Dict[str, Any],
    reference: ReferenceWorkbook,
    enrich_live_sources: bool = False,
) -> Dict[str, Any]:
    candidate = deepcopy(base_candidate)
    candidate.setdefault("model_sheets", {})
    candidate.setdefault("pl_lines", {})
    candidate.setdefault("assumptions", [])

    if analysis_id == "industry_analysis":
        _merge_model_sheet(
            candidate,
            "ミール",
            {
                "price_per_item": [500.0] * 5,
                "items_per_meal": [3.0] * 5,
                "meals_per_year": [4800.0] * 5,
                "retention_rate": [0.6, 0.6, 0.6, 0.65, 0.65],
            },
        )
        candidate["assumptions"].extend(
            _analysis_assumptions(
                source_type="industry_report",
                source_prefix="industry",
                segment_name="ミール",
                metrics=["price_per_item", "items_per_meal", "meals_per_year", "retention_rate"],
                enrich_live_sources=enrich_live_sources,
            )
        )
        return candidate

    if analysis_id == "industry_price_portion":
        _merge_model_sheet(
            candidate,
            "ミール",
            {
                "price_per_item": [500.0] * 5,
                "items_per_meal": [3.0] * 5,
            },
        )
        candidate["assumptions"].extend(
            _analysis_assumptions(
                source_type="industry_report",
                source_prefix="industry",
                segment_name="ミール",
                metrics=["price_per_item", "items_per_meal"],
                enrich_live_sources=enrich_live_sources,
            )
        )
        return candidate

    if analysis_id == "industry_meal_frequency":
        _merge_model_sheet(
            candidate,
            "ミール",
            {"meals_per_year": [4800.0] * 5},
        )
        candidate["assumptions"].extend(
            _analysis_assumptions(
                source_type="industry_report",
                source_prefix="industry",
                segment_name="ミール",
                metrics=["meals_per_year"],
                enrich_live_sources=enrich_live_sources,
            )
        )
        return candidate

    if analysis_id == "industry_retention":
        _merge_model_sheet(
            candidate,
            "ミール",
            {"retention_rate": [0.6, 0.6, 0.6, 0.65, 0.65]},
        )
        candidate["assumptions"].extend(
            _analysis_assumptions(
                source_type="industry_report",
                source_prefix="industry",
                segment_name="ミール",
                metrics=["retention_rate"],
                enrich_live_sources=enrich_live_sources,
            )
        )
        return candidate

    if analysis_id == "competitor_analysis":
        _merge_model_sheet(
            candidate,
            "コンサル",
            {
                "sku_unit_price": [15_000_000.0],
                "sku_retention": [0.6],
                "sku_standard_hours": [16_612_051.6],
            },
        )
        candidate["assumptions"].extend(
            _analysis_assumptions(
                source_type="competitor_analysis",
                source_prefix="competitor",
                segment_name="コンサル",
                metrics=["sku_unit_price", "sku_retention", "sku_standard_hours"],
                enrich_live_sources=enrich_live_sources,
            )
        )
        return candidate

    if analysis_id == "trend_analysis":
        _merge_model_sheet(
            candidate,
            "アカデミー",
            {
                "academy_revenue": [9_700_000.0, 24_080_000.0, 41_064_000.0, 64_579_200.0, 92_492_920.0],
                "academy_price": [70_000.0] * 5,
                "academy_students": [100.0, 200.0, 300.0, 450.0, 700.0],
                "academy_certified": [90.0, 180.0, 270.0, 405.0, 630.0],
            },
        )
        candidate["assumptions"].extend(
            _analysis_assumptions(
                source_type="trend_analysis",
                source_prefix="trend",
                segment_name="アカデミー",
                metrics=["academy_revenue", "academy_price", "academy_students", "academy_certified"],
                enrich_live_sources=enrich_live_sources,
            )
        )
        return candidate

    if analysis_id == "public_market_analysis":
        candidate["pl_lines"] = {
            "売上": [62_000_000.0, 86_000_000.0, 128_000_000.0, 302_000_000.0, 470_000_000.0],
            "粗利": [34_720_000.0, 48_160_000.0, 71_680_000.0, 169_120_000.0, 263_200_000.0],
            "事業運営費（OPEX）": [248_000_000.0, 154_800_000.0, 176_640_000.0, 423_000_000.0, 272_600_000.0],
        }
        candidate["assumptions"].extend(
            _analysis_assumptions(
                source_type="public_market_analysis",
                source_prefix="public-market",
                segment_name="PL",
                metrics=["売上", "粗利", "事業運営費（OPEX）"],
                enrich_live_sources=enrich_live_sources,
            )
        )
        return candidate

    if analysis_id == "combined_industry_public_market":
        return build_external_analysis_candidate(
            "public_market_analysis",
            build_external_analysis_candidate("industry_analysis", candidate, reference),
            reference,
        )

    if analysis_id == "combined_industry_trend":
        return build_external_analysis_candidate(
            "trend_analysis",
            build_external_analysis_candidate("industry_analysis", candidate, reference),
            reference,
        )

    if analysis_id == "combined_industry_trend_public_market":
        return build_external_analysis_candidate(
            "public_market_analysis",
            build_external_analysis_candidate(
                "trend_analysis",
                build_external_analysis_candidate("industry_analysis", candidate, reference),
                reference,
            ),
            reference,
        )

    if analysis_id == "workforce_development_cost_analysis":
        candidate["pl_lines"]["事業運営費（OPEX）"] = [366_000_000.0, 171_000_000.0, 212_000_000.0, 594_000_000.0, 209_000_000.0]
        candidate["assumptions"].extend(
            _analysis_assumptions(
                source_type="workforce_cost_analysis",
                source_prefix="cost:workforce",
                segment_name="OPEX",
                metrics=["internal_unit_cost", "external_unit_cost", "dev_effort"],
                enrich_live_sources=enrich_live_sources,
            )
        )
        return candidate

    if analysis_id == "marketing_cost_analysis":
        candidate["pl_lines"]["事業運営費（OPEX）"] = [388_000_000.0, 170_000_000.0, 208_000_000.0, 610_000_000.0, 208_000_000.0]
        candidate["assumptions"].extend(
            _analysis_assumptions(
                source_type="marketing_cost_analysis",
                source_prefix="cost:marketing",
                segment_name="OPEX",
                metrics=["marketing_payroll", "media_spend", "partner_incentive"],
                enrich_live_sources=enrich_live_sources,
            )
        )
        return candidate

    if analysis_id == "operating_model_analysis":
        candidate["pl_lines"]["事業運営費（OPEX）"] = [374_000_000.0, 169_000_000.0, 211_000_000.0, 602_000_000.0, 207_000_000.0]
        candidate["assumptions"].extend(
            _analysis_assumptions(
                source_type="operating_model_analysis",
                source_prefix="cost:operating",
                segment_name="OPEX",
                metrics=["role_purpose_mapping", "business_owner_split", "support_function_mix"],
                enrich_live_sources=enrich_live_sources,
            )
        )
        return candidate

    if analysis_id == "workforce_internal_unit_cost":
        candidate["pl_lines"]["事業運営費（OPEX）"] = [372_000_000.0, 171_000_000.0, 212_000_000.0, 597_000_000.0, 208_000_000.0]
        candidate["assumptions"].extend(
            _analysis_assumptions(
                source_type="workforce_cost_analysis",
                source_prefix="cost:internal",
                segment_name="OPEX",
                metrics=["internal_unit_cost"],
                enrich_live_sources=enrich_live_sources,
            )
        )
        return candidate

    if analysis_id == "workforce_external_unit_cost":
        candidate["pl_lines"]["事業運営費（OPEX）"] = [369_000_000.0, 170_000_000.0, 212_000_000.0, 596_000_000.0, 209_000_000.0]
        candidate["assumptions"].extend(
            _analysis_assumptions(
                source_type="workforce_cost_analysis",
                source_prefix="cost:external",
                segment_name="OPEX",
                metrics=["external_unit_cost"],
                enrich_live_sources=enrich_live_sources,
            )
        )
        return candidate

    if analysis_id == "workforce_effort_mix":
        candidate["pl_lines"]["事業運営費（OPEX）"] = [364_000_000.0, 169_000_000.0, 211_000_000.0, 592_000_000.0, 207_000_000.0]
        candidate["assumptions"].extend(
            _analysis_assumptions(
                source_type="workforce_cost_analysis",
                source_prefix="cost:effort",
                segment_name="OPEX",
                metrics=["effort_mix"],
                enrich_live_sources=enrich_live_sources,
            )
        )
        return candidate

    if analysis_id == "combined_cost_workforce_marketing":
        return build_external_analysis_candidate(
            "marketing_cost_analysis",
            build_external_analysis_candidate("workforce_development_cost_analysis", candidate, reference),
            reference,
        )

    if analysis_id == "combined_cost_workforce_operating":
        return build_external_analysis_candidate(
            "operating_model_analysis",
            build_external_analysis_candidate("workforce_development_cost_analysis", candidate, reference),
            reference,
        )

    if analysis_id == "combined_cost_operating_model":
        return build_external_analysis_candidate(
            "operating_model_analysis",
            build_external_analysis_candidate(
                "marketing_cost_analysis",
                build_external_analysis_candidate("workforce_development_cost_analysis", candidate, reference),
                reference,
            ),
            reference,
        )

    if analysis_id == "branding_lift_analysis":
        _blend_pl_lines(
            candidate,
            reference,
            revenue_weights=[0.18, 0.18, 0.2, 0.2, 0.2],
            gross_profit_weights=[0.18, 0.18, 0.2, 0.2, 0.2],
        )
        candidate["assumptions"].extend(
            _analysis_assumptions(
                source_type="branding_lift_analysis",
                source_prefix="revenue:branding",
                segment_name="売上",
                metrics=["brand_awareness_lift", "search_share_lift", "direct_conversion_multiplier"],
                enrich_live_sources=enrich_live_sources,
            )
        )
        return candidate

    if analysis_id == "marketing_efficiency_analysis":
        _blend_pl_lines(
            candidate,
            reference,
            revenue_weights=[0.3, 0.3, 0.34, 0.34, 0.34],
            gross_profit_weights=[0.28, 0.28, 0.32, 0.32, 0.32],
        )
        candidate["assumptions"].extend(
            _analysis_assumptions(
                source_type="marketing_efficiency_analysis",
                source_prefix="revenue:marketing",
                segment_name="売上",
                metrics=["marketing_cac", "media_roas", "paid_conversion_efficiency"],
                enrich_live_sources=enrich_live_sources,
            )
        )
        return candidate

    if analysis_id == "sales_efficiency_analysis":
        _merge_model_sheet(
            candidate,
            "コンサル",
            {
                "sku_unit_price": reference.model_sheets["コンサル"]["sku_unit_price"],
                "sku_retention": reference.model_sheets["コンサル"]["sku_retention"],
                "sku_standard_hours": reference.model_sheets["コンサル"]["sku_standard_hours"],
            },
        )
        _blend_pl_lines(
            candidate,
            reference,
            revenue_weights=[0.38, 0.38, 0.42, 0.42, 0.42],
            gross_profit_weights=[0.34, 0.34, 0.38, 0.38, 0.38],
        )
        candidate["assumptions"].extend(
            _analysis_assumptions(
                source_type="sales_efficiency_analysis",
                source_prefix="revenue:sales",
                segment_name="コンサル",
                metrics=["sales_cac", "pipeline_conversion", "account_productivity"],
                enrich_live_sources=enrich_live_sources,
            )
        )
        return candidate

    if analysis_id == "partner_strategy_analysis":
        _merge_model_sheet(
            candidate,
            "コンサル",
            {
                "sku_unit_price": [15_750_000.0],
                "sku_retention": reference.model_sheets["コンサル"]["sku_retention"],
                "sku_standard_hours": reference.model_sheets["コンサル"]["sku_standard_hours"],
            },
        )
        _blend_pl_lines(
            candidate,
            reference,
            revenue_weights=[0.34, 0.34, 0.4, 0.4, 0.4],
            gross_profit_weights=[0.3, 0.3, 0.36, 0.36, 0.36],
        )
        candidate["assumptions"].extend(
            _analysis_assumptions(
                source_type="partner_strategy_analysis",
                source_prefix="revenue:partner",
                segment_name="売上",
                metrics=["partner_sourced_mix", "partner_conversion", "partner_enablement_payback"],
                enrich_live_sources=enrich_live_sources,
            )
        )
        return candidate

    if analysis_id == "staged_acceleration_analysis":
        _merge_model_sheet(
            candidate,
            "コンサル",
            reference.model_sheets["コンサル"],
        )
        _blend_pl_lines(
            candidate,
            reference,
            revenue_weights=[0.28, 0.32, 0.4, 0.68, 0.58],
            gross_profit_weights=[0.24, 0.28, 0.36, 0.64, 0.54],
        )
        candidate["assumptions"].extend(
            _analysis_assumptions(
                source_type="staged_acceleration_analysis",
                source_prefix="revenue:staged",
                segment_name="売上",
                metrics=["validation_window", "acceleration_window", "scale_gate"],
                enrich_live_sources=enrich_live_sources,
            )
        )
        return candidate

    if analysis_id == "validation_period_analysis":
        _blend_pl_lines(
            candidate,
            reference,
            revenue_weights=[0.45, 0.5, 0.55, 0.12, 0.12],
            gross_profit_weights=[0.4, 0.45, 0.5, 0.1, 0.1],
        )
        candidate["assumptions"].extend(
            _analysis_assumptions(
                source_type="validation_period_analysis",
                source_prefix="revenue:validation",
                segment_name="売上",
                metrics=["unit_economics_validation", "pilot_density", "pmf_threshold"],
                enrich_live_sources=enrich_live_sources,
            )
        )
        return candidate

    if analysis_id == "acceleration_period_analysis":
        _merge_model_sheet(
            candidate,
            "コンサル",
            reference.model_sheets["コンサル"],
        )
        _blend_pl_lines(
            candidate,
            reference,
            revenue_weights=[0.08, 0.1, 0.16, 0.8, 0.72],
            gross_profit_weights=[0.06, 0.08, 0.14, 0.76, 0.68],
        )
        candidate["assumptions"].extend(
            _analysis_assumptions(
                source_type="acceleration_period_analysis",
                source_prefix="revenue:acceleration",
                segment_name="売上",
                metrics=["post_validation_spend", "sales_hiring_ramp", "media_scale_window"],
                enrich_live_sources=enrich_live_sources,
            )
        )
        return candidate

    if analysis_id == "gated_acceleration_analysis":
        _merge_model_sheet(
            candidate,
            "コンサル",
            {
                "sku_unit_price": [15_250_000.0],
                "sku_retention": reference.model_sheets["コンサル"]["sku_retention"],
                "sku_standard_hours": reference.model_sheets["コンサル"]["sku_standard_hours"],
            },
        )
        _blend_pl_lines(
            candidate,
            reference,
            revenue_weights=[0.24, 0.28, 0.34, 0.62, 0.54],
            gross_profit_weights=[0.22, 0.26, 0.32, 0.58, 0.5],
        )
        candidate["assumptions"].extend(
            _analysis_assumptions(
                source_type="gated_acceleration_analysis",
                source_prefix="revenue:gated",
                segment_name="売上",
                metrics=["scale_gate", "payback_guardrail", "confidence_trigger"],
                enrich_live_sources=enrich_live_sources,
            )
        )
        return candidate

    if analysis_id == "combined_staged_sales":
        return build_external_analysis_candidate(
            "sales_efficiency_analysis",
            build_external_analysis_candidate("staged_acceleration_analysis", candidate, reference),
            reference,
        )

    if analysis_id == "combined_staged_partner":
        return build_external_analysis_candidate(
            "partner_strategy_analysis",
            build_external_analysis_candidate("staged_acceleration_analysis", candidate, reference),
            reference,
        )

    if analysis_id == "combined_staged_branding":
        return build_external_analysis_candidate(
            "branding_lift_analysis",
            build_external_analysis_candidate("staged_acceleration_analysis", candidate, reference),
            reference,
        )

    raise ValueError(f"Unsupported analysis_id: {analysis_id}")


def _merge_model_sheet(candidate: Dict[str, Any], segment_name: str, metrics: Dict[str, list[float]]) -> None:
    candidate["model_sheets"].setdefault(segment_name, {})
    candidate["model_sheets"][segment_name].update(metrics)


def _analysis_assumptions(
    source_type: str,
    source_prefix: str,
    segment_name: str,
    metrics: list[str],
    enrich_live_sources: bool = False,
) -> list[dict[str, Any]]:
    refs = analysis_source_refs(
        source_type,
        enrich_live_sources=enrich_live_sources,
        cache_dir=DEFAULT_SOURCE_CACHE_DIR,
    )
    return [
        {
            "source_type": source_type,
            "evidence_refs": [
                {"source_id": f"{source_prefix}:{segment_name}:{metric_name}"},
                *refs,
            ],
            "review_status": "approved",
        }
        for metric_name in metrics
    ]


def _blend_series(base_series: list[float], target_series: list[float], weights: list[float]) -> list[float]:
    blended: list[float] = []
    for index, target_value in enumerate(target_series):
        base_value = base_series[index] if index < len(base_series) else target_value
        weight = weights[index] if index < len(weights) else weights[-1]
        blended.append(round((1 - weight) * float(base_value) + weight * float(target_value), 4))
    return blended


def _blend_pl_lines(
    candidate: Dict[str, Any],
    reference: ReferenceWorkbook,
    revenue_weights: list[float],
    gross_profit_weights: list[float],
) -> None:
    candidate["pl_lines"]["売上"] = _blend_series(
        candidate["pl_lines"].get("売上", reference.pl_lines["売上"]),
        reference.pl_lines["売上"],
        revenue_weights,
    )
    candidate["pl_lines"]["粗利"] = _blend_series(
        candidate["pl_lines"].get("粗利", reference.pl_lines["粗利"]),
        reference.pl_lines["粗利"],
        gross_profit_weights,
    )
