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
    hypothesis_title: str = ""
    hypothesis_detail: str = ""
    toggles_on: List[str] = field(default_factory=list)
    toggles_off: List[str] = field(default_factory=list)
    logic_steps: List[str] = field(default_factory=list)
    expected_impacts: Dict[str, float] = field(default_factory=dict)
    evidence_source_types: List[str] = field(default_factory=list)
    next_if_success: List[str] = field(default_factory=list)
    next_if_fail: List[str] = field(default_factory=list)


PROFILE_METADATA: Dict[str, Dict[str, Any]] = {
    "candidate-better": {
        "hypothesis_title": "fixture 改善候補の検証",
        "hypothesis_detail": "baseline より良い fixture を使うと、比較ロジックが改善方向を正しく識別できるはず。",
        "toggles_on": ["fixture_better"],
        "logic_steps": ["candidate_result.json を読み込み、baseline と同一条件で採点する。"],
        "expected_impacts": {"total": 0.01},
        "evidence_source_types": ["fixture"],
        "next_if_success": ["fixture runner での改善識別が正しいと確認した上で live runner へ進む。"],
        "next_if_fail": ["fixture の差分と scoring ロジックの対応を見直す。"],
    },
    "candidate-baseline-like": {
        "hypothesis_title": "fixture ベースライン近似候補の検証",
        "hypothesis_detail": "baseline に近い fixture は、baseline と同程度のスコアになるはず。",
        "toggles_on": ["fixture_baseline_like"],
        "logic_steps": ["baseline_result.json 相当の payload を候補として採点する。"],
        "expected_impacts": {"total": 0.0},
        "evidence_source_types": ["fixture"],
        "next_if_success": ["fixture 比較の安定性を維持したまま診断出力を強化する。"],
        "next_if_fail": ["fixture 比較時の score 差分計算を確認する。"],
    },
    "candidate-revenue-staged-sales": {
        "hypothesis_title": "検証後アクセルに営業効率を重ねる",
        "hypothesis_detail": "3年間の検証後に営業投資を加速し、sales efficiency overlay を重ねると PL 再現が改善するはず。",
        "toggles_on": ["staged", "sales"],
        "toggles_off": ["partner", "branding"],
        "logic_steps": [
            "前半3年を検証期間として扱う。",
            "後半で営業投資を加速させる。",
            "sales efficiency overlay を consulting/revenue 系列に反映する。",
        ],
        "expected_impacts": {"pl": 0.03, "model_sheets": 0.0},
        "evidence_source_types": ["pdf", "external"],
        "next_if_success": ["consulting driver と revenue line の橋渡しをさらに強化する。"],
        "next_if_fail": ["sales overlay の効き方と staged acceleration の接続を見直す。"],
    },
    "candidate-revenue-staged-partner": {
        "hypothesis_title": "検証後アクセルにパートナー戦略を重ねる",
        "hypothesis_detail": "検証後の投資アクセルに partner strategy を重ねると、継続性と売上系列が改善するはず。",
        "toggles_on": ["staged", "partner"],
        "toggles_off": ["sales", "branding"],
        "logic_steps": [
            "前半3年を検証期間として扱う。",
            "後半でパートナー寄与を売上系列に反映する。",
        ],
        "expected_impacts": {"pl": 0.02, "model_sheets": 0.0},
        "evidence_source_types": ["pdf", "external"],
        "next_if_success": ["partner 寄与を sales efficiency と複合して比較する。"],
        "next_if_fail": ["partner overlay の寄与率と継続率補正を見直す。"],
    },
    "candidate-revenue-staged-branding": {
        "hypothesis_title": "検証後アクセルにブランド波及を重ねる",
        "hypothesis_detail": "staged acceleration に branding lift を重ねると、直接施策の効率が上がり PL が改善するはず。",
        "toggles_on": ["staged", "branding"],
        "toggles_off": ["sales", "partner"],
        "logic_steps": [
            "前半3年を検証期間として扱う。",
            "後半で branding lift を direct 施策効率に反映する。",
        ],
        "expected_impacts": {"pl": 0.01, "model_sheets": 0.0},
        "evidence_source_types": ["pdf", "external"],
        "next_if_success": ["branding を sales または marketing と組み合わせて再評価する。"],
        "next_if_fail": ["branding lift の寄与を補助要素として扱い直す。"],
    },
}


def _fallback_metadata(candidate_id: str, label: str) -> Dict[str, Any]:
    toggle_tokens = candidate_id.replace("candidate-", "").split("-")
    return {
        "hypothesis_title": label,
        "hypothesis_detail": f"{label} を適用すると baseline より改善するかを確認する。",
        "toggles_on": toggle_tokens,
        "toggles_off": [],
        "logic_steps": [f"{label} の overlay / 補完ロジックを適用して baseline と比較する。"],
        "expected_impacts": {"total": 0.01},
        "evidence_source_types": ["pdf"],
        "next_if_success": [f"{label} を次の改善候補の土台にする。"],
        "next_if_fail": [f"{label} の仮説と補完ロジックを見直す。"],
    }


def _candidate(
    candidate_id: str,
    label: str,
    *,
    runner: str = "fixture",
    config: Dict[str, Any] | None = None,
) -> CandidateProfile:
    metadata = PROFILE_METADATA.get(candidate_id, _fallback_metadata(candidate_id, label))
    return CandidateProfile(
        candidate_id=candidate_id,
        label=label,
        runner=runner,
        config=config or {},
        **metadata,
    )


def fixture_profiles() -> List[CandidateProfile]:
    return [
        _candidate(
            candidate_id="candidate-better",
            label="Fixture better candidate",
            runner="fixture",
            config={"fixture_name": "candidate_result.json"},
        ),
        _candidate(
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
        _candidate(
            candidate_id="candidate-structure-seeded",
            label="PDF structure-seeded candidate",
            runner="live",
            config={"mode": "structure_seeded"},
        ),
        _candidate(
            candidate_id="candidate-structure-pl-extracted",
            label="PDF structure + PL extracted candidate",
            runner="live",
            config={"mode": "structure_pl_extracted"},
        ),
        _candidate(
            candidate_id="candidate-structure-model-pl-extracted",
            label="PDF structure + academy model + PL extracted candidate",
            runner="live",
            config={"mode": "structure_model_pl_extracted"},
        ),
        _candidate(
            candidate_id="candidate-integrated-derived",
            label="PDF structure + model extraction + benchmark completion candidate",
            runner="live",
            config={"mode": "integrated_derived"},
        ),
        _candidate(
            candidate_id="candidate-reference-seeded",
            label="PDF reference-seeded candidate",
            runner="live",
            config={"mode": "reference_seeded"},
        ),
    ]


def analysis_ablation_profiles() -> List[CandidateProfile]:
    return [
        _candidate(
            candidate_id="candidate-analysis-industry",
            label="Industry-analysis overlay candidate",
            runner="live",
            config={"mode": "industry_analysis"},
        ),
        _candidate(
            candidate_id="candidate-analysis-competitor",
            label="Competitor-analysis overlay candidate",
            runner="live",
            config={"mode": "competitor_analysis"},
        ),
        _candidate(
            candidate_id="candidate-analysis-trend",
            label="Trend-analysis overlay candidate",
            runner="live",
            config={"mode": "trend_analysis"},
        ),
        _candidate(
            candidate_id="candidate-analysis-public-market",
            label="Public-market-analysis overlay candidate",
            runner="live",
            config={"mode": "public_market_analysis"},
        ),
        _candidate(
            candidate_id="candidate-reference-seeded",
            label="PDF reference-seeded candidate",
            runner="live",
            config={"mode": "reference_seeded"},
        ),
    ]


def industry_element_profiles() -> List[CandidateProfile]:
    return [
        _candidate(
            candidate_id="candidate-industry-price-portion",
            label="Industry price/portion candidate",
            runner="live",
            config={"mode": "industry_price_portion"},
        ),
        _candidate(
            candidate_id="candidate-industry-meal-frequency",
            label="Industry meal frequency candidate",
            runner="live",
            config={"mode": "industry_meal_frequency"},
        ),
        _candidate(
            candidate_id="candidate-industry-retention",
            label="Industry retention candidate",
            runner="live",
            config={"mode": "industry_retention"},
        ),
        _candidate(
            candidate_id="candidate-reference-seeded",
            label="PDF reference-seeded candidate",
            runner="live",
            config={"mode": "reference_seeded"},
        ),
    ]


def combination_profiles() -> List[CandidateProfile]:
    return [
        _candidate(
            candidate_id="candidate-combined-industry-public-market",
            label="Industry + public market candidate",
            runner="live",
            config={"mode": "combined_industry_public_market"},
        ),
        _candidate(
            candidate_id="candidate-combined-industry-trend",
            label="Industry + trend candidate",
            runner="live",
            config={"mode": "combined_industry_trend"},
        ),
        _candidate(
            candidate_id="candidate-combined-industry-trend-public-market",
            label="Industry + trend + public market candidate",
            runner="live",
            config={"mode": "combined_industry_trend_public_market"},
        ),
        _candidate(
            candidate_id="candidate-reference-seeded",
            label="PDF reference-seeded candidate",
            runner="live",
            config={"mode": "reference_seeded"},
        ),
    ]


def cost_analysis_profiles() -> List[CandidateProfile]:
    return [
        _candidate(
            candidate_id="candidate-cost-workforce-development",
            label="Workforce and development cost analysis candidate",
            runner="live",
            config={"mode": "workforce_development_cost_analysis"},
        ),
        _candidate(
            candidate_id="candidate-cost-marketing",
            label="Marketing cost analysis candidate",
            runner="live",
            config={"mode": "marketing_cost_analysis"},
        ),
        _candidate(
            candidate_id="candidate-cost-operating-purpose",
            label="Operating model and purpose analysis candidate",
            runner="live",
            config={"mode": "operating_model_analysis"},
        ),
        _candidate(
            candidate_id="candidate-reference-seeded",
            label="PDF reference-seeded candidate",
            runner="live",
            config={"mode": "reference_seeded"},
        ),
    ]


def cost_element_profiles() -> List[CandidateProfile]:
    return [
        _candidate(
            candidate_id="candidate-cost-internal-unit",
            label="Internal workforce unit cost candidate",
            runner="live",
            config={"mode": "workforce_internal_unit_cost"},
        ),
        _candidate(
            candidate_id="candidate-cost-external-unit",
            label="External workforce unit cost candidate",
            runner="live",
            config={"mode": "workforce_external_unit_cost"},
        ),
        _candidate(
            candidate_id="candidate-cost-effort-mix",
            label="Effort mix candidate",
            runner="live",
            config={"mode": "workforce_effort_mix"},
        ),
        _candidate(
            candidate_id="candidate-reference-seeded",
            label="PDF reference-seeded candidate",
            runner="live",
            config={"mode": "reference_seeded"},
        ),
    ]


def cost_combination_profiles() -> List[CandidateProfile]:
    return [
        _candidate(
            candidate_id="candidate-cost-workforce-marketing",
            label="Workforce plus marketing cost candidate",
            runner="live",
            config={"mode": "combined_cost_workforce_marketing"},
        ),
        _candidate(
            candidate_id="candidate-cost-workforce-operating",
            label="Workforce plus operating-model cost candidate",
            runner="live",
            config={"mode": "combined_cost_workforce_operating"},
        ),
        _candidate(
            candidate_id="candidate-cost-combined",
            label="Combined cost operating model candidate",
            runner="live",
            config={"mode": "combined_cost_operating_model"},
        ),
        _candidate(
            candidate_id="candidate-reference-seeded",
            label="PDF reference-seeded candidate",
            runner="live",
            config={"mode": "reference_seeded"},
        ),
    ]


def revenue_analysis_profiles() -> List[CandidateProfile]:
    return [
        _candidate(
            candidate_id="candidate-revenue-branding-lift",
            label="Branding-lift candidate",
            runner="live",
            config={"mode": "branding_lift_analysis"},
        ),
        _candidate(
            candidate_id="candidate-revenue-marketing-efficiency",
            label="Marketing-efficiency candidate",
            runner="live",
            config={"mode": "marketing_efficiency_analysis"},
        ),
        _candidate(
            candidate_id="candidate-revenue-sales-efficiency",
            label="Sales-efficiency candidate",
            runner="live",
            config={"mode": "sales_efficiency_analysis"},
        ),
        _candidate(
            candidate_id="candidate-revenue-partner-strategy",
            label="Partner-strategy candidate",
            runner="live",
            config={"mode": "partner_strategy_analysis"},
        ),
        _candidate(
            candidate_id="candidate-revenue-staged-acceleration",
            label="Staged-acceleration candidate",
            runner="live",
            config={"mode": "staged_acceleration_analysis"},
        ),
        _candidate(
            candidate_id="candidate-reference-seeded",
            label="PDF reference-seeded candidate",
            runner="live",
            config={"mode": "reference_seeded"},
        ),
    ]


def revenue_element_profiles() -> List[CandidateProfile]:
    return [
        _candidate(
            candidate_id="candidate-revenue-validation-period",
            label="Validation-period candidate",
            runner="live",
            config={"mode": "validation_period_analysis"},
        ),
        _candidate(
            candidate_id="candidate-revenue-acceleration-period",
            label="Acceleration-period candidate",
            runner="live",
            config={"mode": "acceleration_period_analysis"},
        ),
        _candidate(
            candidate_id="candidate-revenue-gated-acceleration",
            label="Gated-acceleration candidate",
            runner="live",
            config={"mode": "gated_acceleration_analysis"},
        ),
        _candidate(
            candidate_id="candidate-reference-seeded",
            label="PDF reference-seeded candidate",
            runner="live",
            config={"mode": "reference_seeded"},
        ),
    ]


def revenue_combination_profiles() -> List[CandidateProfile]:
    return [
        _candidate(
            candidate_id="candidate-revenue-staged-sales",
            label="Staged acceleration plus sales efficiency candidate",
            runner="live",
            config={"mode": "combined_staged_sales"},
        ),
        _candidate(
            candidate_id="candidate-revenue-staged-partner",
            label="Staged acceleration plus partner strategy candidate",
            runner="live",
            config={"mode": "combined_staged_partner"},
        ),
        _candidate(
            candidate_id="candidate-revenue-staged-branding",
            label="Staged acceleration plus branding lift candidate",
            runner="live",
            config={"mode": "combined_staged_branding"},
        ),
        _candidate(
            candidate_id="candidate-reference-seeded",
            label="PDF reference-seeded candidate",
            runner="live",
            config={"mode": "reference_seeded"},
        ),
    ]
