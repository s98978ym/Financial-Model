"""Heuristic extraction of model and PL signals directly from PDF text."""

from __future__ import annotations

import re
from typing import Dict, List


NUMBER_PATTERN = r"(-?\d+(?:,\d{3})*(?:\.\d+)?)"


def extract_pl_signals(text: str) -> Dict[str, List[float]]:
    """Extract major PL line series from flattened PDF text.

    The FAM source PDF expresses these values in million JPY, so extracted
    sequences are scaled by 1,000,000.
    """

    series_map: Dict[str, List[float]] = {}
    label_patterns = {
        "売上": [r"(?:売上高|売上)\s+" + _five_numbers_pattern()],
        "粗利": [r"粗利\s+" + _five_numbers_pattern()],
        "事業運営費（OPEX）": [
            r"販売費及び一般管理費\s+" + _five_numbers_pattern(),
            r"OPEX\s+" + _five_numbers_pattern(),
        ],
    }

    for label, patterns in label_patterns.items():
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                values = [round(_parse_number(match.group(index)) * 1_000_000, 4) for index in range(1, 6)]
                series_map[label] = values
                break

    return series_map


def extract_academy_signals(text: str) -> Dict[str, List[float]]:
    """Extract academy model-sheet style signals from PDF text."""

    signals: Dict[str, List[float]] = {}

    price_match = re.search(r"C級\s*" + NUMBER_PATTERN + r"万円", text)
    if price_match:
        base_price = _parse_number(price_match.group(1)) * 10_000
        signals["academy_price"] = [base_price] * 5

    students_match = re.search(
        r"FY26[:：]\s*" + NUMBER_PATTERN
        + r"、FY27[:：]\s*" + NUMBER_PATTERN
        + r"、FY28[:：]\s*" + NUMBER_PATTERN
        + r"、FY29[:：]\s*" + NUMBER_PATTERN
        + r"、FY30[:：]\s*" + NUMBER_PATTERN,
        text,
    )
    if students_match:
        signals["academy_students"] = [
            _parse_number(students_match.group(index))
            for index in range(1, 6)
        ]

    revenue_match = re.search(r"アカデミー\s+" + _five_numbers_pattern(), text)
    if revenue_match:
        signals["academy_revenue"] = [
            round(_parse_number(revenue_match.group(index)) * 1_000_000, 4)
            for index in range(1, 6)
        ]

    return signals


def extract_meal_signals(text: str) -> Dict[str, List[float]]:
    """Extract meal model signals from a per-meal offer description."""

    signals: Dict[str, List[float]] = {}
    meal_offer_match = re.search(
        NUMBER_PATTERN + r"円/食×" + NUMBER_PATTERN + r"食/人×" + NUMBER_PATTERN + r"人/月",
        text,
    )
    if not meal_offer_match:
        return signals

    meal_price = _parse_number(meal_offer_match.group(1))
    meals_per_person = _parse_number(meal_offer_match.group(2))
    people_per_team = _parse_number(meal_offer_match.group(3))

    price_per_item = meal_price / 3
    items_per_meal = 3.0
    meals_per_year = meals_per_person * people_per_team * 12

    signals["price_per_item"] = [price_per_item] * 5
    signals["items_per_meal"] = [items_per_meal] * 5
    signals["meals_per_year"] = [meals_per_year] * 5
    return signals


def _five_numbers_pattern() -> str:
    return r"\s*".join([NUMBER_PATTERN] * 5)


def _parse_number(raw: str) -> float:
    return float(raw.replace(",", ""))
