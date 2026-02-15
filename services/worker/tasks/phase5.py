"""Celery task for Phase 5: Parameter Extraction."""

from __future__ import annotations

import json
import logging

from services.worker.celery_app import app
from services.worker.tasks.heartbeat import heartbeat

logger = logging.getLogger(__name__)


@app.task(bind=True, name="tasks.phase5.run_parameter_extraction")
def run_parameter_extraction(self, job_id: str):
    """Execute Phase 5 Parameter Extraction as a Celery task."""
    from core.providers import AnthropicProvider, ProviderAdapter
    from core.providers.guards import DocumentTruncation
    from services.api.app import db
    from src.agents.parameter_extractor import ParameterExtractorAgent

    try:
        # --- Load job & payload ---
        job = db.get_job(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        db.update_job(job_id, status="running", progress=5, log_msg="Loading data")

        payload = job.get("payload", {})
        if not payload and job.get("logs"):
            for log in job["logs"]:
                if isinstance(log, dict) and "payload" in log:
                    payload = log["payload"]
                    break

        run_id = job["run_id"]
        project_id = payload.get("project_id", "")
        excerpt_chars = payload.get("document_excerpt_chars", 10000)

        # --- Load Phase 4 result (Model Design) ---
        phase4_result = db.get_phase_result(run_id, phase=4)
        if not phase4_result:
            db.update_job(job_id, status="failed", error_msg="Phase 4 result not found")
            return {"status": "failed", "job_id": job_id}

        model_design_json = phase4_result.get("raw_json", {})
        db.update_job(job_id, progress=10, log_msg="Phase 4 data loaded")

        # --- Load document text ---
        docs = db.get_documents_by_project(project_id) if project_id else []
        document_text = ""
        for doc in docs:
            txt = doc.get("extracted_text") or ""
            if txt:
                document_text = txt
                break

        if not document_text:
            db.update_job(job_id, status="failed", error_msg="Document text not found")
            return {"status": "failed", "job_id": job_id}

        # Truncate for Phase 5 (70% front + 25% back to preserve financial data at end)
        truncated = DocumentTruncation.for_phase5(document_text, max_chars=excerpt_chars)
        db.update_job(job_id, progress=15, log_msg=f"Document loaded ({len(truncated)} chars)")

        # --- Apply user edits ---
        edits = payload.get("edits", [])
        if edits:
            db.update_job(job_id, progress=18, log_msg=f"Applying {len(edits)} user edits")

        # --- Run Parameter Extraction ---
        provider = AnthropicProvider()
        adapter = ProviderAdapter(provider)
        extractor = ParameterExtractorAgent(llm_client=adapter)

        db.update_job(job_id, progress=20, log_msg="Starting parameter extraction")

        def _hb_update(pct, msg):
            db.update_job(job_id, progress=pct, log_msg=msg)

        # Pass dict directly (agent handles serialization internally)
        with heartbeat(_hb_update, message="Parameter extraction in progress..."):
            result = extractor.extract_values(
                model_design_json=model_design_json,
                document_text=truncated,
                feedback="",
            )

        # --- Store result ---
        result_dict = result.model_dump()
        pr = db.save_phase_result(run_id=run_id, phase=5, raw_json=result_dict)

        db.update_job(
            job_id, status="completed", progress=100,
            log_msg="Parameter extraction complete",
            result_ref=pr["id"],
        )

        return {"status": "completed", "job_id": job_id}

    except Exception as e:
        logger.exception("Phase 5 task failed for job %s", job_id)
        db.update_job(job_id, status="failed", error_msg=f"{type(e).__name__}: {e}")
        raise
