"""Phase-specific request/response schemas."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Phase 1: Scan
# ---------------------------------------------------------------------------

class Phase1Request(BaseModel):
    project_id: str
    document_id: str
    template_id: str = "v2_ib_grade"
    colors: Dict[str, str] = Field(default_factory=lambda: {
        "input_color": "FFFFF2CC",
        "formula_color": "FF0000FF",
    })


class CatalogItemSchema(BaseModel):
    sheet: str
    cell: str
    labels: List[str] = Field(default_factory=list)
    units: str = ""
    period: str = ""
    block: str = ""
    current_value: Any = None
    data_type: str = "n"
    is_formula: bool = False


class Phase1Response(BaseModel):
    catalog: Dict[str, Any]
    document_summary: Dict[str, Any]


# ---------------------------------------------------------------------------
# Phase 2: Business Model Analysis
# ---------------------------------------------------------------------------

class Phase2Request(BaseModel):
    project_id: str
    document_id: str
    feedback: str = ""


class EvidenceSchema(BaseModel):
    quote: str = ""
    page: Optional[int] = None
    rationale: str = ""


class FinancialTargetSchema(BaseModel):
    year: str
    value: float
    evidence: Optional[EvidenceSchema] = None


class Phase2Result(BaseModel):
    proposals: List[Dict[str, Any]]
    financial_targets: Dict[str, Any]
    industry: str = ""
    business_model_type: str = ""


# ---------------------------------------------------------------------------
# Phase 3: Template Structure Mapping
# ---------------------------------------------------------------------------

class Phase3Request(BaseModel):
    project_id: str
    selected_proposal: str
    catalog_summary: Dict[str, Any]


class SheetMappingSchema(BaseModel):
    sheet_name: str
    purpose: Literal[
        "revenue_model", "cost_detail", "pl_summary",
        "assumptions", "headcount", "capex", "other",
    ]
    mapped_segment: Optional[str] = None
    confidence: float = 0.0


class Phase3Result(BaseModel):
    sheet_mappings: List[SheetMappingSchema]
    suggestions: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Phase 4: Model Design
# ---------------------------------------------------------------------------

class Phase4Request(BaseModel):
    project_id: str
    bm_result_ref: str = ""
    ts_result_ref: str = ""
    catalog_ref: str = ""
    edits: List[Dict[str, Any]] = Field(default_factory=list)


class CellAssignmentSchema(BaseModel):
    sheet: str
    cell: str
    concept: str
    category: str = ""
    segment: Optional[str] = None
    period: str = ""
    unit: str = ""
    confidence: float = 0.0
    label_match: str = ""
    warnings: List[str] = Field(default_factory=list)


class Phase4Result(BaseModel):
    cell_assignments: List[CellAssignmentSchema]
    unmapped_cells: List[Dict[str, Any]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Phase 5: Parameter Extraction
# ---------------------------------------------------------------------------

class Phase5Request(BaseModel):
    project_id: str
    md_result_ref: str = ""
    document_excerpt_chars: int = 10000
    edits: List[Dict[str, Any]] = Field(default_factory=list)


class ExtractionSchema(BaseModel):
    sheet: str
    cell: str
    value: Any = None
    original_text: str = ""
    source: Literal["document", "inferred", "default"] = "default"
    confidence: float = 0.0
    evidence: Optional[EvidenceSchema] = None
    warnings: List[str] = Field(default_factory=list)


class ExtractionStats(BaseModel):
    total: int = 0
    document_source: int = 0
    inferred_source: int = 0
    default_source: int = 0
    avg_confidence: float = 0.0


class Phase5Result(BaseModel):
    extractions: List[ExtractionSchema]
    warnings: List[str] = Field(default_factory=list)
    stats: ExtractionStats = Field(default_factory=ExtractionStats)
