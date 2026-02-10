"""Shared fixtures for API integration tests.

Uses FastAPI TestClient (in-memory, no network) so tests run
without a live server or external dependencies.
"""

from __future__ import annotations

import os
import sys

import pytest

# Ensure project root is on sys.path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Force in-memory DB (no PostgreSQL needed for tests)
os.environ.pop("DATABASE_URL", None)
os.environ.pop("REDIS_URL", None)


@pytest.fixture(autouse=True)
def _reset_in_memory_db():
    """Clear in-memory stores before each test for isolation."""
    from services.api.app import db

    db._mem_projects.clear()
    db._mem_documents.clear()
    db._mem_runs.clear()
    db._mem_phase_results.clear()
    db._mem_edits.clear()
    db._mem_jobs.clear()
    db._mem_llm_audits.clear()
    # Reset pool flag so each test starts fresh
    db._pool = None
    db._pool_init_done = False
    yield


@pytest.fixture()
def client():
    """FastAPI TestClient — no network, no server startup needed."""
    from fastapi.testclient import TestClient

    from services.api.app.main import app

    return TestClient(app)


@pytest.fixture()
def sample_project(client):
    """Create a project and return its id."""
    resp = client.post("/v1/projects", json={"name": "Test Project"})
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.fixture()
def sample_document(client, sample_project):
    """Upload a text document and return (project_id, doc_id)."""
    resp = client.post(
        "/v1/documents/upload",
        data={
            "project_id": sample_project,
            "kind": "text",
            "text": (
                "当社は法人向けSaaSプラットフォームを提供しています。"
                "月額課金モデルで、現在100社の顧客を持ち、ARRは1.2億円です。"
                "主要コストはエンジニア人件費（60%）とクラウドインフラ（20%）です。"
            ),
        },
    )
    assert resp.status_code == 201
    return sample_project, resp.json()["id"]
