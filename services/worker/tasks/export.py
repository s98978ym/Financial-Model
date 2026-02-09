"""Celery task for Phase 6: Excel Export."""

from __future__ import annotations

import json
import logging
import os
import tempfile

from services.worker.celery_app import app

logger = logging.getLogger(__name__)

TEMPLATE_PATH = os.environ.get(
    "TEMPLATE_PATH",
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "templates", "v2_ib_grade.xlsx"),
)


@app.task(bind=True, name="tasks.export.generate_excel")
def generate_excel(self, job_id: str):
    """Execute Phase 6 Excel Generation as a Celery task."""
    from services.api.app import db

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
        scenarios = payload.get("scenarios", ["base", "best", "worst"])

        # --- Load Phase 5 result (extracted parameters) ---
        phase5_result = db.get_phase_result(run_id, phase=5)
        if not phase5_result:
            db.update_job(job_id, status="failed", error_msg="Phase 5 result not found")
            return {"status": "failed", "job_id": job_id}

        parameters_json = phase5_result.get("raw_json", {})
        db.update_job(job_id, progress=15, log_msg="Phase 5 data loaded")

        # --- Attempt Excel generation ---
        try:
            from src.excel.writer import PLWriter
            from src.excel.validator import PLValidator, generate_needs_review_csv
            from src.excel.case_generator import CaseGenerator
            from src.config import PhaseAConfig

            config = PhaseAConfig()
            db.update_job(job_id, progress=20, log_msg="Generating Excel files")

            # Convert parameters to ExtractedParameter format if needed
            extractions = parameters_json.get("extractions", [])

            output_dir = tempfile.mkdtemp(prefix="plgen_export_")
            generated_files = []

            for scenario in scenarios:
                output_path = os.path.join(output_dir, f"PL_{scenario}.xlsx")
                writer = PLWriter(TEMPLATE_PATH, output_path, config)
                writer.generate(extractions)
                generated_files.append(output_path)

                db.update_job(
                    job_id, progress=20 + (60 * (scenarios.index(scenario) + 1) // len(scenarios)),
                    log_msg=f"Generated {scenario} scenario",
                )

            # Generate needs_review.csv
            review_path = os.path.join(output_dir, "needs_review.csv")
            generate_needs_review_csv(extractions, review_path)
            generated_files.append(review_path)

            # Validate
            db.update_job(job_id, progress=90, log_msg="Validating output")
            base_output = os.path.join(output_dir, "PL_base.xlsx")
            if os.path.exists(base_output):
                validator = PLValidator(TEMPLATE_PATH, base_output)
                validation = validator.validate()
            else:
                validation = {"status": "skipped"}

            db.update_job(
                job_id, status="completed", progress=100,
                log_msg="Export complete",
                result_ref=json.dumps({
                    "output_dir": output_dir,
                    "files": generated_files,
                    "validation": validation if isinstance(validation, dict) else {"status": "ok"},
                }),
            )

        except ImportError as ie:
            logger.warning("Excel modules not available: %s — returning stub", ie)
            db.update_job(
                job_id, status="completed", progress=100,
                log_msg="Export complete (stub — Excel modules not available)",
                result_ref=json.dumps({"stub": True, "parameters": parameters_json}),
            )

        return {"status": "completed", "job_id": job_id}

    except Exception as e:
        logger.error("Export task failed for job %s: %s", job_id, e)
        db.update_job(job_id, status="failed", error_msg=str(e))
        raise
