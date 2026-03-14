"""Evidence-constrained planner built on top of canonical engines."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional

from src.domain.canonical_model import CanonicalBusinessModel, Driver, DriverSeries, RevenueEngine
from src.domain.evidence_ledger import AssumptionLedger, AssumptionRecord
from src.engines.base import EngineInput, EngineOutput
from src.engines.progression import ProgressionEngine
from src.engines.project_capacity import ProjectCapacityEngine
from src.engines.subscription import SubscriptionEngine
from src.engines.unit_economics import UnitEconomicsEngine

from .constraints import ConstraintViolation, check_allowed_range, check_project_capacity


Feasibility = Literal["solved", "partially_feasible", "infeasible"]

_ENGINE_PLUGINS = {
    "subscription": SubscriptionEngine(),
    "unit_economics": UnitEconomicsEngine(),
    "progression": ProgressionEngine(),
    "project_capacity": ProjectCapacityEngine(),
}


@dataclass
class PlannerResult:
    feasibility: Feasibility
    solved_driver_values: Dict[str, DriverSeries]
    constraint_violations: List[ConstraintViolation] = field(default_factory=list)
    explanation: str = ""
    target_allocations: Dict[str, float] = field(default_factory=dict)


def plan_to_targets(
    model: CanonicalBusinessModel,
    ledger: AssumptionLedger,
) -> PlannerResult:
    target = _first_revenue_target(model)
    solved_driver_values = _baseline_driver_series(model, ledger)
    if target is None:
        return PlannerResult(
            feasibility="partially_feasible",
            solved_driver_values=solved_driver_values,
            explanation="No revenue target was provided.",
        )

    target_index = _year_to_index(target.year)
    if target_index is None:
        return PlannerResult(
            feasibility="partially_feasible",
            solved_driver_values=solved_driver_values,
            explanation=f"Unsupported target year: {target.year}",
        )

    segment_targets = _allocate_segment_targets(model, target_index, target.value or 0.0, ledger)
    violations: List[ConstraintViolation] = []

    for segment in model.segments:
        segment_target = segment_targets.get(segment.segment_id, 0.0)
        for engine in segment.engines:
            solve_driver = _find_solve_driver(engine)
            current_output = _compute_engine_output(engine, solved_driver_values)

            if solve_driver is None:
                if round(current_output.revenue[target_index]) != round(segment_target):
                    violations.append(
                        ConstraintViolation(
                            code="no_solve_driver",
                            object_id=engine.engine_id,
                            message="No solve-capable driver is available for this engine",
                            actual_value=current_output.revenue[target_index],
                            limit_value=segment_target,
                        )
                    )
                continue

            required_value = _solve_required_value(
                engine=engine,
                solve_driver=solve_driver,
                target_index=target_index,
                target_revenue=segment_target,
                solved_driver_values=solved_driver_values,
            )
            if required_value is None:
                violations.append(
                    ConstraintViolation(
                        code="unsupported_engine",
                        object_id=engine.engine_id,
                        message="Planner could not derive a solve value for this engine",
                    )
                )
                continue

            ledger_record = _ledger_record(ledger, solve_driver.driver_id)
            if ledger_record is not None:
                range_violation = check_allowed_range(ledger_record, required_value)
                if range_violation is not None:
                    violations.append(range_violation)
                    continue

            capacity_violation = _check_engine_capacity(
                engine=engine,
                solve_driver=solve_driver,
                solved_value=required_value,
                solved_driver_values=solved_driver_values,
            )
            if capacity_violation is not None:
                violations.append(capacity_violation)
                continue

            solved_driver_values[solve_driver.driver_id] = _series_set(
                solved_driver_values.get(solve_driver.driver_id, solve_driver.series),
                target_index,
                required_value,
            )

    feasibility: Feasibility = "solved" if not violations else "infeasible"
    explanation = _build_explanation(target.value or 0.0, violations)
    return PlannerResult(
        feasibility=feasibility,
        solved_driver_values=solved_driver_values,
        constraint_violations=violations,
        explanation=explanation,
        target_allocations=segment_targets,
    )


def _first_revenue_target(model: CanonicalBusinessModel):
    if not model.targets.revenue_targets:
        return None
    return model.targets.revenue_targets[0]


def _year_to_index(year: str) -> Optional[int]:
    if not year.startswith("FY"):
        return None
    try:
        index = int(year[2:]) - 1
    except ValueError:
        return None
    if index < 0 or index > 4:
        return None
    return index


def _baseline_driver_series(
    model: CanonicalBusinessModel,
    ledger: AssumptionLedger,
) -> Dict[str, DriverSeries]:
    ledger_map = {record.object_id: record for record in ledger.records}
    baseline: Dict[str, DriverSeries] = {}
    for segment in model.segments:
        for engine in segment.engines:
            for driver in engine.drivers:
                series = DriverSeries(**driver.series.model_dump())
                if series.fy1 is None and driver.driver_id in ledger_map:
                    series.fy1 = ledger_map[driver.driver_id].value
                baseline[driver.driver_id] = series
    return baseline


def _allocate_segment_targets(
    model: CanonicalBusinessModel,
    target_index: int,
    total_target: float,
    ledger: AssumptionLedger,
) -> Dict[str, float]:
    if not model.segments:
        return {}

    baseline = _baseline_driver_series(model, ledger)
    revenues: Dict[str, float] = {}
    for segment in model.segments:
        segment_revenue = 0.0
        for engine in segment.engines:
            output = _compute_engine_output(engine, baseline)
            segment_revenue += output.revenue[target_index]
        revenues[segment.segment_id] = segment_revenue

    total_baseline = sum(revenues.values())
    if total_baseline <= 0:
        equal_share = total_target / len(model.segments)
        return {segment.segment_id: equal_share for segment in model.segments}

    return {
        segment_id: total_target * (revenue / total_baseline)
        for segment_id, revenue in revenues.items()
    }


def _find_solve_driver(engine: RevenueEngine) -> Optional[Driver]:
    for driver in engine.drivers:
        if driver.mode in {"solve_for", "bounded"}:
            return driver
    return None


def _compute_engine_output(
    engine: RevenueEngine,
    solved_driver_values: Dict[str, DriverSeries],
) -> EngineOutput:
    plugin = _ENGINE_PLUGINS.get(engine.engine_type)
    if plugin is None:
        return EngineOutput(revenue=[0] * 5, variable_cost=[0] * 5, gross_profit=[0] * 5, warnings=["unsupported engine"])
    config = _engine_config_from_driver_values(engine, solved_driver_values)
    return plugin.compute(EngineInput(config=config))


def _engine_config_from_driver_values(
    engine: RevenueEngine,
    solved_driver_values: Dict[str, DriverSeries],
) -> Dict[str, object]:
    values = {driver.driver_id: _driver_series_list(driver, solved_driver_values) for driver in engine.drivers}

    if engine.engine_type == "subscription":
        return {
            "plans": [
                {
                    "monthly_price": values.get("monthly_price", [0])[0],
                    "subscribers": values.get("subscribers", _series_fill(0)),
                    "monthly_cost_per_subscriber": values.get("monthly_cost_per_subscriber", [0])[0],
                }
            ]
        }
    if engine.engine_type == "project_capacity":
        config: Dict[str, object] = {
            "skus": [
                {
                    "unit_price": values.get("unit_price", [0])[0],
                    "quantities": values.get("project_count", values.get("quantities", _series_fill(0))),
                    "unit_cost": values.get("unit_cost", [0])[0],
                }
            ]
        }
        if "headcount" in values:
            config["headcount"] = values["headcount"]
        if "max_projects_per_head" in engine.constraints:
            config["max_projects_per_head"] = engine.constraints["max_projects_per_head"]
        return config
    if engine.engine_type == "progression":
        return {
            "tiers": [
                {
                    "price": values.get("price", values.get("tuition", [0]))[0],
                    "students": values.get("students", values.get("entrants", _series_fill(0))),
                    "variable_cost_per_student": values.get("variable_cost_per_student", [0])[0],
                }
            ]
        }
    if engine.engine_type == "unit_economics":
        return {
            "skus": [
                {
                    "price": values.get("price", values.get("price_per_item", [0]))[0],
                    "items_per_txn": values.get("items_per_txn", values.get("items_per_meal", [1]))[0],
                    "txns_per_person": values.get("txns_per_person", [1])[0],
                    "annual_purchases": values.get("annual_purchases", values.get("meals_per_year", [1]))[0],
                    "customers": values.get("customers", values.get("unit_count", _series_fill(0))),
                    "unit_cost": values.get("unit_cost", [0])[0],
                }
            ]
        }
    return {}


def _series_fill(value: float) -> List[float]:
    return [value] * 5


def _driver_value(driver: Driver, solved_driver_values: Dict[str, DriverSeries]) -> float:
    solved = solved_driver_values.get(driver.driver_id)
    if solved and solved.fy1 is not None:
        return float(solved.fy1)
    if driver.series.fy1 is not None:
        return float(driver.series.fy1)
    return 0.0


def _driver_series_list(driver: Driver, solved_driver_values: Dict[str, DriverSeries]) -> List[float]:
    series = solved_driver_values.get(driver.driver_id) or driver.series
    raw = [series.fy1, series.fy2, series.fy3, series.fy4, series.fy5]
    filled: List[float] = []
    last = 0.0
    for value in raw:
        if value is not None:
            last = float(value)
        filled.append(last)
    return filled


def _series_set(series: DriverSeries, index: int, value: float) -> DriverSeries:
    data = series.model_dump()
    data[f"fy{index + 1}"] = value
    return DriverSeries(**data)


def _solve_required_value(
    engine: RevenueEngine,
    solve_driver: Driver,
    target_index: int,
    target_revenue: float,
    solved_driver_values: Dict[str, DriverSeries],
) -> Optional[float]:
    plugin = _ENGINE_PLUGINS.get(engine.engine_type)
    if plugin is None:
        return None

    baseline_config = _engine_config_from_driver_values(engine, solved_driver_values)
    unit_values = dict(solved_driver_values)
    unit_values[solve_driver.driver_id] = _series_set(
        unit_values.get(solve_driver.driver_id, solve_driver.series),
        target_index,
        1.0,
    )
    unit_config = _engine_config_from_driver_values(engine, unit_values)

    baseline_output = plugin.compute(EngineInput(config=baseline_config))
    unit_output = plugin.compute(EngineInput(config=unit_config))
    baseline_revenue = baseline_output.revenue[target_index]
    denominator = unit_output.revenue[target_index]
    if denominator <= 0:
        return None

    required = target_revenue / denominator
    if solve_driver.category in {"volume", "capacity"}:
        required = math.ceil(required)

    if solve_driver.mode == "fixed":
        return float(_driver_value(solve_driver, solved_driver_values))

    return float(required if required >= 0 else 0)


def _ledger_record(ledger: AssumptionLedger, driver_id: str) -> Optional[AssumptionRecord]:
    for record in ledger.records:
        if record.object_id == driver_id:
            return record
    return None


def _check_engine_capacity(
    engine: RevenueEngine,
    solve_driver: Driver,
    solved_value: float,
    solved_driver_values: Dict[str, DriverSeries],
) -> Optional[ConstraintViolation]:
    if engine.engine_type != "project_capacity":
        return None

    max_projects_per_head = engine.constraints.get("max_projects_per_head")
    if not max_projects_per_head:
        return None

    headcount_driver = next((driver for driver in engine.drivers if driver.driver_id == "headcount"), None)
    if headcount_driver is None:
        return None

    headcount = _driver_value(headcount_driver, solved_driver_values)
    return check_project_capacity(
        object_id=solve_driver.driver_id,
        required_projects=solved_value,
        headcount=headcount,
        max_projects_per_head=float(max_projects_per_head),
    )


def _build_explanation(target_revenue: float, violations: List[ConstraintViolation]) -> str:
    if not violations:
        return f"Planner found a feasible path to {round(target_revenue)} revenue."
    joined = ", ".join(f"{violation.object_id}:{violation.code}" for violation in violations)
    return f"Planner could not satisfy the target because of {joined}."
