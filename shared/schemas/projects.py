"""Project schemas for API contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    """Request to create a new project."""

    name: str = Field(..., min_length=1, max_length=200)
    template_id: str = Field(default="v2_ib_grade")


class ProjectResponse(BaseModel):
    """API response for a project."""

    id: str
    name: str
    template_id: str
    owner: Optional[str] = None
    status: Literal["created", "active", "completed", "archived"] = "created"
    current_phase: int = 1
    memo: str = ""
    created_at: datetime
    updated_at: datetime


class ProjectState(BaseModel):
    """Full project state for resuming."""

    project: ProjectResponse
    current_run_id: Optional[str] = None
    phase_results: dict = Field(default_factory=dict)
    pending_edits: list = Field(default_factory=list)
