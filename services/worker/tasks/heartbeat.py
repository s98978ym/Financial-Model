"""Shared heartbeat utility for long-running LLM worker tasks.

Provides a context manager that updates job progress during LLM calls
so the frontend knows the task is still alive.
"""
from __future__ import annotations

import math
import threading
import time
from contextlib import contextmanager
from typing import Callable, Optional


@contextmanager
def heartbeat(
    update_fn: Callable[[int, str], None],
    *,
    interval: float = 4.0,
    start_pct: int = 25,
    ceiling_pct: int = 95,
    time_constant: float = 120.0,
    message: str = "LLM generating response...",
):
    """Context manager that periodically updates job progress.

    Usage::

        def _update(pct, msg):
            db.update_job(job_id, progress=pct, log_msg=msg)

        with heartbeat(_update, start_pct=25):
            result = llm.extract(messages)

    Parameters
    ----------
    update_fn :
        Called with ``(progress_pct, log_message)`` every *interval* seconds.
    interval :
        Seconds between updates (default 4).
    start_pct :
        Progress percentage to start from (default 25).
    ceiling_pct :
        Asymptotic upper bound for progress (default 95).
    time_constant :
        Controls how fast progress approaches *ceiling_pct* (seconds).
        Higher = slower approach.  Default 120 gives:
        ~40% at 30s, ~52% at 60s, ~69% at 2min, ~89% at 5min.
    message :
        Log message sent with each heartbeat.
    """
    stop = threading.Event()
    rng = ceiling_pct - start_pct  # e.g. 70

    def _tick():
        t0 = time.time()
        while not stop.is_set():
            stop.wait(timeout=interval)
            if stop.is_set():
                break
            elapsed = time.time() - t0
            pct = min(int(start_pct + rng * (1 - math.exp(-elapsed / time_constant))), ceiling_pct)
            try:
                update_fn(pct, message)
            except Exception:
                pass

    thread = threading.Thread(target=_tick, daemon=True)
    thread.start()
    try:
        yield
    finally:
        stop.set()
        thread.join(timeout=2)
