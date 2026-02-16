"""Celery task for Phase 2: Business Model Analysis.

Wraps src.agents.business_model_analyzer with job progress tracking.
Uses streaming token progress for real-time feedback during LLM calls.
"""
from __future__ import annotations

import logging

from services.worker.celery_app import app

logger = logging.getLogger(__name__)


@app.task(bind=True, name="tasks.phase2.run_bm_analysis")
def run_bm_analysis(self, job_id: str):
    """Execute Phase 2 Business Model Analysis as a Celery task."""
    from core.providers.base import LLMConfig
    from core.providers.guards import DocumentTruncation
    from services.api.app import db
    from services.worker.tasks.provider_helper import get_adapter_for_run
    from src.agents.business_model_analyzer import BusinessModelAnalyzer

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

        document_id = payload.get("document_id")
        feedback = payload.get("feedback", "")
        run_id = job["run_id"]

        # --- Load document text ---
        doc = db.get_document(document_id) if document_id else None
        document_text = (doc.get("extracted_text") or "") if doc else ""

        if not document_text:
            db.update_job(job_id, status="failed", error_msg="Document text is empty")
            return {"status": "failed", "job_id": job_id}

        db.update_job(job_id, progress=10, log_msg="Document loaded")

        # --- Truncate for Phase 2 (70% front + 25% back) ---
        truncated = DocumentTruncation.for_phase2(document_text)
        db.update_job(job_id, progress=15, log_msg="Document truncated for analysis")

        # --- Run BM Analysis ---
        adapter = get_adapter_for_run(run_id)
        analyzer = BusinessModelAnalyzer(llm_client=adapter)

        db.update_job(job_id, progress=20, log_msg="Starting LLM analysis")

        # Streaming token progress: track actual generation instead of time-based heartbeat.
        # Estimated output: max_tokens * ~4 chars/token. Progress mapped to 20-95%.
        _ESTIMATED_OUTPUT_CHARS = 8192 * 4  # ~32K chars
        _last_reported_pct = [20]

        def _streaming_progress(chars_received: int):
            frac = min(chars_received / _ESTIMATED_OUTPUT_CHARS, 1.0)
            pct = min(int(20 + 75 * frac), 95)
            # Only update DB when progress actually changes (avoid flooding)
            if pct > _last_reported_pct[0]:
                _last_reported_pct[0] = pct
                tokens_est = chars_received // 4
                db.update_job(
                    job_id, progress=pct,
                    log_msg=f"LLM generating... (~{tokens_est} tokens)",
                )

        result = analyzer.analyze(
            truncated,
            feedback=feedback,
            progress_callback=_streaming_progress,
        )

        # --- Store result ---
        result_dict = result.model_dump()

        pr = db.save_phase_result(run_id=run_id, phase=2, raw_json=result_dict)
        db.update_job(
            job_id,
            status="completed",
            progress=100,
            log_msg="Analysis complete",
            result_ref=pr["id"],
        )

        return {"status": "completed", "job_id": job_id}

    except Exception as e:
        logger.exception("Phase 2 task failed for job %s", job_id)
        db.update_job(job_id, status="failed", error_msg=str(e)[:500])
        raise
