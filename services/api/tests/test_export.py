"""Export endpoint tests."""

from __future__ import annotations

from unittest.mock import patch


def test_export_creates_job(client, sample_document):
    project_id, _ = sample_document

    with patch("services.api.app.routers.export._CELERY_ENABLED", False), \
         patch("services.api.app.routers.export._dispatch_export_sync"):
        resp = client.post(
            "/v1/export/excel",
            json={"project_id": project_id},
        )

    assert resp.status_code == 202
    data = resp.json()
    assert data["phase"] == 6
    assert "job_id" in data
    assert "download_url" in data


def test_export_missing_project_id(client):
    resp = client.post("/v1/export/excel", json={})
    assert resp.status_code == 422


def test_download_job_not_found(client):
    resp = client.get("/v1/export/download/nonexistent-id")
    assert resp.status_code == 404


def test_download_not_ready(client, sample_document):
    """Download before job completes should return 409."""
    project_id, _ = sample_document

    with patch("services.api.app.routers.export._CELERY_ENABLED", False), \
         patch("services.api.app.routers.export._dispatch_export_sync"):
        create_resp = client.post(
            "/v1/export/excel",
            json={"project_id": project_id},
        )

    job_id = create_resp.json()["job_id"]
    resp = client.get(f"/v1/export/download/{job_id}")
    assert resp.status_code == 409
