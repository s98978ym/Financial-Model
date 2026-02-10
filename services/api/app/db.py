"""Database connection layer.

Supports two modes:
- PostgreSQL (Supabase) when DATABASE_URL is set
- In-memory fallback for local development without DB

All DB operations go through the ``Database`` class which
transparently handles both modes.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "")

# ---------------------------------------------------------------------------
# Connection pool (lazy init)
# ---------------------------------------------------------------------------

_pool = None


def _get_pool():
    global _pool
    if _pool is not None:
        return _pool
    if not DATABASE_URL:
        return None
    try:
        import psycopg2
        from psycopg2 import pool as pg_pool

        _pool = pg_pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=5,
            dsn=DATABASE_URL,
        )
        logger.info("PostgreSQL connection pool created")
        return _pool
    except Exception as e:
        logger.warning("Failed to create PostgreSQL pool: %s — using in-memory fallback", e)
        return None


@contextmanager
def get_conn():
    """Yield a PostgreSQL connection from the pool."""
    pool = _get_pool()
    if pool is None:
        yield None
        return
    conn = pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


# ---------------------------------------------------------------------------
# In-memory fallback stores
# ---------------------------------------------------------------------------

_mem_projects: Dict[str, dict] = {}
_mem_documents: Dict[str, dict] = {}
_mem_runs: Dict[str, dict] = {}
_mem_phase_results: Dict[str, dict] = {}
_mem_edits: List[dict] = []
_mem_jobs: Dict[str, dict] = {}
_mem_llm_audits: List[dict] = []


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uuid() -> str:
    return str(uuid.uuid4())


def _use_pg() -> bool:
    return _get_pool() is not None


# ===================================================================
# Projects
# ===================================================================

def create_project(name: str, template_id: str = "v2_ib_grade", owner: str = "") -> dict:
    if _use_pg():
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO projects (name, template_id, owner)
                   VALUES (%s, %s, %s)
                   RETURNING id, name, template_id, owner, status, current_phase, created_at, updated_at""",
                (name, template_id, owner),
            )
            row = cur.fetchone()
            return _project_row_to_dict(row)
    else:
        pid = _uuid()
        now = _now_iso()
        p = {
            "id": pid, "name": name, "template_id": template_id,
            "owner": owner, "status": "created", "current_phase": 1,
            "created_at": now, "updated_at": now,
        }
        _mem_projects[pid] = p
        return p


def get_project(project_id: str) -> Optional[dict]:
    if _use_pg():
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT id, name, template_id, owner, status, current_phase, created_at, updated_at
                   FROM projects WHERE id = %s""",
                (project_id,),
            )
            row = cur.fetchone()
            return _project_row_to_dict(row) if row else None
    else:
        return _mem_projects.get(project_id)


def list_projects() -> List[dict]:
    if _use_pg():
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT id, name, template_id, owner, status, current_phase, created_at, updated_at
                   FROM projects ORDER BY created_at DESC"""
            )
            return [_project_row_to_dict(r) for r in cur.fetchall()]
    else:
        return list(_mem_projects.values())


def update_project(project_id: str, **kwargs) -> Optional[dict]:
    if _use_pg():
        sets = []
        vals = []
        for k, v in kwargs.items():
            if k in ("status", "current_phase", "name"):
                sets.append(f"{k} = %s")
                vals.append(v)
        if not sets:
            return get_project(project_id)
        sets.append("updated_at = now()")
        vals.append(project_id)
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                f"UPDATE projects SET {', '.join(sets)} WHERE id = %s "
                "RETURNING id, name, template_id, owner, status, current_phase, created_at, updated_at",
                vals,
            )
            row = cur.fetchone()
            return _project_row_to_dict(row) if row else None
    else:
        p = _mem_projects.get(project_id)
        if p:
            p.update(kwargs)
            p["updated_at"] = _now_iso()
        return p


def _project_row_to_dict(row) -> dict:
    if row is None:
        return {}
    return {
        "id": str(row[0]), "name": row[1], "template_id": row[2],
        "owner": row[3] or "", "status": row[4], "current_phase": row[5],
        "created_at": row[6].isoformat() if hasattr(row[6], "isoformat") else str(row[6]),
        "updated_at": row[7].isoformat() if hasattr(row[7], "isoformat") else str(row[7]),
    }


# ===================================================================
# Documents
# ===================================================================

def create_document(
    project_id: str, kind: str, filename: str = "",
    storage_path: str = "", extracted_text: str = "",
    meta_json: Optional[dict] = None,
) -> dict:
    if _use_pg():
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO documents (project_id, kind, filename, storage_path, extracted_text, meta_json)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   RETURNING id, project_id, kind, filename, storage_path, extracted_text, meta_json, created_at""",
                (project_id, kind, filename or None, storage_path or None,
                 extracted_text or None, json.dumps(meta_json or {})),
            )
            row = cur.fetchone()
            return _doc_row_to_dict(row)
    else:
        did = _uuid()
        now = _now_iso()
        d = {
            "id": did, "project_id": project_id, "kind": kind,
            "filename": filename or None, "storage_path": storage_path or None,
            "extracted_text": extracted_text or None,
            "meta_json": meta_json or {},
            "created_at": now,
        }
        _mem_documents[did] = d
        return d


def get_document(doc_id: str) -> Optional[dict]:
    if _use_pg():
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT id, project_id, kind, filename, storage_path, extracted_text, meta_json, created_at
                   FROM documents WHERE id = %s""",
                (doc_id,),
            )
            row = cur.fetchone()
            return _doc_row_to_dict(row) if row else None
    else:
        return _mem_documents.get(doc_id)


def get_documents_by_project(project_id: str) -> List[dict]:
    if _use_pg():
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT id, project_id, kind, filename, storage_path, extracted_text, meta_json, created_at
                   FROM documents WHERE project_id = %s ORDER BY created_at""",
                (project_id,),
            )
            return [_doc_row_to_dict(r) for r in cur.fetchall()]
    else:
        return [d for d in _mem_documents.values() if d["project_id"] == project_id]


def _doc_row_to_dict(row) -> dict:
    if row is None:
        return {}
    meta = row[6] if isinstance(row[6], dict) else json.loads(row[6] or "{}")
    return {
        "id": str(row[0]), "project_id": str(row[1]), "kind": row[2],
        "filename": row[3], "storage_path": row[4],
        "extracted_text": row[5], "meta_json": meta,
        "created_at": row[7].isoformat() if hasattr(row[7], "isoformat") else str(row[7]),
    }


# ===================================================================
# Runs
# ===================================================================

def create_run(project_id: str) -> dict:
    if _use_pg():
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO runs (project_id) VALUES (%s)
                   RETURNING id, project_id, current_phase, bm_selected_label, status, created_at""",
                (project_id,),
            )
            row = cur.fetchone()
            return {
                "id": str(row[0]), "project_id": str(row[1]),
                "current_phase": row[2], "bm_selected_label": row[3],
                "status": row[4],
                "created_at": row[5].isoformat() if hasattr(row[5], "isoformat") else str(row[5]),
            }
    else:
        rid = _uuid()
        now = _now_iso()
        r = {"id": rid, "project_id": project_id, "current_phase": 1,
             "bm_selected_label": None, "status": "active", "created_at": now}
        _mem_runs[rid] = r
        return r


def get_latest_run(project_id: str) -> Optional[dict]:
    if _use_pg():
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT id, project_id, current_phase, bm_selected_label, status, created_at
                   FROM runs WHERE project_id = %s ORDER BY created_at DESC LIMIT 1""",
                (project_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                "id": str(row[0]), "project_id": str(row[1]),
                "current_phase": row[2], "bm_selected_label": row[3],
                "status": row[4],
                "created_at": row[5].isoformat() if hasattr(row[5], "isoformat") else str(row[5]),
            }
    else:
        runs = [r for r in _mem_runs.values() if r["project_id"] == project_id]
        return runs[-1] if runs else None


# ===================================================================
# Phase Results
# ===================================================================

def save_phase_result(run_id: str, phase: int, raw_json: dict, metrics_json: Optional[dict] = None) -> dict:
    if _use_pg():
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO phase_results (run_id, phase, raw_json, metrics_json)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (run_id, phase) DO UPDATE SET raw_json = EXCLUDED.raw_json,
                       metrics_json = EXCLUDED.metrics_json
                   RETURNING id, run_id, phase, raw_json, metrics_json, created_at""",
                (run_id, phase, json.dumps(raw_json), json.dumps(metrics_json or {})),
            )
            row = cur.fetchone()
            rj = row[3] if isinstance(row[3], dict) else json.loads(row[3] or "{}")
            mj = row[4] if isinstance(row[4], dict) else json.loads(row[4] or "{}")
            return {
                "id": str(row[0]), "run_id": str(row[1]), "phase": row[2],
                "raw_json": rj, "metrics_json": mj,
                "created_at": row[5].isoformat() if hasattr(row[5], "isoformat") else str(row[5]),
            }
    else:
        prid = _uuid()
        now = _now_iso()
        key = f"{run_id}::{phase}"
        pr = {"id": prid, "run_id": run_id, "phase": phase,
              "raw_json": raw_json, "metrics_json": metrics_json or {},
              "created_at": now}
        _mem_phase_results[key] = pr
        return pr


def get_phase_result(run_id: str, phase: int) -> Optional[dict]:
    if _use_pg():
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT id, run_id, phase, raw_json, metrics_json, created_at
                   FROM phase_results WHERE run_id = %s AND phase = %s""",
                (run_id, phase),
            )
            row = cur.fetchone()
            if not row:
                return None
            rj = row[3] if isinstance(row[3], dict) else json.loads(row[3] or "{}")
            mj = row[4] if isinstance(row[4], dict) else json.loads(row[4] or "{}")
            return {
                "id": str(row[0]), "run_id": str(row[1]), "phase": row[2],
                "raw_json": rj, "metrics_json": mj,
                "created_at": row[5].isoformat() if hasattr(row[5], "isoformat") else str(row[5]),
            }
    else:
        return _mem_phase_results.get(f"{run_id}::{phase}")


def get_all_phase_results(run_id: str) -> Dict[int, dict]:
    if _use_pg():
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT id, run_id, phase, raw_json, metrics_json, created_at
                   FROM phase_results WHERE run_id = %s ORDER BY phase""",
                (run_id,),
            )
            results = {}
            for row in cur.fetchall():
                rj = row[3] if isinstance(row[3], dict) else json.loads(row[3] or "{}")
                mj = row[4] if isinstance(row[4], dict) else json.loads(row[4] or "{}")
                results[row[2]] = {
                    "id": str(row[0]), "run_id": str(row[1]), "phase": row[2],
                    "raw_json": rj, "metrics_json": mj,
                    "created_at": row[5].isoformat() if hasattr(row[5], "isoformat") else str(row[5]),
                }
            return results
    else:
        return {
            pr["phase"]: pr
            for key, pr in _mem_phase_results.items()
            if pr["run_id"] == run_id
        }


# ===================================================================
# Jobs
# ===================================================================

def create_job(run_id: str, phase: int, payload: Optional[dict] = None) -> dict:
    if _use_pg():
        with get_conn() as conn:
            cur = conn.cursor()
            # Store payload in logs as first entry (jobs table has no payload column)
            initial_logs = json.dumps([{"ts": _now_iso(), "msg": "Job created", "payload": payload or {}}])
            cur.execute(
                """INSERT INTO jobs (run_id, phase, logs)
                   VALUES (%s, %s, %s)
                   RETURNING id, run_id, phase, status, progress, logs, result_ref, error_msg, created_at, updated_at""",
                (run_id, phase, initial_logs),
            )
            row = cur.fetchone()
            return _job_row_to_dict(row, payload)
    else:
        jid = _uuid()
        now = _now_iso()
        j = {
            "id": jid, "run_id": run_id, "phase": phase,
            "status": "queued", "progress": 0,
            "logs": [], "result": None, "error_msg": None,
            "payload": payload or {},
            "created_at": now, "updated_at": now,
        }
        _mem_jobs[jid] = j
        return j


def get_job(job_id: str) -> Optional[dict]:
    if _use_pg():
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT id, run_id, phase, status, progress, logs, result_ref, error_msg, created_at, updated_at
                   FROM jobs WHERE id = %s""",
                (job_id,),
            )
            row = cur.fetchone()
            return _job_row_to_dict(row) if row else None
    else:
        return _mem_jobs.get(job_id)


def update_job(
    job_id: str, *,
    status: Optional[str] = None, progress: Optional[int] = None,
    log_msg: Optional[str] = None, result_ref: Optional[str] = None,
    error_msg: Optional[str] = None,
) -> Optional[dict]:
    if _use_pg():
        with get_conn() as conn:
            cur = conn.cursor()
            sets = ["updated_at = now()"]
            vals: list = []
            if status:
                sets.append("status = %s")
                vals.append(status)
            if progress is not None:
                sets.append("progress = %s")
                vals.append(progress)
            if log_msg:
                sets.append("logs = logs || %s::jsonb")
                vals.append(json.dumps([{"ts": _now_iso(), "msg": log_msg}]))
            if result_ref:
                sets.append("result_ref = %s")
                vals.append(result_ref)
            if error_msg:
                sets.append("error_msg = %s")
                vals.append(error_msg)
            vals.append(job_id)
            cur.execute(
                f"UPDATE jobs SET {', '.join(sets)} WHERE id = %s "
                "RETURNING id, run_id, phase, status, progress, logs, result_ref, error_msg, created_at, updated_at",
                vals,
            )
            row = cur.fetchone()
            return _job_row_to_dict(row) if row else None
    else:
        j = _mem_jobs.get(job_id)
        if not j:
            return None
        now = _now_iso()
        if status:
            j["status"] = status
        if progress is not None:
            j["progress"] = progress
        if log_msg:
            j["logs"].append({"ts": now, "msg": log_msg})
        if result_ref:
            j["result_ref"] = result_ref
        if error_msg:
            j["error_msg"] = error_msg
        j["updated_at"] = now
        return j


def _job_row_to_dict(row, payload=None) -> dict:
    if row is None:
        return {}
    logs_raw = row[5]
    if isinstance(logs_raw, str):
        logs_raw = json.loads(logs_raw)
    elif logs_raw is None:
        logs_raw = []
    return {
        "id": str(row[0]), "run_id": str(row[1]), "phase": row[2],
        "status": row[3], "progress": row[4],
        "logs": logs_raw, "result_ref": str(row[6]) if row[6] else None,
        "error_msg": row[7],
        "payload": payload or {},
        "created_at": row[8].isoformat() if hasattr(row[8], "isoformat") else str(row[8]),
        "updated_at": row[9].isoformat() if hasattr(row[9], "isoformat") else str(row[9]),
    }


# ===================================================================
# LLM Audits
# ===================================================================

def save_llm_audit(
    run_id: str, phase: int, provider: str, model: str,
    prompt_hash: str, token_usage: dict, latency_ms: int,
    temperature: float = 0.1, max_tokens: int = 32768,
    result_hash: str = "",
) -> dict:
    record = {
        "run_id": run_id, "phase": phase, "provider": provider, "model": model,
        "prompt_hash": prompt_hash, "token_usage": token_usage,
        "latency_ms": latency_ms, "temperature": temperature,
        "max_tokens": max_tokens, "result_hash": result_hash,
    }
    if _use_pg():
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO llm_audits
                   (run_id, phase, provider, model, prompt_hash, token_usage, latency_ms, temperature, max_tokens, result_hash)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING id""",
                (run_id, phase, provider, model, prompt_hash,
                 json.dumps(token_usage), latency_ms, temperature, max_tokens, result_hash),
            )
            row = cur.fetchone()
            record["id"] = str(row[0])
    else:
        record["id"] = _uuid()
        _mem_llm_audits.append(record)
    return record


# ===================================================================
# Edits
# ===================================================================

def save_edit(run_id: str, phase: int, patch_json: dict, author: str = "user") -> dict:
    if _use_pg():
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO edits (run_id, phase, patch_json, author)
                   VALUES (%s, %s, %s, %s)
                   RETURNING id, created_at""",
                (run_id, phase, json.dumps(patch_json), author),
            )
            row = cur.fetchone()
            return {"id": str(row[0]), "run_id": run_id, "phase": phase,
                    "patch_json": patch_json, "author": author,
                    "created_at": row[1].isoformat() if hasattr(row[1], "isoformat") else str(row[1])}
    else:
        eid = _uuid()
        now = _now_iso()
        e = {"id": eid, "run_id": run_id, "phase": phase,
             "patch_json": patch_json, "author": author, "created_at": now}
        _mem_edits.append(e)
        return e


def get_edits(run_id: str, phase: Optional[int] = None) -> List[dict]:
    if _use_pg():
        with get_conn() as conn:
            cur = conn.cursor()
            if phase is not None:
                cur.execute(
                    "SELECT id, run_id, phase, patch_json, author, created_at FROM edits WHERE run_id = %s AND phase = %s ORDER BY created_at",
                    (run_id, phase),
                )
            else:
                cur.execute(
                    "SELECT id, run_id, phase, patch_json, author, created_at FROM edits WHERE run_id = %s ORDER BY created_at",
                    (run_id,),
                )
            return [
                {"id": str(r[0]), "run_id": str(r[1]), "phase": r[2],
                 "patch_json": r[3] if isinstance(r[3], dict) else json.loads(r[3] or "{}"),
                 "author": r[4],
                 "created_at": r[5].isoformat() if hasattr(r[5], "isoformat") else str(r[5])}
                for r in cur.fetchall()
            ]
    else:
        edits = [e for e in _mem_edits if e["run_id"] == run_id]
        if phase is not None:
            edits = [e for e in edits if e["phase"] == phase]
        return edits
