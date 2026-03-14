"""Build concise explanation packs from canonical models, ledgers, and planner output."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from src.domain.canonical_model import CanonicalBusinessModel, Driver
from src.domain.evidence_ledger import AssumptionLedger, AssumptionRecord
from src.solver.planner import PlannerResult


@dataclass
class DriverExplanation:
    driver_id: str
    name: str
    value: float | None
    source_type: str
    evidence_summary: str
    board_ready: bool


@dataclass
class ExplanationPack:
    headline: str
    top_drivers: List[DriverExplanation] = field(default_factory=list)
    evidence_summary: List[str] = field(default_factory=list)
    constraint_summary: List[str] = field(default_factory=list)
    sensitivity_hints: List[str] = field(default_factory=list)
    board_ready: bool = False


def build_explanation_pack(
    model: CanonicalBusinessModel,
    ledger: AssumptionLedger,
    planner_result: PlannerResult,
) -> ExplanationPack:
    ledger_map = {record.object_id: record for record in ledger.records}
    drivers = _top_driver_candidates(model)
    top_drivers = [_build_driver_explanation(driver, ledger_map.get(driver.driver_id), planner_result) for driver in drivers]

    evidence_summary = [
        f"{driver.name}: {driver.source_type} - {driver.evidence_summary}"
        for driver in top_drivers
        if driver.evidence_summary
    ]
    constraint_summary = [violation.message for violation in planner_result.constraint_violations]
    sensitivity_hints = constraint_summary[:] if constraint_summary else [
        f"{driver.name} is sensitive because it is {driver.source_type}-based"
        for driver in top_drivers
        if driver.source_type in {"benchmark", "manual_input", "default"}
    ]
    board_ready = all(driver.board_ready for driver in top_drivers) if top_drivers else False

    target = model.targets.revenue_targets[0] if model.targets.revenue_targets else None
    headline = model.metadata.project_name or "Plan"
    if target and target.value is not None:
        headline = f"{headline}: {target.year} revenue plan"

    return ExplanationPack(
        headline=headline,
        top_drivers=top_drivers,
        evidence_summary=evidence_summary,
        constraint_summary=constraint_summary,
        sensitivity_hints=sensitivity_hints,
        board_ready=board_ready,
    )


def _top_driver_candidates(model: CanonicalBusinessModel) -> List[Driver]:
    candidates: List[Driver] = []
    fixed: List[Driver] = []
    for segment in model.segments:
        for engine in segment.engines:
            for driver in engine.drivers:
                if driver.mode in {"solve_for", "bounded"}:
                    candidates.append(driver)
                elif driver.mode == "fixed":
                    fixed.append(driver)
    return (candidates + fixed)[:5]


def _build_driver_explanation(
    driver: Driver,
    record: AssumptionRecord | None,
    planner_result: PlannerResult,
) -> DriverExplanation:
    solved_value = planner_result.solved_driver_values.get(driver.driver_id)
    value = solved_value.fy1 if solved_value and solved_value.fy1 is not None else driver.series.fy1
    if record is None:
        return DriverExplanation(
            driver_id=driver.driver_id,
            name=driver.name,
            value=value,
            source_type="unknown",
            evidence_summary="",
            board_ready=False,
        )

    evidence_summary = record.explanation
    if not evidence_summary and record.evidence_refs:
        evidence_summary = record.evidence_refs[0].quote or record.evidence_refs[0].rationale

    return DriverExplanation(
        driver_id=driver.driver_id,
        name=driver.name,
        value=value,
        source_type=record.source_type,
        evidence_summary=evidence_summary,
        board_ready=record.board_ready,
    )
