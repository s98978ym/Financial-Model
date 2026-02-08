"""Document upload endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

router = APIRouter()

# In-memory store for MVP
_documents: Dict[str, dict] = {}


@router.post("/documents/upload", status_code=201)
async def upload_document(
    project_id: str = Form(...),
    kind: str = Form("file"),
    text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    """Upload a document (file or text paste)."""
    doc_id = f"doc_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()

    if kind == "text" and text:
        doc = {
            "id": doc_id,
            "project_id": project_id,
            "kind": "text",
            "filename": None,
            "size_bytes": len(text.encode("utf-8")),
            "status": "uploaded",
            "extracted_chars": len(text),
            "extracted_text": text,
            "created_at": now,
        }
    elif kind == "file" and file:
        content = await file.read()
        if len(content) > 20 * 1024 * 1024:  # 20MB limit
            raise HTTPException(
                status_code=413,
                detail={"code": "FILE_TOO_LARGE", "message": "ファイルサイズは20MB以下にしてください"},
            )
        doc = {
            "id": doc_id,
            "project_id": project_id,
            "kind": "file",
            "filename": file.filename,
            "size_bytes": len(content),
            "status": "uploaded",
            "extracted_chars": 0,
            "raw_content": content,  # In production: save to Supabase Storage
            "created_at": now,
        }
    else:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "VALIDATION_ERROR",
                "message": "Either 'text' or 'file' must be provided",
            },
        )

    _documents[doc_id] = doc

    # Return without raw_content
    return {
        "id": doc["id"],
        "project_id": doc["project_id"],
        "kind": doc["kind"],
        "filename": doc.get("filename"),
        "size_bytes": doc["size_bytes"],
        "status": doc["status"],
        "extracted_chars": doc["extracted_chars"],
    }


def get_document(doc_id: str) -> dict:
    """Get document by ID (internal helper)."""
    doc = _documents.get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail={"code": "DOCUMENT_NOT_FOUND"})
    return doc
