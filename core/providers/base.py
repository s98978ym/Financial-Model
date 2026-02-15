"""LLM Provider interface — abstract base for all LLM backends.

Every provider must implement ``generate_json`` and ``stream_text``.
The orchestrator (agents) calls providers via dependency injection,
making it trivial to swap Claude ↔ OpenAI ↔ Gemini.
"""

from __future__ import annotations

import abc
import time
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, Iterator, Optional


@dataclass(frozen=True)
class LLMConfig:
    """Immutable configuration for a single LLM call."""

    model: str = "claude-sonnet-4-5-20250929"
    temperature: float = 0.1
    max_tokens: int = 12288
    timeout_seconds: int = 300
    retry_attempts: int = 2
    retry_base_delay: float = 2.0


@dataclass
class LLMResponse:
    """Standardised response from any LLM provider."""

    raw_text: str
    parsed_json: Optional[Dict[str, Any]] = None
    model: str = ""
    provider: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    stop_reason: str = ""
    prompt_hash: str = ""
    result_hash: str = ""


class LLMProvider(abc.ABC):
    """Abstract base class for LLM providers.

    Subclasses must implement:
    - ``generate_json``: send prompt, receive parsed JSON dict
    - ``stream_text``: send prompt, yield token strings
    """

    provider_name: str = "base"

    @abc.abstractmethod
    def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        config: Optional[LLMConfig] = None,
        schema_hint: Optional[Dict[str, Any]] = None,
    ) -> LLMResponse:
        """Send a prompt and return a parsed JSON response.

        Parameters
        ----------
        system_prompt : str
            System-level instruction (persona, rules, output format).
        user_prompt : str
            User-level content (document text, catalog, etc.).
        config : LLMConfig, optional
            Override default config for this call.
        schema_hint : dict, optional
            Expected JSON schema (for providers that support structured output).

        Returns
        -------
        LLMResponse
            Contains ``parsed_json`` (dict) and usage metadata.

        Raises
        ------
        LLMError
            On API failure, timeout, or invalid JSON after all retries.
        """
        ...

    @abc.abstractmethod
    def stream_text(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        config: Optional[LLMConfig] = None,
    ) -> Iterator[str]:
        """Send a prompt and yield text tokens as they arrive.

        Parameters
        ----------
        system_prompt, user_prompt, config : same as ``generate_json``

        Yields
        ------
        str
            Individual text tokens / chunks.
        """
        ...

    def _default_config(self, config: Optional[LLMConfig]) -> LLMConfig:
        return config or LLMConfig()


class LLMError(Exception):
    """Base exception for LLM provider errors."""

    def __init__(self, message: str, provider: str = "", retryable: bool = False):
        super().__init__(message)
        self.provider = provider
        self.retryable = retryable


class LLMTimeoutError(LLMError):
    """LLM call exceeded timeout."""

    def __init__(self, message: str, provider: str = ""):
        super().__init__(message, provider=provider, retryable=True)


class LLMJSONError(LLMError):
    """LLM returned invalid JSON that could not be repaired."""

    def __init__(self, message: str, raw_text: str = "", provider: str = ""):
        super().__init__(message, provider=provider, retryable=True)
        self.raw_text = raw_text
