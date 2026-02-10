"""Celery application configuration.

Uses Upstash Redis as the broker and result backend.
Supports TLS connections (rediss://) required by Upstash.
"""

from __future__ import annotations

import os
import ssl

from celery import Celery

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# Upstash requires TLS — detect rediss:// and configure SSL
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
    task_time_limit=300,  # 5 minutes hard limit
    task_soft_time_limit=270,  # 4.5 minutes soft limit
    worker_prefetch_multiplier=1,
    worker_concurrency=2,  # Low concurrency for LLM-bound tasks
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    **broker_opts,
)
