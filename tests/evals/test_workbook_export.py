import json
from pathlib import Path

from openpyxl import load_workbook

from src.evals.diagnosis import build_candidate_diagnosis
from src.evals.candidate_profiles import fixture_profiles
from src.evals.reference_workbook import extract_reference_workbook
from src.evals.scoring import score_candidate
from src.evals.workbook_export import export_candidate_workbook


def _rgb_suffix(cell) -> str:
    return (cell.fill.fgColor.rgb or "").upper()[-6:]


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
    assert assumptions_sheet["B2"].fill.fill_type == "solid"
    assert _rgb_suffix(assumptions_sheet["B2"]) == "DDEBF7"
    assert assumptions_sheet["B10"].fill.fill_type == "solid"
    assert _rgb_suffix(assumptions_sheet["B10"]) == "E2F0D9"

    cost_sheet = workbook["費用まとめ"]
    cost_labels = {
        cost_sheet.cell(row=row_index, column=1).value
        for row_index in range(1, cost_sheet.max_row + 1)
        if cost_sheet.cell(row=row_index, column=1).value
    }
    assert "OPEX合計" in cost_labels
    assert cost_sheet["A6"].fill.fill_type == "solid"
    assert _rgb_suffix(cost_sheet["A6"]) == "A6A6A6"
    assert cost_sheet["B6"].fill.fill_type == "solid"
    assert _rgb_suffix(cost_sheet["B6"]) == "A6A6A6"


def test_export_candidate_workbook_expands_academy_and_consulting_structure(tmp_path) -> None:
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

    workbook = load_workbook(output_path, data_only=False)

    academy_sheet = workbook["アカデミーモデル"]
    academy_labels = {
        academy_sheet.cell(row=row_index, column=1).value
        for row_index in range(1, academy_sheet.max_row + 1)
        if academy_sheet.cell(row=row_index, column=1).value
    }
    assert {"C級課程", "B級課程", "A級課程", "S級課程"}.issubset(academy_labels)

    academy_formula_cells = [
        academy_sheet["B5"].value,
        academy_sheet["B10"].value,
        academy_sheet["B15"].value,
        academy_sheet["B20"].value,
    ]
    assert all(isinstance(value, str) and value.startswith("=") for value in academy_formula_cells)

    consult_sheet = workbook["コンサルモデル"]
    consult_headers = [consult_sheet.cell(row=2, column=column_index).value for column_index in range(1, 8)]
    assert consult_headers == [
        "SKU",
        "サービス名",
        "単位",
        "単価（円）",
        "継続率",
        "デリバリー原価単価",
        "標準時間",
    ]

    sku_rows = {
        consult_sheet.cell(row=row_index, column=1).value: row_index
        for row_index in range(1, consult_sheet.max_row + 1)
        if consult_sheet.cell(row=row_index, column=1).value
    }
    assert {"P1", "P2", "P3", "P4", "P5", "P6", "P8", "P9", "P10", "P11", "P12"}.issubset(sku_rows)
    assert isinstance(consult_sheet["H3"].value, str) and consult_sheet["H3"].value.startswith("=")
    assert isinstance(consult_sheet["I3"].value, str) and consult_sheet["I3"].value.startswith("=")
    assert consult_sheet["M15"].fill.fill_type == "solid"
    assert _rgb_suffix(consult_sheet["M15"]) == "D9E2F3"

    assumptions_sheet = workbook["（全Ver）前提条件"]
    assumption_labels = {
        assumptions_sheet.cell(row=row_index, column=1).value
        for row_index in range(1, assumptions_sheet.max_row + 1)
        if assumptions_sheet.cell(row=row_index, column=1).value
    }
    assert "C級新規構成比" in assumption_labels
    assert "C→B進級率" in assumption_labels
    assert "P1売上構成比" in assumption_labels
    assert "ブレンド時給" in assumption_labels
    assert _rgb_suffix(assumptions_sheet["B33"]) == "DDEBF7"
    assert _rgb_suffix(assumptions_sheet["B58"]) == "DDEBF7"

    pl_sheet = workbook["PL設計"]
    assert pl_sheet["A14"].fill.fill_type == "solid"
    assert _rgb_suffix(pl_sheet["A14"]) == "A6A6A6"
    assert pl_sheet["B14"].fill.fill_type == "solid"
    assert _rgb_suffix(pl_sheet["B14"]) == "A6A6A6"
    assert pl_sheet["A3"].fill.fill_type == "solid"
    assert _rgb_suffix(pl_sheet["A3"]) == "D9E2F3"
