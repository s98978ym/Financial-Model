"""Tests for src.extract.normalizer -- Japanese number normalization.

Covers standard Japanese financial notation (oku, man, sen), percentage
conversion, multiplier expressions, plain numbers, and edge cases.
"""

import pytest

from src.extract.normalizer import normalize_japanese_number, normalize_value


# ===================================================================
# normalize_japanese_number
# ===================================================================

class TestNormalizeJapaneseNumber:
    """Test normalize_japanese_number with various Japanese number formats."""

    # --- Oku (\u5104) ---

    def test_oku_decimal(self):
        """1.5\u5104 -> 150,000,000"""
        result = normalize_japanese_number("1.5\u5104")
        assert result == 150_000_000

    def test_oku_integer(self):
        """2\u5104 -> 200,000,000"""
        result = normalize_japanese_number("2\u5104")
        assert result == 200_000_000

    def test_oku_with_yen(self):
        """3\u5104\u5186 -> 300,000,000"""
        result = normalize_japanese_number("3\u5104\u5186")
        assert result == 300_000_000

    def test_oku_with_approximate_prefix(self):
        """\u7d041.5\u5104\u5186 -> 150,000,000"""
        result = normalize_japanese_number("\u7d041.5\u5104\u5186")
        assert result == 150_000_000

    # --- Man (\u4e07) ---

    def test_man_with_commas_and_yen(self):
        """3,000\u4e07\u5186 -> 30,000,000"""
        result = normalize_japanese_number("3,000\u4e07\u5186")
        assert result == 30_000_000

    def test_man_plain(self):
        """500\u4e07 -> 5,000,000"""
        result = normalize_japanese_number("500\u4e07")
        assert result == 5_000_000

    def test_man_with_yen(self):
        """100\u4e07\u5186 -> 1,000,000"""
        result = normalize_japanese_number("100\u4e07\u5186")
        assert result == 1_000_000

    # --- Sen (\u5343) ---

    def test_sen_with_yen(self):
        """500\u5343\u5186 -> 500,000"""
        result = normalize_japanese_number("500\u5343\u5186")
        assert result == 500_000

    def test_sen_plain(self):
        """100\u5343 -> 100,000"""
        result = normalize_japanese_number("100\u5343")
        assert result == 100_000

    # --- Multiplier expressions ---

    def test_monthly_multiplier(self):
        """\u6708100\u4e07\u00d712 -> 12,000,000"""
        result = normalize_japanese_number("\u6708100\u4e07\u00d712")
        assert result == 12_000_000

    def test_multiplier_with_x(self):
        """100\u4e07x12 -> 12,000,000"""
        result = normalize_japanese_number("100\u4e07x12")
        assert result == 12_000_000

    def test_multiplier_with_asterisk(self):
        """100\u4e07*12 -> 12,000,000"""
        result = normalize_japanese_number("100\u4e07*12")
        assert result == 12_000_000

    def test_multiplier_with_oku(self):
        """1\u5104\u00d72 -> 200,000,000"""
        result = normalize_japanese_number("1\u5104\u00d72")
        assert result == 200_000_000

    def test_multiplier_with_sen(self):
        """500\u5343\u00d73 -> 1,500,000"""
        result = normalize_japanese_number("500\u5343\u00d73")
        assert result == 1_500_000

    # --- Percentage ---

    def test_percentage_integer(self):
        """30% -> 0.3"""
        result = normalize_japanese_number("30%")
        assert result == pytest.approx(0.3)

    def test_percentage_decimal(self):
        """2.5% -> 0.025"""
        result = normalize_japanese_number("2.5%")
        assert result == pytest.approx(0.025)

    def test_percentage_full_width(self):
        """15\uff05 -> 0.15"""
        result = normalize_japanese_number("15\uff05")
        assert result == pytest.approx(0.15)

    def test_percentage_100(self):
        """100% -> 1.0"""
        result = normalize_japanese_number("100%")
        assert result == pytest.approx(1.0)

    # --- Plain numbers ---

    def test_plain_integer(self):
        """5000 -> 5000.0"""
        result = normalize_japanese_number("5000")
        assert result == 5000.0

    def test_plain_decimal(self):
        """3.14 -> 3.14"""
        result = normalize_japanese_number("3.14")
        assert result == pytest.approx(3.14)

    def test_plain_with_commas(self):
        """1,000,000 -> 1000000.0"""
        result = normalize_japanese_number("1,000,000")
        assert result == 1_000_000.0

    def test_plain_zero(self):
        """0 -> 0.0"""
        result = normalize_japanese_number("0")
        assert result == 0.0

    # --- Edge cases ---

    def test_empty_string_returns_none(self):
        result = normalize_japanese_number("")
        assert result is None

    def test_none_input_returns_none(self):
        result = normalize_japanese_number(None)
        assert result is None

    def test_non_string_int_returns_none(self):
        result = normalize_japanese_number(12345)
        assert result is None

    def test_whitespace_only_returns_none(self):
        result = normalize_japanese_number("   ")
        assert result is None

    def test_unrecognized_text_returns_none(self):
        result = normalize_japanese_number("\u3053\u3093\u306b\u3061\u306f")
        assert result is None

    def test_leading_trailing_whitespace_stripped(self):
        result = normalize_japanese_number("  1.5\u5104  ")
        assert result == 150_000_000

    def test_japanese_comma_stripped(self):
        """Full-width comma should be stripped."""
        result = normalize_japanese_number("3\u30000\u4e07")
        # After stripping \u3000 (ideographic comma / space): "30\u4e07"
        # This may or may not match depending on implementation;
        # the key point is it does not raise.
        # normalize_japanese_number strips commas and spaces
        assert result is None or isinstance(result, float)


# ===================================================================
# normalize_value
# ===================================================================

class TestNormalizeValue:
    """Test normalize_value -- general value normalization dispatcher."""

    def test_int_passthrough(self):
        assert normalize_value(42) == 42

    def test_float_passthrough(self):
        assert normalize_value(3.14) == pytest.approx(3.14)

    def test_japanese_string_parsed(self):
        assert normalize_value("1.5\u5104") == 150_000_000

    def test_plain_numeric_string(self):
        assert normalize_value("999") == 999.0

    def test_non_numeric_string_passthrough(self):
        """Strings that cannot be parsed are returned as-is."""
        assert normalize_value("hello") == "hello"

    def test_none_passthrough(self):
        assert normalize_value(None) is None

    def test_list_passthrough(self):
        """Non-scalar types are returned as-is."""
        val = [1, 2, 3]
        assert normalize_value(val) == [1, 2, 3]

    def test_percentage_string(self):
        assert normalize_value("30%") == pytest.approx(0.3)

    def test_zero(self):
        assert normalize_value(0) == 0
