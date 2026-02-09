"""Recalculation endpoint — synchronous fast path.

Applies parameter changes and scenario multipliers to compute
the 5-year PL summary, KPIs, and chart data.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter

from .. import db

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Parameter mapping: Phase 5 extractions → recalc driver keys
# ---------------------------------------------------------------------------

_PARAM_KEY_MAP = {
    # Revenue keywords → revenue_fy1
    "売上高": "revenue_fy1",
    "売上": "revenue_fy1",
    "revenue": "revenue_fy1",
    # Growth keywords → growth_rate
    "成長率": "growth_rate",
    "growth": "growth_rate",
    # COGS keywords → cogs_rate
    "原価率": "cogs_rate",
    "原価": "cogs_rate",
    "cogs": "cogs_rate",
    # OPEX keywords → opex_base
    "販管費": "opex_base",
    "opex": "opex_base",
    "人件費": "opex_base",
    # OPEX growth → opex_growth
    "opex増加率": "opex_growth",
}


def _extract_params_from_phase5(phase5_result: dict) -> Dict[str, Any]:
    """Convert Phase 5 extracted parameters to recalc driver keys."""
    params: Dict[str, Any] = {}
    extractions = phase5_result.get("extractions", [])

    for ext in extractions:
        label = (ext.get("label") or ext.get("key") or "").lower()
        value = ext.get("value")
        if value is None:
            continue

        # Try to map label to a known driver key
        for keyword, driver_key in _PARAM_KEY_MAP.items():
            if keyword.lower() in label:
                try:
                    params[driver_key] = float(value)
                except (TypeError, ValueError):
                    pass
                break

    return params


def _apply_scenario_multipliers(
    parameters: Dict[str, Any],
    scenario: str,
    best_mult: Optional[Dict[str, float]] = None,
    worst_mult: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Apply Best/Worst multipliers to parameter values."""
    if scenario == "base":
        return parameters

    mult = best_mult if scenario == "best" else worst_mult
    if not mult:
        return parameters

    adjusted = dict(parameters)
    for key, value in adjusted.items():
        if not isinstance(value, (int, float)):
            continue
        key_lower = key.lower()
        if any(w in key_lower for w in ["revenue", "売上", "単価", "price"]):
            adjusted[key] = value * mult.get("revenue", 1.0)
        elif any(w in key_lower for w in ["cost", "原価", "費用", "opex"]):
            adjusted[key] = value * mult.get("cost", 1.0)

    return adjusted


def _compute_pl(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Compute 5-year PL from parameters."""
    revenue_fy1 = float(parameters.get("revenue_fy1", 100_000_000))
    growth_rate = float(parameters.get("growth_rate", 0.3))
    cogs_rate = float(parameters.get("cogs_rate", 0.3))
    opex_base = float(parameters.get("opex_base", 80_000_000))
    opex_growth = float(parameters.get("opex_growth", 0.1))

    revenue = []
    cogs = []
    gross_profit = []
    opex = []
    operating_profit = []
    fcf = []
    cumulative_fcf = []

    cum = 0.0
    for year in range(5):
        rev = revenue_fy1 * ((1 + growth_rate) ** year)
        cost = rev * cogs_rate
        gp = rev - cost
        ox = opex_base * ((1 + opex_growth) ** year)
        op = gp - ox
        cf = op * 0.9  # simplified FCF
        cum += cf

        revenue.append(round(rev))
        cogs.append(round(cost))
        gross_profit.append(round(gp))
        opex.append(round(ox))
        operating_profit.append(round(op))
        fcf.append(round(cf))
        cumulative_fcf.append(round(cum))

    # KPIs
    break_even = None
    cum_break_even = None
    for i, op in enumerate(operating_profit):
        if op > 0 and break_even is None:
            break_even = f"FY{i + 1}"
    for i, cf in enumerate(cumulative_fcf):
        if cf > 0 and cum_break_even is None:
            cum_break_even = f"FY{i + 1}"

    rev_cagr = ((revenue[-1] / revenue[0]) ** (1 / 4) - 1) if revenue[0] > 0 else 0
    fy5_margin = operating_profit[-1] / revenue[-1] if revenue[-1] > 0 else 0

    return {
        "pl_summary": {
            "revenue": revenue,
            "cogs": cogs,
            "gross_profit": gross_profit,
            "opex": opex,
            "operating_profit": operating_profit,
            "fcf": fcf,
            "cumulative_fcf": cumulative_fcf,
        },
        "kpis": {
            "break_even_year": break_even,
            "cumulative_break_even_year": cum_break_even,
            "revenue_cagr": round(rev_cagr, 4),
            "fy5_op_margin": round(fy5_margin, 4),
        },
        "charts_data": {
            "waterfall": [],
            "revenue_stack": [],
        },
    }


@router.post("/recalc")
async def recalc(body: dict):
    """Recalculate PL from parameters (synchronous).

    Fast path: no LLM, no heavy computation.
    Designed to respond in <500ms for slider interactions.

    If project_id is provided, loads Phase 5 parameters as base,
    then overlays user edits.
    """
    project_id = body.get("project_id")
    parameters = body.get("parameters", {})
    edited_cells = body.get("edited_cells", {})
    scenario = body.get("scenario", "base")

    # Load Phase 5 extracted parameters as base if project_id is given
    base_params: Dict[str, Any] = {}
    if project_id:
        run = db.get_latest_run(project_id)
        if run:
            phase5 = db.get_phase_result(run["id"], 5)
            if phase5 and phase5.get("raw_json"):
                base_params = _extract_params_from_phase5(phase5["raw_json"])
                logger.debug("Loaded %d params from Phase 5", len(base_params))

    # Layer: Phase 5 base → user-provided params → edited cells
    merged = {**base_params, **parameters, **edited_cells}

    # Apply scenario multipliers
    adjusted = _apply_scenario_multipliers(
        merged,
        scenario,
        best_mult=body.get("best_multipliers", {"revenue": 1.2, "cost": 0.9}),
        worst_mult=body.get("worst_multipliers", {"revenue": 0.8, "cost": 1.15}),
    )

    result = _compute_pl(adjusted)
    result["scenario"] = scenario
    result["source_params"] = merged  # Return merged params so frontend knows actual values
    return result
