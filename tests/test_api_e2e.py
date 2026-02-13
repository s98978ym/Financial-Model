"""End-to-end integration tests for the FastAPI PL Generator API.

Tests the full pipeline:
  1. Create project
  2. Upload document (text paste)
  3. Phase 1 scan
  4. Phase 2-5 job creation (verifies dispatch)
  5. Export job creation

No external services required — uses in-memory DB and mocked Celery.
"""

from __future__ import annotations

import json
import os
import sys

import pytest

# Ensure no external services are required
os.environ.pop("DATABASE_URL", None)
os.environ.pop("REDIS_URL", None)
os.environ.pop("SUPABASE_URL", None)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(scope="module")
def client():
    """Create a test client for the FastAPI app."""
    from fastapi.testclient import TestClient
    from services.api.app.main import app
    return TestClient(app)


SAMPLE_BUSINESS_PLAN = """
株式会社テストSaaS 事業計画書

1. 事業概要
B2B SaaSプラットフォームを提供。月額サブスクリプションモデル。

2. 収益構造
- 月額基本料金: ¥50,000/社
- 従量課金: ¥100/ユーザー/月
- 初期費用: ¥200,000

3. 売上予測
FY2024: 売上高 1.5億円 (顧客数 250社)
FY2025: 売上高 3.0億円 (顧客数 500社)
FY2026: 売上高 5.0億円 (顧客数 800社)

4. コスト構造
- 人件費: 売上の40%
- サーバー費: 売上の10%
- 販管費: 売上の20%
- 研究開発費: 売上の15%

5. KPI
- 月次解約率: 2%
- ARPU: ¥60,000
- CAC: ¥300,000
- LTV/CAC: 10x
"""


class TestHealthCheck:
    def test_health(self, client):
        res = client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"

    def test_root(self, client):
        res = client.get("/")
        assert res.status_code == 200
        data = res.json()
        assert "PL Generator" in data["message"]


class TestProjectCRUD:
    def test_create_project(self, client):
        res = client.post("/v1/projects", json={"name": "テストプロジェクト"})
        assert res.status_code == 201
        data = res.json()
        assert data["name"] == "テストプロジェクト"
        assert data["id"]
        assert data["template_id"] == "v2_ib_grade"
        assert data["status"] == "created"

    def test_list_projects(self, client):
        res = client.get("/v1/projects")
        assert res.status_code == 200
        projects = res.json()
        assert isinstance(projects, list)
        assert len(projects) >= 1

    def test_get_project(self, client):
        # Create then get
        create_res = client.post("/v1/projects", json={"name": "取得テスト"})
        project_id = create_res.json()["id"]

        res = client.get(f"/v1/projects/{project_id}")
        assert res.status_code == 200
        assert res.json()["name"] == "取得テスト"

    def test_get_project_not_found(self, client):
        res = client.get("/v1/projects/nonexistent-id")
        assert res.status_code == 404

    def test_get_project_state(self, client):
        create_res = client.post("/v1/projects", json={"name": "状態テスト"})
        project_id = create_res.json()["id"]

        res = client.get(f"/v1/projects/{project_id}/state")
        assert res.status_code == 200
        state = res.json()
        assert state["project"]["id"] == project_id
        assert "phase_results" in state
        assert "documents" in state


class TestDocumentUpload:
    def test_upload_text(self, client):
        # Create project first
        project = client.post("/v1/projects", json={"name": "ドキュメントテスト"}).json()

        res = client.post(
            "/v1/documents/upload",
            data={"project_id": project["id"], "kind": "text", "text": SAMPLE_BUSINESS_PLAN},
        )
        assert res.status_code == 201
        doc = res.json()
        assert doc["id"]
        assert doc["kind"] == "text"
        assert doc["extracted_chars"] > 0

    def test_upload_no_content(self, client):
        project = client.post("/v1/projects", json={"name": "空テスト"}).json()
        res = client.post(
            "/v1/documents/upload",
            data={"project_id": project["id"], "kind": "file"},
        )
        assert res.status_code == 422


class TestPhase1Scan:
    def test_scan_with_text_document(self, client):
        # Setup: create project + upload text
        project = client.post("/v1/projects", json={"name": "Phase1テスト"}).json()
        doc = client.post(
            "/v1/documents/upload",
            data={"project_id": project["id"], "kind": "text", "text": SAMPLE_BUSINESS_PLAN},
        ).json()

        # Phase 1 scan
        res = client.post("/v1/phase1/scan", json={
            "project_id": project["id"],
            "document_id": doc["id"],
            "template_id": "v2_ib_grade",
        })
        assert res.status_code == 200
        data = res.json()
        assert "catalog" in data
        assert "document_summary" in data
        assert data["document_summary"]["total_chars"] > 0

    def test_scan_missing_params(self, client):
        res = client.post("/v1/phase1/scan", json={"project_id": "abc"})
        assert res.status_code == 422

    def test_scan_missing_document(self, client):
        project = client.post("/v1/projects", json={"name": "不在doc"}).json()
        res = client.post("/v1/phase1/scan", json={
            "project_id": project["id"],
            "document_id": "nonexistent-doc",
        })
        assert res.status_code == 404


class TestPhase2to5JobCreation:
    """Test that phases 2-5 create jobs correctly (no Celery execution)."""

    @pytest.fixture(autouse=True)
    def setup_project(self, client):
        """Create a project with document and Phase 1 result."""
        project = client.post("/v1/projects", json={"name": "ジョブテスト"}).json()
        self.project_id = project["id"]

        doc = client.post(
            "/v1/documents/upload",
            data={"project_id": self.project_id, "kind": "text", "text": SAMPLE_BUSINESS_PLAN},
        ).json()
        self.document_id = doc["id"]

        # Run Phase 1
        client.post("/v1/phase1/scan", json={
            "project_id": self.project_id,
            "document_id": self.document_id,
        })

    def test_phase2_creates_job(self, client):
        res = client.post("/v1/phase2/analyze", json={
            "project_id": self.project_id,
            "document_id": self.document_id,
        })
        assert res.status_code == 202
        data = res.json()
        assert data["job_id"]
        assert data["status"] == "queued"
        assert data["phase"] == 2
        assert "poll_url" in data

        # Verify job can be polled
        job_res = client.get(data["poll_url"])
        assert job_res.status_code == 200
        assert job_res.json()["status"] == "queued"

    def test_phase3_creates_job(self, client):
        res = client.post("/v1/phase3/map", json={
            "project_id": self.project_id,
            "selected_proposal": {"label": "SaaS B2B", "segments": ["Main"]},
        })
        assert res.status_code == 202
        data = res.json()
        assert data["phase"] == 3
        assert data["job_id"]

    def test_phase4_creates_job(self, client):
        res = client.post("/v1/phase4/design", json={
            "project_id": self.project_id,
        })
        assert res.status_code == 202
        assert res.json()["phase"] == 4

    def test_phase5_creates_job(self, client):
        res = client.post("/v1/phase5/extract", json={
            "project_id": self.project_id,
        })
        assert res.status_code == 202
        assert res.json()["phase"] == 5


class TestEditsSaveAndRetrieve:
    def test_save_and_get_edits(self, client):
        project = client.post("/v1/projects", json={"name": "編集テスト"}).json()

        # Save edits
        res = client.post(f"/v1/projects/{project['id']}/edits", json={
            "phase": 5,
            "patch": {"cell": "B3", "old_value": 1000, "new_value": 1500},
        })
        assert res.status_code == 200
        assert res.json()["status"] == "saved"

        # Get history
        history_res = client.get(f"/v1/projects/{project['id']}/history")
        assert history_res.status_code == 200
        assert len(history_res.json()["history"]) >= 1


class TestProjectStateWithPhaseResults:
    def test_state_includes_phase1_result(self, client):
        project = client.post("/v1/projects", json={"name": "状態結果テスト"}).json()
        doc = client.post(
            "/v1/documents/upload",
            data={"project_id": project["id"], "kind": "text", "text": SAMPLE_BUSINESS_PLAN},
        ).json()

        # Run Phase 1
        client.post("/v1/phase1/scan", json={
            "project_id": project["id"],
            "document_id": doc["id"],
        })

        # Get state
        state = client.get(f"/v1/projects/{project['id']}/state").json()
        assert "1" in state["phase_results"] or 1 in state["phase_results"]

        # Verify documents are included
        assert len(state["documents"]) >= 1
        assert state["documents"][0]["id"] == doc["id"]


class TestRecalc:
    """Test the recalculation endpoint."""

    def test_recalc_with_defaults(self, client):
        res = client.post("/v1/recalc", json={
            "parameters": {"revenue_fy1": 100_000_000, "growth_rate": 0.3},
            "scenario": "base",
        })
        assert res.status_code == 200
        data = res.json()
        assert "pl_summary" in data
        assert "kpis" in data
        assert len(data["pl_summary"]["revenue"]) == 5
        assert data["scenario"] == "base"

    def test_recalc_with_project_id(self, client):
        project = client.post("/v1/projects", json={"name": "Recalcテスト"}).json()
        res = client.post("/v1/recalc", json={
            "project_id": project["id"],
            "parameters": {},
            "scenario": "base",
        })
        assert res.status_code == 200
        assert "source_params" in res.json()

    def test_recalc_best_scenario(self, client):
        res = client.post("/v1/recalc", json={
            "parameters": {"revenue_fy1": 100_000_000},
            "scenario": "best",
        })
        assert res.status_code == 200
        base_res = client.post("/v1/recalc", json={
            "parameters": {"revenue_fy1": 100_000_000},
            "scenario": "base",
        })
        # Best scenario should have higher revenue
        assert res.json()["pl_summary"]["revenue"][0] >= base_res.json()["pl_summary"]["revenue"][0]

    def test_recalc_worst_scenario(self, client):
        res = client.post("/v1/recalc", json={
            "parameters": {"revenue_fy1": 100_000_000},
            "scenario": "worst",
        })
        assert res.status_code == 200
        base_res = client.post("/v1/recalc", json={
            "parameters": {"revenue_fy1": 100_000_000},
            "scenario": "base",
        })
        # Worst scenario should have lower revenue
        assert res.json()["pl_summary"]["revenue"][0] <= base_res.json()["pl_summary"]["revenue"][0]


class TestExportWithDownload:
    """Test export job creation and download endpoint."""

    def test_export_creates_job_with_download_url(self, client):
        project = client.post("/v1/projects", json={"name": "Exportテスト"}).json()
        res = client.post("/v1/export/excel", json={
            "project_id": project["id"],
            "scenarios": ["base"],
        })
        assert res.status_code == 202
        data = res.json()
        assert data["job_id"]
        assert data["phase"] == 6
        assert "download_url" in data

    def test_download_completed_job(self, client):
        import time

        project = client.post("/v1/projects", json={"name": "DLテスト"}).json()
        # Create export job (runs in background thread)
        res = client.post("/v1/export/excel", json={
            "project_id": project["id"],
        })
        job_id = res.json()["job_id"]

        # Poll until the background thread completes (up to 10s)
        job = None
        for _ in range(20):
            job = client.get(f"/v1/jobs/{job_id}").json()
            if job["status"] in ("completed", "failed"):
                break
            time.sleep(0.5)

        assert job["status"] == "completed"

        # Download
        dl_res = client.get(f"/v1/export/download/{job_id}")
        assert dl_res.status_code == 200
        assert "spreadsheetml" in dl_res.headers.get("content-type", "")
        assert len(dl_res.content) > 0

    def test_download_not_ready(self, client):
        res = client.get("/v1/export/download/nonexistent-job")
        assert res.status_code == 404


class TestGuards:
    """Test core guards (no API, pure Python)."""

    def test_json_output_guard(self):
        from core.providers.guards import JSONOutputGuard
        result = JSONOutputGuard.enforce('{"key": "value"}')
        assert result == {"key": "value"}

    def test_json_guard_strips_markdown(self):
        from core.providers.guards import JSONOutputGuard
        result = JSONOutputGuard.enforce('```json\n{"key": "value"}\n```')
        assert result == {"key": "value"}

    def test_json_guard_finds_first_brace(self):
        from core.providers.guards import JSONOutputGuard
        result = JSONOutputGuard.enforce('Here is the JSON: {"key": "value"}')
        assert result == {"key": "value"}

    def test_document_truncation_phase2(self):
        from core.providers.guards import DocumentTruncation
        short = "abc" * 100
        assert DocumentTruncation.for_phase2(short) == short

        long = "x" * 50000
        truncated = DocumentTruncation.for_phase2(long, max_chars=30000)
        assert len(truncated) < 50000
        assert "[...中略...]" in truncated

    def test_evidence_guard(self):
        from core.providers.guards import EvidenceGuard
        extractions = [
            {"value": 100, "confidence": 0.9, "evidence": {"quote": "売上100万円"}},
            {"value": 200, "confidence": 0.8},  # No evidence
        ]
        result = EvidenceGuard.verify(extractions, "この事業の売上100万円を見込む")
        assert result[0]["confidence"] == 0.9  # Has evidence
        assert result[1]["confidence"] <= 0.3  # Penalized

    def test_extraction_completeness(self):
        from core.providers.guards import ExtractionCompleteness
        result = ExtractionCompleteness.ensure(
            {"extractions": []},
            [{"sheet": "PL", "cell": "B3", "current_value": 100}],
        )
        assert len(result["extractions"]) == 1
        assert result["extractions"][0]["source"] == "default"
