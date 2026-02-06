"""Number normalization utilities for Japanese business documents."""
import re
from typing import Any, Optional


def normalize_japanese_number(text: str) -> Optional[float]:
    """Normalize Japanese number expressions to float.

    Examples:
        "1.5億" -> 150000000
        "3,000万円" -> 30000000
        "月100万×12" -> 12000000
        "500千円" -> 500000
        "30%" -> 0.3
    """
    if not isinstance(text, str):
        return None

    text = text.strip().replace(",", "").replace("、", "").replace(" ", "")

    # Handle percentage
    pct_match = re.match(r'^([0-9.]+)\s*[%％]$', text)
    if pct_match:
        return float(pct_match.group(1)) / 100

    # Handle multiplier expressions like "月100万×12"
    mult_match = re.match(r'.*?([0-9.]+)\s*(億|万|千)?\s*円?\s*[×x\*]\s*([0-9.]+)', text)
    if mult_match:
        base = float(mult_match.group(1))
        unit = mult_match.group(2)
        multiplier = float(mult_match.group(3))
        if unit == "億":
            base *= 100_000_000
        elif unit == "万":
            base *= 10_000
        elif unit == "千":
            base *= 1_000
        return base * multiplier

    # Standard number with Japanese unit
    num_match = re.match(r'^約?([0-9.]+)\s*(億|万|千)?\s*円?$', text)
    if num_match:
        value = float(num_match.group(1))
        unit = num_match.group(2)
        if unit == "億":
            value *= 100_000_000
        elif unit == "万":
            value *= 10_000
        elif unit == "千":
            value *= 1_000
        return value

    # Plain number
    plain_match = re.match(r'^([0-9.]+)$', text)
    if plain_match:
        return float(plain_match.group(1))

    return None


def normalize_value(value: Any) -> Any:
    """Normalize a value - try Japanese number parsing, then standard."""
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        result = normalize_japanese_number(value)
        if result is not None:
            return result
        try:
            return float(value)
        except (ValueError, TypeError):
            return value
    return value
