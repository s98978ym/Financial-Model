"""Project CRUD endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List

from fastapi import APIRouter, HTTPException

# In-memory store for MVP (replaced by Supabase in production)
_projects: Dict[str, dict] = {}

router = APIRouter()


@router.post("/projects", status_code=201)
async def create_project(body: dict):
    """Create a new project."""
    project_id = f"proj_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()
    project = {
        "id": project_id,
        "name": body.get("name", "Untitled"),
        "template_id": body.get("template_id", "v2_ib_grade"),
        "status": "created",
        "current_phase": 1,
        "created_at": now,
        "updated_at": now,
    }
    _projects[project_id] = project
    return project


@router.get("/projects")
async def list_projects():
    """List all projects."""
    return list(_projects.values())


@router.get("/projects/{project_id}")
async def get_project(project_id: str):
    """Get project by ID."""
    project = _projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail={"code": "PROJECT_NOT_FOUND"})
    return project


@router.get("/projects/{project_id}/state")
async def get_project_state(project_id: str):
    """Get full project state for resuming."""
    project = _projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail={"code": "PROJECT_NOT_FOUND"})
    return {
        "project": project,
        "current_run_id": None,
        "phase_results": {},
        "pending_edits": [],
    }


@router.post("/projects/{project_id}/edits")
async def save_edits(project_id: str, body: dict):
    """Save incremental edits (patch)."""
    project = _projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail={"code": "PROJECT_NOT_FOUND"})
    # Store edit patch (in-memory for MVP)
    return {"status": "saved", "project_id": project_id}


@router.get("/projects/{project_id}/history")
async def get_history(project_id: str):
    """List change history for rollback."""
    project = _projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail={"code": "PROJECT_NOT_FOUND"})
    return {"history": [], "project_id": project_id}
