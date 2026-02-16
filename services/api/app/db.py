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
_pool_init_done = False  # True once we've attempted to connect (success or failure)


def _get_pool():
    global _pool, _pool_init_done
    if _pool is not None:
        return _pool
    if _pool_init_done:
        return None  # Already tried and failed — don't retry on every request
    _pool_init_done = True
    if not DATABASE_URL:
        logger.info("No DATABASE_URL set — using in-memory fallback")
        return None
    try:
        import psycopg2
        from psycopg2 import pool as pg_pool

        _pool = pg_pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=3,
            dsn=DATABASE_URL,
            connect_timeout=5,
        )
        logger.info("PostgreSQL connection pool created")
        _run_migrations(_pool)
        return _pool
    except Exception as e:
        logger.warning("Failed to create PostgreSQL pool: %s — using in-memory fallback", e)
        return None


def _run_migrations(pool):
    """Apply lightweight schema migrations (add missing columns/tables)."""
    global _has_memo_col, _has_llm_cols
    try:
        conn = pool.getconn()
        try:
            cur = conn.cursor()
            # --- memo column ---
            cur.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'projects' AND column_name = 'memo'"
            )
            if cur.fetchone():
                _has_memo_col = True
            else:
                cur.execute("ALTER TABLE projects ADD COLUMN memo TEXT NOT NULL DEFAULT ''")
                conn.commit()
                _has_memo_col = True
                logger.info("Migration: added 'memo' column to projects table")

            # --- LLM provider/model columns ---
            cur.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'projects' AND column_name = 'llm_provider'"
            )
            if cur.fetchone():
                _has_llm_cols = True
            else:
                cur.execute("ALTER TABLE projects ADD COLUMN llm_provider TEXT")
                cur.execute("ALTER TABLE projects ADD COLUMN llm_model TEXT")
                conn.commit()
                _has_llm_cols = True
                logger.info("Migration: added llm_provider/llm_model columns to projects")

            # --- system_settings table ---
            cur.execute(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                "WHERE table_name = 'system_settings')"
            )
            if not cur.fetchone()[0]:
                cur.execute(
                    "CREATE TABLE system_settings ("
                    "  key TEXT PRIMARY KEY,"
                    "  value JSONB NOT NULL,"
                    "  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()"
                    ")"
                )
                cur.execute(
                    "INSERT INTO system_settings (key, value) VALUES "
                    "('llm_default', %s) ON CONFLICT (key) DO NOTHING",
                    (json.dumps({"provider": "anthropic", "model": "claude-sonnet-4-5-20250929"}),),
                )
                conn.commit()
                logger.info("Migration: created system_settings table")
        except Exception as e:
            conn.rollback()
            logger.warning("Migration failed (non-fatal): %s", e)
        finally:
            pool.putconn(conn)
    except Exception as e:
        logger.warning("Could not run migrations: %s", e)


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
_mem_prompt_versions: List[dict] = []
_mem_system_settings: Dict[str, Any] = {
    "llm_default": {"provider": "anthropic", "model": "claude-sonnet-4-5-20250929"},
}


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uuid() -> str:
    return str(uuid.uuid4())


def _use_pg() -> bool:
    return _get_pool() is not None


# Track whether optional columns have been confirmed present
_has_memo_col = False
_has_llm_cols = False


def _proj_cols() -> str:
    """Return SELECT/RETURNING column list for projects based on schema."""
    base = "id, name, template_id, owner, status, current_phase"
    if _has_memo_col:
        base += ", memo"
    if _has_llm_cols:
        base += ", llm_provider, llm_model"
    base += ", created_at, updated_at"
    return base


# ===================================================================
# Projects
# ===================================================================

def create_project(
    name: str, template_id: str = "v2_ib_grade", owner: str = "",
    llm_provider: Optional[str] = None, llm_model: Optional[str] = None,
) -> dict:
    if _use_pg():
        cols = "name, template_id, owner"
        vals: list = [name, template_id, owner]
        placeholders = "%s, %s, %s"
        if llm_provider:
            cols += ", llm_provider"
            vals.append(llm_provider)
            placeholders += ", %s"
        if llm_model:
            cols += ", llm_model"
            vals.append(llm_model)
            placeholders += ", %s"
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                f"INSERT INTO projects ({cols}) "
                f"VALUES ({placeholders}) RETURNING {_proj_cols()}",
                vals,
            )
            row = cur.fetchone()
            return _project_row_to_dict(row)
    else:
        pid = _uuid()
        now = _now_iso()
        p = {
            "id": pid, "name": name, "template_id": template_id,
            "owner": owner, "status": "created", "current_phase": 1,
            "memo": "", "llm_provider": llm_provider, "llm_model": llm_model,
            "created_at": now, "updated_at": now,
        }
        _mem_projects[pid] = p
        return p


def get_project(project_id: str) -> Optional[dict]:
    if _use_pg():
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(f"SELECT {_proj_cols()} FROM projects WHERE id = %s", (project_id,))
            row = cur.fetchone()
            return _project_row_to_dict(row) if row else None
    else:
        return _mem_projects.get(project_id)


def list_projects() -> List[dict]:
    if _use_pg():
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(f"SELECT {_proj_cols()} FROM projects ORDER BY created_at DESC")
            return [_project_row_to_dict(r) for r in cur.fetchall()]
    else:
        return list(_mem_projects.values())


def update_project(project_id: str, **kwargs) -> Optional[dict]:
    if _use_pg():
        allowed = {"status", "current_phase", "name"}
        if _has_memo_col:
            allowed.add("memo")
        sets = []
        vals = []
        for k, v in kwargs.items():
            if k in allowed:
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
                f"RETURNING {_proj_cols()}",
                vals,
            )
            row = cur.fetchone()
            return _project_row_to_dict(row) if row else None
    else:
        p = _mem_projects.get(project_id)
        if p:
            for k, v in kwargs.items():
                if k in ("status", "current_phase", "name", "memo"):
                    p[k] = v
            p["updated_at"] = _now_iso()
        return p


def delete_project(project_id: str) -> bool:
    """Delete a project and all related data (cascades via FK)."""
    if _use_pg():
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM projects WHERE id = %s", (project_id,))
            return cur.rowcount > 0
    else:
        if project_id in _mem_projects:
            del _mem_projects[project_id]
            # Clean up related in-memory data
            doc_ids = [k for k, v in _mem_documents.items() if v["project_id"] == project_id]
            for did in doc_ids:
                del _mem_documents[did]
            run_ids = [k for k, v in _mem_runs.items() if v["project_id"] == project_id]
            for rid in run_ids:
                del _mem_runs[rid]
                # Clean phase results and jobs for this run
                pr_keys = [k for k in _mem_phase_results if k.startswith(rid + "::")]
                for pk in pr_keys:
                    del _mem_phase_results[pk]
                job_ids = [k for k, v in _mem_jobs.items() if v["run_id"] == rid]
                for jid in job_ids:
                    del _mem_jobs[jid]
            return True
        return False


def _project_row_to_dict(row) -> dict:
    if row is None:
        return {}
    # Dynamic column mapping based on _has_memo_col / _has_llm_cols flags.
    # Base cols: id(0), name(1), template_id(2), owner(3), status(4), current_phase(5)
    d: dict = {
        "id": str(row[0]), "name": row[1], "template_id": row[2],
        "owner": row[3] or "", "status": row[4], "current_phase": row[5],
    }
    idx = 6
    if _has_memo_col:
        d["memo"] = row[idx] or ""
        idx += 1
    else:
        d["memo"] = ""
    if _has_llm_cols:
        d["llm_provider"] = row[idx] or None
        d["llm_model"] = row[idx + 1] or None
        idx += 2
    else:
        d["llm_provider"] = None
        d["llm_model"] = None
    d["created_at"] = row[idx].isoformat() if hasattr(row[idx], "isoformat") else str(row[idx])
    d["updated_at"] = row[idx + 1].isoformat() if hasattr(row[idx + 1], "isoformat") else str(row[idx + 1])
    return d


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


# ===================================================================
# Prompt Versions
# ===================================================================

def _ensure_prompt_versions_table():
    """Auto-create prompt_versions table if it doesn't exist (Postgres only)."""
    if not _use_pg():
        return
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS prompt_versions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    prompt_key TEXT NOT NULL,
                    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
                    content TEXT NOT NULL,
                    label TEXT DEFAULT '',
                    author TEXT DEFAULT 'admin',
                    is_active BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
            """)
    except Exception as e:
        logger.warning("prompt_versions migration skipped: %s", e)


def save_prompt_version(prompt_key: str, content: str, project_id: Optional[str] = None,
                        label: str = "", author: str = "admin", is_active: bool = True) -> dict:
    """Save a new prompt version. If is_active, deactivate other versions for same key+project."""
    _ensure_prompt_versions_table()

    if _use_pg():
        with get_conn() as conn:
            cur = conn.cursor()
            if is_active:
                if project_id:
                    cur.execute(
                        "UPDATE prompt_versions SET is_active = FALSE WHERE prompt_key = %s AND project_id = %s",
                        (prompt_key, project_id),
                    )
                else:
                    cur.execute(
                        "UPDATE prompt_versions SET is_active = FALSE WHERE prompt_key = %s AND project_id IS NULL",
                        (prompt_key,),
                    )
            cur.execute(
                """INSERT INTO prompt_versions (prompt_key, project_id, content, label, author, is_active)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   RETURNING id, created_at""",
                (prompt_key, project_id, content, label, author, is_active),
            )
            row = cur.fetchone()
            return {"id": str(row[0]), "prompt_key": prompt_key, "project_id": project_id,
                    "content": content, "label": label, "author": author, "is_active": is_active,
                    "created_at": row[1].isoformat() if hasattr(row[1], "isoformat") else str(row[1])}
    else:
        if is_active:
            for pv in _mem_prompt_versions:
                if pv["prompt_key"] == prompt_key and pv.get("project_id") == project_id:
                    pv["is_active"] = False
        vid = _uuid()
        now = _now_iso()
        v = {"id": vid, "prompt_key": prompt_key, "project_id": project_id,
             "content": content, "label": label, "author": author,
             "is_active": is_active, "created_at": now}
        _mem_prompt_versions.append(v)
        return v


def get_prompt_versions(prompt_key: str, project_id: Optional[str] = None) -> List[dict]:
    """Get all versions for a prompt key, optionally scoped to a project."""
    _ensure_prompt_versions_table()

    if _use_pg():
        with get_conn() as conn:
            cur = conn.cursor()
            if project_id:
                cur.execute(
                    """SELECT id, prompt_key, project_id, content, label, author, is_active, created_at
                       FROM prompt_versions
                       WHERE prompt_key = %s AND (project_id = %s OR project_id IS NULL)
                       ORDER BY created_at DESC""",
                    (prompt_key, project_id),
                )
            else:
                cur.execute(
                    """SELECT id, prompt_key, project_id, content, label, author, is_active, created_at
                       FROM prompt_versions
                       WHERE prompt_key = %s AND project_id IS NULL
                       ORDER BY created_at DESC""",
                    (prompt_key,),
                )
            return [
                {"id": str(r[0]), "prompt_key": r[1], "project_id": str(r[2]) if r[2] else None,
                 "content": r[3], "label": r[4], "author": r[5], "is_active": r[6],
                 "created_at": r[7].isoformat() if hasattr(r[7], "isoformat") else str(r[7])}
                for r in cur.fetchall()
            ]
    else:
        versions = [v for v in _mem_prompt_versions if v["prompt_key"] == prompt_key]
        if project_id:
            versions = [v for v in versions if v.get("project_id") in (project_id, None)]
        else:
            versions = [v for v in versions if v.get("project_id") is None]
        return sorted(versions, key=lambda v: v["created_at"], reverse=True)


def get_active_prompt(prompt_key: str, project_id: Optional[str] = None) -> Optional[dict]:
    """Get the active version for a prompt key. Project-level overrides global."""
    _ensure_prompt_versions_table()

    if _use_pg():
        with get_conn() as conn:
            cur = conn.cursor()
            if project_id:
                cur.execute(
                    """SELECT id, prompt_key, project_id, content, label, author, is_active, created_at
                       FROM prompt_versions
                       WHERE prompt_key = %s AND project_id = %s AND is_active = TRUE
                       LIMIT 1""",
                    (prompt_key, project_id),
                )
                row = cur.fetchone()
                if row:
                    return {"id": str(row[0]), "prompt_key": row[1], "project_id": str(row[2]) if row[2] else None,
                            "content": row[3], "label": row[4], "author": row[5], "is_active": row[6],
                            "created_at": row[7].isoformat() if hasattr(row[7], "isoformat") else str(row[7])}
            # Fallback to global
            cur.execute(
                """SELECT id, prompt_key, project_id, content, label, author, is_active, created_at
                   FROM prompt_versions
                   WHERE prompt_key = %s AND project_id IS NULL AND is_active = TRUE
                   LIMIT 1""",
                (prompt_key,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return {"id": str(row[0]), "prompt_key": row[1], "project_id": None,
                    "content": row[3], "label": row[4], "author": row[5], "is_active": row[6],
                    "created_at": row[7].isoformat() if hasattr(row[7], "isoformat") else str(row[7])}
    else:
        if project_id:
            for v in reversed(_mem_prompt_versions):
                if v["prompt_key"] == prompt_key and v.get("project_id") == project_id and v["is_active"]:
                    return v
        for v in reversed(_mem_prompt_versions):
            if v["prompt_key"] == prompt_key and v.get("project_id") is None and v["is_active"]:
                return v
        return None


def deactivate_all_prompt_versions(prompt_key: str, project_id: Optional[str] = None) -> None:
    """Deactivate all versions for a prompt key+scope (used for reset to default)."""
    _ensure_prompt_versions_table()

    if _use_pg():
        with get_conn() as conn:
            cur = conn.cursor()
            if project_id:
                cur.execute(
                    "UPDATE prompt_versions SET is_active = FALSE WHERE prompt_key = %s AND project_id = %s",
                    (prompt_key, project_id),
                )
            else:
                cur.execute(
                    "UPDATE prompt_versions SET is_active = FALSE WHERE prompt_key = %s AND project_id IS NULL",
                    (prompt_key,),
                )
    else:
        for v in _mem_prompt_versions:
            if v["prompt_key"] == prompt_key and v.get("project_id") == project_id:
                v["is_active"] = False


def activate_prompt_version(version_id: str, prompt_key: str, project_id: Optional[str] = None) -> Optional[dict]:
    """Activate a specific version (deactivates others for same key+project)."""
    _ensure_prompt_versions_table()

    if _use_pg():
        with get_conn() as conn:
            cur = conn.cursor()
            if project_id:
                cur.execute(
                    "UPDATE prompt_versions SET is_active = FALSE WHERE prompt_key = %s AND project_id = %s",
                    (prompt_key, project_id),
                )
            else:
                cur.execute(
                    "UPDATE prompt_versions SET is_active = FALSE WHERE prompt_key = %s AND project_id IS NULL",
                    (prompt_key,),
                )
            cur.execute(
                "UPDATE prompt_versions SET is_active = TRUE WHERE id = %s RETURNING id, content, label, created_at",
                (version_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return {"id": str(row[0]), "content": row[1], "label": row[2],
                    "created_at": row[3].isoformat() if hasattr(row[3], "isoformat") else str(row[3])}
    else:
        for v in _mem_prompt_versions:
            if v["prompt_key"] == prompt_key and v.get("project_id") == project_id:
                v["is_active"] = False
        for v in _mem_prompt_versions:
            if v["id"] == version_id:
                v["is_active"] = True
                return v
        return None


# ===================================================================
# System Settings
# ===================================================================

def get_system_setting(key: str) -> Optional[Any]:
    """Get a system setting value by key."""
    if _use_pg():
        with get_conn() as conn:
            cur = conn.cursor()
            try:
                cur.execute("SELECT value FROM system_settings WHERE key = %s", (key,))
                row = cur.fetchone()
                return row[0] if row else None
            except Exception:
                return None
    else:
        return _mem_system_settings.get(key)


def set_system_setting(key: str, value: Any) -> None:
    """Set a system setting value (upsert)."""
    if _use_pg():
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO system_settings (key, value, updated_at) VALUES (%s, %s, now()) "
                "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now()",
                (key, json.dumps(value)),
            )
    else:
        _mem_system_settings[key] = value


def get_llm_default() -> dict:
    """Get the system-wide default LLM provider/model for non-admin users."""
    val = get_system_setting("llm_default")
    if isinstance(val, dict):
        return val
    return {"provider": "anthropic", "model": "claude-sonnet-4-5-20250929"}


def set_llm_default(provider: str, model: str) -> dict:
    """Set the system-wide default LLM provider/model."""
    val = {"provider": provider, "model": model}
    set_system_setting("llm_default", val)
    return val


def get_project_llm_config(project_id: str) -> dict:
    """Get the effective LLM config for a project.

    Falls back to system default if the project has no explicit setting.
    """
    project = get_project(project_id)
    if project and project.get("llm_provider"):
        return {
            "provider": project["llm_provider"],
            "model": project.get("llm_model") or "",
        }
    return get_llm_default()
