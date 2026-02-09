"""Phase execution endpoints (Phase 1-5).

Phase 1 (scan) is synchronous for small files.
Phases 2-5 are async (Celery jobs) since they involve LLM calls.
"""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, HTTPException

from .. import db
from .jobs import create_job

logger = logging.getLogger(__name__)
router = APIRouter()

# Celery dispatch is enabled when REDIS_URL is set
_CELERY_ENABLED = bool(os.environ.get("REDIS_URL"))


def _dispatch_celery(task_name: str, job_id: str):
    """Dispatch a Celery task if enabled, otherwise log a warning."""
    if not _CELERY_ENABLED:
        logger.warning("Celery not enabled (no REDIS_URL) — job %s will not be processed", job_id)
        return
    from services.worker.celery_app import app as celery_app
    celery_app.send_task(task_name, args=[job_id])
    logger.info("Dispatched %s for job %s", task_name, job_id)


@router.post("/phase1/scan")
async def phase1_scan(body: dict):
    """Phase 1: Scan template + extract document text.

    Synchronous for now. For large PDFs, could be converted to a job.
    """
    project_id = body.get("project_id")
    document_id = body.get("document_id")

    if not project_id or not document_id:
        raise HTTPException(
            status_code=422,
            detail={"code": "VALIDATION_ERROR", "message": "project_id and document_id required"},
        )

    # In production: call core.catalog.scanner.scan_template()
    # and core.ingest.reader.read_document()
    # For now, return a stub response
    return {
        "catalog": {
            "items": [],
            "block_index": {},
            "total_items": 0,
        },
        "document_summary": {
            "total_chars": 0,
            "pages": 0,
            "preview": "",
        },
    }


@router.post("/phase2/analyze", status_code=202)
async def phase2_analyze(body: dict):
    """Phase 2: Business Model Analysis (async job)."""
    project_id = body.get("project_id")
    document_id = body.get("document_id")
    feedback = body.get("feedback", "")

    if not project_id or not document_id:
        raise HTTPException(
            status_code=422,
            detail={"code": "VALIDATION_ERROR", "message": "project_id and document_id required"},
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
    selected_proposal = body.get("selected_proposal")
    catalog_summary = body.get("catalog_summary", {})

    if not project_id or not selected_proposal:
        raise HTTPException(
            status_code=422,
            detail={"code": "VALIDATION_ERROR", "message": "project_id and selected_proposal required"},
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
    """Phase 4: Model Design — cell assignments (async job)."""
    project_id = body.get("project_id")

    if not project_id:
        raise HTTPException(
            status_code=422,
            detail={"code": "VALIDATION_ERROR", "message": "project_id required"},
        )

    run = db.get_latest_run(project_id)
    if not run:
        run = db.create_run(project_id)

    job = create_job(phase=4, run_id=run["id"], payload={
        "project_id": project_id,
        "bm_result_ref": body.get("bm_result_ref", ""),
        "ts_result_ref": body.get("ts_result_ref", ""),
        "catalog_ref": body.get("catalog_ref", ""),
        "edits": body.get("edits", []),
    })

    _dispatch_celery("tasks.phase4.run_model_design", job["id"])

    return {
        "job_id": job["id"],
        "status": "queued",
        "phase": 4,
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
