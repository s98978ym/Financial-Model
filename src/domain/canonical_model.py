"""Canonical business model schema."""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class ModelMetadata(BaseModel):
    project_name: str = ""
    currency: str = "JPY"
    horizon_years: int = 5
    source_documents: List[str] = Field(default_factory=list)
    notes: str = ""


class YearValue(BaseModel):
    year: str
    value: Optional[float] = None
    evidence: str = ""
    source: Literal["document", "inferred", "target", "default"] = "document"


class BreakevenTarget(BaseModel):
    year: str
    type: Literal["single_year", "cumulative"]
    evidence: str = ""
    source: Literal["document", "inferred", "target", "default"] = "document"


class FinancialTargets(BaseModel):
    revenue_targets: List[YearValue] = Field(default_factory=list)
    operating_profit_targets: List[YearValue] = Field(default_factory=list)
    ebitda_targets: List[YearValue] = Field(default_factory=list)
    breakeven_targets: List[BreakevenTarget] = Field(default_factory=list)


class DriverSeries(BaseModel):
    fy1: Optional[float] = None
    fy2: Optional[float] = None
    fy3: Optional[float] = None
    fy4: Optional[float] = None
    fy5: Optional[float] = None


class Driver(BaseModel):
    driver_id: str
    name: str
    unit: str = ""
    category: Literal["volume", "price", "rate", "capacity", "timing", "cost", "other"] = "other"
    series: DriverSeries = Field(default_factory=DriverSeries)
    source: Literal["document", "inferred", "target", "default", "manual", "benchmark"] = "document"
    confidence: float = 0.5
    mode: Literal["fixed", "bounded", "solve_for", "derived"] = "fixed"
    decision_required: bool = False
    evidence: str = ""
    tags: List[str] = Field(default_factory=list)


class RevenueEngine(BaseModel):
    engine_id: str
    engine_type: Literal[
        "subscription",
        "unit_economics",
        "progression",
        "project_capacity",
        "marketplace",
        "usage",
        "advertising",
        "licensing",
        "custom_formula",
    ]
    name: str
    drivers: List[Driver] = Field(default_factory=list)
    revenue_equation: str = ""
    cost_equation: Optional[str] = None
    constraints: dict = Field(default_factory=dict)
    assumptions: List[str] = Field(default_factory=list)


class BusinessSegment(BaseModel):
    segment_id: str
    name: str
    customer_type: str = ""
    offer_type: str = ""
    engines: List[RevenueEngine] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)


class CostPool(BaseModel):
    cost_pool_id: str
    name: str
    behavior: Literal["fixed", "variable", "semi_variable", "step_fixed", "planned_capex"] = "fixed"
    equation: str = ""
    allocation_basis: str = ""
    evidence: str = ""


class BindingSpec(BaseModel):
    segment_id: Optional[str] = None
    engine_id: Optional[str] = None
    target_type: Literal["pl_line", "sheet_cell", "kpi", "scenario_knob"]
    target_ref: str
    transform: str = ""


class CanonicalBusinessModel(BaseModel):
    metadata: ModelMetadata = Field(default_factory=ModelMetadata)
    targets: FinancialTargets = Field(default_factory=FinancialTargets)
    segments: List[BusinessSegment] = Field(default_factory=list)
    cost_pools: List[CostPool] = Field(default_factory=list)
    bindings: List[BindingSpec] = Field(default_factory=list)
    global_assumptions: List[str] = Field(default_factory=list)

