from pathlib import Path

from src.evals.reference_workbook import extract_reference_workbook


def test_extract_reference_workbook_reads_named_model_sections() -> None:
    fixture = Path("tests/fixtures/evals/reference_workbook_minimal.xlsx")

    reference = extract_reference_workbook(fixture)

    assert set(reference.segment_names) == {"アカデミー", "コンサル", "ミール"}
    assert reference.model_sheets["ミール"]["price_per_item"][0] == 500
    assert reference.pl_lines["売上"][0] == 9_700_000


def test_extract_reference_workbook_ignores_formatting_and_keeps_series_only() -> None:
    fixture = Path("tests/fixtures/evals/reference_workbook_minimal.xlsx")

    reference = extract_reference_workbook(fixture)

    assert reference.model_sheets["コンサル"]["sku_unit_price"][0] == 15_000_000
    assert reference.model_sheets["アカデミー"]["academy_students"][0] == 127
