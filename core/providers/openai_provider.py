"""OpenAI provider stub — ready for future integration.

Implements the same LLMProvider interface as AnthropicProvider.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from typing import Any, Callable, Dict, Iterator, Optional

from .base import LLMConfig, LLMError, LLMProvider, LLMResponse
from .guards import JSONOutputGuard

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """LLM Provider backed by OpenAI API (GPT-4, etc.).

    This is a stub implementation. To activate:
    1. pip install openai
    2. Set OPENAI_API_KEY environment variable
    3. Instantiate with desired model
    """

    provider_name = "openai"

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: str = "gpt-5",
    ):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.default_model = default_model
        self._client = None

    @property
    def client(self):
        if self._client is None:
            if not self.api_key:
                raise LLMError("OPENAI_API_KEY is not set", provider=self.provider_name)
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
            except ImportError:
                raise LLMError(
                    "openai package required: pip install openai",
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
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> LLMResponse:
        cfg = self._default_config(config)
        model = self.default_model

        full_system = system_prompt + JSONOutputGuard.system_prompt_suffix()
        prompt_hash = hashlib.sha256(
            (full_system + user_prompt).encode()
        ).hexdigest()[:16]

        msgs = [
            {"role": "system", "content": full_system},
            {"role": "user", "content": user_prompt},
        ]

        t0 = time.time()

        if progress_callback:
            # Stream for progress tracking
            stream = self.client.chat.completions.create(
                model=model, messages=msgs,
                temperature=cfg.temperature, max_tokens=cfg.max_tokens,
                response_format={"type": "json_object"} if schema_hint else None,
                stream=True,
            )
            chunks = []
            received_chars = 0
            for chunk in stream:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    chunks.append(delta.content)
                    received_chars += len(delta.content)
                    try:
                        progress_callback(received_chars)
                    except Exception:
                        pass
            raw_text = "".join(chunks)
            input_tokens = 0
            output_tokens = 0
            stop_reason = chunk.choices[0].finish_reason or "" if chunk else ""
        else:
            response = self.client.chat.completions.create(
                model=model, messages=msgs,
                temperature=cfg.temperature, max_tokens=cfg.max_tokens,
                response_format={"type": "json_object"} if schema_hint else None,
            )
            raw_text = response.choices[0].message.content or ""
            input_tokens = response.usage.prompt_tokens if response.usage else 0
            output_tokens = response.usage.completion_tokens if response.usage else 0
            stop_reason = response.choices[0].finish_reason or ""

        latency_ms = int((time.time() - t0) * 1000)
        parsed = JSONOutputGuard.enforce(raw_text)

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

    def stream_text(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        config: Optional[LLMConfig] = None,
    ) -> Iterator[str]:
        cfg = self._default_config(config)
        stream = self.client.chat.completions.create(
            model=self.default_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content
