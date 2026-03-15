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
        "PDCAチェックシート",
        "PL設計",
        "ミールモデル",
        "アカデミーモデル",
        "コンサルモデル",
        "費用計画",
        "（全Ver）前提条件",
    ]

    review_sheet = workbook["PDCAチェックシート"]
    assert review_sheet.freeze_panes == "B2"
    assert review_sheet.column_dimensions["A"].width >= 22
    assert review_sheet.column_dimensions["B"].width >= 18
    pdca_labels = {
        review_sheet.cell(row=row_index, column=1).value
        for row_index in range(1, review_sheet.max_row + 1)
        if review_sheet.cell(row=row_index, column=1).value
    }
    assert "今回の結論" in pdca_labels
    assert "PDCA全体推移" in pdca_labels
    assert "評価スコア" in pdca_labels
    assert "根拠と前提" in pdca_labels
    assert "関連ファイル" in pdca_labels
    assert "次の改善施策" in pdca_labels
    assert review_sheet["A12"].value == "今回の仮説"
    assert review_sheet["D12"].value
    assert review_sheet["A13"].value == "仮説の詳細"
    assert review_sheet["D13"].value

    pl_sheet = workbook["PL設計"]
    assert pl_sheet.freeze_panes == "B2"
    assert pl_sheet.column_dimensions["A"].width >= 18
    assert 10 <= pl_sheet.column_dimensions["B"].width <= 14
    assert pl_sheet.row_dimensions[1].height >= 20
    pl_rows = {
        pl_sheet.cell(row=row_index, column=1).value: row_index
        for row_index in range(1, pl_sheet.max_row + 1)
        if pl_sheet.cell(row=row_index, column=1).value
    }
    assert "営業利益" in pl_rows
    assert "開発費（償却）" in pl_rows
    assert isinstance(pl_sheet.cell(row=pl_rows["営業利益"], column=2).value, str)
    assert pl_sheet.cell(row=pl_rows["営業利益"], column=2).value.startswith("=")

    assumptions_sheet = workbook["（全Ver）前提条件"]
    assert assumptions_sheet.freeze_panes == "B2"
    assert assumptions_sheet.column_dimensions["A"].width >= 18
    assert assumptions_sheet.column_dimensions["G"].width >= 28
    assumption_labels = {
        assumptions_sheet.cell(row=row_index, column=1).value
        for row_index in range(1, assumptions_sheet.max_row + 1)
        if assumptions_sheet.cell(row=row_index, column=1).value
    }
    assert "売上目標" in assumption_labels
    assert "人件費比率" in assumption_labels
    assert "開発投資額（キャッシュ）" in assumption_labels
    assert "開発償却期間（年）" in assumption_labels
    assert "PL計上開発費（償却）" in assumption_labels
    assert assumptions_sheet["B2"].fill.fill_type == "solid"
    assert _rgb_suffix(assumptions_sheet["B2"]) == "DDEBF7"
    assert assumptions_sheet["B2"].number_format == "#,##0"
    assert assumptions_sheet["B10"].fill.fill_type == "solid"
    assert _rgb_suffix(assumptions_sheet["B10"]) == "E2F0D9"
    assert assumptions_sheet["B10"].number_format == "#,##0"
    assert assumptions_sheet["B28"].number_format == "0.0%"

    cost_sheet = workbook["費用計画"]
    assert cost_sheet.freeze_panes == "B2"
    assert cost_sheet.column_dimensions["A"].width >= 20
    cost_labels = {
        cost_sheet.cell(row=row_index, column=1).value
        for row_index in range(1, cost_sheet.max_row + 1)
        if cost_sheet.cell(row=row_index, column=1).value
    }
    assert "費用サマリー" in cost_labels
    assert "開発償却ブロック" in cost_labels
    assert "費用明細" in cost_labels
    assert "OPEX合計" in cost_labels
    assert "開発投資（キャッシュ）" in cost_labels
    assert "償却方法" in cost_labels
    assert "償却期間（年）" in cost_labels
    assert "当期償却額（PL計上）" in cost_labels
    assert "当期投資の期末未償却残高" in cost_labels
    assert cost_sheet["B17"].value == "FY1"
    assert cost_sheet["F17"].value == "FY5"
    assert cost_sheet["G17"].value == "カテゴリ"
    assert cost_sheet["A7"].fill.fill_type == "solid"
    assert _rgb_suffix(cost_sheet["A7"]) == "A6A6A6"
    assert cost_sheet["B7"].fill.fill_type == "solid"
    assert _rgb_suffix(cost_sheet["B7"]) == "A6A6A6"
    assert cost_sheet["B7"].number_format == "#,##0"
    assert cost_sheet["B11"].value == "定額法"
    assert cost_sheet["B12"].value == 5
    assert isinstance(cost_sheet["B10"].value, str)
    assert cost_sheet["B10"].value.startswith("=")
    assert isinstance(cost_sheet["B13"].value, str)
    assert cost_sheet["B13"].value.startswith("=")
    assert isinstance(cost_sheet["B18"].value, str)
    assert cost_sheet["B18"].value.startswith("=")
    assert cost_sheet["G18"].value == "人件費"


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
    assert academy_sheet.freeze_panes == "B2"
    assert academy_sheet.column_dimensions["A"].width >= 18
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
    assert consult_sheet.freeze_panes == "A3"
    assert consult_sheet.column_dimensions["B"].width >= 20
    assert consult_sheet.column_dimensions["H"].width >= 12
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
    assert consult_sheet["D3"].number_format == "#,##0"
    assert consult_sheet["E3"].number_format == "0.0%"
    assert consult_sheet["H3"].number_format == "#,##0.0"
    assert consult_sheet["B3"].alignment.wrap_text is True

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
    assert pl_sheet["B2"].number_format == "#,##0"
    assert pl_sheet["B8"].number_format == "0.0%"
    assert pl_sheet["B15"].number_format == "0.0%"
    assert pl_sheet["A3"].alignment.horizontal == "left"
