"""Celery task for Phase 2: Business Model Analysis.

Wraps src.agents.business_model_analyzer with job progress tracking.
"""
from __future__ import annotations

import json
import logging
import math
import threading
import time
import traceback

from services.worker.celery_app import app

logger = logging.getLogger(__name__)


@app.task(bind=True, name="tasks.phase2.run_bm_analysis")
def run_bm_analysis(self, job_id: str):
    """Execute Phase 2 Business Model Analysis as a Celery task."""
    from core.providers import AnthropicProvider, ProviderAdapter
    from core.providers.guards import DocumentTruncation
    from services.api.app import db
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
        provider = AnthropicProvider()
        adapter = ProviderAdapter(provider)
        analyzer = BusinessModelAnalyzer(llm_client=adapter)

        db.update_job(job_id, progress=20, log_msg="Starting LLM analysis")

        # Run analysis with a heartbeat thread that updates progress
        # so the frontend knows the job is still alive during the LLM call
        _heartbeat_stop = threading.Event()

        def _heartbeat():
            t0 = time.time()
            while not _heartbeat_stop.is_set():
                _heartbeat_stop.wait(timeout=8)
                if _heartbeat_stop.is_set():
                    break
                elapsed = time.time() - t0
                # Asymptotic progress: fast early, slows down approaching 95%
                # ~40% at 30s, ~52% at 60s, ~69% at 2min, ~89% at 5min, ~94% at 10min
                pct = min(int(25 + 70 * (1 - math.exp(-elapsed / 120))), 95)
                try:
                    db.update_job(job_id, progress=pct, log_msg="LLM generating response...")
                except Exception:
                    pass

        hb_thread = threading.Thread(target=_heartbeat, daemon=True)
        hb_thread.start()

        try:
            result = analyzer.analyze(truncated, feedback=feedback)
        finally:
            _heartbeat_stop.set()
            hb_thread.join(timeout=2)

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
