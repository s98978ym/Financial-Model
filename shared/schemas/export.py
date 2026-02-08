"""Export schemas."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class ExportRequest(BaseModel):
    """Request to generate Excel file(s)."""

    project_id: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    scenarios: List[Literal["base", "best", "worst"]] = Field(
        default=["base", "best", "worst"]
    )
    options: Dict[str, Any] = Field(default_factory=lambda: {
        "include_needs_review": True,
        "include_case_diff": True,
        "best_multipliers": {"revenue": 1.2, "cost": 0.9},
        "worst_multipliers": {"revenue": 0.8, "cost": 1.15},
    })


class ExportFileInfo(BaseModel):
    scenario: str
    url: str
    expires_at: Optional[str] = None


class ValidationInfo(BaseModel):
    formulas_preserved: bool = True
    no_excel_errors: bool = True
    full_calc_on_load: bool = True
    changed_cells: int = 0


class ExportResult(BaseModel):
    files: List[ExportFileInfo] = Field(default_factory=list)
    needs_review_url: Optional[str] = None
    validation: ValidationInfo = Field(default_factory=ValidationInfo)
