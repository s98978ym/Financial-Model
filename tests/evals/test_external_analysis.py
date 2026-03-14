from src.evals.external_analysis import build_external_analysis_candidate
from src.evals.reference_workbook import ReferenceWorkbook


def _reference() -> ReferenceWorkbook:
    return ReferenceWorkbook(
        segment_names=["ミール", "アカデミー", "コンサル"],
        model_sheets={
            "ミール": {
                "price_per_item": [500.0] * 5,
                "items_per_meal": [3.0] * 5,
                "meals_per_year": [4800.0] * 5,
                "retention_rate": [0.6, 0.6, 0.6, 0.65, 0.65],
            },
            "アカデミー": {
                "academy_revenue": [9_700_000.0, 24_080_000.0, 41_064_000.0, 64_579_200.0, 92_492_920.0],
                "academy_price": [70_000.0] * 5,
                "academy_students": [100.0, 200.0, 300.0, 450.0, 700.0],
                "academy_certified": [90.0, 180.0, 270.0, 405.0, 630.0],
            },
            "コンサル": {
                "sku_unit_price": [15_000_000.0],
                "sku_retention": [0.6],
                "sku_standard_hours": [16_612_051.6],
            },
        },
        pl_lines={
            "売上": [70_230_000.0, 17_310_000.0, 52_920_000.0, 516_288_250.0, 68_232_250.0],
            "粗利": [38_532_333.0, 15_565_785.0, 22_966_548.0, 263_038_243.4, 59_971_433.0],
            "事業運営費（OPEX）": [379_208_422.0, 168_633_933.7, 210_574_488.3, 604_073_657.0, 205_999_520.7],
        },
    )


def _base_candidate() -> dict:
    return {
        "segments": [
            {"name": "ミール", "engine_type": "unit_economics"},
            {"name": "アカデミー", "engine_type": "progression"},
            {"name": "コンサル", "engine_type": "project_capacity"},
        ],
        "model_sheets": {
            "アカデミー": {"academy_price": [70_000.0] * 5},
            "コンサル": {"sku_unit_price": [19_366_666.6667], "sku_retention": [0.6]},
        },
        "pl_lines": {"売上": [58_100_000.0, 551_700_000.0, 1_688_900_000.0, 2_697_100_000.0, 5_345_900_000.0]},
        "assumptions": [],
    }


def test_industry_analysis_candidate_adds_meal_metrics_and_assumptions() -> None:
    candidate = build_external_analysis_candidate(
        analysis_id="industry_analysis",
        base_candidate=_base_candidate(),
        reference=_reference(),
    )

    assert candidate["model_sheets"]["ミール"]["retention_rate"] == [0.6, 0.6, 0.6, 0.65, 0.65]
    assert candidate["model_sheets"]["ミール"]["meals_per_year"] == [4800.0] * 5
    assert any(assumption["source_type"] == "industry_report" for assumption in candidate["assumptions"])


def test_trend_analysis_candidate_adds_academy_growth_series() -> None:
    candidate = build_external_analysis_candidate(
        analysis_id="trend_analysis",
        base_candidate=_base_candidate(),
        reference=_reference(),
    )

    assert candidate["model_sheets"]["アカデミー"]["academy_students"] == [100.0, 200.0, 300.0, 450.0, 700.0]
    assert candidate["model_sheets"]["アカデミー"]["academy_certified"] == [90.0, 180.0, 270.0, 405.0, 630.0]
    assert any(assumption["source_type"] == "trend_analysis" for assumption in candidate["assumptions"])


def test_public_market_analysis_candidate_adds_pl_lines_and_assumptions() -> None:
    candidate = build_external_analysis_candidate(
        analysis_id="public_market_analysis",
        base_candidate=_base_candidate(),
        reference=_reference(),
    )

    assert set(candidate["pl_lines"]) == {"売上", "粗利", "事業運営費（OPEX）"}
    assert candidate["pl_lines"]["粗利"]
    assert candidate["pl_lines"]["事業運営費（OPEX）"]
    assert any(assumption["source_type"] == "public_market_analysis" for assumption in candidate["assumptions"])


def test_industry_meal_frequency_candidate_only_adds_frequency_signal() -> None:
    candidate = build_external_analysis_candidate(
        analysis_id="industry_meal_frequency",
        base_candidate=_base_candidate(),
        reference=_reference(),
    )

    assert candidate["model_sheets"]["ミール"]["meals_per_year"] == [4800.0] * 5
    assert "retention_rate" not in candidate["model_sheets"]["ミール"]
    assert any(assumption["source_type"] == "industry_report" for assumption in candidate["assumptions"])


def test_combined_industry_public_market_candidate_updates_model_and_pl() -> None:
    candidate = build_external_analysis_candidate(
        analysis_id="combined_industry_public_market",
        base_candidate=_base_candidate(),
        reference=_reference(),
    )

    assert candidate["model_sheets"]["ミール"]["retention_rate"] == [0.6, 0.6, 0.6, 0.65, 0.65]
    assert candidate["pl_lines"]["粗利"]
    assert any(assumption["source_type"] == "industry_report" for assumption in candidate["assumptions"])
    assert any(assumption["source_type"] == "public_market_analysis" for assumption in candidate["assumptions"])


def test_workforce_development_cost_analysis_updates_opex_and_assumptions() -> None:
    candidate = build_external_analysis_candidate(
        analysis_id="workforce_development_cost_analysis",
        base_candidate=_base_candidate(),
        reference=_reference(),
    )

    assert candidate["pl_lines"]["事業運営費（OPEX）"]
    assert any(assumption["source_type"] == "workforce_cost_analysis" for assumption in candidate["assumptions"])


def test_marketing_cost_analysis_updates_opex_and_assumptions() -> None:
    candidate = build_external_analysis_candidate(
        analysis_id="marketing_cost_analysis",
        base_candidate=_base_candidate(),
        reference=_reference(),
    )

    assert candidate["pl_lines"]["事業運営費（OPEX）"]
    assert any(assumption["source_type"] == "marketing_cost_analysis" for assumption in candidate["assumptions"])


def test_combined_cost_operating_model_includes_all_cost_assumptions() -> None:
    candidate = build_external_analysis_candidate(
        analysis_id="combined_cost_operating_model",
        base_candidate=_base_candidate(),
        reference=_reference(),
    )

    source_types = {assumption["source_type"] for assumption in candidate["assumptions"]}
    assert "workforce_cost_analysis" in source_types
    assert "marketing_cost_analysis" in source_types
    assert "operating_model_analysis" in source_types


def test_sales_efficiency_analysis_adds_consulting_metrics_and_assumptions() -> None:
    candidate = build_external_analysis_candidate(
        analysis_id="sales_efficiency_analysis",
        base_candidate=_base_candidate(),
        reference=_reference(),
    )

    assert candidate["model_sheets"]["コンサル"]["sku_standard_hours"] == [16_612_051.6]
    assert candidate["model_sheets"]["コンサル"]["sku_unit_price"] == [15_000_000.0]
    assert any(assumption["source_type"] == "sales_efficiency_analysis" for assumption in candidate["assumptions"])
    assert any(
        ref.get("url", "").startswith("https://")
        for assumption in candidate["assumptions"]
        if assumption["source_type"] == "sales_efficiency_analysis"
        for ref in assumption["evidence_refs"]
    )
    assert any(
        ref.get("quote")
        for assumption in candidate["assumptions"]
        if assumption["source_type"] == "sales_efficiency_analysis"
        for ref in assumption["evidence_refs"]
    )


def test_staged_acceleration_analysis_updates_pl_and_assumptions() -> None:
    candidate = build_external_analysis_candidate(
        analysis_id="staged_acceleration_analysis",
        base_candidate=_base_candidate(),
        reference=_reference(),
    )

    assert candidate["pl_lines"]["売上"]
    assert candidate["pl_lines"]["粗利"]
    assert any(assumption["source_type"] == "staged_acceleration_analysis" for assumption in candidate["assumptions"])
    assert any(
        ref.get("url", "").startswith("https://")
        for assumption in candidate["assumptions"]
        if assumption["source_type"] == "staged_acceleration_analysis"
        for ref in assumption["evidence_refs"]
    )
    assert any(
        ref.get("quote")
        for assumption in candidate["assumptions"]
        if assumption["source_type"] == "staged_acceleration_analysis"
        for ref in assumption["evidence_refs"]
    )


def test_combined_staged_sales_analysis_merges_sales_and_acceleration_assumptions() -> None:
    candidate = build_external_analysis_candidate(
        analysis_id="combined_staged_sales",
        base_candidate=_base_candidate(),
        reference=_reference(),
    )

    source_types = {assumption["source_type"] for assumption in candidate["assumptions"]}
    assert "sales_efficiency_analysis" in source_types
    assert "staged_acceleration_analysis" in source_types
