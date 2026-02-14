"""Document upload schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class DocumentUploadResponse(BaseModel):
    """Response after document upload."""

    id: str
    project_id: str
    kind: Literal["file", "text"]
    filename: Optional[str] = None
    size_bytes: int = 0
    status: str = "uploaded"
    extracted_chars: int = 0
    created_at: Optional[datetime] = None


class DocumentSummary(BaseModel):
    """Summary of extracted document content."""

    total_chars: int
    pages: int = 0
    preview: str = ""
