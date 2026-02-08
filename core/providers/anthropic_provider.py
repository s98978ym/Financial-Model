"""Anthropic Claude provider implementation.

Wraps the existing LLM client logic into the Provider interface,
preserving streaming, JSON repair, and markdown stripping.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from typing import Any, Dict, Iterator, Optional

from .base import LLMConfig, LLMError, LLMJSONError, LLMProvider, LLMResponse, LLMTimeoutError
from .guards import JSONOutputGuard

logger = logging.getLogger(__name__)


class AnthropicProvider(LLMProvider):
    """LLM Provider backed by Anthropic Claude API."""

    provider_name = "anthropic"

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: str = "claude-sonnet-4-5-20250929",
        base_url: Optional[str] = None,
    ):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.default_model = default_model
        self.base_url = base_url
        self._client = None

    @property
    def client(self):
        if self._client is None:
            if not self.api_key:
                raise LLMError(
                    "ANTHROPIC_API_KEY が設定されていません。",
                    provider=self.provider_name,
                )
            try:
                from anthropic import Anthropic

                kwargs: Dict[str, Any] = {"api_key": self.api_key}
                if self.base_url:
                    kwargs["base_url"] = self.base_url
                self._client = Anthropic(**kwargs)
            except ImportError:
                raise LLMError(
                    "anthropic パッケージが必要です: pip install anthropic",
                    provider=self.provider_name,
                )
        return self._client

    def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        config: Optional[LLMConfig] = None,
        schema_hint: Optional[Dict[str, Any]] = None,
    ) -> LLMResponse:
        cfg = self._default_config(config)
        model = cfg.model if cfg.model != "claude-sonnet-4-5-20250929" else self.default_model

        # Append JSON enforcement to system prompt
        full_system = system_prompt + JSONOutputGuard.system_prompt_suffix()

        # Build prompt hash for audit
        prompt_hash = hashlib.sha256(
            (full_system + user_prompt).encode()
        ).hexdigest()[:16]

        last_error: Optional[Exception] = None
        for attempt in range(cfg.retry_attempts + 1):
            if attempt > 0:
                delay = cfg.retry_base_delay * (2 ** (attempt - 1))
                logger.warning(
                    "Retry %d/%d after %.1fs delay",
                    attempt, cfg.retry_attempts, delay,
                )
                time.sleep(delay)

            t0 = time.time()
            try:
                kwargs: Dict[str, Any] = {
                    "model": model,
                    "max_tokens": cfg.max_tokens,
                    "temperature": cfg.temperature,
                    "system": full_system,
                    "messages": [{"role": "user", "content": user_prompt}],
                }

                with self.client.messages.stream(**kwargs) as stream:
                    response = stream.get_final_message()

                latency_ms = int((time.time() - t0) * 1000)
                raw_text = response.content[0].text
                stop_reason = getattr(response, "stop_reason", "unknown")

                # Parse usage
                usage = getattr(response, "usage", None)
                input_tokens = getattr(usage, "input_tokens", 0) if usage else 0
                output_tokens = getattr(usage, "output_tokens", 0) if usage else 0

                # Parse JSON with guards
                parsed = JSONOutputGuard.enforce(raw_text, stop_reason=stop_reason)

                result_hash = hashlib.sha256(
                    json.dumps(parsed, sort_keys=True).encode()
                ).hexdigest()[:16]

                return LLMResponse(
                    raw_text=raw_text,
                    parsed_json=parsed,
                    model=model,
                    provider=self.provider_name,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    latency_ms=latency_ms,
                    stop_reason=stop_reason,
                    prompt_hash=prompt_hash,
                    result_hash=result_hash,
                )

            except LLMJSONError:
                raise  # Don't retry JSON errors (same prompt = same output)
            except LLMError:
                raise
            except Exception as e:
                last_error = e
                logger.error("Anthropic API error (attempt %d): %s", attempt + 1, e)
                continue

        raise LLMError(
            f"Anthropic API failed after {cfg.retry_attempts + 1} attempts: {last_error}",
            provider=self.provider_name,
            retryable=False,
        )

    def stream_text(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        config: Optional[LLMConfig] = None,
    ) -> Iterator[str]:
        cfg = self._default_config(config)
        model = cfg.model if cfg.model != "claude-sonnet-4-5-20250929" else self.default_model

        try:
            with self.client.messages.stream(
                model=model,
                max_tokens=cfg.max_tokens,
                temperature=cfg.temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            ) as stream:
                for text in stream.text_stream:
                    yield text
        except Exception as e:
            raise LLMError(
                f"Anthropic streaming failed: {e}",
                provider=self.provider_name,
            )
