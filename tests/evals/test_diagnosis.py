from src.evals.candidate_profiles import revenue_combination_profiles
from src.evals.scoring import ScoreResult


def test_build_candidate_diagnosis_includes_logic_evidence_and_verdict() -> None:
    from src.evals.candidate_profiles import CandidateProfile
    from src.evals.diagnosis import build_candidate_diagnosis

    profile = CandidateProfile(
        candidate_id="candidate-demo",
        label="Demo",
        hypothesis_title="営業効率を重ねる",
        hypothesis_detail="PL改善を狙う",
        toggles_on=["sales_efficiency"],
        toggles_off=["partner_strategy"],
        logic_steps=["consulting系列に営業効率を反映する"],
        expected_impacts={"pl": 0.03},
        evidence_source_types=["pdf", "external"],
        next_if_success=["consulting bridge を強化する"],
        next_if_fail=["sales overlay を見直す"],
    )
    baseline = ScoreResult(
        layer_scores={"structure": 1.0, "model_sheets": 0.9, "pl": 0.5, "explainability": 0.9},
        total_score=0.825,
    )
    score = ScoreResult(
        layer_scores={"structure": 1.0, "model_sheets": 0.9, "pl": 0.56, "explainability": 0.91},
        total_score=0.8425,
    )

    diagnosis = build_candidate_diagnosis(
        profile,
        score,
        baseline,
        evidence_summary={"pdf_facts": ["3年間検証"], "external_sources": []},
    )

    assert diagnosis["hypothesis"]["title"] == "営業効率を重ねる"
    assert diagnosis["logic"]["toggles_on"] == ["sales_efficiency"]
    assert diagnosis["score"]["layers"]["pl"]["delta"] == 0.06
    assert diagnosis["verdict"]["status"] in {"hit", "partial_hit", "miss"}
    assert diagnosis["next_actions"]


def test_build_candidate_diagnosis_treats_total_as_supported_expected_impact() -> None:
    from src.evals.candidate_profiles import CandidateProfile
    from src.evals.diagnosis import build_candidate_diagnosis

    profile = CandidateProfile(
        candidate_id="candidate-total",
        label="Total",
        hypothesis_title="総合スコア改善",
        hypothesis_detail="総合スコアが baseline より上がるはず。",
        expected_impacts={"total": 0.01},
        next_if_success=["次の候補へ進む"],
        next_if_fail=["score 差分ロジックを見直す"],
    )
    baseline = ScoreResult(
        layer_scores={"structure": 0.5, "model_sheets": 0.5, "pl": 0.5, "explainability": 0.5},
        total_score=0.5,
    )
    score = ScoreResult(
        layer_scores={"structure": 0.5, "model_sheets": 0.5, "pl": 0.5, "explainability": 0.5},
        total_score=0.7,
    )

    diagnosis = build_candidate_diagnosis(profile, score, baseline)

    assert diagnosis["verdict"]["status"] == "hit"


def test_candidate_profile_exposes_hypothesis_metadata() -> None:
    profile = next(
        profile
        for profile in revenue_combination_profiles()
        if profile.candidate_id == "candidate-revenue-staged-sales"
    )

    assert profile.hypothesis_title
    assert "staged" in profile.toggles_on
    assert "sales" in profile.toggles_on
    assert profile.logic_steps
    assert "pl" in profile.expected_impacts
