"""Recalculation endpoint — synchronous fast path.

Applies parameter changes and scenario multipliers to compute
the 5-year PL summary, KPIs, and chart data.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter

router = APIRouter()


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
    # Simple heuristic: revenue-related cells get revenue multiplier,
    # cost-related get cost multiplier
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
    """Compute 5-year PL from parameters.

    This is a simplified computation engine. In production, this wraps
    the core Excel formula engine or a pure-Python recalculation model.
    """
    # Extract key parameters with defaults
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
            "waterfall": [],  # Populated by frontend-specific chart logic
            "revenue_stack": [],
        },
    }


@router.post("/recalc")
async def recalc(body: dict):
    """Recalculate PL from parameters (synchronous).

    Fast path: no LLM, no heavy computation.
    Designed to respond in <500ms for slider interactions.
    """
    parameters = body.get("parameters", {})
    edited_cells = body.get("edited_cells", {})
    scenario = body.get("scenario", "base")

    # Merge edits over parameters
    merged = {**parameters, **edited_cells}

    # Apply scenario multipliers
    adjusted = _apply_scenario_multipliers(
        merged,
        scenario,
        best_mult={"revenue": 1.2, "cost": 0.9},
        worst_mult={"revenue": 0.8, "cost": 1.15},
    )

    result = _compute_pl(adjusted)
    result["scenario"] = scenario
    return result
