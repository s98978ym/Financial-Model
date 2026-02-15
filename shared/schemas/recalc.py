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


class SegmentSummary(BaseModel):
    """Per-segment revenue and gross profit."""

    name: str = ""
    revenue: List[float] = Field(default_factory=list)
    cogs: List[float] = Field(default_factory=list)
    gross_profit: List[float] = Field(default_factory=list)
    cogs_rate: float = 0.0
    growth_rate: float = 0.0


class SGABreakdown(BaseModel):
    """SGA category breakdown — flat totals per category (5-year)."""

    payroll: List[int] = Field(default_factory=list)
    marketing: List[int] = Field(default_factory=list)
    office: List[int] = Field(default_factory=list)
    system: List[int] = Field(default_factory=list)
    other: List[int] = Field(default_factory=list)


class PayrollRoleDetail(BaseModel):
    """Single personnel role: salary x headcount."""

    label: str = ""
    salary: int = 0
    headcount: List[int] = Field(default_factory=list)
    cost: List[int] = Field(default_factory=list)


class PayrollDetail(BaseModel):
    """Payroll with per-role breakdown."""

    roles: Dict[str, PayrollRoleDetail] = Field(default_factory=dict)
    total: List[int] = Field(default_factory=list)


class MarketingDetail(BaseModel):
    """Marketing with subcategory breakdown."""

    categories: Dict[str, List[int]] = Field(default_factory=dict)
    total: List[int] = Field(default_factory=list)


class SGADetail(BaseModel):
    """Nested SGA detail with role-level payroll and marketing subcategories."""

    payroll: PayrollDetail = Field(default_factory=PayrollDetail)
    marketing: MarketingDetail = Field(default_factory=MarketingDetail)
    office: List[int] = Field(default_factory=list)
    system: List[int] = Field(default_factory=list)
    other: List[int] = Field(default_factory=list)


class PLSummary(BaseModel):
    """5-year PL summary with segment and SGA breakdown."""

    revenue: List[float] = Field(default_factory=list)
    cogs: List[float] = Field(default_factory=list)
    gross_profit: List[float] = Field(default_factory=list)
    opex: List[float] = Field(default_factory=list)
    depreciation: List[float] = Field(default_factory=list)
    capex: List[float] = Field(default_factory=list)
    operating_profit: List[float] = Field(default_factory=list)
    fcf: List[float] = Field(default_factory=list)
    cumulative_fcf: List[float] = Field(default_factory=list)
    # Segment breakdown
    segments: List[SegmentSummary] = Field(default_factory=list)
    # SGA category breakdown (flat totals for charts)
    sga_breakdown: Optional[SGABreakdown] = None
    # SGA detail with role-level payroll & marketing subcategories
    sga_detail: Optional[SGADetail] = None


class DepreciationSettings(BaseModel):
    """Depreciation calculation settings."""

    mode: str = "manual"  # "manual" or "auto"
    useful_life: int = 5
    method: str = "straight_line"  # "straight_line" or "declining_balance"
    existing_depreciation: float = 0


class KPIs(BaseModel):
    """Key performance indicators."""

    break_even_year: Optional[str] = None
    cumulative_break_even_year: Optional[str] = None
    revenue_cagr: float = 0.0
    fy5_op_margin: float = 0.0
    gp_margin: float = 0.0


class RecalcResponse(BaseModel):
    """Response from PL recalculation."""

    pl_summary: PLSummary
    kpis: KPIs
    charts_data: Dict[str, Any] = Field(default_factory=dict)
    scenario: str = "base"
    depreciation_settings: Optional[DepreciationSettings] = None
