"""Job tracking schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class JobLogEntry(BaseModel):
    ts: str
    msg: str
    payload: Optional[Dict[str, Any]] = None


class JobStatus(BaseModel):
    id: str
    status: Literal["queued", "running", "completed", "failed", "timeout"] = "queued"
    progress: int = Field(default=0, ge=0, le=100)
    phase: int = 0
    logs: List[JobLogEntry] = Field(default_factory=list)
    result: Optional[str] = None
    error_msg: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class JobCreated(BaseModel):
    """Response when a job is queued."""

    job_id: str
    status: str = "queued"
    phase: int = 0
    poll_url: str = ""
