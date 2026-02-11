"""Celery task for Phase 4: Model Design."""

from __future__ import annotations

import json
import logging

from services.worker.celery_app import app

logger = logging.getLogger(__name__)


@app.task(bind=True, name="tasks.phase4.run_model_design")
def run_model_design(self, job_id: str):
    """Execute Phase 4 Model Design as a Celery task."""
    from core.providers import AnthropicProvider, ProviderAdapter
    from services.api.app import db
    from src.agents.model_designer import ModelDesigner

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

        # --- Load Phase 2 & 3 results ---
        phase2_result = db.get_phase_result(run_id, phase=2)
        phase3_result = db.get_phase_result(run_id, phase=3)

        if not phase2_result or not phase3_result:
            missing = []
            if not phase2_result:
                missing.append("Phase 2")
            if not phase3_result:
                missing.append("Phase 3")
            db.update_job(job_id, status="failed", error_msg=f"Missing results: {', '.join(missing)}")
            return {"status": "failed", "job_id": job_id}

        analysis_json = phase2_result.get("raw_json", {})
        ts_json = phase3_result.get("raw_json", {})
        catalog_items = payload.get("catalog_ref", [])
        if isinstance(catalog_items, str):
            catalog_items = []

        db.update_job(job_id, progress=15, log_msg="Phase 2 & 3 data loaded")

        # --- Apply user edits ---
        edits = payload.get("edits", [])
        if edits:
            db.update_job(job_id, progress=18, log_msg=f"Applying {len(edits)} user edits")

        # --- Run Model Design ---
        provider = AnthropicProvider()
        adapter = ProviderAdapter(provider)
        designer = ModelDesigner(llm_client=adapter)

        db.update_job(job_id, progress=20, log_msg="Starting model design")
        result = designer.design(
            analysis_json=json.dumps(analysis_json),
            template_structure_json=json.dumps(ts_json),
            catalog_items=catalog_items,
            feedback="",
        )

        # --- Store result ---
        result_dict = result.to_dict() if hasattr(result, "to_dict") else json.loads(json.dumps(result, default=str))
        pr = db.save_phase_result(run_id=run_id, phase=4, raw_json=result_dict)

        db.update_job(
            job_id, status="completed", progress=100,
            log_msg="Model design complete",
            result_ref=pr["id"],
        )

        return {"status": "completed", "job_id": job_id}

    except Exception as e:
        logger.exception("Phase 4 task failed for job %s", job_id)
        db.update_job(job_id, status="failed", error_msg=str(e))
        raise
