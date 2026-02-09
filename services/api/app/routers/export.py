"""Excel export endpoint."""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, HTTPException

from .. import db
from .jobs import create_job

logger = logging.getLogger(__name__)
router = APIRouter()

_CELERY_ENABLED = bool(os.environ.get("REDIS_URL"))


@router.post("/export/excel", status_code=202)
async def export_excel(body: dict):
    """Generate Excel file(s) for download (async job).

    Creates Best/Base/Worst scenario files + needs_review.csv.
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

    job = create_job(phase=6, run_id=run["id"], payload={
        "project_id": project_id,
        "parameters": body.get("parameters", {}),
        "scenarios": body.get("scenarios", ["base", "best", "worst"]),
        "options": body.get("options", {}),
    })

    if _CELERY_ENABLED:
        from services.worker.celery_app import app as celery_app
        celery_app.send_task("tasks.export.generate_excel", args=[job["id"]])
        logger.info("Dispatched export task for job %s", job["id"])
    else:
        logger.warning("Celery not enabled — export job %s will not be processed", job["id"])

    return {
        "job_id": job["id"],
        "status": "queued",
        "phase": 6,
        "poll_url": f"/v1/jobs/{job['id']}",
    }
