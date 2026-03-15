import json
from pathlib import Path

from openpyxl import load_workbook

from src.evals.diagnosis import build_candidate_diagnosis
from src.evals.candidate_profiles import fixture_profiles
from src.evals.reference_workbook import extract_reference_workbook
from src.evals.scoring import score_candidate
from src.evals.workbook_export import export_candidate_workbook


def test_export_candidate_workbook_writes_expected_sheets(tmp_path) -> None:
    fixture_dir = Path("tests/fixtures/evals")
    candidate = json.loads((fixture_dir / "candidate_result.json").read_text(encoding="utf-8"))
    baseline = json.loads((fixture_dir / "baseline_result.json").read_text(encoding="utf-8"))
    reference = extract_reference_workbook(fixture_dir / "reference_workbook_minimal.xlsx")
    candidate_score = score_candidate(reference, candidate)
    baseline_score = score_candidate(reference, baseline)
    profile = next(profile for profile in fixture_profiles() if profile.candidate_id == "candidate-better")
    diagnosis = build_candidate_diagnosis(
        profile,
        candidate_score,
        baseline_score,
        evidence_summary={"pdf_facts": [], "external_sources": [], "benchmark_fills": [], "seed_notes": []},
    )

    output_path = tmp_path / "candidate.xlsx"
    export_candidate_workbook(
        output_path=output_path,
        candidate_id=profile.candidate_id,
        candidate_payload=candidate,
        diagnosis=diagnosis,
        baseline_total=baseline_score.total_score,
        run_root=tmp_path,
    )

    assert output_path.exists()
    workbook = load_workbook(output_path, data_only=False)
    assert workbook.sheetnames == [
        "Summary",
        "PL設計",
        "ミールモデル",
        "アカデミーモデル",
        "コンサルモデル",
        "Assumptions",
        "Artifacts",
    ]
