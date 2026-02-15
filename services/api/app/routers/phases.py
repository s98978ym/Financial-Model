"""Phase execution endpoints (Phase 1-5).

Phase 1 (scan) is synchronous for small files.
Phases 2-5 are async (Celery jobs) since they involve LLM calls.
"""

from __future__ import annotations

import logging
import importlib
import os
import threading
from typing import Optional

from fastapi import APIRouter, HTTPException

from .. import db
from .jobs import create_job

logger = logging.getLogger(__name__)
router = APIRouter()

# Celery dispatch is enabled when REDIS_URL is set
_CELERY_ENABLED = bool(os.environ.get("REDIS_URL"))

# Map Celery task names → actual task functions for sync fallback
_TASK_FUNCTIONS = {}


def _register_task(task_name: str):
    """Lazily import and cache the task function."""
    if task_name in _TASK_FUNCTIONS:
        return _TASK_FUNCTIONS[task_name]
    fn = None
    try:
        if "phase2" in task_name:
            from services.worker.tasks.phase2 import run_bm_analysis
            fn = run_bm_analysis
        elif "phase3" in task_name:
            from services.worker.tasks.phase3 import run_template_mapping
            fn = run_template_mapping
        elif "phase4" in task_name:
            from services.worker.tasks.phase4 import run_model_design
            fn = run_model_design
        elif "phase5" in task_name:
            from services.worker.tasks.phase5 import run_parameter_extraction
            fn = run_parameter_extraction
    except Exception as e:
        logger.error("Failed to import task %s: %s", task_name, e)
    _TASK_FUNCTIONS[task_name] = fn
    return fn


def _dispatch_celery(task_name: str, job_id: str):
    """Dispatch a Celery task if enabled, otherwise run synchronously in background thread."""
    if _CELERY_ENABLED:
        try:
            from services.worker.celery_app import app as celery_app
            celery_app.send_task(task_name, args=[job_id])
            logger.info("Dispatched %s for job %s via Celery", task_name, job_id)
            return
        except Exception as e:
            logger.exception("Celery dispatch failed for %s (job %s), falling back to sync", task_name, job_id)
            # Fall through to sync fallback instead of leaving job stuck in "queued"

    # Sync fallback: run task in background thread
    fn = _register_task(task_name)
    if fn is None:
        logger.error("No sync fallback for %s — job %s will not be processed", task_name, job_id)
        db.update_job(job_id, status="failed", error_msg="Worker unavailable")
        return

    def _run():
        try:
            logger.info("Running %s synchronously for job %s", task_name, job_id)
            # Celery tasks with bind=True expect (self, job_id).
            # Task.run is the raw function; Task.__call__ injects self.
            # When Celery is installed, fn is a Task object — calling fn(job_id)
            # triggers Task.__call__ which correctly passes self for bind=True.
            # When fn is a raw function, just call it directly.
            fn(job_id)
        except Exception as e:
            logger.exception("Sync task %s failed for job %s: %s", task_name, job_id, e)
            try:
                db.update_job(job_id, status="failed", error_msg=str(e)[:500])
            except Exception:
                logger.error("Failed to update job %s status to failed", job_id)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    logger.info("Started sync thread for %s (job %s)", task_name, job_id)


TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "templates")


def _resolve_template(template_id: str) -> str:
    """Resolve template_id to an absolute file path."""
    # Map known IDs → filenames
    name_map = {
        "v2_ib_grade": "base.xlsx",
        "base": "base.xlsx",
        "worst": "worst.xlsx",
    }
    filename = name_map.get(template_id, f"{template_id}.xlsx")
    path = os.path.normpath(os.path.join(TEMPLATE_DIR, filename))
    if os.path.exists(path):
        return path
    # Fallback: try all xlsx files in templates/
    for f in os.listdir(TEMPLATE_DIR):
        if f.endswith(".xlsx"):
            return os.path.join(TEMPLATE_DIR, f)
    raise FileNotFoundError(f"Template not found: {template_id}")


@router.post("/phase1/scan")
async def phase1_scan(body: dict):
    """Phase 1: Scan template + extract document text.

    Synchronous — no LLM, just file parsing.
    """
    project_id = body.get("project_id")
    document_id = body.get("document_id")
    template_id = body.get("template_id", "v2_ib_grade")
    colors = body.get("colors", {})
    input_color = colors.get("input_color", "FFFFF2CC")

    if not project_id or not document_id:
        raise HTTPException(
            status_code=422,
            detail={"code": "VALIDATION_ERROR", "message": "project_id and document_id required"},
        )

    # --- Ensure run exists ---
    run = db.get_latest_run(project_id)
    if not run:
        run = db.create_run(project_id)

    # ------------------------------------------------------------------
    # 1. Template scan
    # ------------------------------------------------------------------
    catalog_dict: dict = {"items": [], "block_index": {}, "total_items": 0}
    try:
        template_path = _resolve_template(template_id)
        from src.catalog.scanner import scan_template
        catalog = scan_template(template_path, input_color=input_color)
        # Serialize Pydantic model to dict
        items_list = [item.model_dump() for item in catalog.items]
        block_index = {}
        for key, block_items in catalog.blocks.items():
            block_index[key] = [
                item.model_dump()
                for item in block_items
            ]
        catalog_dict = {
            "items": items_list,
            "block_index": block_index,
            "total_items": len(items_list),
        }
        logger.info("Template scan: %d items in %d blocks", len(items_list), len(block_index))
    except Exception as e:
        logger.error("Template scan failed: %s", e)
        catalog_dict["error"] = str(e)

    # ------------------------------------------------------------------
    # 2. Document text extraction
    # ------------------------------------------------------------------
    doc_summary: dict = {"total_chars": 0, "pages": 0, "preview": ""}
    document_text = ""

    doc = db.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail={"code": "DOCUMENT_NOT_FOUND"})

    # For text-pasted documents, the text is already available
    if doc.get("extracted_text"):
        document_text = doc["extracted_text"]
        doc_summary = {
            "total_chars": len(document_text),
            "pages": 1,
            "preview": document_text[:500],
        }
    elif doc.get("storage_path"):
        # File-based document — download and extract
        try:
            from core.storage import download_file
            from src.ingest.reader import read_document
            import gc
            import tempfile

            content = download_file(doc["storage_path"])
            if content:
                file_size_mb = len(content) / (1024 * 1024)
                logger.info(
                    "Phase 1: extracting text from %.1f MB file: %s",
                    file_size_mb, doc.get("filename", "unknown"),
                )

                filename = doc.get("filename") or "upload.pdf"
                suffix = os.path.splitext(filename)[1] or ".pdf"
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                    tmp.write(content)
                    tmp_path = tmp.name

                # Release the file content from memory before extraction
                del content
                gc.collect()

                try:
                    doc_content = read_document(tmp_path)
                    document_text = doc_content.full_text
                    doc_summary = {
                        "total_chars": doc_content.text_char_count,
                        "pages": doc_content.total_pages,
                        "preview": document_text[:500],
                    }
                finally:
                    os.unlink(tmp_path)
                    gc.collect()
            else:
                doc_summary["error"] = "File content not found in storage"
        except Exception as e:
            logger.error("Document extraction failed: %s", e)
            doc_summary["error"] = str(e)

    # ------------------------------------------------------------------
    # 3. Store extracted text back to document record & save phase result
    # ------------------------------------------------------------------
    if document_text and not doc.get("extracted_text"):
        # Update document with extracted text for later phases
        if db._use_pg():
            with db.get_conn() as conn:
                if conn:
                    cur = conn.cursor()
                    cur.execute(
                        "UPDATE documents SET extracted_text = %s WHERE id = %s",
                        (document_text, document_id),
                    )
        else:
            mem_doc = db._mem_documents.get(document_id)
            if mem_doc:
                mem_doc["extracted_text"] = document_text

    # Save Phase 1 result
    db.save_phase_result(run_id=run["id"], phase=1, raw_json={
        "catalog": catalog_dict,
        "document_summary": doc_summary,
    })

    # Update project phase
    db.update_project(project_id, current_phase=2)

    return {
        "catalog": catalog_dict,
        "document_summary": doc_summary,
    }


@router.post("/phase2/analyze", status_code=202)
async def phase2_analyze(body: dict):
    """Phase 2: Business Model Analysis (async job)."""
    project_id = body.get("project_id")
    document_id = body.get("document_id")
    feedback = body.get("feedback", "")

    if not project_id:
        raise HTTPException(
            status_code=422,
            detail={"code": "VALIDATION_ERROR", "message": "project_id required"},
        )

    # Auto-resolve document_id from project's documents if not provided
    if not document_id:
        docs = db.get_documents_by_project(project_id)
        if docs:
            document_id = docs[0]["id"]
            logger.info("Auto-resolved document_id=%s for project %s", document_id, project_id)

    if not document_id:
        raise HTTPException(
            status_code=422,
            detail={"code": "VALIDATION_ERROR", "message": "document_id required — upload a document in Phase 1 first"},
        )

    run = db.get_latest_run(project_id)
    if not run:
        run = db.create_run(project_id)

    job = create_job(phase=2, run_id=run["id"], payload={
        "project_id": project_id,
        "document_id": document_id,
        "feedback": feedback,
    })

    _dispatch_celery("tasks.phase2.run_bm_analysis", job["id"])

    return {
        "job_id": job["id"],
        "status": "queued",
        "phase": 2,
        "poll_url": f"/v1/jobs/{job['id']}",
    }


@router.post("/phase3/map", status_code=202)
async def phase3_map(body: dict):
    """Phase 3: Template Structure Mapping (async job)."""
    project_id = body.get("project_id")
    selected_proposal = body.get("selected_proposal", {})
    catalog_summary = body.get("catalog_summary", {})

    if not project_id:
        raise HTTPException(
            status_code=422,
            detail={"code": "VALIDATION_ERROR", "message": "project_id required"},
        )

    run = db.get_latest_run(project_id)
    if not run:
        run = db.create_run(project_id)

    job = create_job(phase=3, run_id=run["id"], payload={
        "project_id": project_id,
        "selected_proposal": selected_proposal,
        "catalog_summary": catalog_summary,
    })

    _dispatch_celery("tasks.phase3.run_template_mapping", job["id"])

    return {
        "job_id": job["id"],
        "status": "queued",
        "phase": 3,
        "poll_url": f"/v1/jobs/{job['id']}",
    }


@router.post("/phase4/design", status_code=202)
async def phase4_design(body: dict):
    """Phase 4: Model Design — cell assignments (async job).

    Validates Phase 3 prerequisite:
    - If Phase 3 result does not exist → 409 error (must complete Phase 3 first)
    - If Phase 3 result exists but sheet_mappings is empty → proceed in estimation mode
    """
    project_id = body.get("project_id")

    if not project_id:
        raise HTTPException(
            status_code=422,
            detail={"code": "VALIDATION_ERROR", "message": "project_id required"},
        )

    run = db.get_latest_run(project_id)
    if not run:
        run = db.create_run(project_id)

    # --- Phase 3 prerequisite check ---
    phase3_result = db.get_phase_result(run["id"], phase=3)
    estimation_mode = False

    if not phase3_result:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "PHASE3_NOT_COMPLETED",
                "message": "Phase 3（テンプレートマッピング）が完了していません。先にPhase 3を実行してください。",
            },
        )

    # Phase 3 exists — check if results are substantively empty
    raw = phase3_result.get("raw_json", {})
    mappings = raw.get("sheet_mappings", [])
    if not mappings:
        # If user explicitly requested estimation mode, proceed
        if not body.get("allow_estimation"):
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "PHASE3_EMPTY_RESULT",
                    "message": "Phase 3は完了しましたが、シートマッピングが空です。推定モードで続行しますか？",
                    "allow_estimation": True,
                },
            )
        estimation_mode = True

    job = create_job(phase=4, run_id=run["id"], payload={
        "project_id": project_id,
        "bm_result_ref": body.get("bm_result_ref", ""),
        "ts_result_ref": body.get("ts_result_ref", ""),
        "catalog_ref": body.get("catalog_ref", ""),
        "edits": body.get("edits", []),
        "estimation_mode": estimation_mode,
    })

    _dispatch_celery("tasks.phase4.run_model_design", job["id"])

    return {
        "job_id": job["id"],
        "status": "queued",
        "phase": 4,
        "estimation_mode": estimation_mode,
        "poll_url": f"/v1/jobs/{job['id']}",
    }


@router.post("/phase5/extract", status_code=202)
async def phase5_extract(body: dict):
    """Phase 5: Parameter Extraction (async job)."""
    project_id = body.get("project_id")

    if not project_id:
        raise HTTPException(
            status_code=422,
            detail={"code": "VALIDATION_ERROR", "message": "project_id required"},
        )

    run = db.get_latest_run(project_id)
    if not run:
        run = db.create_run(project_id)

    job = create_job(phase=5, run_id=run["id"], payload={
        "project_id": project_id,
        "md_result_ref": body.get("md_result_ref", ""),
        "document_excerpt_chars": body.get("document_excerpt_chars", 10000),
        "edits": body.get("edits", []),
    })

    _dispatch_celery("tasks.phase5.run_parameter_extraction", job["id"])

    return {
        "job_id": job["id"],
        "status": "queued",
        "phase": 5,
        "poll_url": f"/v1/jobs/{job['id']}",
    }


# ===================================================================
# Edits — Save & Retrieve user decisions (Phase 2 selection, Phase 3
#          proposal decisions, Scenario parameter edits, etc.)
# ===================================================================


@router.post("/edits")
async def save_user_edit(body: dict):
    """Save a user edit/decision for a given phase.

    Used by:
    - Phase 2: selected_proposal_index
    - Phase 3: proposal decisions (adopt/skip/instructions)
    - Phase 6: scenario parameter overrides
    """
    project_id = body.get("project_id")
    phase = body.get("phase")
    patch_json = body.get("patch_json", {})

    if not project_id or phase is None:
        raise HTTPException(
            status_code=422,
            detail={"code": "VALIDATION_ERROR", "message": "project_id and phase required"},
        )

    run = db.get_latest_run(project_id)
    if not run:
        run = db.create_run(project_id)

    edit = db.save_edit(run_id=run["id"], phase=phase, patch_json=patch_json)
    return edit


@router.get("/edits/{project_id}")
async def get_user_edits(project_id: str, phase: Optional[int] = None):
    """Get all user edits for a project, optionally filtered by phase."""
    run = db.get_latest_run(project_id)
    if not run:
        return []
    return db.get_edits(run_id=run["id"], phase=phase)
