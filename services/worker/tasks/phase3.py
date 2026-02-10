"""Celery task for Phase 3: Template Structure Mapping."""

from __future__ import annotations

import json
import logging

from services.worker.celery_app import app

logger = logging.getLogger(__name__)


@app.task(bind=True, name="tasks.phase3.run_template_mapping")
def run_template_mapping(self, job_id: str):
    """Execute Phase 3 Template Structure Mapping as a Celery task."""
    from core.providers import AnthropicProvider, ProviderAdapter
    from services.api.app import db
    from src.agents.template_mapper import TemplateMapper

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
        selected_proposal = payload.get("selected_proposal", {})
        catalog_summary = payload.get("catalog_summary", {})

        # --- Load Phase 2 result (BM Analysis) ---
        phase2_result = db.get_phase_result(run_id, phase=2)
        if not phase2_result:
            db.update_job(job_id, status="failed", error_msg="Phase 2 result not found")
            return {"status": "failed", "job_id": job_id}

        analysis_json = phase2_result.get("raw_json", {})
        # Use selected_proposal from payload or default to first proposal
        if not selected_proposal and "proposals" in analysis_json:
            proposals = analysis_json.get("proposals", [])
            selected_proposal = proposals[0] if proposals else {}

        catalog_items = catalog_summary.get("items", [])

        db.update_job(job_id, progress=15, log_msg="Phase 2 data loaded")

        # --- Run Template Mapping ---
        provider = AnthropicProvider()
        adapter = ProviderAdapter(provider)
        mapper = TemplateMapper(llm_client=adapter)

        db.update_job(job_id, progress=20, log_msg="Starting template mapping")
        result = mapper.map_structure(
            analysis_json=json.dumps(selected_proposal) if isinstance(selected_proposal, dict) else selected_proposal,
            catalog_items=catalog_items,
            feedback="",
        )

        # --- Store result ---
        result_dict = result.to_dict() if hasattr(result, "to_dict") else json.loads(json.dumps(result, default=str))
        db.save_phase_result(run_id=run_id, phase=3, raw_json=result_dict)

        db.update_job(
            job_id, status="completed", progress=100,
            log_msg="Template mapping complete",
            result_ref=f"phase_result:{run_id}:3",
        )

        return {"status": "completed", "job_id": job_id}

    except Exception as e:
        logger.error("Phase 3 task failed for job %s: %s", job_id, e)
        db.update_job(job_id, status="failed", error_msg=str(e))
        raise
