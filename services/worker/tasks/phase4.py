"""Celery task for Phase 4: Model Design."""

from __future__ import annotations

import logging

from services.worker.celery_app import app

logger = logging.getLogger(__name__)


@app.task(bind=True, name="tasks.phase4.run_model_design")
def run_model_design(self, job_id: str):
    """Execute Phase 4 Model Design as a Celery task."""
    try:
        self.update_state(state="STARTED", meta={"progress": 0, "phase": 4})
        logger.info("Phase 4 task started for job %s", job_id)

        # TODO: Wire up core.agents.model_designer
        # provider = AnthropicProvider()
        # designer = ModelDesigner(provider)
        # result = designer.design(analysis_json, ts_json, catalog_items)

        self.update_state(state="SUCCESS", meta={"progress": 100, "phase": 4})
        return {"status": "completed", "job_id": job_id}
    except Exception as e:
        logger.error("Phase 4 task failed for job %s: %s", job_id, e)
        raise
