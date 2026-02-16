"""Google Gemini provider stub — ready for future integration.

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


class GoogleProvider(LLMProvider):
    """LLM Provider backed by Google Gemini API.

    This is a stub implementation. To activate:
    1. pip install google-generativeai
    2. Set GOOGLE_API_KEY environment variable
    3. Instantiate with desired model
    """

    provider_name = "google"

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: str = "gemini-2.5-pro",
    ):
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY", "")
        self.default_model = default_model
        self._model = None

    @property
    def model(self):
        if self._model is None:
            if not self.api_key:
                raise LLMError("GOOGLE_API_KEY is not set", provider=self.provider_name)
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self._model = genai.GenerativeModel(self.default_model)
            except ImportError:
                raise LLMError(
                    "google-generativeai package required: pip install google-generativeai",
                    provider=self.provider_name,
                )
        return self._model

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

        full_system = system_prompt + JSONOutputGuard.system_prompt_suffix()
        prompt_hash = hashlib.sha256(
            (full_system + user_prompt).encode()
        ).hexdigest()[:16]

        gen_config = {
            "temperature": cfg.temperature,
            "max_output_tokens": cfg.max_tokens,
        }
        content = f"{full_system}\n\n{user_prompt}"

        t0 = time.time()

        if progress_callback:
            # Stream for progress tracking
            stream_response = self.model.generate_content(
                content, generation_config=gen_config, stream=True,
            )
            chunks = []
            received_chars = 0
            for chunk in stream_response:
                if chunk.text:
                    chunks.append(chunk.text)
                    received_chars += len(chunk.text)
                    try:
                        progress_callback(received_chars)
                    except Exception:
                        pass
            raw_text = "".join(chunks)
            usage = getattr(stream_response, "usage_metadata", None)
        else:
            response = self.model.generate_content(
                content, generation_config=gen_config,
            )
            raw_text = response.text or ""
            usage = getattr(response, "usage_metadata", None)

        latency_ms = int((time.time() - t0) * 1000)
        parsed = JSONOutputGuard.enforce(raw_text)

        result_hash = hashlib.sha256(
            json.dumps(parsed, sort_keys=True).encode()
        ).hexdigest()[:16]

        return LLMResponse(
            raw_text=raw_text,
            parsed_json=parsed,
            model=self.default_model,
            provider=self.provider_name,
            input_tokens=getattr(usage, "prompt_token_count", 0) if usage else 0,
            output_tokens=getattr(usage, "candidates_token_count", 0) if usage else 0,
            latency_ms=latency_ms,
            stop_reason="stop",
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
        response = self.model.generate_content(
            f"{system_prompt}\n\n{user_prompt}",
            generation_config={
                "temperature": cfg.temperature,
                "max_output_tokens": cfg.max_tokens,
            },
            stream=True,
        )
        for chunk in response:
            if chunk.text:
                yield chunk.text
