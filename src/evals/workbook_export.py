"""Workbook export helpers for FAM PDCA artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Font


YEAR_HEADERS = ["FY1", "FY2", "FY3", "FY4", "FY5"]

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
    "personnel_cost": 2,
    "marketing_cost": 3,
    "development_cost": 4,
    "other_opex": 5,
    "opex_total": 6,
}

COST_LIST_ROWS = [
    ("営業人件費", "人件費", 0.35, "personnel_cost"),
    ("運営人件費", "人件費", 0.30, "personnel_cost"),
    ("管理人件費", "人件費", 0.20, "personnel_cost"),
    ("採用・教育人件費", "人件費", 0.15, "personnel_cost"),
    ("メディア費", "マーケ費", 0.50, "marketing_cost"),
    ("イベント・販促費", "マーケ費", 0.30, "marketing_cost"),
    ("パートナーインセンティブ", "マーケ費", 0.20, "marketing_cost"),
    ("外部開発費", "開発費", 0.60, "development_cost"),
    ("内部開発費", "開発費", 0.40, "development_cost"),
    ("その他固定費", "その他OPEX", 1.00, "other_opex"),
]


def export_candidate_workbook(
    *,
    output_path: Path,
    candidate_id: str,
    candidate_payload: dict[str, Any],
    diagnosis: dict[str, Any],
    baseline_total: float,
    run_root: Path,
) -> None:
    """Export one candidate workbook for human review."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    workbook = Workbook()
    summary_sheet = workbook.active
    summary_sheet.title = "Summary"

    assumptions = _build_workbook_assumptions(candidate_payload)
    _write_summary_sheet(summary_sheet, candidate_id, diagnosis, baseline_total)
    _write_pl_sheet(workbook.create_sheet("PL設計"))
    _write_meal_sheet(workbook.create_sheet("ミールモデル"))
    _write_academy_sheet(workbook.create_sheet("アカデミーモデル"))
    _write_consulting_sheet(workbook.create_sheet("コンサルモデル"))
    _write_cost_summary_sheet(workbook.create_sheet("費用まとめ"))
    _write_cost_list_sheet(workbook.create_sheet("費用リスト"))
    _write_plan_assumptions_sheet(workbook.create_sheet("（全Ver）前提条件"), assumptions)
    _write_assumptions_sheet(workbook.create_sheet("Assumptions"), candidate_payload.get("assumptions", []))
    _write_artifacts_sheet(workbook.create_sheet("Artifacts"), run_root=run_root, candidate_id=candidate_id)
    workbook.save(output_path)


def _write_summary_sheet(
    sheet,
    candidate_id: str,
    diagnosis: dict[str, Any],
    baseline_total: float,
) -> None:
    hypothesis = diagnosis.get("hypothesis", {})
    verdict = diagnosis.get("verdict", {})
    score = diagnosis.get("score", {})

    rows = [
        ["candidate_id", candidate_id],
        ["hypothesis_title", hypothesis.get("title", "")],
        ["hypothesis_detail", hypothesis.get("detail", "")],
        ["verdict", verdict.get("status", "")],
        ["verdict_reason", verdict.get("reason", "")],
        ["total_score", score.get("total", 0.0)],
        ["delta_vs_baseline", score.get("delta_vs_baseline", round(score.get("total", 0.0) - baseline_total, 4))],
        ["baseline_total", baseline_total],
    ]
    _write_key_value_rows(sheet, rows)


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
        ("development_cost", "開発費"),
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
        personnel_ref = _sheet_ref("費用まとめ", f"{model_col}{COST_SUMMARY_ROWS['personnel_cost']}")
        marketing_ref = _sheet_ref("費用まとめ", f"{model_col}{COST_SUMMARY_ROWS['marketing_cost']}")
        development_ref = _sheet_ref("費用まとめ", f"{model_col}{COST_SUMMARY_ROWS['development_cost']}")
        other_opex_ref = _sheet_ref("費用まとめ", f"{model_col}{COST_SUMMARY_ROWS['other_opex']}")
        sheet[f"{model_col}{PL_ROWS['academy_revenue']}"] = f"={_sheet_ref('アカデミーモデル', f'{model_col}6')}"
        sheet[f"{model_col}{PL_ROWS['consult_revenue']}"] = f"={_sheet_ref('コンサルモデル', f'{model_col}6')}"
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


def _write_academy_sheet(sheet) -> None:
    _write_header_row(sheet)
    labels = [
        "公開単価",
        "実効単価",
        "受講人数",
        "認証人数(期末)",
        "認証率",
        "売上",
    ]
    for row_index, label in enumerate(labels, start=2):
        sheet.cell(row=row_index, column=1, value=label)

    for column_index, assumption_col in enumerate(_year_columns(), start=2):
        model_col = excel_col(column_index)
        public_price_ref = _sheet_ref("（全Ver）前提条件", f"{assumption_col}{ASSUMPTION_ROWS['academy_public_price']}")
        effective_price_ref = _sheet_ref("（全Ver）前提条件", f"{assumption_col}{ASSUMPTION_ROWS['academy_effective_price']}")
        students_ref = _sheet_ref("（全Ver）前提条件", f"{assumption_col}{ASSUMPTION_ROWS['academy_students']}")
        certified_ref = _sheet_ref("（全Ver）前提条件", f"{assumption_col}{ASSUMPTION_ROWS['academy_certified']}")
        sheet[f"{model_col}2"] = f"={public_price_ref}"
        sheet[f"{model_col}3"] = f"={effective_price_ref}"
        sheet[f"{model_col}4"] = f"={students_ref}"
        sheet[f"{model_col}5"] = f"={certified_ref}"
        sheet[f"{model_col}6"] = f"={model_col}3*{model_col}4"
        sheet[f"{model_col}7"] = f"=IF({model_col}4<>0,{model_col}5/{model_col}4,0)"


def _write_consulting_sheet(sheet) -> None:
    _write_header_row(sheet)
    labels = [
        "SKU単価",
        "SKU継続率",
        "標準工数",
        "推定案件数",
        "売上",
    ]
    for row_index, label in enumerate(labels, start=2):
        sheet.cell(row=row_index, column=1, value=label)

    for column_index, assumption_col in enumerate(_year_columns(), start=2):
        model_col = excel_col(column_index)
        unit_price_ref = _sheet_ref("（全Ver）前提条件", f"{assumption_col}{ASSUMPTION_ROWS['consult_unit_price']}")
        retention_ref = _sheet_ref("（全Ver）前提条件", f"{assumption_col}{ASSUMPTION_ROWS['consult_retention']}")
        standard_hours_ref = _sheet_ref("（全Ver）前提条件", f"{assumption_col}{ASSUMPTION_ROWS['consult_standard_hours']}")
        project_count_ref = _sheet_ref("（全Ver）前提条件", f"{assumption_col}{ASSUMPTION_ROWS['consult_project_count']}")
        sheet[f"{model_col}2"] = f"={unit_price_ref}"
        sheet[f"{model_col}3"] = f"={retention_ref}"
        sheet[f"{model_col}4"] = f"={standard_hours_ref}"
        sheet[f"{model_col}5"] = f"={project_count_ref}"
        sheet[f"{model_col}6"] = f"={model_col}2*{model_col}5"


def _write_cost_summary_sheet(sheet) -> None:
    _write_header_row(sheet)
    labels = {
        COST_SUMMARY_ROWS["personnel_cost"]: "人件費",
        COST_SUMMARY_ROWS["marketing_cost"]: "マーケ費",
        COST_SUMMARY_ROWS["development_cost"]: "開発費",
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
        development_ratio_ref = _sheet_ref("（全Ver）前提条件", f"{assumption_col}{ASSUMPTION_ROWS['development_ratio']}")
        other_ratio_ref = _sheet_ref("（全Ver）前提条件", f"{assumption_col}{ASSUMPTION_ROWS['other_ratio']}")
        for row_index, ratio_key in ratio_map.items():
            ratio_ref = {
                "personnel_ratio": personnel_ratio_ref,
                "marketing_ratio": marketing_ratio_ref,
                "development_ratio": development_ratio_ref,
                "other_ratio": other_ratio_ref,
            }[ratio_key]
            sheet[f"{model_col}{row_index}"] = f"={opex_ref}*{ratio_ref}"
        sheet[f"{model_col}{COST_SUMMARY_ROWS['opex_total']}"] = (
            f"=SUM({model_col}{COST_SUMMARY_ROWS['personnel_cost']}:{model_col}{COST_SUMMARY_ROWS['other_opex']})"
        )


def _write_cost_list_sheet(sheet) -> None:
    sheet.cell(row=1, column=1, value="アイテム")
    sheet.cell(row=1, column=2, value="カテゴリ")
    for column_index, header in enumerate(YEAR_HEADERS, start=3):
        sheet.cell(row=1, column=column_index, value=header)
    sheet["A1"].font = Font(bold=True)
    sheet["B1"].font = Font(bold=True)
    for column_index in range(3, 8):
        sheet.cell(row=1, column=column_index).font = Font(bold=True)

    for row_index, (item_name, category_name, share, cost_key) in enumerate(COST_LIST_ROWS, start=2):
        sheet.cell(row=row_index, column=1, value=item_name)
        sheet.cell(row=row_index, column=2, value=category_name)
        cost_row = COST_SUMMARY_ROWS[cost_key]
        for column_index in range(3, 8):
            model_col = excel_col(column_index)
            summary_col = excel_col(column_index - 1)
            sheet[f"{model_col}{row_index}"] = f"={_sheet_ref('費用まとめ', f'{summary_col}{cost_row}')}*{share}"


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

    return {
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
    }


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
    sheet["A1"].font = Font(bold=True)
    for column_index, header in enumerate(YEAR_HEADERS, start=2):
        sheet.cell(row=1, column=column_index, value=header)
        sheet.cell(row=1, column=column_index).font = Font(bold=True)


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
