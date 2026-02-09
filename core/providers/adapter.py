"""Adapter: bridge AnthropicProvider → legacy agent extract(messages) interface.

Existing agents call ``self.llm.extract(messages)`` where messages is
a list of dicts in OpenAI chat format.  This adapter wraps AnthropicProvider
so it can be passed as ``llm_client`` to any agent.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .anthropic_provider import AnthropicProvider
from .base import LLMConfig

logger = logging.getLogger(__name__)


class ProviderAdapter:
    """Wraps AnthropicProvider to expose the ``extract(messages)`` interface
    expected by src/agents/*.py classes."""

    def __init__(self, provider: Optional[AnthropicProvider] = None):
        self._provider = provider or AnthropicProvider()

    def extract(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
    ) -> Dict[str, Any]:
        """Convert OpenAI-format messages to provider call and return parsed JSON."""
        system_text = ""
        user_parts: list[str] = []

        for msg in messages:
            if msg["role"] == "system":
                system_text = msg["content"]
            elif msg["role"] == "user":
                user_parts.append(msg["content"])
            elif msg["role"] == "assistant":
                user_parts.append(f"[Previous assistant response]\n{msg['content']}")

        user_prompt = "\n\n".join(user_parts)

        config = LLMConfig(temperature=temperature)
        response = self._provider.generate_json(
            system_prompt=system_text,
            user_prompt=user_prompt,
            config=config,
        )

        return response.parsed_json or {}
