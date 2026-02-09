"""Celery task for Phase 6: Excel Export."""

from __future__ import annotations

import logging

from services.worker.celery_app import app

logger = logging.getLogger(__name__)


@app.task(bind=True, name="tasks.export.generate_excel")
def generate_excel(self, job_id: str):
    """Execute Phase 6 Excel Generation as a Celery task."""
    try:
        self.update_state(state="STARTED", meta={"progress": 0, "phase": 6})
        logger.info("Export task started for job %s", job_id)

        # TODO: Wire up core.excel.writer + core.excel.case_generator
        # writer = PLWriter(template_path, output_path, colors)
        # writer.generate(parameters)
        # validator = PLValidator(template_path, output_path, colors)
        # validation = validator.validate()

        self.update_state(state="SUCCESS", meta={"progress": 100, "phase": 6})
        return {"status": "completed", "job_id": job_id}
    except Exception as e:
        logger.error("Export task failed for job %s: %s", job_id, e)
        raise
