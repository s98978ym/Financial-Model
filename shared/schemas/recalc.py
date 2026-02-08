"""Recalculation schemas."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class RecalcRequest(BaseModel):
    """Request to recalculate PL from parameters."""

    project_id: str
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Cell reference -> value mapping (e.g., '収益モデル1::C8': 50000)",
    )
    edited_cells: Dict[str, Any] = Field(
        default_factory=dict,
        description="Cells modified by user (overlay on parameters)",
    )
    scenario: Literal["base", "best", "worst"] = "base"


class PLSummary(BaseModel):
    """5-year PL summary."""

    revenue: List[float] = Field(default_factory=list)
    cogs: List[float] = Field(default_factory=list)
    gross_profit: List[float] = Field(default_factory=list)
    opex: List[float] = Field(default_factory=list)
    operating_profit: List[float] = Field(default_factory=list)
    fcf: List[float] = Field(default_factory=list)
    cumulative_fcf: List[float] = Field(default_factory=list)


class KPIs(BaseModel):
    """Key performance indicators."""

    break_even_year: Optional[str] = None
    cumulative_break_even_year: Optional[str] = None
    revenue_cagr: float = 0.0
    fy5_op_margin: float = 0.0


class RecalcResponse(BaseModel):
    """Response from PL recalculation."""

    pl_summary: PLSummary
    kpis: KPIs
    charts_data: Dict[str, Any] = Field(default_factory=dict)
    scenario: str = "base"
