"""Synthesize canonical models and assumption ledgers from discovery analysis."""

from __future__ import annotations

import re
from typing import Optional

from src.agents.business_model_analyzer import (
    BreakevenTarget as AnalyzerBreakevenTarget,
    BusinessModelAnalysis,
    BusinessModelProposal,
    CostItem,
    RevenueDriver,
    YearTarget as AnalyzerYearTarget,
)

from .canonical_model import (
    BreakevenTarget,
    BusinessSegment,
    CanonicalBusinessModel,
    Driver,
    DriverSeries,
    FinancialTargets,
    ModelMetadata,
    RevenueEngine,
    YearValue,
)
from .evidence_ledger import AssumptionLedger, AssumptionRecord, EvidenceRef


_NAME_ID_MAP = {
    "ミール": "meal",
    "アカデミー": "academy",
    "コンサル": "consulting",
    "コンサルティング": "consulting",
    "saas subscription": "saas",
    "saas": "saas",
}


def _pick_proposal(analysis: BusinessModelAnalysis, proposal_index: Optional[int] = None) -> BusinessModelProposal:
    if analysis.proposals:
        index = analysis.selected_index if proposal_index is None else proposal_index
        return analysis.proposals[index]

    return BusinessModelProposal(
        label="legacy",
        industry=analysis.industry,
        business_model_type=analysis.business_model_type,
        executive_summary=analysis.executive_summary,
        segments=analysis.segments,
        shared_costs=analysis.shared_costs,
        growth_trajectory=analysis.growth_trajectory,
        risk_factors=analysis.risk_factors,
        time_horizon=analysis.time_horizon,
        confidence=1.0,
        reasoning="legacy-top-level-fields",
    )


def _slug(value: str, fallback: str) -> str:
    lowered = value.strip().lower()
    if lowered in _NAME_ID_MAP:
        return _NAME_ID_MAP[lowered]

    ascii_slug = re.sub(r"[^a-z0-9]+", "_", lowered).strip("_")
    return ascii_slug or fallback


def _map_engine_type(model_type: str) -> str:
    normalized = (model_type or "").strip().lower()
    if normalized in {"subscription", "unit_economics", "progression"}:
        return normalized
    if normalized in {"project", "consulting", "project_capacity"}:
        return "project_capacity"
    if normalized in {"academy"}:
        return "progression"
    return "custom_formula"


def _parse_float(value: object) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _map_year_value(target: AnalyzerYearTarget) -> YearValue:
    return YearValue(
        year=target.year,
        value=target.value,
        evidence=target.evidence,
        source=target.source,
    )


def _map_breakeven_target(target: AnalyzerBreakevenTarget, breakeven_type: str) -> BreakevenTarget:
    return BreakevenTarget(
        year=target.year,
        type=breakeven_type,  # type: ignore[arg-type]
        evidence=target.evidence,
        source=target.source,
    )


def _map_financial_targets(analysis: BusinessModelAnalysis) -> FinancialTargets:
    targets = analysis.financial_targets
    if not targets:
        return FinancialTargets()

    breakeven_targets = []
    if targets.single_year_breakeven:
        breakeven_targets.append(_map_breakeven_target(targets.single_year_breakeven, "single_year"))
    if targets.cumulative_breakeven:
        breakeven_targets.append(_map_breakeven_target(targets.cumulative_breakeven, "cumulative"))

    return FinancialTargets(
        revenue_targets=[_map_year_value(target) for target in targets.revenue_targets],
        operating_profit_targets=[_map_year_value(target) for target in targets.op_targets],
        ebitda_targets=[],
        breakeven_targets=breakeven_targets,
    )


def _map_driver(segment_id: str, revenue_driver: RevenueDriver) -> Driver:
    parsed_value = _parse_float(revenue_driver.estimated_value)
    return Driver(
        driver_id=f"{segment_id}_{_slug(revenue_driver.name, 'driver')}",
        name=revenue_driver.name,
        unit=revenue_driver.unit,
        category="other",
        series=DriverSeries(fy1=parsed_value),
        source="document" if revenue_driver.is_from_document else "inferred",
        confidence=1.0 if revenue_driver.is_from_document else 0.5,
        mode="fixed" if parsed_value is not None else "bounded",
        decision_required=parsed_value is None,
        evidence=revenue_driver.evidence,
        tags=[segment_id],
    )


def synthesize_canonical_model(
    analysis: BusinessModelAnalysis,
    proposal_index: Optional[int] = None,
) -> CanonicalBusinessModel:
    proposal = _pick_proposal(analysis, proposal_index=proposal_index)
    segments = []

    for idx, segment in enumerate(proposal.segments, start=1):
        segment_id = _slug(segment.name, f"segment_{idx}")
        engine_type = _map_engine_type(segment.model_type)
        engine = RevenueEngine(
            engine_id=f"{segment_id}_engine_1",
            engine_type=engine_type,  # type: ignore[arg-type]
            name=segment.name,
            drivers=[_map_driver(segment_id, driver) for driver in segment.revenue_drivers],
            revenue_equation=segment.revenue_formula,
            assumptions=list(segment.key_assumptions),
        )
        segments.append(
            BusinessSegment(
                segment_id=segment_id,
                name=segment.name,
                customer_type=proposal.business_model_type,
                offer_type=segment.model_type,
                engines=[engine],
                assumptions=list(segment.key_assumptions),
            )
        )

    return CanonicalBusinessModel(
        metadata=ModelMetadata(
            project_name=analysis.company_name,
            currency=analysis.currency or "JPY",
            horizon_years=analysis.financial_targets.horizon_years if analysis.financial_targets else 5,
            notes=proposal.executive_summary,
        ),
        targets=_map_financial_targets(analysis),
        segments=segments,
        global_assumptions=[
            value for value in [proposal.growth_trajectory, proposal.reasoning] if value
        ],
    )


def _driver_record(segment_id: str, revenue_driver: RevenueDriver) -> AssumptionRecord:
    parsed_value = _parse_float(revenue_driver.estimated_value)
    is_document = revenue_driver.is_from_document
    return AssumptionRecord(
        record_id=f"assump_{segment_id}_{_slug(revenue_driver.name, 'driver')}",
        object_type="driver",
        object_id=f"{segment_id}_{_slug(revenue_driver.name, 'driver')}",
        metric_name=revenue_driver.name,
        value=parsed_value,
        unit=revenue_driver.unit,
        source_type="document" if is_document else "manual_input",
        confidence=1.0 if is_document else 0.5,
        evidence_refs=[
            EvidenceRef(
                ref_type="document_quote" if is_document else "management_note",
                source_id=segment_id,
                quote=revenue_driver.evidence,
                rationale="driver evidence",
            )
        ] if revenue_driver.evidence else [],
        review_status="grounded" if is_document else ("decision_required" if parsed_value is None else "needs_review"),
        board_ready=is_document and bool(revenue_driver.evidence),
        explanation=revenue_driver.evidence or "",
    )


def _cost_record(cost_item: CostItem) -> AssumptionRecord:
    parsed_value = _parse_float(cost_item.estimated_value)
    is_document = cost_item.is_from_document
    return AssumptionRecord(
        record_id=f"assump_cost_{_slug(cost_item.name, 'cost')}",
        object_type="cost_pool",
        object_id=_slug(cost_item.name, "cost"),
        metric_name=cost_item.name,
        value=parsed_value,
        unit="JPY",
        source_type="document" if is_document else "manual_input",
        confidence=1.0 if is_document else 0.5,
        evidence_refs=[
            EvidenceRef(
                ref_type="document_quote" if is_document else "management_note",
                source_id="shared_costs",
                quote=cost_item.evidence,
                rationale="cost evidence",
            )
        ] if cost_item.evidence else [],
        review_status="grounded" if is_document else "needs_review",
        board_ready=is_document and bool(cost_item.evidence),
        explanation=cost_item.evidence or "",
    )


def build_assumption_ledger(
    analysis: BusinessModelAnalysis,
    proposal_index: Optional[int] = None,
) -> AssumptionLedger:
    proposal = _pick_proposal(analysis, proposal_index=proposal_index)
    records = []

    for idx, segment in enumerate(proposal.segments, start=1):
        segment_id = _slug(segment.name, f"segment_{idx}")
        records.extend(_driver_record(segment_id, driver) for driver in segment.revenue_drivers)

    records.extend(_cost_record(cost_item) for cost_item in proposal.shared_costs)

    return AssumptionLedger(records=records)
