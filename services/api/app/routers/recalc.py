"""Recalculation endpoint — synchronous fast path.

Applies parameter changes and scenario multipliers to compute
the 5-year PL summary, KPIs, and chart data.

Supports:
  - Per-segment revenue & gross profit with model sheet linkage
  - Detailed SGA categories (payroll, marketing, office, system, other)
  - Depreciation auto-calculation from CAPEX with amortization settings
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

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
    # OPEX keywords → opex_base (total SGA/OPEX only)
    "販管費": "opex_base",
    "opex": "opex_base",
    # Payroll → payroll (component, not total OPEX)
    "人件費": "payroll",
    # Marketing → sga_marketing
    "マーケティング": "sga_marketing",
    "広告宣伝費": "sga_marketing",
    # Office → sga_office
    "オフィス": "sga_office",
    "一般管理費": "sga_office",
    # System → sga_system
    "システム": "sga_system",
    "開発費": "sga_system",
    # OPEX growth → opex_growth
    "opex増加率": "opex_growth",
    # Depreciation → depreciation
    "減価償却": "depreciation",
    "depreciation": "depreciation",
    # CAPEX → capex
    "capex": "capex",
    "設備投資": "capex",
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

    # Extract segment-level data from Phase 5 sheet-based extractions
    segments = phase5_result.get("segments", [])
    if segments:
        params["_segments"] = segments

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
        if key.startswith("_"):
            continue  # skip internal keys like _segments
        if not isinstance(value, (int, float)):
            continue
        key_lower = key.lower()
        if any(w in key_lower for w in ["revenue", "売上", "単価", "price"]):
            adjusted[key] = value * mult.get("revenue", 1.0)
        elif any(w in key_lower for w in ["cost", "原価", "費用", "opex", "sga_", "payroll"]):
            adjusted[key] = value * mult.get("cost", 1.0)

    return adjusted


# ---------------------------------------------------------------------------
# Depreciation auto-calculation from CAPEX
# ---------------------------------------------------------------------------

def _compute_depreciation_from_capex(
    capex_per_year: List[float],
    useful_life: int,
    method: str = "straight_line",
    existing_depreciation: float = 0,
) -> List[float]:
    """Compute annual depreciation from CAPEX schedule.

    Each year's CAPEX is spread over `useful_life` years using the chosen method.
    Returns 5-year depreciation schedule.

    Parameters
    ----------
    capex_per_year : list[float]
        CAPEX for each of the 5 fiscal years.
    useful_life : int
        Useful life in years (typically 3-10 for software/equipment).
    method : str
        "straight_line" (default) or "declining_balance"
    existing_depreciation : float
        Depreciation from assets acquired before the projection period.
    """
    depr = [existing_depreciation] * 5

    for invest_year in range(5):
        cx = capex_per_year[invest_year]
        if cx <= 0:
            continue

        if method == "declining_balance":
            # 200% declining balance
            db_rate = min(2.0 / useful_life, 1.0)
            remaining = cx
            for dep_year in range(invest_year, 5):
                annual = remaining * db_rate
                # Switch to straight-line if it gives a larger amount
                years_left = useful_life - (dep_year - invest_year)
                if years_left > 0:
                    sl_annual = remaining / years_left
                    if sl_annual >= annual:
                        annual = sl_annual
                depr[dep_year] += round(annual)
                remaining -= annual
                if remaining <= 0:
                    break
        else:
            # Straight-line
            annual = cx / useful_life
            for dep_year in range(invest_year, min(invest_year + useful_life, 5)):
                depr[dep_year] += round(annual)

    return [round(d) for d in depr]


# ---------------------------------------------------------------------------
# SGA category breakdown
# ---------------------------------------------------------------------------

def _compute_headcount_cost(
    avg_salary: float,
    headcount_per_year: List[float],
) -> List[int]:
    """Compute annual cost for a role: avg_salary × headcount."""
    return [round(avg_salary * hc) for hc in headcount_per_year]


# Default personnel roles with (avg_salary, default_headcount_fy1-5)
_DEFAULT_ROLES = {
    "planning":  {"label": "事業企画",         "salary": 7_000_000, "hc": [1, 1, 2, 2, 3]},
    "sales":     {"label": "営業",             "salary": 6_000_000, "hc": [1, 2, 3, 5, 7]},
    "marketing": {"label": "マーケティング",   "salary": 6_500_000, "hc": [1, 1, 2, 2, 3]},
    "support":   {"label": "カスタマーサポート", "salary": 4_500_000, "hc": [0, 1, 2, 3, 4]},
    "corporate": {"label": "コーポレート",     "salary": 7_500_000, "hc": [1, 1, 2, 2, 3]},
    "other_hr":  {"label": "その他",           "salary": 5_500_000, "hc": [0, 0, 1, 1, 2]},
}

# Default marketing subcategories
_DEFAULT_MKTG_SUBCATS = [
    "digital_ad", "offline_ad", "pr", "events", "branding", "crm", "content", "other_mktg",
]

_MKTG_LABELS = {
    "digital_ad": "デジタル広告（獲得）",
    "offline_ad": "オフライン広告",
    "pr": "PR・広報",
    "events": "イベント・展示会",
    "branding": "ブランディング",
    "crm": "CRM・リテンション",
    "content": "コンテンツ制作",
    "other_mktg": "その他マーケ費",
}


def _compute_sga_breakdown(
    parameters: Dict[str, Any],
    opex_total_per_year: List[float],
) -> Dict[str, Any]:
    """Compute detailed SGA breakdown.

    Returns a nested structure:
    {
      "payroll": {
        "roles": { "planning": { "salary": N, "headcount": [...], "cost": [...] }, ... },
        "total": [...]
      },
      "marketing": {
        "categories": { "digital_ad": [...], "pr": [...], ... },
        "total": [...]
      },
      "office": [...],
      "rd": [...],
      "other": [...],
    }
    """
    opex_growth = float(parameters.get("opex_growth", 0.1))

    # ─── Payroll: role × (salary × headcount) ───
    payroll_roles: Dict[str, Any] = {}
    payroll_total = [0] * 5

    for role_key, defaults in _DEFAULT_ROLES.items():
        salary = float(parameters.get(f"pr_{role_key}_salary", defaults["salary"]))
        hc_key = f"pr_{role_key}_hc"
        # headcount can be provided as a list [fy1..fy5] or scalar
        hc_raw = parameters.get(hc_key, defaults["hc"])
        if isinstance(hc_raw, list):
            hc = [float(h) for h in hc_raw[:5]]
            while len(hc) < 5:
                hc.append(hc[-1] if hc else 0)
        else:
            hc_fy1 = float(hc_raw)
            hc_growth = float(parameters.get(f"pr_{role_key}_hc_growth", 0.2))
            hc = [round(hc_fy1 * ((1 + hc_growth) ** y)) for y in range(5)]

        cost = _compute_headcount_cost(salary, hc)
        payroll_roles[role_key] = {
            "label": defaults["label"],
            "salary": round(salary),
            "headcount": [round(h) for h in hc],
            "cost": cost,
        }
        for y in range(5):
            payroll_total[y] += cost[y]

    # ─── Marketing: category breakdown ───
    mktg_categories: Dict[str, List[int]] = {}
    mktg_total = [0] * 5

    # Check for detailed marketing subcategory inputs
    has_mktg_detail = any(
        parameters.get(f"mk_{sub}") is not None for sub in _DEFAULT_MKTG_SUBCATS
    )

    # Default allocation ratios for marketing subcategories
    _MKTG_DEFAULT_RATIOS = {
        "digital_ad": 0.30,
        "offline_ad": 0.10,
        "pr":         0.10,
        "events":     0.10,
        "branding":   0.10,
        "crm":        0.10,
        "content":    0.10,
        "other_mktg": 0.10,
    }

    if has_mktg_detail:
        for sub in _DEFAULT_MKTG_SUBCATS:
            val = float(parameters.get(f"mk_{sub}", 0))
            growth = float(parameters.get(f"mk_{sub}_growth", opex_growth))
            yearly = [round(val * ((1 + growth) ** y)) for y in range(5)]
            mktg_categories[sub] = yearly
            for y in range(5):
                mktg_total[y] += yearly[y]
    else:
        # Derive subcategories from total marketing budget using default ratios
        mktg_fy1 = float(parameters.get("sga_marketing", opex_total_per_year[0] * 0.20))
        mktg_growth = float(parameters.get("marketing_growth", opex_growth))
        for y in range(5):
            mktg_total[y] = round(mktg_fy1 * ((1 + mktg_growth) ** y))
        # Always populate subcategory breakdown
        for sub in _DEFAULT_MKTG_SUBCATS:
            ratio = _MKTG_DEFAULT_RATIOS.get(sub, 0.10)
            mktg_categories[sub] = [round(mktg_total[y] * ratio) for y in range(5)]

    # ─── Office costs ───
    office_fy1 = float(parameters.get("sga_office", opex_total_per_year[0] * 0.10))
    office_growth = float(parameters.get("office_growth", opex_growth * 0.5))
    office_total = [round(office_fy1 * ((1 + office_growth) ** y)) for y in range(5)]

    # ─── R&D / System costs ───
    system_fy1 = float(parameters.get("sga_system", opex_total_per_year[0] * 0.15))
    system_growth = float(parameters.get("system_growth", opex_growth))
    system_total = [round(system_fy1 * ((1 + system_growth) ** y)) for y in range(5)]

    # ─── Other ───
    other_fy1 = float(parameters.get("sga_other", opex_total_per_year[0] * 0.05))
    other_growth = float(parameters.get("other_growth", opex_growth * 0.5))
    other_total = [round(other_fy1 * ((1 + other_growth) ** y)) for y in range(5)]

    return {
        "payroll": {
            "roles": payroll_roles,
            "total": payroll_total,
        },
        "marketing": {
            "categories": mktg_categories,
            "total": mktg_total,
        },
        "office": office_total,
        "system": system_total,
        "other": other_total,
    }


# ---------------------------------------------------------------------------
# Segment revenue breakdown
# ---------------------------------------------------------------------------

def _compute_segments(parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Compute per-segment revenue and gross profit.

    Supports up to 10 segments. Each segment can have:
      - seg_{n}_name: segment name
      - seg_{n}_revenue_fy1: initial revenue
      - seg_{n}_growth: growth rate
      - seg_{n}_cogs_rate: variable cost rate

    If no segments are provided, creates a single "全体" segment from totals.
    """
    segments_data = parameters.get("_segments", [])
    segments_input = parameters.get("segments", [])

    # Try structured segment input first
    if segments_input:
        segments_data = segments_input

    # Check for per-segment parameters (seg_1_revenue_fy1, etc.)
    param_segments = []
    for n in range(1, 11):
        prefix = f"seg_{n}_"
        rev_key = f"{prefix}revenue_fy1"
        if rev_key in parameters:
            param_segments.append({
                "name": parameters.get(f"{prefix}name", f"セグメント{n}"),
                "revenue_fy1": float(parameters[rev_key]),
                "growth_rate": float(parameters.get(f"{prefix}growth", parameters.get("growth_rate", 0.3))),
                "cogs_rate": float(parameters.get(f"{prefix}cogs_rate", parameters.get("cogs_rate", 0.3))),
            })

    if param_segments:
        segments_data = param_segments

    if not segments_data:
        # Single segment from aggregated values
        revenue_fy1 = float(parameters.get("revenue_fy1", 100_000_000))
        growth_rate = float(parameters.get("growth_rate", 0.3))
        cogs_rate = float(parameters.get("cogs_rate", 0.3))
        segments_data = [{
            "name": "全体",
            "revenue_fy1": revenue_fy1,
            "growth_rate": growth_rate,
            "cogs_rate": cogs_rate,
        }]

    result = []
    for seg in segments_data:
        name = seg.get("name", "セグメント")
        rev_fy1 = float(seg.get("revenue_fy1", 0))
        growth = float(seg.get("growth_rate", 0.3))
        cogs_rate = float(seg.get("cogs_rate", 0.3))

        revenue = []
        cogs = []
        gross_profit = []
        for year in range(5):
            rev = rev_fy1 * ((1 + growth) ** year)
            cost = rev * cogs_rate
            gp = rev - cost
            revenue.append(round(rev))
            cogs.append(round(cost))
            gross_profit.append(round(gp))

        result.append({
            "name": name,
            "revenue": revenue,
            "cogs": cogs,
            "gross_profit": gross_profit,
            "cogs_rate": round(cogs_rate, 4),
            "growth_rate": round(growth, 4),
        })

    return result


def _compute_pl(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Compute 5-year PL from parameters.

    Enhanced with:
      - Per-segment revenue/GP breakdown
      - SGA category detail (payroll, marketing, office, system, other)
      - Depreciation auto-calculation from CAPEX
    """
    growth_rate = float(parameters.get("growth_rate", 0.3))
    cogs_rate = float(parameters.get("cogs_rate", 0.3))
    opex_base = float(parameters.get("opex_base", 80_000_000))
    opex_growth = float(parameters.get("opex_growth", 0.1))

    # --- Segment-level revenue ---
    segments = _compute_segments(parameters)

    # Aggregate from segments
    revenue = [0] * 5
    cogs = [0] * 5
    gross_profit = [0] * 5
    for seg in segments:
        for y in range(5):
            revenue[y] += seg["revenue"][y]
            cogs[y] += seg["cogs"][y]
            gross_profit[y] += seg["gross_profit"][y]

    # If payroll is provided but opex_base is default, use payroll as a component
    payroll = parameters.get("payroll")
    if payroll is not None and "opex_base" not in parameters:
        opex_base = float(payroll) / 0.45

    # --- OPEX with SGA breakdown ---
    opex = []
    for year in range(5):
        ox = opex_base * ((1 + opex_growth) ** year)
        opex.append(round(ox))

    sga_detail = _compute_sga_breakdown(parameters, opex)

    # Extract flat totals per category for charts / backward compat
    sga_breakdown = {
        "payroll": sga_detail["payroll"]["total"],
        "marketing": sga_detail["marketing"]["total"],
        "office": sga_detail["office"],
        "system": sga_detail["system"],
        "other": sga_detail["other"],
    }

    # If categories were provided, recompute opex from category sum
    has_categories = any(
        parameters.get(k) is not None
        for k in ["payroll", "sga_marketing", "sga_office", "sga_system", "sga_other"]
    )
    if has_categories:
        opex = [
            sga_breakdown["payroll"][y] + sga_breakdown["marketing"][y]
            + sga_breakdown["office"][y] + sga_breakdown["system"][y]
            + sga_breakdown["other"][y]
            for y in range(5)
        ]

    # --- Depreciation (auto-calc or manual) ---
    depreciation_mode = parameters.get("depreciation_mode", "manual")
    capex_val = float(parameters.get("capex", 0))
    capex_per_year = parameters.get("capex_schedule", [capex_val] * 5)
    capex_per_year = [float(c) for c in capex_per_year[:5]]
    while len(capex_per_year) < 5:
        capex_per_year.append(capex_val)

    if depreciation_mode == "auto":
        useful_life = int(parameters.get("useful_life", 5))
        depr_method = parameters.get("depreciation_method", "straight_line")
        existing_depr = float(parameters.get("existing_depreciation", 0))
        depreciation_list = _compute_depreciation_from_capex(
            capex_per_year, useful_life, method=depr_method, existing_depreciation=existing_depr,
        )
    else:
        depreciation_val = float(parameters.get("depreciation", 0))
        depreciation_list = [round(depreciation_val)] * 5

    capex_list = [round(c) for c in capex_per_year]

    # --- P&L ---
    operating_profit = []
    fcf = []
    cumulative_fcf = []

    cum = 0.0
    for year in range(5):
        depr = depreciation_list[year]
        cx = capex_list[year]
        op = gross_profit[year] - opex[year] - depr
        cf = op + depr - cx
        cum += cf

        operating_profit.append(round(op))
        fcf.append(round(cf))
        cumulative_fcf.append(round(cum))

    # KPIs
    break_even = None
    cum_break_even = None
    for i, op_val in enumerate(operating_profit):
        if op_val > 0 and break_even is None:
            break_even = f"FY{i + 1}"
    for i, cf_val in enumerate(cumulative_fcf):
        if cf_val > 0 and cum_break_even is None:
            cum_break_even = f"FY{i + 1}"

    rev_cagr = ((revenue[-1] / revenue[0]) ** (1 / 4) - 1) if revenue[0] > 0 else 0
    fy5_margin = operating_profit[-1] / revenue[-1] if revenue[-1] > 0 else 0

    # Gross margin
    gp_margin = gross_profit[-1] / revenue[-1] if revenue[-1] > 0 else 0

    return {
        "pl_summary": {
            "revenue": revenue,
            "cogs": cogs,
            "gross_profit": gross_profit,
            "opex": opex,
            "depreciation": depreciation_list,
            "capex": capex_list,
            "operating_profit": operating_profit,
            "fcf": fcf,
            "cumulative_fcf": cumulative_fcf,
            # New: segment breakdown
            "segments": [
                {
                    "name": seg["name"],
                    "revenue": seg["revenue"],
                    "cogs": seg["cogs"],
                    "gross_profit": seg["gross_profit"],
                    "cogs_rate": seg["cogs_rate"],
                    "growth_rate": seg["growth_rate"],
                }
                for seg in segments
            ],
            # SGA category totals (flat, for charts)
            "sga_breakdown": sga_breakdown,
            # SGA detail with role-level payroll & marketing subcategories
            "sga_detail": sga_detail,
        },
        "kpis": {
            "break_even_year": break_even,
            "cumulative_break_even_year": cum_break_even,
            "revenue_cagr": round(rev_cagr, 4),
            "fy5_op_margin": round(fy5_margin, 4),
            "gp_margin": round(gp_margin, 4),
        },
        "charts_data": {
            "waterfall": [],
            "revenue_stack": [],
        },
        "depreciation_settings": {
            "mode": depreciation_mode,
            "useful_life": int(parameters.get("useful_life", 5)),
            "method": parameters.get("depreciation_method", "straight_line"),
            "existing_depreciation": float(parameters.get("existing_depreciation", 0)),
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
