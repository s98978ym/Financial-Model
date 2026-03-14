"""Evidence and assumption ledger models."""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class EvidenceRef(BaseModel):
    ref_type: Literal[
        "document_quote",
        "historical_actual",
        "benchmark",
        "internal_case",
        "management_note",
        "solver_result",
    ]
    source_id: str = ""
    location: str = ""
    quote: str = ""
    rationale: str = ""


class ValueRange(BaseModel):
    min: Optional[float] = None
    base: Optional[float] = None
    max: Optional[float] = None


class AssumptionRecord(BaseModel):
    record_id: str
    object_type: Literal["driver", "target", "cost_pool", "constraint"]
    object_id: str
    metric_name: str
    value: Optional[float] = None
    unit: str = ""
    source_type: Literal[
        "document",
        "historical_actual",
        "benchmark",
        "internal_case",
        "management_decision",
        "solver_derived",
        "manual_input",
        "default",
    ]
    confidence: float = 0.5
    evidence_refs: List[EvidenceRef] = Field(default_factory=list)
    allowed_range: ValueRange = Field(default_factory=ValueRange)
    owner: str = ""
    review_status: Literal[
        "grounded",
        "needs_review",
        "decision_required",
        "approved",
        "rejected",
    ] = "needs_review"
    board_ready: bool = False
    explanation: str = ""


class AssumptionLedger(BaseModel):
    records: List[AssumptionRecord] = Field(default_factory=list)
