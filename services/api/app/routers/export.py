"""Excel export endpoint."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .jobs import create_job

router = APIRouter()


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

    job = create_job(phase=6, run_id=project_id, payload={
        "project_id": project_id,
        "parameters": body.get("parameters", {}),
        "scenarios": body.get("scenarios", ["base", "best", "worst"]),
        "options": body.get("options", {}),
    })

    # In production: dispatch to Celery
    # celery_app.send_task("tasks.export.generate_excel", args=[job["id"]])

    return {
        "job_id": job["id"],
        "status": "queued",
        "phase": 6,
        "poll_url": f"/v1/jobs/{job['id']}",
    }
