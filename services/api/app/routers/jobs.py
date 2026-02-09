"""Job tracking endpoints and in-memory job store."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException

router = APIRouter()

# In-memory job store (replaced by DB + Celery in production)
_jobs: Dict[str, dict] = {}


def get_job_store() -> Dict[str, dict]:
    return _jobs


def create_job(
    phase: int,
    run_id: str,
    payload: Optional[Dict[str, Any]] = None,
) -> dict:
    """Create a new job record."""
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()
    job = {
        "id": job_id,
        "run_id": run_id,
        "phase": phase,
        "status": "queued",
        "progress": 0,
        "logs": [],
        "result": None,
        "error_msg": None,
        "payload": payload or {},
        "created_at": now,
        "updated_at": now,
    }
    _jobs[job_id] = job
    return job


def update_job(
    job_id: str,
    *,
    status: Optional[str] = None,
    progress: Optional[int] = None,
    log_msg: Optional[str] = None,
    result: Optional[Dict[str, Any]] = None,
    error_msg: Optional[str] = None,
) -> dict:
    """Update a job record."""
    job = _jobs.get(job_id)
    if not job:
        raise ValueError(f"Job not found: {job_id}")

    now = datetime.now(timezone.utc).isoformat()
    if status:
        job["status"] = status
    if progress is not None:
        job["progress"] = progress
    if log_msg:
        job["logs"].append({"ts": now, "msg": log_msg})
    if result is not None:
        job["result"] = result
    if error_msg:
        job["error_msg"] = error_msg
    job["updated_at"] = now
    return job


@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    """Poll job status."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail={"code": "JOB_NOT_FOUND"})

    # Don't expose payload in API response
    return {
        "id": job["id"],
        "status": job["status"],
        "progress": job["progress"],
        "phase": job["phase"],
        "logs": job["logs"],
        "result": job["result"],
        "error_msg": job.get("error_msg"),
        "created_at": job["created_at"],
        "updated_at": job["updated_at"],
    }
