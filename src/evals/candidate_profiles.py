"""Candidate profiles for reference-driven PDCA runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class CandidateProfile:
    candidate_id: str
    label: str
    runner: str = "fixture"
    config: Dict[str, Any] = field(default_factory=dict)


def fixture_profiles() -> List[CandidateProfile]:
    return [
        CandidateProfile(
            candidate_id="candidate-better",
            label="Fixture better candidate",
            runner="fixture",
            config={"fixture_name": "candidate_result.json"},
        ),
        CandidateProfile(
            candidate_id="candidate-baseline-like",
            label="Fixture baseline-like candidate",
            runner="fixture",
            config={"fixture_name": "baseline_result.json"},
        ),
    ]


def fixture_path(root: Path, fixture_name: str) -> Path:
    return root / "tests" / "fixtures" / "evals" / fixture_name


def live_profiles() -> List[CandidateProfile]:
    return [
        CandidateProfile(
            candidate_id="candidate-structure-seeded",
            label="PDF structure-seeded candidate",
            runner="live",
            config={"mode": "structure_seeded"},
        ),
        CandidateProfile(
            candidate_id="candidate-structure-pl-extracted",
            label="PDF structure + PL extracted candidate",
            runner="live",
            config={"mode": "structure_pl_extracted"},
        ),
        CandidateProfile(
            candidate_id="candidate-structure-model-pl-extracted",
            label="PDF structure + academy model + PL extracted candidate",
            runner="live",
            config={"mode": "structure_model_pl_extracted"},
        ),
        CandidateProfile(
            candidate_id="candidate-integrated-derived",
            label="PDF structure + model extraction + benchmark completion candidate",
            runner="live",
            config={"mode": "integrated_derived"},
        ),
        CandidateProfile(
            candidate_id="candidate-reference-seeded",
            label="PDF reference-seeded candidate",
            runner="live",
            config={"mode": "reference_seeded"},
        ),
    ]


def analysis_ablation_profiles() -> List[CandidateProfile]:
    return [
        CandidateProfile(
            candidate_id="candidate-analysis-industry",
            label="Industry-analysis overlay candidate",
            runner="live",
            config={"mode": "industry_analysis"},
        ),
        CandidateProfile(
            candidate_id="candidate-analysis-competitor",
            label="Competitor-analysis overlay candidate",
            runner="live",
            config={"mode": "competitor_analysis"},
        ),
        CandidateProfile(
            candidate_id="candidate-analysis-trend",
            label="Trend-analysis overlay candidate",
            runner="live",
            config={"mode": "trend_analysis"},
        ),
        CandidateProfile(
            candidate_id="candidate-analysis-public-market",
            label="Public-market-analysis overlay candidate",
            runner="live",
            config={"mode": "public_market_analysis"},
        ),
        CandidateProfile(
            candidate_id="candidate-reference-seeded",
            label="PDF reference-seeded candidate",
            runner="live",
            config={"mode": "reference_seeded"},
        ),
    ]


def industry_element_profiles() -> List[CandidateProfile]:
    return [
        CandidateProfile(
            candidate_id="candidate-industry-price-portion",
            label="Industry price/portion candidate",
            runner="live",
            config={"mode": "industry_price_portion"},
        ),
        CandidateProfile(
            candidate_id="candidate-industry-meal-frequency",
            label="Industry meal frequency candidate",
            runner="live",
            config={"mode": "industry_meal_frequency"},
        ),
        CandidateProfile(
            candidate_id="candidate-industry-retention",
            label="Industry retention candidate",
            runner="live",
            config={"mode": "industry_retention"},
        ),
        CandidateProfile(
            candidate_id="candidate-reference-seeded",
            label="PDF reference-seeded candidate",
            runner="live",
            config={"mode": "reference_seeded"},
        ),
    ]


def combination_profiles() -> List[CandidateProfile]:
    return [
        CandidateProfile(
            candidate_id="candidate-combined-industry-public-market",
            label="Industry + public market candidate",
            runner="live",
            config={"mode": "combined_industry_public_market"},
        ),
        CandidateProfile(
            candidate_id="candidate-combined-industry-trend",
            label="Industry + trend candidate",
            runner="live",
            config={"mode": "combined_industry_trend"},
        ),
        CandidateProfile(
            candidate_id="candidate-combined-industry-trend-public-market",
            label="Industry + trend + public market candidate",
            runner="live",
            config={"mode": "combined_industry_trend_public_market"},
        ),
        CandidateProfile(
            candidate_id="candidate-reference-seeded",
            label="PDF reference-seeded candidate",
            runner="live",
            config={"mode": "reference_seeded"},
        ),
    ]


def cost_analysis_profiles() -> List[CandidateProfile]:
    return [
        CandidateProfile(
            candidate_id="candidate-cost-workforce-development",
            label="Workforce and development cost analysis candidate",
            runner="live",
            config={"mode": "workforce_development_cost_analysis"},
        ),
        CandidateProfile(
            candidate_id="candidate-cost-marketing",
            label="Marketing cost analysis candidate",
            runner="live",
            config={"mode": "marketing_cost_analysis"},
        ),
        CandidateProfile(
            candidate_id="candidate-cost-operating-purpose",
            label="Operating model and purpose analysis candidate",
            runner="live",
            config={"mode": "operating_model_analysis"},
        ),
        CandidateProfile(
            candidate_id="candidate-reference-seeded",
            label="PDF reference-seeded candidate",
            runner="live",
            config={"mode": "reference_seeded"},
        ),
    ]


def cost_element_profiles() -> List[CandidateProfile]:
    return [
        CandidateProfile(
            candidate_id="candidate-cost-internal-unit",
            label="Internal workforce unit cost candidate",
            runner="live",
            config={"mode": "workforce_internal_unit_cost"},
        ),
        CandidateProfile(
            candidate_id="candidate-cost-external-unit",
            label="External workforce unit cost candidate",
            runner="live",
            config={"mode": "workforce_external_unit_cost"},
        ),
        CandidateProfile(
            candidate_id="candidate-cost-effort-mix",
            label="Effort mix candidate",
            runner="live",
            config={"mode": "workforce_effort_mix"},
        ),
        CandidateProfile(
            candidate_id="candidate-reference-seeded",
            label="PDF reference-seeded candidate",
            runner="live",
            config={"mode": "reference_seeded"},
        ),
    ]


def cost_combination_profiles() -> List[CandidateProfile]:
    return [
        CandidateProfile(
            candidate_id="candidate-cost-workforce-marketing",
            label="Workforce plus marketing cost candidate",
            runner="live",
            config={"mode": "combined_cost_workforce_marketing"},
        ),
        CandidateProfile(
            candidate_id="candidate-cost-workforce-operating",
            label="Workforce plus operating-model cost candidate",
            runner="live",
            config={"mode": "combined_cost_workforce_operating"},
        ),
        CandidateProfile(
            candidate_id="candidate-cost-combined",
            label="Combined cost operating model candidate",
            runner="live",
            config={"mode": "combined_cost_operating_model"},
        ),
        CandidateProfile(
            candidate_id="candidate-reference-seeded",
            label="PDF reference-seeded candidate",
            runner="live",
            config={"mode": "reference_seeded"},
        ),
    ]


def revenue_analysis_profiles() -> List[CandidateProfile]:
    return [
        CandidateProfile(
            candidate_id="candidate-revenue-branding-lift",
            label="Branding-lift candidate",
            runner="live",
            config={"mode": "branding_lift_analysis"},
        ),
        CandidateProfile(
            candidate_id="candidate-revenue-marketing-efficiency",
            label="Marketing-efficiency candidate",
            runner="live",
            config={"mode": "marketing_efficiency_analysis"},
        ),
        CandidateProfile(
            candidate_id="candidate-revenue-sales-efficiency",
            label="Sales-efficiency candidate",
            runner="live",
            config={"mode": "sales_efficiency_analysis"},
        ),
        CandidateProfile(
            candidate_id="candidate-revenue-partner-strategy",
            label="Partner-strategy candidate",
            runner="live",
            config={"mode": "partner_strategy_analysis"},
        ),
        CandidateProfile(
            candidate_id="candidate-revenue-staged-acceleration",
            label="Staged-acceleration candidate",
            runner="live",
            config={"mode": "staged_acceleration_analysis"},
        ),
        CandidateProfile(
            candidate_id="candidate-reference-seeded",
            label="PDF reference-seeded candidate",
            runner="live",
            config={"mode": "reference_seeded"},
        ),
    ]


def revenue_element_profiles() -> List[CandidateProfile]:
    return [
        CandidateProfile(
            candidate_id="candidate-revenue-validation-period",
            label="Validation-period candidate",
            runner="live",
            config={"mode": "validation_period_analysis"},
        ),
        CandidateProfile(
            candidate_id="candidate-revenue-acceleration-period",
            label="Acceleration-period candidate",
            runner="live",
            config={"mode": "acceleration_period_analysis"},
        ),
        CandidateProfile(
            candidate_id="candidate-revenue-gated-acceleration",
            label="Gated-acceleration candidate",
            runner="live",
            config={"mode": "gated_acceleration_analysis"},
        ),
        CandidateProfile(
            candidate_id="candidate-reference-seeded",
            label="PDF reference-seeded candidate",
            runner="live",
            config={"mode": "reference_seeded"},
        ),
    ]


def revenue_combination_profiles() -> List[CandidateProfile]:
    return [
        CandidateProfile(
            candidate_id="candidate-revenue-staged-sales",
            label="Staged acceleration plus sales efficiency candidate",
            runner="live",
            config={"mode": "combined_staged_sales"},
        ),
        CandidateProfile(
            candidate_id="candidate-revenue-staged-partner",
            label="Staged acceleration plus partner strategy candidate",
            runner="live",
            config={"mode": "combined_staged_partner"},
        ),
        CandidateProfile(
            candidate_id="candidate-revenue-staged-branding",
            label="Staged acceleration plus branding lift candidate",
            runner="live",
            config={"mode": "combined_staged_branding"},
        ),
        CandidateProfile(
            candidate_id="candidate-reference-seeded",
            label="PDF reference-seeded candidate",
            runner="live",
            config={"mode": "reference_seeded"},
        ),
    ]
