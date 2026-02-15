"""Celery task for Phase 3: Template Structure Mapping."""

from __future__ import annotations

import json
import logging

from services.worker.celery_app import app
from services.worker.tasks.heartbeat import heartbeat

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

        # --- Load Phase 2 result (BM Analysis) ---
        phase2_result = db.get_phase_result(run_id, phase=2)
        if not phase2_result:
            db.update_job(job_id, status="failed", error_msg="Phase 2 result not found — run Phase 2 first")
            return {"status": "failed", "job_id": job_id}

        analysis_json = phase2_result.get("raw_json", {})
        # Use selected_proposal from payload or default to first proposal
        if not selected_proposal and "proposals" in analysis_json:
            proposals = analysis_json.get("proposals", [])
            selected_proposal = proposals[0] if proposals else {}

        # --- Load Phase 1 catalog (template cells) ---
        phase1_result = db.get_phase_result(run_id, phase=1)
        catalog_items = []
        if phase1_result:
            p1_json = phase1_result.get("raw_json", {})
            catalog_items = p1_json.get("catalog", {}).get("items", [])
        logger.info("Phase 3: loaded %d catalog items from Phase 1", len(catalog_items))

        db.update_job(job_id, progress=15, log_msg=f"Data loaded: {len(catalog_items)} catalog items")

        # --- Run Template Mapping ---
        provider = AnthropicProvider()
        adapter = ProviderAdapter(provider)
        mapper = TemplateMapper(llm_client=adapter)

        db.update_job(job_id, progress=20, log_msg="Starting template mapping (calling Claude API)")

        def _hb_update(pct, msg):
            db.update_job(job_id, progress=pct, log_msg=msg)

        # Pass selected_proposal as dict (NOT json.dumps — mapper handles serialization)
        with heartbeat(_hb_update, time_constant=60.0, message="Template mapping in progress..."):
            result = mapper.map_structure(
                analysis_json=selected_proposal,
                catalog_items=catalog_items,
                feedback="",
            )

        # --- Store result ---
        result_dict = result.model_dump()

        pr = db.save_phase_result(run_id=run_id, phase=3, raw_json=result_dict)

        db.update_job(
            job_id, status="completed", progress=100,
            log_msg="Template mapping complete",
            result_ref=pr["id"],
        )

        return {"status": "completed", "job_id": job_id}

    except Exception as e:
        logger.exception("Phase 3 task failed for job %s", job_id)
        error_detail = f"{type(e).__name__}: {e}"
        db.update_job(job_id, status="failed", error_msg=error_detail)
        raise
