"""Workbook export helpers for FAM PDCA artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from openpyxl import Workbook


YEAR_HEADERS = ["FY1", "FY2", "FY3", "FY4", "FY5"]

MODEL_SHEET_LAYOUTS = {
    "ミール": (
        "ミールモデル",
        [
            ("price_per_item", "価格/アイテム"),
            ("items_per_meal", "アイテム/食事"),
            ("meals_per_year", "食事数/年"),
            ("retention_rate", "継続率"),
        ],
    ),
    "アカデミー": (
        "アカデミーモデル",
        [
            ("academy_price", "アカデミー単価"),
            ("academy_revenue", "アカデミー売上"),
            ("academy_students", "受講人数"),
            ("academy_certified", "認証人数(期末)"),
        ],
    ),
    "コンサル": (
        "コンサルモデル",
        [
            ("sku_unit_price", "SKU単価"),
            ("sku_retention", "SKU継続率"),
            ("sku_standard_hours", "標準工数"),
        ],
    ),
}

PL_LAYOUT = [
    ("売上", "売上"),
    ("粗利", "粗利"),
    ("事業運営費（OPEX）", "事業運営費（OPEX）"),
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

    _write_summary_sheet(summary_sheet, candidate_id, diagnosis, baseline_total)
    _write_pl_sheet(workbook.create_sheet("PL設計"), candidate_payload.get("pl_lines", {}))

    model_sheets = candidate_payload.get("model_sheets", {})
    for segment_name, (sheet_name, metric_layout) in MODEL_SHEET_LAYOUTS.items():
        _write_model_sheet(
            workbook.create_sheet(sheet_name),
            metric_layout=metric_layout,
            model_metrics=model_sheets.get(segment_name, {}),
        )

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
    for row_index, row in enumerate(rows, start=1):
        for col_index, value in enumerate(row, start=1):
            sheet.cell(row=row_index, column=col_index, value=value)


def _write_pl_sheet(sheet, pl_lines: dict[str, list[float]]) -> None:
    _write_series_sheet(sheet, row_layout=PL_LAYOUT, series_by_key=pl_lines)


def _write_model_sheet(sheet, *, metric_layout: Iterable[tuple[str, str]], model_metrics: dict[str, list[float]]) -> None:
    _write_series_sheet(sheet, row_layout=metric_layout, series_by_key=model_metrics)


def _write_series_sheet(sheet, *, row_layout: Iterable[tuple[str, str]], series_by_key: dict[str, list[float]]) -> None:
    sheet.cell(row=1, column=1, value="項目")
    for column_index, header in enumerate(YEAR_HEADERS, start=2):
        sheet.cell(row=1, column=column_index, value=header)

    for row_index, (key, label) in enumerate(row_layout, start=2):
        sheet.cell(row=row_index, column=1, value=label)
        for column_index, value in enumerate(series_by_key.get(key, []), start=2):
            sheet.cell(row=row_index, column=column_index, value=value)


def _write_assumptions_sheet(sheet, assumptions: list[dict[str, Any]]) -> None:
    headers = ["source_type", "review_status", "evidence_count", "evidence_ids"]
    for column_index, header in enumerate(headers, start=1):
        sheet.cell(row=1, column=column_index, value=header)

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
    for row_index, row in enumerate(rows, start=1):
        for col_index, value in enumerate(row, start=1):
            sheet.cell(row=row_index, column=col_index, value=value)
