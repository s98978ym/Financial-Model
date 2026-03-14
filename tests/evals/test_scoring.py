from pathlib import Path
import json

from src.evals.reference_workbook import extract_reference_workbook
from src.evals.scoring import score_candidate


def test_score_candidate_returns_layer_scores_and_total() -> None:
    reference = extract_reference_workbook(Path("tests/fixtures/evals/reference_workbook_minimal.xlsx"))
    candidate = json.loads(Path("tests/fixtures/evals/candidate_result.json").read_text())

    result = score_candidate(reference, candidate)

    assert set(result.layer_scores) == {"structure", "model_sheets", "pl", "explainability"}
    assert result.total_score > 0


def test_better_candidate_scores_higher_than_baseline() -> None:
    reference = extract_reference_workbook(Path("tests/fixtures/evals/reference_workbook_minimal.xlsx"))
    baseline = json.loads(Path("tests/fixtures/evals/baseline_result.json").read_text())
    candidate = json.loads(Path("tests/fixtures/evals/candidate_result.json").read_text())

    baseline_score = score_candidate(reference, baseline)
    candidate_score = score_candidate(reference, candidate)

    assert candidate_score.total_score > baseline_score.total_score
