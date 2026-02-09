"""Celery task for Phase 5: Parameter Extraction."""

from __future__ import annotations

import logging

from services.worker.celery_app import app

logger = logging.getLogger(__name__)


@app.task(bind=True, name="tasks.phase5.run_parameter_extraction")
def run_parameter_extraction(self, job_id: str):
    """Execute Phase 5 Parameter Extraction as a Celery task."""
    try:
        self.update_state(state="STARTED", meta={"progress": 0, "phase": 5})
        logger.info("Phase 5 task started for job %s", job_id)

        # TODO: Wire up core.agents.parameter_extractor
        # provider = AnthropicProvider()
        # extractor = ParameterExtractorAgent(provider)
        # result = extractor.extract_values(model_design_json, document_text)

        self.update_state(state="SUCCESS", meta={"progress": 100, "phase": 5})
        return {"status": "completed", "job_id": job_id}
    except Exception as e:
        logger.error("Phase 5 task failed for job %s: %s", job_id, e)
        raise
