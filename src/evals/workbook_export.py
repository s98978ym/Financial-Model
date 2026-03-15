"""Workbook export helpers for FAM PDCA artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill


YEAR_HEADERS = ["FY1", "FY2", "FY3", "FY4", "FY5"]

ACADEMY_LEVELS = [
    {
        "code": "c",
        "label": "C級課程",
        "share_default": [1.00, 0.65, 0.45, 0.35, 0.25],
        "price_multiplier": 1.0,
        "completion": 0.90,
        "certification": 1.00,
        "progression_to_next": 0.60,
    },
    {
        "code": "b",
        "label": "B級課程",
        "share_default": [0.00, 0.20, 0.20, 0.18, 0.15],
        "price_multiplier": 100000 / 70000,
        "completion": 0.90,
        "certification": 0.50,
        "progression_to_next": 0.30,
    },
    {
        "code": "a",
        "label": "A級課程",
        "share_default": [0.00, 0.10, 0.18, 0.22, 0.25],
        "price_multiplier": 300000 / 70000,
        "completion": 0.80,
        "certification": 0.50,
        "progression_to_next": 0.90,
    },
    {
        "code": "s",
        "label": "S級課程",
        "share_default": [0.00, 0.05, 0.17, 0.25, 0.35],
        "price_multiplier": 0.0,
        "completion": 0.90,
        "certification": 0.75,
        "progression_to_next": 0.00,
    },
]

CONSULT_SKUS = [
    {"sku": "P1", "service_name": "S総合（年契）", "unit": "契約/年", "base_price": 15000000, "retention_multiplier": 1.00, "standard_hours": 480, "share_default": [0.18, 0.20, 0.22, 0.24, 0.25]},
    {"sku": "P2", "service_name": "A総合（年契）", "unit": "契約/年", "base_price": 10000000, "retention_multiplier": 0.83, "standard_hours": 360, "share_default": [0.20, 0.22, 0.22, 0.22, 0.23]},
    {"sku": "P3", "service_name": "Sチーム年契", "unit": "契約/年", "base_price": 5000000, "retention_multiplier": 0.83, "standard_hours": 240, "share_default": [0.10, 0.10, 0.10, 0.10, 0.10]},
    {"sku": "P4", "service_name": "Aチーム年契", "unit": "契約/年", "base_price": 1500000, "retention_multiplier": 0.83, "standard_hours": 120, "share_default": [0.10, 0.12, 0.13, 0.14, 0.15]},
    {"sku": "P5", "service_name": "セミナー（単発）", "unit": "回", "base_price": 300000, "retention_multiplier": 0.00, "standard_hours": 10, "share_default": [0.10, 0.08, 0.07, 0.06, 0.05]},
    {"sku": "P6", "service_name": "ライトセミナー", "unit": "回", "base_price": 60000, "retention_multiplier": 0.00, "standard_hours": 6, "share_default": [0.06, 0.05, 0.04, 0.03, 0.03]},
    {"sku": "P8", "service_name": "S個別（年契）", "unit": "人/年", "base_price": 500000, "retention_multiplier": 0.83, "standard_hours": 30, "share_default": [0.07, 0.07, 0.08, 0.08, 0.08]},
    {"sku": "P9", "service_name": "A個別（年契）", "unit": "人/年", "base_price": 500000, "retention_multiplier": 0.83, "standard_hours": 30, "share_default": [0.07, 0.06, 0.06, 0.05, 0.05]},
    {"sku": "P10", "service_name": "S個別（単発）", "unit": "回", "base_price": 50000, "retention_multiplier": 0.00, "standard_hours": 3, "share_default": [0.05, 0.04, 0.03, 0.03, 0.03]},
    {"sku": "P11", "service_name": "A個別（単発）", "unit": "回", "base_price": 50000, "retention_multiplier": 0.00, "standard_hours": 3, "share_default": [0.05, 0.04, 0.03, 0.03, 0.02]},
    {"sku": "P12", "service_name": "OJT", "unit": "回", "base_price": 0, "retention_multiplier": 0.00, "standard_hours": 3, "share_default": [0.02, 0.02, 0.02, 0.02, 0.01]},
]

ASSUMPTION_ROWS = {
    "revenue_target": 2,
    "gross_profit_target": 3,
    "opex_target": 4,
    "academy_public_price": 6,
    "academy_students": 7,
    "academy_certified": 8,
    "academy_revenue": 9,
    "academy_effective_price": 10,
    "meal_price_per_item": 12,
    "meal_items_per_meal": 13,
    "meal_meals_per_year": 14,
    "meal_retention_rate": 15,
    "meal_share_non_academy": 16,
    "meal_unit_count": 17,
    "meal_revenue": 18,
    "consult_unit_price": 20,
    "consult_retention": 21,
    "consult_standard_hours": 22,
    "consult_revenue": 23,
    "consult_project_count": 24,
    "gross_margin_ratio": 26,
    "personnel_ratio": 28,
    "marketing_ratio": 29,
    "development_ratio": 30,
    "other_ratio": 31,
    "academy_c_share": 33,
    "academy_b_share": 34,
    "academy_a_share": 35,
    "academy_s_share": 36,
    "academy_c_to_b": 38,
    "academy_b_to_a": 39,
    "academy_a_to_s": 40,
    "academy_c_price_multiplier": 42,
    "academy_b_price_multiplier": 43,
    "academy_a_price_multiplier": 44,
    "academy_s_price_multiplier": 45,
    "academy_c_completion": 47,
    "academy_c_certification": 48,
    "academy_b_completion": 49,
    "academy_b_certification": 50,
    "academy_a_completion": 51,
    "academy_a_certification": 52,
    "academy_s_completion": 53,
    "academy_s_certification": 54,
    "blended_hourly_rate": 56,
    "consult_p1_share": 58,
    "consult_p2_share": 59,
    "consult_p3_share": 60,
    "consult_p4_share": 61,
    "consult_p5_share": 62,
    "consult_p6_share": 63,
    "consult_p8_share": 64,
    "consult_p9_share": 65,
    "consult_p10_share": 66,
    "consult_p11_share": 67,
    "consult_p12_share": 68,
    "development_investment": 70,
    "development_amortization_years": 71,
    "development_amortization_expense": 72,
    "development_unamortized_balance": 73,
}

PL_ROWS = {
    "revenue_total": 2,
    "academy_revenue": 3,
    "consult_revenue": 4,
    "meal_revenue": 5,
    "cogs": 6,
    "gross_profit": 7,
    "gross_margin_ratio": 8,
    "personnel_cost": 9,
    "marketing_cost": 10,
    "development_cost": 11,
    "other_opex": 12,
    "opex_total": 13,
    "operating_profit": 14,
    "operating_margin": 15,
}

COST_SUMMARY_ROWS = {
    "personnel_cost": 3,
    "marketing_cost": 4,
    "development_cost": 5,
    "other_opex": 6,
    "opex_total": 7,
}

COST_LIST_ROWS = [
    ("営業人件費", "人件費", 0.35, "personnel_cost"),
    ("運営人件費", "人件費", 0.30, "personnel_cost"),
    ("管理人件費", "人件費", 0.20, "personnel_cost"),
    ("採用・教育人件費", "人件費", 0.15, "personnel_cost"),
    ("メディア費", "マーケ費", 0.50, "marketing_cost"),
    ("イベント・販促費", "マーケ費", 0.30, "marketing_cost"),
    ("パートナーインセンティブ", "マーケ費", 0.20, "marketing_cost"),
    ("外部開発償却費", "開発費（償却）", 0.60, "development_cost"),
    ("内部開発償却費", "開発費（償却）", 0.40, "development_cost"),
    ("その他固定費", "その他OPEX", 1.00, "other_opex"),
]

COST_PLAN_ROWS = {
    "summary_title": 1,
    "summary_header": 2,
    "amortization_title": 9,
    "amortization_start": 10,
    "detail_title": 16,
    "detail_header": 17,
    "detail_start": 18,
}

ACADEMY_ROW_LAYOUT = {
    "c": {"label": 2, "price": 3, "students": 4, "certified": 5, "revenue": 6},
    "b": {"label": 7, "price": 8, "students": 9, "certified": 10, "revenue": 11},
    "a": {"label": 12, "price": 13, "students": 14, "certified": 15, "revenue": 16},
    "s": {"label": 17, "price": 18, "students": 19, "certified": 20, "revenue": 21},
    "total_students": 23,
    "total_revenue": 24,
}

CONSULT_DETAIL_START_ROW = 3
CONSULT_TOTAL_REVENUE_ROW = 15
CONSULT_TOTAL_DELIVERY_ROW = 16
CONSULT_TOTAL_GROSS_PROFIT_ROW = 17

INPUT_FILL = PatternFill(fill_type="solid", fgColor="DDEBF7")
FORMULA_FILL = PatternFill(fill_type="solid", fgColor="E2F0D9")
SUBTOTAL_FILL = PatternFill(fill_type="solid", fgColor="D9E2F3")
TOTAL_FILL = PatternFill(fill_type="solid", fgColor="A6A6A6")
BOLD_FONT = Font(bold=True)
TOTAL_FONT = Font(bold=True, color="FFFFFF")
NUMBER_FORMAT = "#,##0"
COUNT_DECIMAL_FORMAT = "#,##0.0"
PERCENT_FORMAT = "0.0%"
LEFT_ALIGN = Alignment(horizontal="left", vertical="center")
RIGHT_ALIGN = Alignment(horizontal="right", vertical="center")
CENTER_ALIGN = Alignment(horizontal="center", vertical="center")
WRAP_LEFT_ALIGN = Alignment(horizontal="left", vertical="center", wrap_text=True)


def export_candidate_workbook(
    *,
    output_path: Path,
    candidate_id: str,
    candidate_payload: dict[str, Any],
    diagnosis: dict[str, Any],
    baseline_total: float,
    run_root: Path,
    iteration_summaries: list[dict[str, Any]] | None = None,
) -> None:
    """Export one candidate workbook for human review."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    workbook = Workbook()
    review_sheet = workbook.active
    review_sheet.title = "PDCAチェックシート"

    assumptions = _build_workbook_assumptions(candidate_payload)
    _write_pdca_check_sheet(
        review_sheet,
        candidate_id=candidate_id,
        diagnosis=diagnosis,
        baseline_total=baseline_total,
        candidate_payload=candidate_payload,
        run_root=run_root,
        iteration_summaries=iteration_summaries or [],
    )
    _write_pl_sheet(workbook.create_sheet("PL設計"))
    _write_meal_sheet(workbook.create_sheet("ミールモデル"))
    _write_academy_sheet(workbook.create_sheet("アカデミーモデル"))
    _write_consulting_sheet(workbook.create_sheet("コンサルモデル"))
    _write_cost_plan_sheet(workbook.create_sheet("費用計画"), assumptions)
    _write_plan_assumptions_sheet(workbook.create_sheet("（全Ver）前提条件"), assumptions)
    workbook.save(output_path)


def _write_pdca_check_sheet(
    sheet,
    *,
    candidate_id: str,
    diagnosis: dict[str, Any],
    baseline_total: float,
    candidate_payload: dict[str, Any],
    run_root: Path,
    iteration_summaries: list[dict[str, Any]],
) -> None:
    hypothesis = diagnosis.get("hypothesis", {})
    verdict = diagnosis.get("verdict", {})
    score = diagnosis.get("score", {})
    logic = diagnosis.get("logic", {})
    evidence = diagnosis.get("evidence", {})

    row = 1
    row = _write_section_title(sheet, row, "今回の結論")
    conclusion_rows = [
        ("候補ID", candidate_id),
        ("仮説タイトル", hypothesis.get("title", "")),
        ("仮説の要点", hypothesis.get("detail", "")),
        ("判定", verdict.get("status", "")),
        ("判定理由", verdict.get("reason", "")),
        ("総合スコア", score.get("total", 0.0)),
        ("baseline比", score.get("delta_vs_baseline", round(score.get("total", 0.0) - baseline_total, 4))),
        ("baselineスコア", baseline_total),
    ]
    row = _write_labeled_values(sheet, row, conclusion_rows, numeric_labels={"総合スコア", "baseline比", "baselineスコア"})

    row += 1
    row = _write_section_title(sheet, row, "仮説")
    hypothesis_rows = [
        ("ONにした要素", ", ".join(logic.get("toggles_on", [])) or "-"),
        ("OFFにした要素", ", ".join(logic.get("toggles_off", [])) or "-"),
        ("ロジック", "\n".join(logic.get("steps", [])) or "-"),
    ]
    row = _write_labeled_values(sheet, row, hypothesis_rows)

    row += 1
    row = _write_section_title(sheet, row, "PDCA全体推移")
    row = _write_iteration_trend_table(
        sheet,
        row,
        iteration_summaries
        or [
            {
                "iteration": 1,
                "candidate_id": candidate_id,
                "hypothesis": hypothesis.get("title", ""),
                "result": verdict.get("reason", ""),
                "total_score": score.get("total", 0.0),
                "delta_vs_baseline": score.get("delta_vs_baseline", round(score.get("total", 0.0) - baseline_total, 4)),
                "next_action": (diagnosis.get("next_actions") or [""])[0],
            }
        ],
    )

    row += 1
    row = _write_section_title(sheet, row, "評価スコア")
    row = _write_score_table(sheet, row, score, baseline_total)

    row += 1
    row = _write_section_title(sheet, row, "根拠と前提")
    row = _write_assumption_table(sheet, row, candidate_payload.get("assumptions", []))

    row += 1
    row = _write_section_title(sheet, row, "関連ファイル")
    artifact_rows = [
        ("summary", str(run_root / "summary.md")),
        ("scores", str(run_root / "scores.json")),
        ("diagnosis", str(run_root / "diagnosis.json")),
        ("candidate_json", str(run_root / "candidates" / f"{candidate_id}.json")),
        ("reference", str(run_root / "reference.json")),
        ("baseline", str(run_root / "baseline.json")),
        ("外部根拠タイプ", ", ".join(evidence.get("source_types", [])) or "-"),
    ]
    row = _write_labeled_values(sheet, row, artifact_rows)

    row += 1
    row = _write_section_title(sheet, row, "次の改善施策")
    next_actions = diagnosis.get("next_actions", []) or ["次の施策は未設定です。"]
    row = _write_bullet_list(sheet, row, next_actions)

    sheet.freeze_panes = "B2"
    _set_column_widths(sheet, {"A": 24, "B": 24, "C": 28, "D": 34, "E": 12, "F": 12, "G": 30})
    _set_row_heights(sheet, {1: 24})
    _align_range(sheet, start_row=1, end_row=sheet.max_row, start_col=1, end_col=1, alignment=LEFT_ALIGN)
    _align_range(sheet, start_row=1, end_row=sheet.max_row, start_col=2, end_col=2, alignment=LEFT_ALIGN)
    _align_range(sheet, start_row=1, end_row=sheet.max_row, start_col=3, end_col=4, alignment=WRAP_LEFT_ALIGN)
    _align_range(sheet, start_row=1, end_row=sheet.max_row, start_col=5, end_col=6, alignment=RIGHT_ALIGN)
    _align_range(sheet, start_row=1, end_row=sheet.max_row, start_col=7, end_col=7, alignment=WRAP_LEFT_ALIGN)


def _write_pl_sheet(sheet) -> None:
    _write_header_row(sheet)
    labels = [
        ("revenue_total", "売上"),
        ("academy_revenue", "アカデミー"),
        ("consult_revenue", "コンサル"),
        ("meal_revenue", "ミール"),
        ("cogs", "売上原価"),
        ("gross_profit", "粗利"),
        ("gross_margin_ratio", "粗利率"),
        ("personnel_cost", "人件費"),
        ("marketing_cost", "マーケ費"),
        ("development_cost", "開発費（償却）"),
        ("other_opex", "その他OPEX"),
        ("opex_total", "事業運営費（OPEX）"),
        ("operating_profit", "営業利益"),
        ("operating_margin", "営業利益率"),
    ]
    for key, label in labels:
        sheet.cell(row=PL_ROWS[key], column=1, value=label)

    for column_index, assumption_col in enumerate(_year_columns(), start=2):
        model_col = excel_col(column_index)
        gross_margin_ref = _sheet_ref("（全Ver）前提条件", f"{assumption_col}{ASSUMPTION_ROWS['gross_margin_ratio']}")
        personnel_ref = _sheet_ref("費用計画", f"{model_col}{COST_SUMMARY_ROWS['personnel_cost']}")
        marketing_ref = _sheet_ref("費用計画", f"{model_col}{COST_SUMMARY_ROWS['marketing_cost']}")
        development_ref = _sheet_ref("費用計画", f"{model_col}{COST_SUMMARY_ROWS['development_cost']}")
        other_opex_ref = _sheet_ref("費用計画", f"{model_col}{COST_SUMMARY_ROWS['other_opex']}")
        academy_total_row = ACADEMY_ROW_LAYOUT["total_revenue"]
        consult_total_col = excel_col(column_index)
        sheet[f"{model_col}{PL_ROWS['academy_revenue']}"] = f"={_sheet_ref('アカデミーモデル', f'{model_col}{academy_total_row}')}"
        sheet[f"{model_col}{PL_ROWS['consult_revenue']}"] = f"={_sheet_ref('コンサルモデル', f'{consult_total_col}{CONSULT_TOTAL_REVENUE_ROW}')}"
        sheet[f"{model_col}{PL_ROWS['meal_revenue']}"] = f"={_sheet_ref('ミールモデル', f'{model_col}7')}"
        sheet[f"{model_col}{PL_ROWS['revenue_total']}"] = (
            f"=SUM({model_col}{PL_ROWS['academy_revenue']}:{model_col}{PL_ROWS['meal_revenue']})"
        )
        sheet[f"{model_col}{PL_ROWS['cogs']}"] = (
            f"={model_col}{PL_ROWS['revenue_total']}*(1-{gross_margin_ref})"
        )
        sheet[f"{model_col}{PL_ROWS['gross_profit']}"] = (
            f"={model_col}{PL_ROWS['revenue_total']}-{model_col}{PL_ROWS['cogs']}"
        )
        sheet[f"{model_col}{PL_ROWS['gross_margin_ratio']}"] = (
            f"=IF({model_col}{PL_ROWS['revenue_total']}<>0,{model_col}{PL_ROWS['gross_profit']}/{model_col}{PL_ROWS['revenue_total']},0)"
        )
        sheet[f"{model_col}{PL_ROWS['personnel_cost']}"] = f"={personnel_ref}"
        sheet[f"{model_col}{PL_ROWS['marketing_cost']}"] = f"={marketing_ref}"
        sheet[f"{model_col}{PL_ROWS['development_cost']}"] = f"={development_ref}"
        sheet[f"{model_col}{PL_ROWS['other_opex']}"] = f"={other_opex_ref}"
        sheet[f"{model_col}{PL_ROWS['opex_total']}"] = (
            f"=SUM({model_col}{PL_ROWS['personnel_cost']}:{model_col}{PL_ROWS['other_opex']})"
        )
        sheet[f"{model_col}{PL_ROWS['operating_profit']}"] = (
            f"={model_col}{PL_ROWS['gross_profit']}-{model_col}{PL_ROWS['opex_total']}"
        )
        sheet[f"{model_col}{PL_ROWS['operating_margin']}"] = (
            f"=IF({model_col}{PL_ROWS['revenue_total']}<>0,{model_col}{PL_ROWS['operating_profit']}/{model_col}{PL_ROWS['revenue_total']},0)"
        )
    _style_subtotal_rows(sheet, [PL_ROWS["academy_revenue"], PL_ROWS["consult_revenue"], PL_ROWS["meal_revenue"]])
    _style_formula_rows(sheet, [PL_ROWS["gross_margin_ratio"], PL_ROWS["operating_margin"]])
    _style_total_rows(sheet, [PL_ROWS["revenue_total"], PL_ROWS["gross_profit"], PL_ROWS["opex_total"], PL_ROWS["operating_profit"]])
    _set_number_format_rows(
        sheet,
        [
            PL_ROWS["revenue_total"],
            PL_ROWS["academy_revenue"],
            PL_ROWS["consult_revenue"],
            PL_ROWS["meal_revenue"],
            PL_ROWS["cogs"],
            PL_ROWS["gross_profit"],
            PL_ROWS["personnel_cost"],
            PL_ROWS["marketing_cost"],
            PL_ROWS["development_cost"],
            PL_ROWS["other_opex"],
            PL_ROWS["opex_total"],
            PL_ROWS["operating_profit"],
        ],
        number_format=NUMBER_FORMAT,
    )
    _set_number_format_rows(sheet, [PL_ROWS["gross_margin_ratio"], PL_ROWS["operating_margin"]], number_format=PERCENT_FORMAT)
    _apply_standard_layout(sheet, freeze_panes="B2", label_width=18, year_width=12)
    _set_row_heights(
        sheet,
        {
            PL_ROWS["revenue_total"]: 24,
            PL_ROWS["gross_profit"]: 24,
            PL_ROWS["opex_total"]: 24,
            PL_ROWS["operating_profit"]: 26,
        },
    )


def _write_meal_sheet(sheet) -> None:
    _write_header_row(sheet)
    labels = [
        "価格/アイテム",
        "アイテム/食事",
        "食事数/年",
        "継続率",
        "推定ユニット数",
        "売上",
    ]
    for row_index, label in enumerate(labels, start=2):
        sheet.cell(row=row_index, column=1, value=label)

    mapping = {
        2: "meal_price_per_item",
        3: "meal_items_per_meal",
        4: "meal_meals_per_year",
        5: "meal_retention_rate",
        6: "meal_unit_count",
    }
    for column_index, assumption_col in enumerate(_year_columns(), start=2):
        model_col = excel_col(column_index)
        for row_index, assumption_key in mapping.items():
            sheet[f"{model_col}{row_index}"] = f"={_sheet_ref('（全Ver）前提条件', f'{assumption_col}{ASSUMPTION_ROWS[assumption_key]}')}"
        sheet[f"{model_col}7"] = f"={model_col}2*{model_col}3*{model_col}4*{model_col}6"
    _style_formula_rows(sheet, [2, 3, 4, 5, 6])
    _style_subtotal_rows(sheet, [7])
    _set_number_format_rows(sheet, [2, 3, 4, 6, 7], number_format=NUMBER_FORMAT)
    _set_number_format_rows(sheet, [5], number_format=PERCENT_FORMAT)
    _apply_standard_layout(sheet, freeze_panes="B2", label_width=20, year_width=12)


def _write_academy_sheet(sheet) -> None:
    _write_header_row(sheet)
    for level in ACADEMY_LEVELS:
        rows = ACADEMY_ROW_LAYOUT[level["code"]]
        sheet.cell(row=rows["label"], column=1, value=level["label"])
        sheet.cell(row=rows["price"], column=1, value="単価")
        sheet.cell(row=rows["students"], column=1, value="受講人数")
        sheet.cell(row=rows["certified"], column=1, value="認証人数(期末)")
        sheet.cell(row=rows["revenue"], column=1, value="売上")

    sheet.cell(row=ACADEMY_ROW_LAYOUT["total_students"], column=1, value="アカデミー合計人数")
    sheet.cell(row=ACADEMY_ROW_LAYOUT["total_revenue"], column=1, value="アカデミー合計売上")

    for column_index, assumption_col in enumerate(_year_columns(), start=2):
        model_col = excel_col(column_index)
        total_students_ref = _sheet_ref("（全Ver）前提条件", f"{assumption_col}{ASSUMPTION_ROWS['academy_students']}")
        effective_price_ref = _sheet_ref("（全Ver）前提条件", f"{assumption_col}{ASSUMPTION_ROWS['academy_effective_price']}")
        raw_students = {
            "c": _academy_raw_student_expr("c", assumption_col, None),
            "b": _academy_raw_student_expr("b", assumption_col, excel_col(column_index - 1) if column_index > 2 else None),
            "a": _academy_raw_student_expr("a", assumption_col, excel_col(column_index - 1) if column_index > 2 else None),
            "s": _academy_raw_student_expr("s", assumption_col, excel_col(column_index - 1) if column_index > 2 else None),
        }
        raw_total = "+".join(f"({expr})" for expr in raw_students.values())

        for level in ACADEMY_LEVELS:
            code = level["code"]
            rows = ACADEMY_ROW_LAYOUT[code]
            students_cell = f"{model_col}{rows['students']}"
            price_cell = f"{model_col}{rows['price']}"
            certified_cell = f"{model_col}{rows['certified']}"
            revenue_cell = f"{model_col}{rows['revenue']}"

            sheet[students_cell] = (
                f"=IF(({raw_total})<>0,{total_students_ref}*({raw_students[code]})/({raw_total}),0)"
            )
            completion_ref = _sheet_ref("（全Ver）前提条件", f"{assumption_col}{ASSUMPTION_ROWS[f'academy_{code}_completion']}")
            certification_ref = _sheet_ref("（全Ver）前提条件", f"{assumption_col}{ASSUMPTION_ROWS[f'academy_{code}_certification']}")
            multiplier_ref = _sheet_ref("（全Ver）前提条件", f"{assumption_col}{ASSUMPTION_ROWS[f'academy_{code}_price_multiplier']}")

            weighted_terms: list[str] = []
            for other in ACADEMY_LEVELS:
                other_code = other["code"]
                other_multiplier_ref = _sheet_ref(
                    "（全Ver）前提条件",
                    f"{assumption_col}{ASSUMPTION_ROWS[f'academy_{other_code}_price_multiplier']}",
                )
                other_students_cell = f"{model_col}{ACADEMY_ROW_LAYOUT[other_code]['students']}"
                weighted_terms.append(f"{other_multiplier_ref}*{other_students_cell}")
            weighted_multiplier = "+".join(weighted_terms)
            sheet[price_cell] = (
                f"=IF(({weighted_multiplier})<>0,{effective_price_ref}*{multiplier_ref}*{total_students_ref}/({weighted_multiplier}),0)"
            )
            sheet[certified_cell] = f"={students_cell}*{completion_ref}*{certification_ref}"
            sheet[revenue_cell] = f"={price_cell}*{students_cell}"

        sheet[f"{model_col}{ACADEMY_ROW_LAYOUT['total_students']}"] = (
            f"=SUM({model_col}{ACADEMY_ROW_LAYOUT['c']['students']},{model_col}{ACADEMY_ROW_LAYOUT['b']['students']},"
            f"{model_col}{ACADEMY_ROW_LAYOUT['a']['students']},{model_col}{ACADEMY_ROW_LAYOUT['s']['students']})"
        )
        sheet[f"{model_col}{ACADEMY_ROW_LAYOUT['total_revenue']}"] = (
            f"=SUM({model_col}{ACADEMY_ROW_LAYOUT['c']['revenue']},{model_col}{ACADEMY_ROW_LAYOUT['b']['revenue']},"
            f"{model_col}{ACADEMY_ROW_LAYOUT['a']['revenue']},{model_col}{ACADEMY_ROW_LAYOUT['s']['revenue']})"
        )
    _style_formula_rows(sheet, [3, 4, 5, 6, 8, 9, 10, 11, 13, 14, 15, 16, 18, 19, 20, 21])
    _style_subtotal_rows(sheet, [ACADEMY_ROW_LAYOUT["total_students"]])
    _style_total_rows(sheet, [ACADEMY_ROW_LAYOUT["total_revenue"]])
    _set_number_format_rows(sheet, [3, 4, 5, 6, 8, 9, 10, 11, 13, 14, 15, 16, 18, 19, 20, 21, ACADEMY_ROW_LAYOUT["total_students"], ACADEMY_ROW_LAYOUT["total_revenue"]], number_format=NUMBER_FORMAT)
    _apply_standard_layout(sheet, freeze_panes="B2", label_width=18, year_width=12)
    _set_row_heights(
        sheet,
        {
            2: 24,
            7: 24,
            12: 24,
            17: 24,
            ACADEMY_ROW_LAYOUT["total_students"]: 24,
            ACADEMY_ROW_LAYOUT["total_revenue"]: 26,
        },
    )


def _write_consulting_sheet(sheet) -> None:
    year_count_columns = [excel_col(column_index) for column_index in range(8, 13)]
    year_revenue_columns = [excel_col(column_index) for column_index in range(13, 18)]
    year_cost_columns = [excel_col(column_index) for column_index in range(18, 23)]

    for column_index, header in enumerate(["SKU", "サービス名", "単位", "単価（円）", "継続率", "デリバリー原価単価", "標準時間"], start=1):
        sheet.cell(row=2, column=column_index, value=header)
        sheet.cell(row=2, column=column_index).font = Font(bold=True)

    for idx, year in enumerate(YEAR_HEADERS):
        sheet.cell(row=1, column=8 + idx, value=f"{year} 件数")
        sheet.cell(row=1, column=13 + idx, value=f"{year} 売上")
        sheet.cell(row=1, column=18 + idx, value=f"{year} 原価")
        sheet.cell(row=1, column=8 + idx).font = BOLD_FONT
        sheet.cell(row=1, column=13 + idx).font = BOLD_FONT
        sheet.cell(row=1, column=18 + idx).font = BOLD_FONT

    unit_price_scale_ref = _sheet_ref("（全Ver）前提条件", f"B{ASSUMPTION_ROWS['consult_unit_price']}")
    retention_ref = _sheet_ref("（全Ver）前提条件", f"B{ASSUMPTION_ROWS['consult_retention']}")
    blended_hourly_rate_ref = _sheet_ref("（全Ver）前提条件", f"B{ASSUMPTION_ROWS['blended_hourly_rate']}")

    for offset, sku in enumerate(CONSULT_SKUS):
        row_index = CONSULT_DETAIL_START_ROW + offset
        sheet.cell(row=row_index, column=1, value=sku["sku"])
        sheet.cell(row=row_index, column=2, value=sku["service_name"])
        sheet.cell(row=row_index, column=3, value=sku["unit"])
        price_multiplier = sku["base_price"] / CONSULT_SKUS[0]["base_price"] if CONSULT_SKUS[0]["base_price"] else 0
        sheet.cell(row=row_index, column=4, value=f"={unit_price_scale_ref}*{price_multiplier}")
        sheet.cell(row=row_index, column=5, value=f"=MIN(1,{retention_ref}*{sku['retention_multiplier']})")
        sheet.cell(row=row_index, column=7, value=sku["standard_hours"])
        sheet.cell(row=row_index, column=6, value=f"=G{row_index}*{blended_hourly_rate_ref}")

        for year_idx, year_col in enumerate(_year_columns()):
            share_row = ASSUMPTION_ROWS[f"consult_{sku['sku'].lower()}_share"]
            share_ref = _sheet_ref(
                "（全Ver）前提条件",
                f"{year_col}{share_row}",
            )
            target_revenue_ref = _sheet_ref("（全Ver）前提条件", f"{year_col}{ASSUMPTION_ROWS['consult_revenue']}")
            count_col = year_count_columns[year_idx]
            revenue_col = year_revenue_columns[year_idx]
            cost_col = year_cost_columns[year_idx]
            sheet[f"{count_col}{row_index}"] = f"=IF($D{row_index}<>0,({target_revenue_ref}*{share_ref})/$D{row_index},0)"
            sheet[f"{revenue_col}{row_index}"] = f"={count_col}{row_index}*$D{row_index}"
            sheet[f"{cost_col}{row_index}"] = f"={count_col}{row_index}*$F{row_index}"

    sheet.cell(row=CONSULT_TOTAL_REVENUE_ROW, column=1, value="コンサル売上合計")
    sheet.cell(row=CONSULT_TOTAL_DELIVERY_ROW, column=1, value="デリバリー原価合計")
    sheet.cell(row=CONSULT_TOTAL_GROSS_PROFIT_ROW, column=1, value="コンサル粗利")
    for column_index, model_col in enumerate(_year_columns(), start=13):
        summary_col = excel_col(column_index - 11)
        cost_col = excel_col(column_index + 5)
        revenue_col = excel_col(column_index)
        sheet[f"{summary_col}{CONSULT_TOTAL_REVENUE_ROW}"] = f"=SUM({revenue_col}{CONSULT_DETAIL_START_ROW}:{revenue_col}{CONSULT_DETAIL_START_ROW + len(CONSULT_SKUS) - 1})"
        sheet[f"{summary_col}{CONSULT_TOTAL_DELIVERY_ROW}"] = f"=SUM({cost_col}{CONSULT_DETAIL_START_ROW}:{cost_col}{CONSULT_DETAIL_START_ROW + len(CONSULT_SKUS) - 1})"
        sheet[f"{summary_col}{CONSULT_TOTAL_GROSS_PROFIT_ROW}"] = f"={summary_col}{CONSULT_TOTAL_REVENUE_ROW}-{summary_col}{CONSULT_TOTAL_DELIVERY_ROW}"
    for row_index in range(CONSULT_DETAIL_START_ROW, CONSULT_DETAIL_START_ROW + len(CONSULT_SKUS)):
        _apply_row_style(sheet, row_index, 4, 6, fill=FORMULA_FILL)
        _apply_row_style(sheet, row_index, 8, 22, fill=FORMULA_FILL)
    _style_subtotal_rows(sheet, [CONSULT_TOTAL_REVENUE_ROW, CONSULT_TOTAL_DELIVERY_ROW], start_col=1, end_col=17)
    _style_total_rows(sheet, [CONSULT_TOTAL_GROSS_PROFIT_ROW], start_col=1, end_col=17)
    for row_index in range(CONSULT_DETAIL_START_ROW, CONSULT_DETAIL_START_ROW + len(CONSULT_SKUS)):
        _set_number_format_rows(sheet, [row_index], number_format=NUMBER_FORMAT, start_col=4, end_col=4)
        _set_number_format_rows(sheet, [row_index], number_format=PERCENT_FORMAT, start_col=5, end_col=5)
        _set_number_format_rows(sheet, [row_index], number_format=NUMBER_FORMAT, start_col=6, end_col=7)
        _set_number_format_rows(sheet, [row_index], number_format=COUNT_DECIMAL_FORMAT, start_col=8, end_col=12)
        _set_number_format_rows(sheet, [row_index], number_format=NUMBER_FORMAT, start_col=13, end_col=22)
    _set_number_format_rows(sheet, [CONSULT_TOTAL_REVENUE_ROW, CONSULT_TOTAL_DELIVERY_ROW, CONSULT_TOTAL_GROSS_PROFIT_ROW], number_format=NUMBER_FORMAT)
    sheet.freeze_panes = "A3"
    _set_column_widths(
        sheet,
        {
            "A": 10,
            "B": 28,
            "C": 12,
            "D": 14,
            "E": 12,
            "F": 16,
            "G": 12,
            "H": 12,
            "I": 12,
            "J": 12,
            "K": 12,
            "L": 12,
            "M": 14,
            "N": 14,
            "O": 14,
            "P": 14,
            "Q": 14,
            "R": 14,
            "S": 14,
            "T": 14,
            "U": 14,
            "V": 14,
        },
    )
    _set_row_heights(sheet, {1: 22, 2: 22, CONSULT_TOTAL_REVENUE_ROW: 24, CONSULT_TOTAL_DELIVERY_ROW: 24, CONSULT_TOTAL_GROSS_PROFIT_ROW: 26})
    for row_index in range(CONSULT_DETAIL_START_ROW, CONSULT_DETAIL_START_ROW + len(CONSULT_SKUS)):
        sheet.row_dimensions[row_index].height = 32
    _align_range(sheet, start_row=1, end_row=sheet.max_row, start_col=1, end_col=1, alignment=LEFT_ALIGN)
    _align_range(sheet, start_row=1, end_row=sheet.max_row, start_col=2, end_col=2, alignment=WRAP_LEFT_ALIGN)
    _align_range(sheet, start_row=1, end_row=sheet.max_row, start_col=3, end_col=22, alignment=RIGHT_ALIGN)


def _write_cost_plan_sheet(sheet, assumptions: dict[str, list[float]]) -> None:
    sheet.cell(row=COST_PLAN_ROWS["summary_title"], column=1, value="費用サマリー")
    _apply_row_style(sheet, COST_PLAN_ROWS["summary_title"], 1, 6, fill=SUBTOTAL_FILL, font=BOLD_FONT)
    sheet.cell(row=COST_PLAN_ROWS["summary_header"], column=1, value="項目")
    sheet.cell(row=COST_PLAN_ROWS["summary_header"], column=1).font = BOLD_FONT
    for column_index, header in enumerate(YEAR_HEADERS, start=2):
        sheet.cell(row=COST_PLAN_ROWS["summary_header"], column=column_index, value=header)
        sheet.cell(row=COST_PLAN_ROWS["summary_header"], column=column_index).font = BOLD_FONT
    labels = {
        COST_SUMMARY_ROWS["personnel_cost"]: "人件費",
        COST_SUMMARY_ROWS["marketing_cost"]: "マーケ費",
        COST_SUMMARY_ROWS["development_cost"]: "開発費（PL計上・償却）",
        COST_SUMMARY_ROWS["other_opex"]: "その他OPEX",
        COST_SUMMARY_ROWS["opex_total"]: "OPEX合計",
    }
    for row_index, label in labels.items():
        sheet.cell(row=row_index, column=1, value=label)

    ratio_map = {
        COST_SUMMARY_ROWS["personnel_cost"]: "personnel_ratio",
        COST_SUMMARY_ROWS["marketing_cost"]: "marketing_ratio",
        COST_SUMMARY_ROWS["development_cost"]: "development_ratio",
        COST_SUMMARY_ROWS["other_opex"]: "other_ratio",
    }
    for column_index, assumption_col in enumerate(_year_columns(), start=2):
        model_col = excel_col(column_index)
        opex_ref = _sheet_ref("（全Ver）前提条件", f"{assumption_col}{ASSUMPTION_ROWS['opex_target']}")
        personnel_ratio_ref = _sheet_ref("（全Ver）前提条件", f"{assumption_col}{ASSUMPTION_ROWS['personnel_ratio']}")
        marketing_ratio_ref = _sheet_ref("（全Ver）前提条件", f"{assumption_col}{ASSUMPTION_ROWS['marketing_ratio']}")
        other_ratio_ref = _sheet_ref("（全Ver）前提条件", f"{assumption_col}{ASSUMPTION_ROWS['other_ratio']}")
        development_amortization_ref = _sheet_ref(
            "（全Ver）前提条件",
            f"{assumption_col}{ASSUMPTION_ROWS['development_amortization_expense']}",
        )
        for row_index, ratio_key in ratio_map.items():
            ratio_ref = {
                "personnel_ratio": personnel_ratio_ref,
                "marketing_ratio": marketing_ratio_ref,
                "development_ratio": development_amortization_ref,
                "other_ratio": other_ratio_ref,
            }[ratio_key]
            if ratio_key == "development_ratio":
                sheet[f"{model_col}{row_index}"] = f"={ratio_ref}"
            else:
                sheet[f"{model_col}{row_index}"] = f"={opex_ref}*{ratio_ref}"
        sheet[f"{model_col}{COST_SUMMARY_ROWS['opex_total']}"] = (
            f"=SUM({model_col}{COST_SUMMARY_ROWS['personnel_cost']}:{model_col}{COST_SUMMARY_ROWS['other_opex']})"
        )
    _style_subtotal_rows(
        sheet,
        [
            COST_SUMMARY_ROWS["personnel_cost"],
            COST_SUMMARY_ROWS["marketing_cost"],
            COST_SUMMARY_ROWS["development_cost"],
            COST_SUMMARY_ROWS["other_opex"],
        ],
    )
    _style_total_rows(sheet, [COST_SUMMARY_ROWS["opex_total"]])
    _set_number_format_rows(
        sheet,
        [
            COST_SUMMARY_ROWS["personnel_cost"],
            COST_SUMMARY_ROWS["marketing_cost"],
            COST_SUMMARY_ROWS["development_cost"],
            COST_SUMMARY_ROWS["other_opex"],
            COST_SUMMARY_ROWS["opex_total"],
        ],
        number_format=NUMBER_FORMAT,
    )
    sheet.cell(row=COST_PLAN_ROWS["amortization_title"], column=1, value="開発償却ブロック")
    _apply_row_style(sheet, COST_PLAN_ROWS["amortization_title"], 1, 7, fill=SUBTOTAL_FILL, font=BOLD_FONT)
    amortization_labels = {
        COST_PLAN_ROWS["amortization_start"]: "開発投資（キャッシュ）",
        COST_PLAN_ROWS["amortization_start"] + 1: "償却方法",
        COST_PLAN_ROWS["amortization_start"] + 2: "償却期間（年）",
        COST_PLAN_ROWS["amortization_start"] + 3: "当期償却額（PL計上）",
        COST_PLAN_ROWS["amortization_start"] + 4: "当期投資の期末未償却残高",
    }
    for row_index, label in amortization_labels.items():
        sheet.cell(row=row_index, column=1, value=label)
    for column_index, assumption_col in enumerate(_year_columns(), start=2):
        model_col = excel_col(column_index)
        development_investment_ref = _sheet_ref(
            "（全Ver）前提条件",
            f"{assumption_col}{ASSUMPTION_ROWS['development_investment']}",
        )
        development_expense_ref = _sheet_ref(
            "（全Ver）前提条件",
            f"{assumption_col}{ASSUMPTION_ROWS['development_amortization_expense']}",
        )
        development_unamortized_ref = _sheet_ref(
            "（全Ver）前提条件",
            f"{assumption_col}{ASSUMPTION_ROWS['development_unamortized_balance']}",
        )
        sheet[f"{model_col}{COST_PLAN_ROWS['amortization_start'] + 1}"] = "定額法"
        sheet[f"{model_col}{COST_PLAN_ROWS['amortization_start']}"] = f"={development_investment_ref}"
        sheet[f"{model_col}{COST_PLAN_ROWS['amortization_start'] + 2}"] = assumptions["development_amortization_years"][column_index - 2]
        sheet[f"{model_col}{COST_PLAN_ROWS['amortization_start'] + 3}"] = f"={development_expense_ref}"
        sheet[f"{model_col}{COST_PLAN_ROWS['amortization_start'] + 4}"] = f"={development_unamortized_ref}"
    _style_formula_rows(
        sheet,
        [
            COST_PLAN_ROWS["amortization_start"],
            COST_PLAN_ROWS["amortization_start"] + 3,
            COST_PLAN_ROWS["amortization_start"] + 4,
        ],
    )
    _style_input_rows(sheet, [COST_PLAN_ROWS["amortization_start"] + 2])
    _set_number_format_rows(
        sheet,
        [COST_PLAN_ROWS["amortization_start"], COST_PLAN_ROWS["amortization_start"] + 3, COST_PLAN_ROWS["amortization_start"] + 4],
        number_format=NUMBER_FORMAT,
    )
    _set_number_format_rows(sheet, [COST_PLAN_ROWS["amortization_start"] + 2], number_format=NUMBER_FORMAT)
    sheet.cell(row=COST_PLAN_ROWS["detail_title"], column=1, value="費用明細")
    _apply_row_style(sheet, COST_PLAN_ROWS["detail_title"], 1, 7, fill=SUBTOTAL_FILL, font=BOLD_FONT)
    detail_header_row = COST_PLAN_ROWS["detail_header"]
    sheet.cell(row=detail_header_row, column=1, value="アイテム")
    for column_index, header in enumerate(YEAR_HEADERS, start=2):
        sheet.cell(row=detail_header_row, column=column_index, value=header)
    sheet.cell(row=detail_header_row, column=7, value="カテゴリ")
    sheet["A10"].font = Font(bold=True)
    sheet["G10"].font = Font(bold=True)
    for column_index in range(2, 7):
        sheet.cell(row=detail_header_row, column=column_index).font = Font(bold=True)

    for row_index, (item_name, category_name, share, cost_key) in enumerate(COST_LIST_ROWS, start=COST_PLAN_ROWS["detail_start"]):
        sheet.cell(row=row_index, column=1, value=item_name)
        sheet.cell(row=row_index, column=7, value=category_name)
        cost_row = COST_SUMMARY_ROWS[cost_key]
        for column_index in range(2, 7):
            model_col = excel_col(column_index)
            sheet[f"{model_col}{row_index}"] = f"={_sheet_ref('費用計画', f'{model_col}{cost_row}')}*{share}"
    for row_index in range(COST_PLAN_ROWS["detail_start"], COST_PLAN_ROWS["detail_start"] + len(COST_LIST_ROWS)):
        _apply_row_style(sheet, row_index, 2, 6, fill=FORMULA_FILL)
        _set_number_format_rows(sheet, [row_index], number_format=NUMBER_FORMAT, start_col=2, end_col=6)
    _apply_standard_layout(sheet, freeze_panes="B2", label_width=22, year_width=12)
    _set_column_widths(sheet, {"A": 24, "B": 12, "C": 12, "D": 12, "E": 12, "F": 12, "G": 14})
    _set_row_heights(
        sheet,
        {
            COST_SUMMARY_ROWS["opex_total"]: 24,
            COST_PLAN_ROWS["summary_title"]: 24,
            COST_PLAN_ROWS["amortization_title"]: 24,
            COST_PLAN_ROWS["detail_title"]: 24,
        },
    )
    _align_range(sheet, start_row=1, end_row=sheet.max_row, start_col=1, end_col=1, alignment=LEFT_ALIGN)
    _align_range(sheet, start_row=1, end_row=sheet.max_row, start_col=2, end_col=6, alignment=RIGHT_ALIGN)
    _align_range(sheet, start_row=1, end_row=sheet.max_row, start_col=7, end_col=7, alignment=LEFT_ALIGN)


def _write_plan_assumptions_sheet(sheet, assumptions: dict[str, list[float]]) -> None:
    sheet.cell(row=1, column=1, value="項目")
    for column_index, header in enumerate(YEAR_HEADERS, start=2):
        sheet.cell(row=1, column=column_index, value=header)
    sheet.cell(row=1, column=7, value="説明")
    for cell in ("A1", "G1", "B1", "C1", "D1", "E1", "F1"):
        sheet[cell].font = Font(bold=True)

    row_specs = [
        ("revenue_target", "売上目標", "candidate の PL 売上系列"),
        ("gross_profit_target", "粗利目標", "candidate の PL 粗利系列"),
        ("opex_target", "OPEX目標", "candidate の PL OPEX 系列"),
        ("academy_public_price", "アカデミー公開単価", "抽出または補完した公開単価"),
        ("academy_students", "アカデミー受講人数", "抽出した受講人数系列"),
        ("academy_certified", "アカデミー認証人数", "抽出した認証人数系列"),
        ("academy_revenue", "アカデミー売上目標", "抽出または trend 補完した売上系列"),
        ("academy_effective_price", "アカデミー実効単価", "売上目標 ÷ 受講人数"),
        ("meal_price_per_item", "ミール価格/アイテム", "industry 補完または抽出値"),
        ("meal_items_per_meal", "ミールアイテム/食事", "industry 補完または抽出値"),
        ("meal_meals_per_year", "ミール食事数/年", "industry 補完または抽出値"),
        ("meal_retention_rate", "ミール継続率", "industry 補完または抽出値"),
        ("meal_share_non_academy", "ミール残余売上比率", "非アカデミー残余売上に対するミール比率の透明な仮定"),
        ("meal_unit_count", "ミール推定ユニット数", "残余売上比率から逆算した推定ユニット数"),
        ("meal_revenue", "ミール売上", "ユニットエコノミクスから計算した売上"),
        ("consult_unit_price", "コンサルSKU単価", "benchmark または抽出値"),
        ("consult_retention", "コンサル継続率", "benchmark または抽出値"),
        ("consult_standard_hours", "コンサル標準工数", "benchmark または抽出値"),
        ("consult_revenue", "コンサル売上", "総売上の残余から計算した売上"),
        ("consult_project_count", "コンサル推定案件数", "コンサル売上 ÷ SKU単価"),
        ("gross_margin_ratio", "粗利率", "粗利目標 ÷ 売上目標"),
        ("personnel_ratio", "人件費比率", "OPEX のうち人件費の比率"),
        ("marketing_ratio", "マーケ費比率", "OPEX のうちマーケ費の比率"),
        ("development_ratio", "開発費比率", "OPEX のうち開発費の比率"),
        ("other_ratio", "その他費用比率", "OPEX のうちその他費用の比率"),
        ("development_investment", "開発投資額（キャッシュ）", "PL計上する開発償却費と償却年数から逆算した投資額"),
        ("development_amortization_years", "開発償却期間（年）", "開発投資の初期値。定額法で5年償却"),
        ("development_amortization_expense", "PL計上開発費（償却）", "OPEX比率から計算した当期の償却費"),
        ("development_unamortized_balance", "開発投資の期末未償却残高", "当期投資額から当期償却額を差し引いた残高"),
        ("academy_c_share", "C級新規構成比", "アカデミー総受講人数のうち C級に配分する比率"),
        ("academy_b_share", "B級新規構成比", "アカデミー総受講人数のうち B級に配分する比率"),
        ("academy_a_share", "A級新規構成比", "アカデミー総受講人数のうち A級に配分する比率"),
        ("academy_s_share", "S級新規構成比", "アカデミー総受講人数のうち S級に配分する比率"),
        ("academy_c_to_b", "C→B進級率", "前年度のC級認証者がB級へ進む比率"),
        ("academy_b_to_a", "B→A進級率", "前年度のB級認証者がA級へ進む比率"),
        ("academy_a_to_s", "A→S進級率", "前年度のA級認証者がS級へ進む比率"),
        ("academy_c_price_multiplier", "C級価格倍率", "アカデミー実効単価に対する C級倍率"),
        ("academy_b_price_multiplier", "B級価格倍率", "アカデミー実効単価に対する B級倍率"),
        ("academy_a_price_multiplier", "A級価格倍率", "アカデミー実効単価に対する A級倍率"),
        ("academy_s_price_multiplier", "S級価格倍率", "アカデミー実効単価に対する S級倍率"),
        ("academy_c_completion", "C級修了率", "C級の修了率仮定"),
        ("academy_c_certification", "C級認証率", "C級の認証率仮定"),
        ("academy_b_completion", "B級修了率", "B級の修了率仮定"),
        ("academy_b_certification", "B級認証率", "B級の認証率仮定"),
        ("academy_a_completion", "A級修了率", "A級の修了率仮定"),
        ("academy_a_certification", "A級認証率", "A級の認証率仮定"),
        ("academy_s_completion", "S級修了率", "S級の修了率仮定"),
        ("academy_s_certification", "S級認証率", "S級の認証率仮定"),
        ("blended_hourly_rate", "ブレンド時給", "コンサルのデリバリー原価に使う透明な時給仮定"),
        ("consult_p1_share", "P1売上構成比", "コンサル売上のうち P1 に配分する比率"),
        ("consult_p2_share", "P2売上構成比", "コンサル売上のうち P2 に配分する比率"),
        ("consult_p3_share", "P3売上構成比", "コンサル売上のうち P3 に配分する比率"),
        ("consult_p4_share", "P4売上構成比", "コンサル売上のうち P4 に配分する比率"),
        ("consult_p5_share", "P5売上構成比", "コンサル売上のうち P5 に配分する比率"),
        ("consult_p6_share", "P6売上構成比", "コンサル売上のうち P6 に配分する比率"),
        ("consult_p8_share", "P8売上構成比", "コンサル売上のうち P8 に配分する比率"),
        ("consult_p9_share", "P9売上構成比", "コンサル売上のうち P9 に配分する比率"),
        ("consult_p10_share", "P10売上構成比", "コンサル売上のうち P10 に配分する比率"),
        ("consult_p11_share", "P11売上構成比", "コンサル売上のうち P11 に配分する比率"),
        ("consult_p12_share", "P12売上構成比", "コンサル売上のうち P12 に配分する比率"),
    ]

    for key, label, description in row_specs:
        row_index = ASSUMPTION_ROWS[key]
        sheet.cell(row=row_index, column=1, value=label)
        sheet.cell(row=row_index, column=7, value=description)

    for key, series in assumptions.items():
        row_index = ASSUMPTION_ROWS[key]
        for column_index, value in enumerate(series, start=2):
            sheet.cell(row=row_index, column=column_index, value=value)

    for column_index, year_col in enumerate(_year_columns(), start=2):
        col = excel_col(column_index)
        sheet[f"{col}{ASSUMPTION_ROWS['academy_effective_price']}"] = (
            f"=IF({col}{ASSUMPTION_ROWS['academy_students']}<>0,{col}{ASSUMPTION_ROWS['academy_revenue']}/{col}{ASSUMPTION_ROWS['academy_students']},0)"
        )
        sheet[f"{col}{ASSUMPTION_ROWS['meal_unit_count']}"] = (
            f"=MAX(0,(({col}{ASSUMPTION_ROWS['revenue_target']}-{col}{ASSUMPTION_ROWS['academy_revenue']})*"
            f"{col}{ASSUMPTION_ROWS['meal_share_non_academy']})/"
            f"({col}{ASSUMPTION_ROWS['meal_price_per_item']}*{col}{ASSUMPTION_ROWS['meal_items_per_meal']}*{col}{ASSUMPTION_ROWS['meal_meals_per_year']}))"
        )
        sheet[f"{col}{ASSUMPTION_ROWS['meal_revenue']}"] = (
            f"={col}{ASSUMPTION_ROWS['meal_price_per_item']}*{col}{ASSUMPTION_ROWS['meal_items_per_meal']}*"
            f"{col}{ASSUMPTION_ROWS['meal_meals_per_year']}*{col}{ASSUMPTION_ROWS['meal_unit_count']}"
        )
        sheet[f"{col}{ASSUMPTION_ROWS['consult_revenue']}"] = (
            f"=MAX(0,{col}{ASSUMPTION_ROWS['revenue_target']}-{col}{ASSUMPTION_ROWS['academy_revenue']}-{col}{ASSUMPTION_ROWS['meal_revenue']})"
        )
        sheet[f"{col}{ASSUMPTION_ROWS['consult_project_count']}"] = (
            f"=IF({col}{ASSUMPTION_ROWS['consult_unit_price']}<>0,{col}{ASSUMPTION_ROWS['consult_revenue']}/{col}{ASSUMPTION_ROWS['consult_unit_price']},0)"
        )
        sheet[f"{col}{ASSUMPTION_ROWS['gross_margin_ratio']}"] = (
            f"=IF({col}{ASSUMPTION_ROWS['revenue_target']}<>0,{col}{ASSUMPTION_ROWS['gross_profit_target']}/{col}{ASSUMPTION_ROWS['revenue_target']},0)"
        )
        sheet[f"{col}{ASSUMPTION_ROWS['development_amortization_expense']}"] = (
            f"={col}{ASSUMPTION_ROWS['opex_target']}*{col}{ASSUMPTION_ROWS['development_ratio']}"
        )
        sheet[f"{col}{ASSUMPTION_ROWS['development_investment']}"] = (
            f"={col}{ASSUMPTION_ROWS['development_amortization_expense']}*{col}{ASSUMPTION_ROWS['development_amortization_years']}"
        )
        sheet[f"{col}{ASSUMPTION_ROWS['development_unamortized_balance']}"] = (
            f"=MAX(0,{col}{ASSUMPTION_ROWS['development_investment']}-{col}{ASSUMPTION_ROWS['development_amortization_expense']})"
        )
    derived_rows = [
        ASSUMPTION_ROWS["academy_effective_price"],
        ASSUMPTION_ROWS["meal_unit_count"],
        ASSUMPTION_ROWS["meal_revenue"],
        ASSUMPTION_ROWS["consult_revenue"],
        ASSUMPTION_ROWS["consult_project_count"],
        ASSUMPTION_ROWS["gross_margin_ratio"],
        ASSUMPTION_ROWS["development_investment"],
        ASSUMPTION_ROWS["development_amortization_expense"],
        ASSUMPTION_ROWS["development_unamortized_balance"],
    ]
    input_rows = [
        row_index
        for row_key, row_index in ASSUMPTION_ROWS.items()
        if row_key
        not in {
            "academy_effective_price",
            "meal_unit_count",
            "meal_revenue",
            "consult_revenue",
            "consult_project_count",
            "gross_margin_ratio",
            "development_investment",
            "development_amortization_expense",
            "development_unamortized_balance",
        }
    ]
    _style_input_rows(sheet, input_rows)
    _style_formula_rows(sheet, derived_rows)
    percentage_rows = [
        ASSUMPTION_ROWS["meal_retention_rate"],
        ASSUMPTION_ROWS["consult_retention"],
        ASSUMPTION_ROWS["gross_margin_ratio"],
        ASSUMPTION_ROWS["personnel_ratio"],
        ASSUMPTION_ROWS["marketing_ratio"],
        ASSUMPTION_ROWS["development_ratio"],
        ASSUMPTION_ROWS["other_ratio"],
        ASSUMPTION_ROWS["academy_c_share"],
        ASSUMPTION_ROWS["academy_b_share"],
        ASSUMPTION_ROWS["academy_a_share"],
        ASSUMPTION_ROWS["academy_s_share"],
        ASSUMPTION_ROWS["academy_c_to_b"],
        ASSUMPTION_ROWS["academy_b_to_a"],
        ASSUMPTION_ROWS["academy_a_to_s"],
        ASSUMPTION_ROWS["academy_c_completion"],
        ASSUMPTION_ROWS["academy_c_certification"],
        ASSUMPTION_ROWS["academy_b_completion"],
        ASSUMPTION_ROWS["academy_b_certification"],
        ASSUMPTION_ROWS["academy_a_completion"],
        ASSUMPTION_ROWS["academy_a_certification"],
        ASSUMPTION_ROWS["academy_s_completion"],
        ASSUMPTION_ROWS["academy_s_certification"],
    ]
    decimal_count_rows = [ASSUMPTION_ROWS["consult_project_count"]]
    integer_input_rows = [ASSUMPTION_ROWS["development_amortization_years"]]
    for row_index in input_rows + derived_rows:
        fmt = PERCENT_FORMAT if row_index in percentage_rows else NUMBER_FORMAT
        if row_index in decimal_count_rows:
            fmt = COUNT_DECIMAL_FORMAT
        if row_index in integer_input_rows:
            fmt = NUMBER_FORMAT
        _set_number_format_rows(sheet, [row_index], number_format=fmt)
    sheet.freeze_panes = "B2"
    _set_column_widths(
        sheet,
        {
            "A": 20,
            "B": 12,
            "C": 12,
            "D": 12,
            "E": 12,
            "F": 12,
            "G": 34,
        },
    )
    _set_row_heights(sheet, {1: 22})
    _align_range(sheet, start_row=1, end_row=sheet.max_row, start_col=1, end_col=1, alignment=LEFT_ALIGN)
    _align_range(sheet, start_row=1, end_row=sheet.max_row, start_col=2, end_col=6, alignment=RIGHT_ALIGN)
    _align_range(sheet, start_row=1, end_row=sheet.max_row, start_col=7, end_col=7, alignment=WRAP_LEFT_ALIGN)


def _academy_raw_student_expr(code: str, assumption_col: str, previous_model_col: str | None) -> str:
    total_students_ref = _sheet_ref("（全Ver）前提条件", f"{assumption_col}{ASSUMPTION_ROWS['academy_students']}")
    share_ref = _sheet_ref("（全Ver）前提条件", f"{assumption_col}{ASSUMPTION_ROWS[f'academy_{code}_share']}")
    base_expr = f"{total_students_ref}*{share_ref}"
    if previous_model_col is None:
        return base_expr

    if code == "b":
        previous_ref = f"{previous_model_col}{ACADEMY_ROW_LAYOUT['c']['certified']}"
        progression_ref = _sheet_ref("（全Ver）前提条件", f"{assumption_col}{ASSUMPTION_ROWS['academy_c_to_b']}")
        return f"{base_expr}+{previous_ref}*{progression_ref}"
    if code == "a":
        previous_ref = f"{previous_model_col}{ACADEMY_ROW_LAYOUT['b']['certified']}"
        progression_ref = _sheet_ref("（全Ver）前提条件", f"{assumption_col}{ASSUMPTION_ROWS['academy_b_to_a']}")
        return f"{base_expr}+{previous_ref}*{progression_ref}"
    if code == "s":
        previous_ref = f"{previous_model_col}{ACADEMY_ROW_LAYOUT['a']['certified']}"
        progression_ref = _sheet_ref("（全Ver）前提条件", f"{assumption_col}{ASSUMPTION_ROWS['academy_a_to_s']}")
        return f"{base_expr}+{previous_ref}*{progression_ref}"
    return base_expr


def _write_assumptions_sheet(sheet, assumptions: list[dict[str, Any]]) -> None:
    headers = ["source_type", "review_status", "evidence_count", "evidence_ids"]
    for column_index, header in enumerate(headers, start=1):
        sheet.cell(row=1, column=column_index, value=header)
        sheet.cell(row=1, column=column_index).font = Font(bold=True)

    for row_index, assumption in enumerate(assumptions, start=2):
        evidence_refs = assumption.get("evidence_refs", [])
        evidence_ids = ", ".join(
            ref.get("source_id") or ref.get("title") or ""
            for ref in evidence_refs
            if ref.get("source_id") or ref.get("title")
        )
        values = [
            assumption.get("source_type", ""),
            assumption.get("review_status", ""),
            len(evidence_refs),
            evidence_ids,
        ]
        for column_index, value in enumerate(values, start=1):
            sheet.cell(row=row_index, column=column_index, value=value)


def _write_artifacts_sheet(sheet, *, run_root: Path, candidate_id: str) -> None:
    rows = [
        ["run_root", str(run_root)],
        ["summary", str(run_root / "summary.md")],
        ["scores", str(run_root / "scores.json")],
        ["diagnosis", str(run_root / "diagnosis.json")],
        ["candidate_json", str(run_root / "candidates" / f"{candidate_id}.json")],
        ["reference", str(run_root / "reference.json")],
        ["baseline", str(run_root / "baseline.json")],
    ]
    _write_key_value_rows(sheet, rows)


def _write_section_title(sheet, row_index: int, title: str) -> int:
    sheet.cell(row=row_index, column=1, value=title)
    _apply_row_style(sheet, row_index, 1, 4, fill=SUBTOTAL_FILL, font=BOLD_FONT)
    return row_index + 1


def _write_labeled_values(
    sheet,
    row_index: int,
    rows: list[tuple[str, Any]],
    *,
    numeric_labels: set[str] | None = None,
) -> int:
    numeric_labels = numeric_labels or set()
    for label, value in rows:
        sheet.cell(row=row_index, column=1, value=label)
        target_col = 2 if label in numeric_labels else 4
        sheet.cell(row=row_index, column=target_col, value=value)
        row_index += 1
    return row_index


def _write_score_table(sheet, row_index: int, score: dict[str, Any], baseline_total: float) -> int:
    headers = ["項目", "スコア", "差分", "補足"]
    for column_index, header in enumerate(headers, start=1):
        sheet.cell(row=row_index, column=column_index, value=header)
        sheet.cell(row=row_index, column=column_index).font = BOLD_FONT
    row_index += 1
    total = score.get("total", 0.0)
    total_delta = score.get("delta_vs_baseline", round(total - baseline_total, 4))
    score_rows = [("total", total, total_delta, "総合評価")]
    for layer_name, layer_payload in score.get("layers", {}).items():
        score_rows.append((layer_name, layer_payload.get("value", 0.0), layer_payload.get("delta", 0.0), "個別評価"))
    for label, value, delta, note in score_rows:
        sheet.cell(row=row_index, column=1, value=label)
        sheet.cell(row=row_index, column=2, value=value)
        sheet.cell(row=row_index, column=3, value=delta)
        sheet.cell(row=row_index, column=4, value=note)
        sheet.cell(row=row_index, column=2).number_format = "0.0000"
        sheet.cell(row=row_index, column=3).number_format = "+0.0000;-0.0000;0.0000"
        row_index += 1
    return row_index


def _write_assumption_table(sheet, row_index: int, assumptions: list[dict[str, Any]]) -> int:
    headers = ["source_type", "review_status", "evidence_count", "evidence_ids"]
    for column_index, header in enumerate(headers, start=1):
        sheet.cell(row=row_index, column=column_index, value=header)
        sheet.cell(row=row_index, column=column_index).font = BOLD_FONT
    row_index += 1
    if not assumptions:
        sheet.cell(row=row_index, column=1, value="前提データなし")
        return row_index + 1
    for assumption in assumptions:
        evidence_refs = assumption.get("evidence_refs", [])
        evidence_ids = ", ".join(
            ref.get("source_id") or ref.get("title") or ""
            for ref in evidence_refs
            if ref.get("source_id") or ref.get("title")
        )
        sheet.cell(row=row_index, column=1, value=assumption.get("source_type", ""))
        sheet.cell(row=row_index, column=2, value=assumption.get("review_status", ""))
        sheet.cell(row=row_index, column=3, value=len(evidence_refs))
        sheet.cell(row=row_index, column=4, value=evidence_ids)
        row_index += 1
    return row_index


def _write_bullet_list(sheet, row_index: int, lines: list[str]) -> int:
    for line in lines:
        sheet.cell(row=row_index, column=1, value="・")
        sheet.cell(row=row_index, column=4, value=line)
        row_index += 1
    return row_index


def _write_iteration_trend_table(sheet, row_index: int, iteration_summaries: list[dict[str, Any]]) -> int:
    headers = ["回", "候補", "仮説", "検証結果", "総合", "差分", "次の施策"]
    for column_index, header in enumerate(headers, start=1):
        sheet.cell(row=row_index, column=column_index, value=header)
        sheet.cell(row=row_index, column=column_index).font = BOLD_FONT
    row_index += 1
    for item in iteration_summaries:
        sheet.cell(row=row_index, column=1, value=item.get("iteration"))
        sheet.cell(row=row_index, column=2, value=item.get("candidate_id", ""))
        sheet.cell(row=row_index, column=3, value=item.get("hypothesis", ""))
        sheet.cell(row=row_index, column=4, value=item.get("result", ""))
        sheet.cell(row=row_index, column=5, value=item.get("total_score", 0.0))
        sheet.cell(row=row_index, column=6, value=item.get("delta_vs_baseline", 0.0))
        sheet.cell(row=row_index, column=7, value=item.get("next_action", ""))
        sheet.cell(row=row_index, column=5).number_format = "0.0000"
        sheet.cell(row=row_index, column=6).number_format = "+0.0000;-0.0000;0.0000"
        row_index += 1
    return row_index


def _build_workbook_assumptions(candidate_payload: dict[str, Any]) -> dict[str, list[float]]:
    model_sheets = candidate_payload.get("model_sheets", {})
    academy = model_sheets.get("アカデミー", {})
    meal = model_sheets.get("ミール", {})
    consult = model_sheets.get("コンサル", {})
    pl_lines = candidate_payload.get("pl_lines", {})

    revenue_target = _normalize_series(pl_lines.get("売上", []), default=0.0)
    gross_profit_target = _normalize_series(pl_lines.get("粗利", []), default=0.0)
    opex_target = _normalize_series(pl_lines.get("事業運営費（OPEX）", []), default=0.0)

    academy_price = _normalize_series(academy.get("academy_price", []), default=0.0)
    academy_students = _normalize_series(academy.get("academy_students", []), default=0.0)
    academy_certified = _normalize_series(academy.get("academy_certified", []), default=0.0)
    academy_revenue = _normalize_series(
        academy.get("academy_revenue", []),
        default=0.0,
        fallback=_series_product(academy_price, academy_students),
    )

    meal_price = _normalize_series(meal.get("price_per_item", []), default=0.0)
    meal_items = _normalize_series(meal.get("items_per_meal", []), default=1.0)
    meal_meals = _normalize_series(meal.get("meals_per_year", []), default=0.0)
    meal_retention = _normalize_series(meal.get("retention_rate", []), default=0.0)

    consult_price = _normalize_series(consult.get("sku_unit_price", []), default=0.0)
    consult_retention = _normalize_series(consult.get("sku_retention", []), default=0.0)
    consult_standard_hours = _normalize_series(consult.get("sku_standard_hours", []), default=0.0)
    assumptions = {
        "revenue_target": revenue_target,
        "gross_profit_target": gross_profit_target,
        "opex_target": opex_target,
        "academy_public_price": academy_price,
        "academy_students": academy_students,
        "academy_certified": academy_certified,
        "academy_revenue": academy_revenue,
        "meal_price_per_item": meal_price,
        "meal_items_per_meal": meal_items,
        "meal_meals_per_year": meal_meals,
        "meal_retention_rate": meal_retention,
        "meal_share_non_academy": [0.15] * len(YEAR_HEADERS),
        "consult_unit_price": consult_price,
        "consult_retention": consult_retention,
        "consult_standard_hours": consult_standard_hours,
        "personnel_ratio": [0.45] * len(YEAR_HEADERS),
        "marketing_ratio": [0.25] * len(YEAR_HEADERS),
        "development_ratio": [0.20] * len(YEAR_HEADERS),
        "other_ratio": [0.10] * len(YEAR_HEADERS),
        "development_amortization_years": [5] * len(YEAR_HEADERS),
    }
    for level in ACADEMY_LEVELS:
        code = level["code"]
        assumptions[f"academy_{code}_share"] = list(level["share_default"])
        assumptions[f"academy_{code}_price_multiplier"] = [level["price_multiplier"]] * len(YEAR_HEADERS)
        assumptions[f"academy_{code}_completion"] = [level["completion"]] * len(YEAR_HEADERS)
        assumptions[f"academy_{code}_certification"] = [level["certification"]] * len(YEAR_HEADERS)
        if code != "s":
            assumptions[f"academy_{code}_to_{ACADEMY_LEVELS[ACADEMY_LEVELS.index(level)+1]['code']}"] = [level["progression_to_next"]] * len(YEAR_HEADERS)
    assumptions["blended_hourly_rate"] = [3150.0] * len(YEAR_HEADERS)
    for sku in CONSULT_SKUS:
        assumptions[f"consult_{sku['sku'].lower()}_share"] = list(sku["share_default"])
    return assumptions


def _normalize_series(
    values: list[float] | tuple[float, ...],
    *,
    default: float,
    fallback: list[float] | None = None,
    length: int = 5,
) -> list[float]:
    if values:
        series = [float(value) for value in values]
    elif fallback:
        series = [float(value) for value in fallback]
    else:
        series = []

    if not series:
        return [default] * length
    if len(series) >= length:
        return series[:length]
    series = series + [series[-1]] * (length - len(series))
    return series


def _series_product(left: list[float], right: list[float]) -> list[float]:
    left_series = _normalize_series(left, default=0.0)
    right_series = _normalize_series(right, default=0.0)
    return [left_value * right_value for left_value, right_value in zip(left_series, right_series)]


def _write_header_row(sheet) -> None:
    sheet.cell(row=1, column=1, value="項目")
    sheet["A1"].font = BOLD_FONT
    for column_index, header in enumerate(YEAR_HEADERS, start=2):
        sheet.cell(row=1, column=column_index, value=header)
        sheet.cell(row=1, column=column_index).font = BOLD_FONT


def _apply_row_style(sheet, row_index: int, start_col: int, end_col: int, *, fill: PatternFill, font: Font | None = None) -> None:
    for column_index in range(start_col, end_col + 1):
        cell = sheet.cell(row=row_index, column=column_index)
        cell.fill = fill
        if font is not None:
            cell.font = font


def _style_input_rows(sheet, row_indexes: list[int], *, start_col: int = 2, end_col: int = 6) -> None:
    for row_index in row_indexes:
        _apply_row_style(sheet, row_index, start_col, end_col, fill=INPUT_FILL)


def _style_formula_rows(sheet, row_indexes: list[int], *, start_col: int = 2, end_col: int = 6) -> None:
    for row_index in row_indexes:
        _apply_row_style(sheet, row_index, start_col, end_col, fill=FORMULA_FILL)


def _style_subtotal_rows(sheet, row_indexes: list[int], *, start_col: int = 1, end_col: int = 6) -> None:
    for row_index in row_indexes:
        _apply_row_style(sheet, row_index, start_col, end_col, fill=SUBTOTAL_FILL, font=BOLD_FONT)


def _style_total_rows(sheet, row_indexes: list[int], *, start_col: int = 1, end_col: int = 6) -> None:
    for row_index in row_indexes:
        _apply_row_style(sheet, row_index, start_col, end_col, fill=TOTAL_FILL, font=TOTAL_FONT)


def _set_number_format_rows(sheet, row_indexes: list[int], *, number_format: str, start_col: int = 2, end_col: int = 6) -> None:
    for row_index in row_indexes:
        for column_index in range(start_col, end_col + 1):
            sheet.cell(row=row_index, column=column_index).number_format = number_format


def _set_column_widths(sheet, widths: dict[str, float]) -> None:
    for column, width in widths.items():
        sheet.column_dimensions[column].width = width


def _set_row_heights(sheet, heights: dict[int, float]) -> None:
    for row_index, height in heights.items():
        sheet.row_dimensions[row_index].height = height


def _align_range(sheet, *, start_row: int, end_row: int, start_col: int, end_col: int, alignment: Alignment) -> None:
    for row_index in range(start_row, end_row + 1):
        for column_index in range(start_col, end_col + 1):
            sheet.cell(row=row_index, column=column_index).alignment = alignment


def _apply_standard_layout(sheet, *, freeze_panes: str, label_width: float = 20, year_width: float = 12) -> None:
    sheet.freeze_panes = freeze_panes
    _set_column_widths(
        sheet,
        {
            "A": label_width,
            "B": year_width,
            "C": year_width,
            "D": year_width,
            "E": year_width,
            "F": year_width,
        },
    )
    _set_row_heights(sheet, {1: 22})
    _align_range(sheet, start_row=1, end_row=sheet.max_row, start_col=1, end_col=1, alignment=LEFT_ALIGN)
    if sheet.max_column >= 2:
        _align_range(sheet, start_row=1, end_row=sheet.max_row, start_col=2, end_col=min(6, sheet.max_column), alignment=RIGHT_ALIGN)


def _write_key_value_rows(sheet, rows: list[list[Any]]) -> None:
    for row_index, row in enumerate(rows, start=1):
        for col_index, value in enumerate(row, start=1):
            sheet.cell(row=row_index, column=col_index, value=value)
        sheet.cell(row=row_index, column=1).font = Font(bold=(row_index == 1 or len(row) > 1))


def _sheet_ref(sheet_name: str, cell_ref: str) -> str:
    escaped = sheet_name.replace("'", "''")
    return f"'{escaped}'!{cell_ref}"


def _year_columns() -> list[str]:
    return [excel_col(column_index) for column_index in range(2, 7)]


def excel_col(column_index: int) -> str:
    result = ""
    index = column_index
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result
