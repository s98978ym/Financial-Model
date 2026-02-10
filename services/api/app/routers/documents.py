"""Document upload endpoints."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from .. import db

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/documents/upload", status_code=201)
async def upload_document(
    project_id: str = Form(...),
    kind: str = Form("file"),
    text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    """Upload a document (file or text paste)."""
    if kind == "text" and text:
        doc = db.create_document(
            project_id=project_id,
            kind="text",
            filename="",
            extracted_text=text,
            meta_json={"size_bytes": len(text.encode("utf-8"))},
        )
    elif kind == "file" and file:
        content = await file.read()
        if len(content) > 20 * 1024 * 1024:  # 20MB limit
            raise HTTPException(
                status_code=413,
                detail={"code": "FILE_TOO_LARGE", "message": "ファイルサイズは20MB以下にしてください"},
            )

        # Upload to Supabase Storage (or local fallback)
        storage_path = ""
        try:
            from core.storage import upload_file
            content_type = file.content_type or "application/octet-stream"
            storage_path = upload_file(
                project_id=project_id,
                filename=file.filename or "upload",
                content=content,
                content_type=content_type,
            )
        except Exception as e:
            logger.warning("Storage upload failed: %s — continuing without storage", e)

        doc = db.create_document(
            project_id=project_id,
            kind="file",
            filename=file.filename or "",
            storage_path=storage_path,
            meta_json={"size_bytes": len(content)},
        )
    else:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "VALIDATION_ERROR",
                "message": "Either 'text' or 'file' must be provided",
            },
        )

    return {
        "id": doc["id"],
        "project_id": doc["project_id"],
        "kind": doc["kind"],
        "filename": doc.get("filename"),
        "size_bytes": doc.get("meta_json", {}).get("size_bytes", 0),
        "status": "uploaded",
        "extracted_chars": len(doc.get("extracted_text") or ""),
    }


def get_document(doc_id: str) -> dict:
    """Get document by ID (internal helper)."""
    doc = db.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail={"code": "DOCUMENT_NOT_FOUND"})
    return doc
