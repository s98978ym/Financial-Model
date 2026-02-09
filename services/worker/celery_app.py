"""Celery application configuration.

Uses Upstash Redis as the broker and result backend.
"""

from __future__ import annotations

import os

from celery import Celery

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

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
)
