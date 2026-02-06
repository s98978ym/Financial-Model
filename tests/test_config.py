"""Tests for src.config.models -- Pydantic v2 configuration models."""

import pytest
from src.config.models import (
    CatalogItem,
    CellTarget,
    ColorConfig,
    Evidence,
    ExtractedParameter,
    InputCatalog,
    PhaseAConfig,
    ValidationResult,
)


class TestColorConfig:
    def test_default_input_color(self):
        c = ColorConfig()
        assert c.input_color == "FFFFF2CC"

    def test_default_formula_color(self):
        c = ColorConfig()
        assert c.formula_color == "FF0000FF"

    def test_default_total_color(self):
        c = ColorConfig()
        assert c.total_color == "FFD9D9D9"

    def test_apply_flags_default_false(self):
        c = ColorConfig()
        assert c.apply_formula_color is False
        assert c.apply_total_color is False

    def test_custom_colors(self):
        c = ColorConfig(input_color="FFFF0000", formula_color="FF00FF00")
        assert c.input_color == "FFFF0000"
        assert c.formula_color == "FF00FF00"

    def test_six_digit_hex_normalized(self):
        c = ColorConfig(input_color="FF0000")
        assert c.input_color == "FFFF0000"


class TestPhaseAConfig:
    def test_default_industry(self):
        cfg = PhaseAConfig()
        assert cfg.industry == "その他"

    def test_default_business_model(self):
        cfg = PhaseAConfig()
        assert cfg.business_model == "B2B"

    def test_default_strictness(self):
        cfg = PhaseAConfig()
        assert cfg.strictness == "normal"

    def test_default_cases(self):
        cfg = PhaseAConfig()
        assert cfg.cases == ["base", "worst"]

    def test_default_simulation_false(self):
        cfg = PhaseAConfig()
        assert cfg.simulation is False

    def test_default_colors(self):
        cfg = PhaseAConfig()
        assert isinstance(cfg.colors, ColorConfig)

    def test_custom_values(self):
        cfg = PhaseAConfig(
            industry="SaaS",
            business_model="B2C",
            strictness="strict",
            cases=["best", "base", "worst"],
            simulation=True,
        )
        assert cfg.industry == "SaaS"
        assert cfg.business_model == "B2C"
        assert cfg.strictness == "strict"
        assert "best" in cfg.cases
        assert cfg.simulation is True

    def test_is_strict(self):
        cfg = PhaseAConfig(strictness="strict")
        assert cfg.is_strict() is True

    def test_is_not_strict(self):
        cfg = PhaseAConfig(strictness="normal")
        assert cfg.is_strict() is False

    def test_case_deduplication(self):
        cfg = PhaseAConfig(cases=["base", "base", "worst"])
        assert cfg.cases == ["base", "worst"]


class TestCatalogItem:
    def test_basic_creation(self):
        item = CatalogItem(sheet="Sheet1", cell="B3")
        assert item.sheet == "Sheet1"
        assert item.cell == "B3"

    def test_field_is_cell(self):
        item = CatalogItem(sheet="Sheet1", cell="B3")
        assert hasattr(item, "cell")

    def test_default_values(self):
        item = CatalogItem(sheet="Sheet1", cell="B3")
        assert item.current_value is None
        assert item.has_formula is False
        assert item.label_candidates == []
        assert item.unit_candidates == []
        assert item.year_or_period is None
        assert item.block is None

    def test_address_property(self):
        item = CatalogItem(sheet="PL設計", cell="B3")
        assert item.address == "PL設計!B3"

    def test_formula_item(self):
        item = CatalogItem(sheet="S", cell="A1", has_formula=True)
        assert item.has_formula is True

    def test_label_and_unit_candidates(self):
        item = CatalogItem(
            sheet="S", cell="B5",
            label_candidates=["売上高", "Revenue"],
            unit_candidates=["円"],
        )
        assert len(item.label_candidates) == 2
        assert item.unit_candidates == ["円"]

    def test_primary_label(self):
        item = CatalogItem(sheet="S", cell="B3", label_candidates=["売上高"])
        assert item.primary_label() == "売上高"

    def test_primary_label_fallback(self):
        item = CatalogItem(sheet="S", cell="B3")
        assert item.primary_label() == "S!B3"

    def test_mutable_defaults_are_independent(self):
        item1 = CatalogItem(sheet="S", cell="A1")
        item2 = CatalogItem(sheet="S", cell="A2")
        item1.label_candidates.append("test")
        assert "test" not in item2.label_candidates


class TestInputCatalog:
    def test_empty_catalog(self):
        cat = InputCatalog()
        assert len(cat) == 0
        assert cat.items == []

    def test_add_item(self):
        cat = InputCatalog()
        item = CatalogItem(sheet="S", cell="B3")
        cat.add(item)
        assert len(cat) == 1

    def test_blocks_populated_on_add(self):
        cat = InputCatalog()
        item = CatalogItem(sheet="S", cell="B3", block="Revenue")
        cat.add(item)
        assert "S::Revenue" in cat.blocks

    def test_sheets_method(self):
        cat = InputCatalog()
        cat.add(CatalogItem(sheet="Sheet1", cell="A1"))
        cat.add(CatalogItem(sheet="Sheet2", cell="A1"))
        cat.add(CatalogItem(sheet="Sheet1", cell="A2"))
        assert cat.sheets() == ["Sheet1", "Sheet2"]

    def test_rebuild_blocks(self):
        items = [
            CatalogItem(sheet="S", cell="A1", block="A"),
            CatalogItem(sheet="S", cell="A2", block="B"),
        ]
        cat = InputCatalog(items=items)
        cat.rebuild_blocks()
        assert "S::A" in cat.blocks
        assert "S::B" in cat.blocks


class TestCellTarget:
    def test_creation(self):
        t = CellTarget(sheet="PL設計", cell="B3")
        assert t.sheet == "PL設計"
        assert t.cell == "B3"

    def test_address(self):
        t = CellTarget(sheet="PL設計", cell="B3")
        assert t.address == "PL設計!B3"

    def test_hash_and_eq(self):
        t1 = CellTarget(sheet="S", cell="A1")
        t2 = CellTarget(sheet="S", cell="A1")
        assert t1 == t2
        assert hash(t1) == hash(t2)


class TestEvidence:
    def test_default_empty(self):
        e = Evidence()
        assert e.quote == ""
        assert e.is_empty() is True

    def test_with_values(self):
        e = Evidence(quote="売上は1.5億", page_or_slide="p.3")
        assert e.is_empty() is False

    def test_display_text(self):
        e = Evidence(quote="売上は1.5億", page_or_slide="p.3")
        text = e.to_display_text()
        assert "p.3" in text
        assert "1.5億" in text


class TestExtractedParameter:
    def test_default_selected_true(self):
        p = ExtractedParameter(key="k", label="L", value=100)
        assert p.selected is True

    def test_default_adjusted_value_none(self):
        p = ExtractedParameter(key="k", label="L", value=100)
        assert p.adjusted_value is None

    def test_default_confidence(self):
        p = ExtractedParameter(key="k", label="L", value=100)
        assert p.confidence == 0.0

    def test_default_source(self):
        p = ExtractedParameter(key="k", label="L", value=100)
        assert p.source == "document"

    def test_selected_false(self):
        p = ExtractedParameter(key="k", label="L", value=100, selected=False)
        assert p.selected is False

    def test_adjusted_value_overrides(self):
        p = ExtractedParameter(key="k", label="L", value=100, adjusted_value=200)
        assert p.effective_value == 200

    def test_effective_value_default(self):
        p = ExtractedParameter(key="k", label="L", value=100)
        assert p.effective_value == 100

    def test_mapped_targets(self):
        targets = [CellTarget(sheet="S", cell="A1"), CellTarget(sheet="S", cell="A2")]
        p = ExtractedParameter(key="k", label="L", value=100, mapped_targets=targets)
        assert len(p.mapped_targets) == 2

    def test_high_confidence(self):
        p = ExtractedParameter(key="k", label="L", value=100, confidence=0.9)
        assert p.is_high_confidence() is True

    def test_low_confidence(self):
        p = ExtractedParameter(key="k", label="L", value=100, confidence=0.5)
        assert p.is_high_confidence() is False


class TestValidationResult:
    def test_default_all_true(self):
        v = ValidationResult()
        assert v.passed is True
        assert v.formula_preserved is True
        assert v.no_new_errors is True
        assert v.full_calc_on_load is True

    def test_add_error_fails(self):
        v = ValidationResult()
        v.add_error("Something broke")
        assert v.passed is False
        assert len(v.errors_found) == 1

    def test_add_warning_does_not_fail(self):
        v = ValidationResult()
        v.add_warning("Minor issue")
        assert v.passed is True
        assert len(v.warnings) == 1

    def test_changed_cells_default_empty(self):
        v = ValidationResult()
        assert v.changed_cells == []

    def test_report_text(self):
        v = ValidationResult()
        text = v.to_report_text()
        assert "PASSED" in text
