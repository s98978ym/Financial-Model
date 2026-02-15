"""Phase endpoint tests.

Tests the API contract (request/response format, validation, job creation).
Does NOT test actual LLM calls — those are mocked to avoid external deps.
"""

from __future__ import annotations

from unittest.mock import patch


# ── Phase 1 (synchronous) ──────────────────────────────────

def test_phase1_scan(client, sample_document):
    project_id, doc_id = sample_document
    resp = client.post(
        "/v1/phase1/scan",
        json={"project_id": project_id, "document_id": doc_id},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "catalog" in data


def test_phase1_missing_fields(client):
    resp = client.post("/v1/phase1/scan", json={})
    assert resp.status_code == 422


def test_phase1_doc_not_found(client, sample_project):
    resp = client.post(
        "/v1/phase1/scan",
        json={"project_id": sample_project, "document_id": "nonexistent"},
    )
    assert resp.status_code == 404


# ── Phase 2 (async) ────────────────────────────────────────

def test_phase2_creates_job(client, sample_document):
    project_id, doc_id = sample_document
    with patch("services.api.app.routers.phases._dispatch_celery"):
        resp = client.post(
            "/v1/phase2/analyze",
            json={"project_id": project_id, "document_id": doc_id},
        )
    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "queued"
    assert data["phase"] == 2
    assert "job_id" in data
    assert "poll_url" in data


def test_phase2_missing_fields(client):
    resp = client.post("/v1/phase2/analyze", json={"project_id": ""})
    assert resp.status_code == 422


# ── Phase 3 (async) ────────────────────────────────────────

def test_phase3_creates_job(client, sample_document):
    project_id, _ = sample_document
    with patch("services.api.app.routers.phases._dispatch_celery"):
        resp = client.post(
            "/v1/phase3/map",
            json={"project_id": project_id},
        )
    assert resp.status_code == 202
    data = resp.json()
    assert data["phase"] == 3
    assert "job_id" in data


def test_phase3_accepts_empty_proposal(client, sample_document):
    """Regression: empty dict selected_proposal must NOT cause 422."""
    project_id, _ = sample_document
    with patch("services.api.app.routers.phases._dispatch_celery"):
        resp = client.post(
            "/v1/phase3/map",
            json={"project_id": project_id, "selected_proposal": {}},
        )
    assert resp.status_code == 202


def test_phase3_accepts_no_proposal(client, sample_document):
    """selected_proposal omitted entirely — should still work."""
    project_id, _ = sample_document
    with patch("services.api.app.routers.phases._dispatch_celery"):
        resp = client.post(
            "/v1/phase3/map",
            json={"project_id": project_id},
        )
    assert resp.status_code == 202


def test_phase3_missing_project_id(client):
    resp = client.post("/v1/phase3/map", json={})
    assert resp.status_code == 422


# ── Phase 4 (async) ────────────────────────────────────────

def test_phase4_requires_phase3(client, sample_document):
    """Phase 4 should return 409 when Phase 3 has not been completed."""
    project_id, _ = sample_document
    resp = client.post(
        "/v1/phase4/design",
        json={"project_id": project_id},
    )
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "PHASE3_NOT_COMPLETED"


def test_phase4_creates_job(client, sample_document):
    """Phase 4 succeeds when Phase 3 result exists with mappings."""
    from services.api.app import db
    project_id, _ = sample_document
    run = db.get_latest_run(project_id)
    if not run:
        run = db.create_run(project_id)
    db.save_phase_result(
        run_id=run["id"], phase=3,
        raw_json={"sheet_mappings": [{"sheet_name": "PL", "sheet_purpose": "revenue_model"}]},
    )
    with patch("services.api.app.routers.phases._dispatch_celery"):
        resp = client.post(
            "/v1/phase4/design",
            json={"project_id": project_id},
        )
    assert resp.status_code == 202
    data = resp.json()
    assert data["phase"] == 4


def test_phase4_estimation_mode(client, sample_document):
    """Phase 4 enters estimation mode when Phase 3 result is empty."""
    from services.api.app import db
    project_id, _ = sample_document
    run = db.get_latest_run(project_id)
    if not run:
        run = db.create_run(project_id)
    db.save_phase_result(run_id=run["id"], phase=3, raw_json={"sheet_mappings": []})
    # Without allow_estimation → 409
    resp = client.post("/v1/phase4/design", json={"project_id": project_id})
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "PHASE3_EMPTY_RESULT"
    # With allow_estimation → 202
    with patch("services.api.app.routers.phases._dispatch_celery"):
        resp2 = client.post("/v1/phase4/design", json={
            "project_id": project_id,
            "allow_estimation": True,
        })
    assert resp2.status_code == 202
    assert resp2.json()["estimation_mode"] is True


def test_phase4_missing_project_id(client):
    resp = client.post("/v1/phase4/design", json={})
    assert resp.status_code == 422


# ── Phase 5 (async) ────────────────────────────────────────

def test_phase5_creates_job(client, sample_document):
    project_id, _ = sample_document
    with patch("services.api.app.routers.phases._dispatch_celery"):
        resp = client.post(
            "/v1/phase5/extract",
            json={"project_id": project_id},
        )
    assert resp.status_code == 202
    data = resp.json()
    assert data["phase"] == 5


def test_phase5_missing_project_id(client):
    resp = client.post("/v1/phase5/extract", json={})
    assert resp.status_code == 422


# ── Job polling ─────────────────────────────────────────────

def test_job_polling(client, sample_document):
    """Create a phase job and verify it appears in GET /jobs/{id}."""
    project_id, doc_id = sample_document
    with patch("services.api.app.routers.phases._dispatch_celery"):
        create_resp = client.post(
            "/v1/phase2/analyze",
            json={"project_id": project_id, "document_id": doc_id},
        )
    job_id = create_resp.json()["job_id"]

    resp = client.get(f"/v1/jobs/{job_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == job_id
    assert data["status"] in ("queued", "running", "completed", "failed")
    assert "progress" in data


def test_job_not_found(client):
    resp = client.get("/v1/jobs/nonexistent-job-id")
    assert resp.status_code == 404


# ── Cross-phase data flow ──────────────────────────────────

def test_full_pipeline_job_creation(client, sample_document):
    """Verify all phases can create jobs sequentially for the same project."""
    from services.api.app import db

    project_id, doc_id = sample_document

    with patch("services.api.app.routers.phases._dispatch_celery"):
        # Phase 2
        r2 = client.post(
            "/v1/phase2/analyze",
            json={"project_id": project_id, "document_id": doc_id},
        )
        assert r2.status_code == 202

        # Phase 3
        r3 = client.post(
            "/v1/phase3/map",
            json={"project_id": project_id, "selected_proposal": {"label": "SaaS Model"}},
        )
        assert r3.status_code == 202

        # Simulate Phase 3 completing (since Celery is mocked, we inject the result)
        run = db.get_latest_run(project_id)
        db.save_phase_result(
            run_id=run["id"], phase=3,
            raw_json={"sheet_mappings": [{"sheet_name": "PL", "sheet_purpose": "revenue_model"}]},
        )

        # Phase 4 (requires Phase 3 result)
        r4 = client.post(
            "/v1/phase4/design",
            json={"project_id": project_id},
        )
        assert r4.status_code == 202

        # Phase 5
        r5 = client.post(
            "/v1/phase5/extract",
            json={"project_id": project_id},
        )
        assert r5.status_code == 202

    # All should have unique job IDs
    job_ids = {r.json()["job_id"] for r in [r2, r3, r4, r5]}
    assert len(job_ids) == 4, "Each phase should create a unique job"

    # Project state should have a run
    state = client.get(f"/v1/projects/{project_id}/state").json()
    assert state["current_run_id"] is not None
