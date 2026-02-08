"""LLM audit logging — tracks every LLM call for cost monitoring and debugging.

Audit records are stored in-memory by default, with an optional DB backend
for persistence via Supabase/Postgres.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .base import LLMResponse

logger = logging.getLogger(__name__)


@dataclass
class AuditRecord:
    """Single LLM call audit entry."""

    run_id: str = ""
    phase: int = 0
    provider: str = ""
    model: str = ""
    prompt_hash: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    temperature: float = 0.1
    max_tokens: int = 32768
    result_hash: str = ""
    timestamp: float = field(default_factory=time.time)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "phase": self.phase,
            "provider": self.provider,
            "model": self.model,
            "prompt_hash": self.prompt_hash,
            "token_usage": {
                "input": self.input_tokens,
                "output": self.output_tokens,
            },
            "latency_ms": self.latency_ms,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "result_hash": self.result_hash,
            "timestamp": self.timestamp,
            "error": self.error,
        }


class AuditLogger:
    """Collects and persists LLM audit records.

    Usage::

        audit = AuditLogger()
        # ... after LLM call ...
        audit.log(response, run_id="run_123", phase=2)

        # Get cost summary
        print(audit.summary())
    """

    def __init__(self, persist_fn: Optional[Callable[[AuditRecord], None]] = None):
        """
        Parameters
        ----------
        persist_fn : callable, optional
            Function to persist an audit record (e.g., DB insert).
            If None, records are stored in-memory only.
        """
        self._records: List[AuditRecord] = []
        self._persist_fn = persist_fn

    def log(
        self,
        response: LLMResponse,
        *,
        run_id: str = "",
        phase: int = 0,
        temperature: float = 0.1,
        max_tokens: int = 32768,
        error: Optional[str] = None,
    ) -> AuditRecord:
        """Record an LLM call."""
        record = AuditRecord(
            run_id=run_id,
            phase=phase,
            provider=response.provider,
            model=response.model,
            prompt_hash=response.prompt_hash,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            latency_ms=response.latency_ms,
            temperature=temperature,
            max_tokens=max_tokens,
            result_hash=response.result_hash,
            error=error,
        )
        self._records.append(record)

        if self._persist_fn:
            try:
                self._persist_fn(record)
            except Exception as e:
                logger.error("Failed to persist audit record: %s", e)

        logger.info(
            "LLM audit: provider=%s model=%s tokens=%d+%d latency=%dms phase=%d",
            record.provider,
            record.model,
            record.input_tokens,
            record.output_tokens,
            record.latency_ms,
            record.phase,
        )
        return record

    def summary(self) -> Dict[str, Any]:
        """Return aggregate stats for all recorded calls."""
        total_input = sum(r.input_tokens for r in self._records)
        total_output = sum(r.output_tokens for r in self._records)
        total_latency = sum(r.latency_ms for r in self._records)
        errors = sum(1 for r in self._records if r.error)

        by_phase: Dict[int, Dict[str, int]] = {}
        for r in self._records:
            if r.phase not in by_phase:
                by_phase[r.phase] = {"calls": 0, "input_tokens": 0, "output_tokens": 0}
            by_phase[r.phase]["calls"] += 1
            by_phase[r.phase]["input_tokens"] += r.input_tokens
            by_phase[r.phase]["output_tokens"] += r.output_tokens

        return {
            "total_calls": len(self._records),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_latency_ms": total_latency,
            "errors": errors,
            "by_phase": by_phase,
        }

    @property
    def records(self) -> List[AuditRecord]:
        return list(self._records)
