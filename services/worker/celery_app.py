"""Celery application configuration.

Uses Upstash Redis as the broker and result backend.
Supports TLS connections (rediss://) required by Upstash.
"""

from __future__ import annotations

import logging
import os
import ssl
import sys

from celery import Celery
from celery.signals import worker_ready

logger = logging.getLogger(__name__)

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# -------------------------------------------------------------------
# Startup validation — fail fast with clear error messages
# -------------------------------------------------------------------
_REQUIRED_VARS = {
    "REDIS_URL": "Upstash Redis TLS URL (rediss://...)",
    "DATABASE_URL": "Supabase PostgreSQL connection string",
}
_RECOMMENDED_VARS = {
    "ANTHROPIC_API_KEY": "Required for Claude LLM tasks",
}

_missing = [k for k in _REQUIRED_VARS if not os.environ.get(k)]
_missing_rec = [k for k in _RECOMMENDED_VARS if not os.environ.get(k)]

if _missing:
    for k in _missing:
        print(f"[WORKER ERROR] Missing required env var: {k} — {_REQUIRED_VARS[k]}", file=sys.stderr)
    print(
        "[WORKER ERROR] Set these in the Render dashboard (Environment tab). "
        "Worker cannot start without them.",
        file=sys.stderr,
    )
    sys.exit(1)

if _missing_rec:
    for k in _missing_rec:
        logger.warning("Missing recommended env var: %s — %s", k, _RECOMMENDED_VARS[k])

# -------------------------------------------------------------------
# TLS / SSL configuration for Upstash Redis
# -------------------------------------------------------------------
_use_tls = REDIS_URL.startswith("rediss://")

broker_opts = {}
backend_opts = {}

if _use_tls:
    # Celery/kombu need explicit SSL settings for rediss://
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = True
    ssl_context.verify_mode = ssl.CERT_REQUIRED

    broker_opts = {
        "broker_use_ssl": {
            "ssl_cert_reqs": ssl.CERT_REQUIRED,
            "ssl_ca_certs": None,  # Use system CA bundle
        },
        "redis_backend_use_ssl": {
            "ssl_cert_reqs": ssl.CERT_REQUIRED,
            "ssl_ca_certs": None,
        },
    }

app = Celery(
    "plgen_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "services.worker.tasks.phase2",
        "services.worker.tasks.phase3",
        "services.worker.tasks.phase4",
        "services.worker.tasks.phase5",
        "services.worker.tasks.export",
    ],
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Tokyo",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minutes hard limit (LLM calls can take 5+ min)
    task_soft_time_limit=540,  # 9 minutes soft limit
    worker_prefetch_multiplier=1,
    worker_concurrency=2,  # Low concurrency for LLM-bound tasks
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=5,
    **broker_opts,
)


@worker_ready.connect
def _on_worker_ready(**kwargs):
    """Log connection status when worker successfully starts."""
    masked = REDIS_URL[:20] + "..." if len(REDIS_URL) > 20 else REDIS_URL
    logger.info("Worker ready — broker: %s (TLS=%s)", masked, _use_tls)
    db_url = os.environ.get("DATABASE_URL", "")
    if db_url:
        logger.info("Database configured (Supabase)")
    else:
        logger.warning("No DATABASE_URL — using in-memory fallback")
    if os.environ.get("ANTHROPIC_API_KEY"):
        logger.info("ANTHROPIC_API_KEY configured")
    else:
        logger.warning("No ANTHROPIC_API_KEY — LLM tasks will fail")
