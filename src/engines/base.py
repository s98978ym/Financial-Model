"""Common interfaces and helpers for revenue engine plugins."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Protocol


DEFAULT_HORIZON_YEARS = 5


@dataclass
class EngineInput:
    config: Dict[str, Any]
    horizon_years: int = DEFAULT_HORIZON_YEARS


@dataclass
class EngineOutput:
    revenue: List[int]
    variable_cost: List[int]
    gross_profit: List[int]
    warnings: List[str] = field(default_factory=list)
    required_driver_names: List[str] = field(default_factory=list)
    constraint_hints: List[str] = field(default_factory=list)


class RevenueEnginePlugin(Protocol):
    engine_type: str

    def compute(self, engine_input: EngineInput) -> EngineOutput:
        ...


def zero_series(horizon_years: int = DEFAULT_HORIZON_YEARS) -> List[int]:
    return [0] * horizon_years


def coerce_series(values: Any, horizon_years: int = DEFAULT_HORIZON_YEARS) -> List[float]:
    raw = values or []
    series: List[float] = []
    for idx in range(horizon_years):
        if idx < len(raw):
            try:
                series.append(float(raw[idx]))
            except (TypeError, ValueError):
                series.append(0.0)
        else:
            series.append(0.0)
    return series
