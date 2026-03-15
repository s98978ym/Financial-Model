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
        "費用まとめ",
        "費用リスト",
        "（全Ver）前提条件",
        "Assumptions",
        "Artifacts",
    ]

    pl_sheet = workbook["PL設計"]
    pl_rows = {
        pl_sheet.cell(row=row_index, column=1).value: row_index
        for row_index in range(1, pl_sheet.max_row + 1)
        if pl_sheet.cell(row=row_index, column=1).value
    }
    assert "営業利益" in pl_rows
    assert isinstance(pl_sheet.cell(row=pl_rows["営業利益"], column=2).value, str)
    assert pl_sheet.cell(row=pl_rows["営業利益"], column=2).value.startswith("=")

    assumptions_sheet = workbook["（全Ver）前提条件"]
    assumption_labels = {
        assumptions_sheet.cell(row=row_index, column=1).value
        for row_index in range(1, assumptions_sheet.max_row + 1)
        if assumptions_sheet.cell(row=row_index, column=1).value
    }
    assert "売上目標" in assumption_labels
    assert "人件費比率" in assumption_labels

    cost_sheet = workbook["費用まとめ"]
    cost_labels = {
        cost_sheet.cell(row=row_index, column=1).value
        for row_index in range(1, cost_sheet.max_row + 1)
        if cost_sheet.cell(row=row_index, column=1).value
    }
    assert "OPEX合計" in cost_labels
