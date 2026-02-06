"""Tests for src.excel.case_generator -- Best/Base/Worst case generation.

Verifies that CaseGenerator applies the correct multipliers to revenue,
cost, growth, and churn parameters while leaving unclassified params
unchanged.
"""

from copy import deepcopy

import pytest

from src.config.models import (
    CellTarget,
    ExtractedParameter,
    PhaseAConfig,
)
from src.excel.case_generator import (
    CaseGenerator,
    CASE_RULES,
    REVENUE_KEYWORDS,
    COST_KEYWORDS,
    GROWTH_KEYWORDS,
    CHURN_KEYWORDS,
)


# ===================================================================
# Fixtures
# ===================================================================

@pytest.fixture
def three_case_config():
    """PhaseAConfig requesting base, best, and worst cases."""
    return PhaseAConfig(
        industry="SaaS",
        business_model="B2B",
        cases=["base", "best", "worst"],
    )


@pytest.fixture
def base_parameters():
    """A set of base-case parameters covering all multiplier categories."""
    return [
        ExtractedParameter(
            key="revenue_fy2024",
            label="\u58f2\u4e0a\u9ad8 FY2024",
            value=100_000_000,
            mapped_targets=[CellTarget(sheet="PL", cell="B3")],
            selected=True,
        ),
        ExtractedParameter(
            key="cogs_fy2024",
            label="\u539f\u4fa1\u8cbb\u7528 FY2024",
            value=40_000_000,
            mapped_targets=[CellTarget(sheet="PL", cell="B4")],
            selected=True,
        ),
        ExtractedParameter(
            key="growth_rate",
            label="\u6210\u9577\u7387",
            value=0.15,
            mapped_targets=[CellTarget(sheet="KPI", cell="B2")],
            selected=True,
        ),
        ExtractedParameter(
            key="churn_rate",
            label="\u89e3\u7d04\u7387",
            value=0.05,
            mapped_targets=[CellTarget(sheet="KPI", cell="B3")],
            selected=True,
        ),
        ExtractedParameter(
            key="headcount",
            label="\u5f93\u696d\u54e1\u6570",
            value=50,
            mapped_targets=[CellTarget(sheet="PL", cell="B8")],
            selected=True,
        ),
    ]


# ===================================================================
# CASE_RULES constant sanity checks
# ===================================================================

class TestCaseRules:
    """Sanity checks for the built-in CASE_RULES."""

    def test_base_multipliers_are_one(self):
        for key, val in CASE_RULES["base"].items():
            assert val == 1.0, f"Base rule {key} should be 1.0"

    def test_best_revenue_above_one(self):
        assert CASE_RULES["best"]["revenue_multiplier"] > 1.0

    def test_best_cost_below_one(self):
        assert CASE_RULES["best"]["cost_multiplier"] < 1.0

    def test_worst_revenue_below_one(self):
        assert CASE_RULES["worst"]["revenue_multiplier"] < 1.0

    def test_worst_cost_above_one(self):
        assert CASE_RULES["worst"]["cost_multiplier"] > 1.0

    def test_best_churn_below_one(self):
        assert CASE_RULES["best"]["churn_multiplier"] < 1.0

    def test_worst_churn_above_one(self):
        assert CASE_RULES["worst"]["churn_multiplier"] > 1.0


# ===================================================================
# Base case: unchanged
# ===================================================================

class TestBaseCase:
    """The base case should be identical to the input parameters."""

    def test_base_case_values_unchanged(self, three_case_config, base_parameters):
        gen = CaseGenerator(three_case_config)
        cases = gen.generate_cases(base_parameters)
        assert "base" in cases
        base = cases["base"]
        for orig, derived in zip(base_parameters, base):
            assert derived.value == orig.value

    def test_base_case_keys_preserved(self, three_case_config, base_parameters):
        gen = CaseGenerator(three_case_config)
        cases = gen.generate_cases(base_parameters)
        base_keys = [p.key for p in cases["base"]]
        orig_keys = [p.key for p in base_parameters]
        assert base_keys == orig_keys

    def test_base_case_is_deep_copy(self, three_case_config, base_parameters):
        """Base case should be a deep copy, not the same objects."""
        gen = CaseGenerator(three_case_config)
        cases = gen.generate_cases(base_parameters)
        # Mutating the base case should not affect original
        cases["base"][0].value = -1
        assert base_parameters[0].value == 100_000_000


# ===================================================================
# Best case: revenue up, cost down
# ===================================================================

class TestBestCase:
    """Best case should increase revenue and decrease costs."""

    def test_best_case_generated(self, three_case_config, base_parameters):
        gen = CaseGenerator(three_case_config)
        cases = gen.generate_cases(base_parameters)
        assert "best" in cases

    def test_best_revenue_increased(self, three_case_config, base_parameters):
        gen = CaseGenerator(three_case_config)
        cases = gen.generate_cases(base_parameters)
        best_revenue = next(p for p in cases["best"] if p.key == "revenue_fy2024")
        orig_revenue = next(p for p in base_parameters if p.key == "revenue_fy2024")
        assert best_revenue.value > orig_revenue.value

    def test_best_revenue_uses_correct_multiplier(self, three_case_config, base_parameters):
        gen = CaseGenerator(three_case_config)
        cases = gen.generate_cases(base_parameters)
        best_revenue = next(p for p in cases["best"] if p.key == "revenue_fy2024")
        expected = round(100_000_000 * CASE_RULES["best"]["revenue_multiplier"], 2)
        assert best_revenue.value == expected

    def test_best_cost_decreased(self, three_case_config, base_parameters):
        gen = CaseGenerator(three_case_config)
        cases = gen.generate_cases(base_parameters)
        best_cost = next(p for p in cases["best"] if p.key == "cogs_fy2024")
        orig_cost = next(p for p in base_parameters if p.key == "cogs_fy2024")
        assert best_cost.value < orig_cost.value

    def test_best_growth_increased(self, three_case_config, base_parameters):
        gen = CaseGenerator(three_case_config)
        cases = gen.generate_cases(base_parameters)
        best_growth = next(p for p in cases["best"] if p.key == "growth_rate")
        orig_growth = next(p for p in base_parameters if p.key == "growth_rate")
        assert best_growth.value > orig_growth.value

    def test_best_churn_decreased(self, three_case_config, base_parameters):
        gen = CaseGenerator(three_case_config)
        cases = gen.generate_cases(base_parameters)
        best_churn = next(p for p in cases["best"] if p.key == "churn_rate")
        orig_churn = next(p for p in base_parameters if p.key == "churn_rate")
        assert best_churn.value < orig_churn.value


# ===================================================================
# Worst case: revenue down, cost up
# ===================================================================

class TestWorstCase:
    """Worst case should decrease revenue and increase costs."""

    def test_worst_case_generated(self, three_case_config, base_parameters):
        gen = CaseGenerator(three_case_config)
        cases = gen.generate_cases(base_parameters)
        assert "worst" in cases

    def test_worst_revenue_decreased(self, three_case_config, base_parameters):
        gen = CaseGenerator(three_case_config)
        cases = gen.generate_cases(base_parameters)
        worst_revenue = next(p for p in cases["worst"] if p.key == "revenue_fy2024")
        orig_revenue = next(p for p in base_parameters if p.key == "revenue_fy2024")
        assert worst_revenue.value < orig_revenue.value

    def test_worst_revenue_uses_correct_multiplier(self, three_case_config, base_parameters):
        gen = CaseGenerator(three_case_config)
        cases = gen.generate_cases(base_parameters)
        worst_revenue = next(p for p in cases["worst"] if p.key == "revenue_fy2024")
        expected = round(100_000_000 * CASE_RULES["worst"]["revenue_multiplier"], 2)
        assert worst_revenue.value == expected

    def test_worst_cost_increased(self, three_case_config, base_parameters):
        gen = CaseGenerator(three_case_config)
        cases = gen.generate_cases(base_parameters)
        worst_cost = next(p for p in cases["worst"] if p.key == "cogs_fy2024")
        orig_cost = next(p for p in base_parameters if p.key == "cogs_fy2024")
        assert worst_cost.value > orig_cost.value

    def test_worst_growth_decreased(self, three_case_config, base_parameters):
        gen = CaseGenerator(three_case_config)
        cases = gen.generate_cases(base_parameters)
        worst_growth = next(p for p in cases["worst"] if p.key == "growth_rate")
        orig_growth = next(p for p in base_parameters if p.key == "growth_rate")
        assert worst_growth.value < orig_growth.value

    def test_worst_churn_increased(self, three_case_config, base_parameters):
        gen = CaseGenerator(three_case_config)
        cases = gen.generate_cases(base_parameters)
        worst_churn = next(p for p in cases["worst"] if p.key == "churn_rate")
        orig_churn = next(p for p in base_parameters if p.key == "churn_rate")
        assert worst_churn.value > orig_churn.value


# ===================================================================
# Unclassified parameters: no adjustment
# ===================================================================

class TestUnclassifiedParams:
    """Parameters that don't match any keyword should remain unchanged."""

    def test_headcount_unchanged_in_best(self, three_case_config, base_parameters):
        gen = CaseGenerator(three_case_config)
        cases = gen.generate_cases(base_parameters)
        best_hc = next(p for p in cases["best"] if p.key == "headcount")
        orig_hc = next(p for p in base_parameters if p.key == "headcount")
        assert best_hc.value == orig_hc.value

    def test_headcount_unchanged_in_worst(self, three_case_config, base_parameters):
        gen = CaseGenerator(three_case_config)
        cases = gen.generate_cases(base_parameters)
        worst_hc = next(p for p in cases["worst"] if p.key == "headcount")
        orig_hc = next(p for p in base_parameters if p.key == "headcount")
        assert worst_hc.value == orig_hc.value


# ===================================================================
# Non-numeric values: unchanged
# ===================================================================

class TestNonNumericValues:
    """String / None values should pass through without modification."""

    def test_string_value_unchanged(self, three_case_config):
        params = [
            ExtractedParameter(
                key="company_name",
                label="\u4f1a\u793e\u540d",
                value="\u682a\u5f0f\u4f1a\u793eABC",
                selected=True,
            ),
        ]
        gen = CaseGenerator(three_case_config)
        cases = gen.generate_cases(params)
        assert cases["best"][0].value == "\u682a\u5f0f\u4f1a\u793eABC"
        assert cases["worst"][0].value == "\u682a\u5f0f\u4f1a\u793eABC"

    def test_none_value_unchanged(self, three_case_config):
        params = [
            ExtractedParameter(
                key="notes",
                label="\u5099\u8003",
                value=None,
                selected=True,
            ),
        ]
        gen = CaseGenerator(three_case_config)
        cases = gen.generate_cases(params)
        assert cases["best"][0].value is None


# ===================================================================
# adjusted_value handling
# ===================================================================

class TestAdjustedValueCases:
    """When adjusted_value is set, it should also be adjusted by the case rules."""

    def test_adjusted_value_scaled_in_best(self, three_case_config):
        params = [
            ExtractedParameter(
                key="revenue_fy2024",
                label="\u58f2\u4e0a FY2024",
                value=100_000_000,
                adjusted_value=110_000_000,
                selected=True,
            ),
        ]
        gen = CaseGenerator(three_case_config)
        cases = gen.generate_cases(params)
        best = cases["best"][0]
        expected_adj = round(110_000_000 * CASE_RULES["best"]["revenue_multiplier"], 2)
        assert best.adjusted_value == expected_adj

    def test_adjusted_value_none_stays_none(self, three_case_config):
        params = [
            ExtractedParameter(
                key="revenue_fy2024",
                label="\u58f2\u4e0a FY2024",
                value=100_000_000,
                adjusted_value=None,
                selected=True,
            ),
        ]
        gen = CaseGenerator(three_case_config)
        cases = gen.generate_cases(params)
        assert cases["best"][0].adjusted_value is None


# ===================================================================
# Case diff report
# ===================================================================

class TestCaseDiffReport:
    """Test the human-readable diff report."""

    def test_diff_report_contains_all_cases(self, three_case_config, base_parameters):
        gen = CaseGenerator(three_case_config)
        cases = gen.generate_cases(base_parameters)
        report = gen.get_case_diff_report(cases)
        assert "base" in report
        assert "best" in report
        assert "worst" in report

    def test_diff_report_contains_parameter_keys(self, three_case_config, base_parameters):
        gen = CaseGenerator(three_case_config)
        cases = gen.generate_cases(base_parameters)
        report = gen.get_case_diff_report(cases)
        assert "revenue_fy2024" in report

    def test_diff_report_single_case(self):
        config = PhaseAConfig(cases=["base"])
        gen = CaseGenerator(config)
        params = [ExtractedParameter(key="x", label="X", value=1, selected=True)]
        cases = gen.generate_cases(params)
        report = gen.get_case_diff_report(cases)
        assert "one case" in report.lower() or "no diff" in report.lower()


# ===================================================================
# Keyword classification
# ===================================================================

class TestKeywordClassification:
    """Ensure the keyword lists are populated."""

    def test_revenue_keywords_not_empty(self):
        assert len(REVENUE_KEYWORDS) > 0

    def test_cost_keywords_not_empty(self):
        assert len(COST_KEYWORDS) > 0

    def test_growth_keywords_not_empty(self):
        assert len(GROWTH_KEYWORDS) > 0

    def test_churn_keywords_not_empty(self):
        assert len(CHURN_KEYWORDS) > 0

    def test_revenue_keywords_include_japanese(self):
        assert any(kw for kw in REVENUE_KEYWORDS if not kw.isascii())

    def test_cost_keywords_include_japanese(self):
        assert any(kw for kw in COST_KEYWORDS if not kw.isascii())
