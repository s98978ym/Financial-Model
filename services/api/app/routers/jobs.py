"""Job tracking endpoints — delegates to db layer."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException

from .. import db

router = APIRouter()


def create_job(
    phase: int,
    run_id: str,
    payload: Optional[Dict[str, Any]] = None,
) -> dict:
    """Create a new job record (helper used by phases.py and export.py)."""
    return db.create_job(run_id=run_id, phase=phase, payload=payload)


def update_job(
    job_id: str,
    *,
    status: Optional[str] = None,
    progress: Optional[int] = None,
    log_msg: Optional[str] = None,
    result_ref: Optional[str] = None,
    error_msg: Optional[str] = None,
) -> dict:
    """Update a job record (helper used by worker tasks)."""
    result = db.update_job(
        job_id, status=status, progress=progress,
        log_msg=log_msg, result_ref=result_ref, error_msg=error_msg,
    )
    if not result:
        raise ValueError(f"Job not found: {job_id}")
    return result


@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    """Poll job status.

    When the job is completed and has a result_ref, the phase result's
    raw_json is inlined as ``result_data`` so the frontend can display
    results immediately without waiting for a separate projectState refetch.
    """
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail={"code": "JOB_NOT_FOUND"})

    resp: dict = {
        "id": job["id"],
        "status": job["status"],
        "progress": job["progress"],
        "phase": job["phase"],
        "logs": job.get("logs", []),
        "result": job.get("result_ref"),
        "error_msg": job.get("error_msg"),
        "log_msg": job["logs"][-1]["msg"] if job.get("logs") else None,
        "created_at": job["created_at"],
        "updated_at": job["updated_at"],
    }

    # Inline result data on completion to eliminate FE projectState wait
    if job["status"] == "completed" and job.get("result_ref"):
        pr = db.get_phase_result(job["run_id"], job["phase"])
        if pr:
            resp["result_data"] = pr.get("raw_json")

    return resp
