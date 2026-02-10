"""Excel export endpoints — generate and download."""

from __future__ import annotations

import io
import logging
import os
import tempfile

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from .. import db
from .jobs import create_job

logger = logging.getLogger(__name__)
router = APIRouter()

_CELERY_ENABLED = bool(os.environ.get("REDIS_URL"))

# In-memory file store for local dev (when no object storage)
_file_store: dict[str, bytes] = {}


@router.post("/export/excel", status_code=202)
async def export_excel(body: dict):
    """Generate Excel file(s) for download (async job).

    Creates Best/Base/Worst scenario files + needs_review.csv.
    """
    project_id = body.get("project_id")
    if not project_id:
        raise HTTPException(
            status_code=422,
            detail={"code": "VALIDATION_ERROR", "message": "project_id required"},
        )

    run = db.get_latest_run(project_id)
    if not run:
        run = db.create_run(project_id)

    job = create_job(phase=6, run_id=run["id"], payload={
        "project_id": project_id,
        "parameters": body.get("parameters", {}),
        "scenarios": body.get("scenarios", ["base", "best", "worst"]),
        "options": body.get("options", {}),
    })

    if _CELERY_ENABLED:
        from services.worker.celery_app import app as celery_app
        celery_app.send_task("tasks.export.generate_excel", args=[job["id"]])
        logger.info("Dispatched export task for job %s", job["id"])
    else:
        # Local dev: generate synchronously using recalc engine
        _generate_local_excel(job["id"], run["id"], body)

    return {
        "job_id": job["id"],
        "status": "queued",
        "phase": 6,
        "poll_url": f"/v1/jobs/{job['id']}",
        "download_url": f"/v1/export/download/{job['id']}",
    }


@router.get("/export/download/{job_id}")
async def download_excel(job_id: str):
    """Download generated Excel file.

    Returns the .xlsx file as a streaming response.
    """
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail={"code": "JOB_NOT_FOUND"})

    if job["status"] != "completed":
        raise HTTPException(
            status_code=409,
            detail={
                "code": "NOT_READY",
                "message": f"Job status is '{job['status']}', wait for completion",
                "status": job["status"],
            },
        )

    # Try to load from file store or disk
    result_ref = job.get("result_ref") or ""
    file_bytes = None

    # Check in-memory store
    if job_id in _file_store:
        file_bytes = _file_store[job_id]
    # Check disk path
    elif result_ref and os.path.exists(result_ref):
        with open(result_ref, "rb") as f:
            file_bytes = f.read()

    if not file_bytes:
        raise HTTPException(
            status_code=404,
            detail={"code": "FILE_NOT_FOUND", "message": "Excel file no longer available"},
        )

    project_name = "pl_model"
    # Try to get project name for filename
    if job.get("run_id"):
        run = None
        # Get project info from run
        for p in db.list_projects():
            r = db.get_latest_run(p["id"])
            if r and r["id"] == job["run_id"]:
                project_name = p.get("name", "pl_model").replace(" ", "_")[:30]
                break

    filename = f"{project_name}_base.xlsx"

    # Use RFC 5987 encoding for non-ASCII filenames
    from urllib.parse import quote
    encoded_filename = quote(filename)
    disposition = f"attachment; filename*=UTF-8''{encoded_filename}"

    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": disposition},
    )


def _generate_local_excel(job_id: str, run_id: str, body: dict):
    """Generate Excel file locally (no Celery) for development."""
    try:
        db.update_job(job_id, status="running", progress=10, log_msg="Starting local generation")

        # Try real PLWriter first
        try:
            from src.excel.writer import PLWriter
            from src.excel.case_generator import CaseGenerator
            from src.config.models import ExtractedParameter, CellTarget

            # Load Phase 5 results
            phase5 = db.get_phase_result(run_id, 5)
            if phase5 and phase5.get("raw_json", {}).get("extractions"):
                extractions = phase5["raw_json"]["extractions"]
                params = []
                for ext in extractions:
                    targets = [CellTarget(sheet=t["sheet"], cell=t["cell"])
                               for t in ext.get("mapped_targets", [])]
                    params.append(ExtractedParameter(
                        key=ext.get("key", ""),
                        label=ext.get("label", ""),
                        value=ext.get("value"),
                        unit=ext.get("unit", ""),
                        mapped_targets=targets,
                        confidence=ext.get("confidence", 0.5),
                        source=ext.get("source", "document"),
                        selected=True,
                    ))

                # Find template
                from services.api.app.routers.phases import _resolve_template
                template_path = _resolve_template("v2_ib_grade")

                writer = PLWriter(template_path=template_path)
                output_path = writer.generate(params, scenario="base")

                with open(output_path, "rb") as f:
                    _file_store[job_id] = f.read()

                db.update_job(
                    job_id, status="completed", progress=100,
                    log_msg="Excel generated", result_ref=output_path,
                )
                return
        except ImportError:
            logger.info("PLWriter not available, using openpyxl fallback")
        except Exception as e:
            logger.warning("PLWriter failed: %s — falling back", e)

        # Fallback: create a simple Excel with recalc data
        import openpyxl
        from .recalc import _compute_pl

        parameters = body.get("parameters", {})
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "PL Summary"

        # Header
        headers = ["", "FY1", "FY2", "FY3", "FY4", "FY5"]
        for col, h in enumerate(headers, 1):
            ws.cell(row=1, column=col, value=h).font = openpyxl.styles.Font(bold=True)

        pl = _compute_pl(parameters)["pl_summary"]
        rows_data = [
            ("売上高", pl["revenue"]),
            ("売上原価", pl["cogs"]),
            ("粗利", pl["gross_profit"]),
            ("OPEX", pl["opex"]),
            ("営業利益", pl["operating_profit"]),
            ("FCF", pl["fcf"]),
            ("累積FCF", pl["cumulative_fcf"]),
        ]

        for r, (label, values) in enumerate(rows_data, 2):
            ws.cell(row=r, column=1, value=label)
            for c, v in enumerate(values, 2):
                ws.cell(row=r, column=c, value=v)

        buf = io.BytesIO()
        wb.save(buf)
        _file_store[job_id] = buf.getvalue()

        db.update_job(
            job_id, status="completed", progress=100,
            log_msg="Excel generated (fallback)",
        )

    except Exception as e:
        logger.error("Local Excel generation failed: %s", e)
        db.update_job(job_id, status="failed", error_msg=str(e))
