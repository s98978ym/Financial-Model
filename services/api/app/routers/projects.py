"""Project CRUD endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import db

router = APIRouter()


@router.post("/projects", status_code=201)
async def create_project(body: dict):
    """Create a new project."""
    project = db.create_project(
        name=body.get("name", "Untitled"),
        template_id=body.get("template_id", "v2_ib_grade"),
        owner=body.get("owner", ""),
    )
    return project


@router.get("/projects")
async def list_projects():
    """List all projects."""
    return db.list_projects()


@router.get("/projects/{project_id}")
async def get_project(project_id: str):
    """Get project by ID."""
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail={"code": "PROJECT_NOT_FOUND"})
    return project


@router.get("/projects/{project_id}/state")
async def get_project_state(project_id: str):
    """Get full project state for resuming."""
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail={"code": "PROJECT_NOT_FOUND"})

    run = db.get_latest_run(project_id)
    phase_results = {}
    pending_edits = []
    if run:
        phase_results = db.get_all_phase_results(run["id"])
        pending_edits = db.get_edits(run["id"])

    documents = db.get_documents_by_project(project_id)

    return {
        "project": project,
        "current_run_id": run["id"] if run else None,
        "phase_results": phase_results,
        "pending_edits": pending_edits,
        "documents": documents,
    }


@router.post("/projects/{project_id}/edits")
async def save_edits(project_id: str, body: dict):
    """Save incremental edits (patch)."""
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail={"code": "PROJECT_NOT_FOUND"})

    run = db.get_latest_run(project_id)
    if not run:
        run = db.create_run(project_id)

    phase = body.get("phase", 0)
    patch = body.get("patch", body)
    edit = db.save_edit(run_id=run["id"], phase=phase, patch_json=patch)
    return {"status": "saved", "project_id": project_id, "edit_id": edit["id"]}


@router.get("/projects/{project_id}/history")
async def get_history(project_id: str):
    """List change history for rollback."""
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail={"code": "PROJECT_NOT_FOUND"})

    run = db.get_latest_run(project_id)
    history = db.get_edits(run["id"]) if run else []
    return {"history": history, "project_id": project_id}
