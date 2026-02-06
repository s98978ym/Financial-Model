"""LLM client for parameter extraction — Anthropic Claude API."""
import json
import os
import logging
import re
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Raised when the LLM API call fails."""


class LLMClient:
    """Client for LLM API calls (Anthropic Claude)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-5-20250929",
        base_url: Optional[str] = None,
    ):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.model = model
        self.base_url = base_url
        self._client = None

    @property
    def client(self):
        if self._client is None:
            if not self.api_key:
                raise LLMError(
                    "ANTHROPIC_API_KEY が設定されていません。"
                    "Streamlit Cloud の場合: Settings → Secrets で設定してください。"
                    "ローカルの場合: export ANTHROPIC_API_KEY='sk-ant-...' を実行してください。"
                )
            try:
                from anthropic import Anthropic
                kwargs: Dict[str, Any] = {"api_key": self.api_key}
                if self.base_url:
                    kwargs["base_url"] = self.base_url
                self._client = Anthropic(**kwargs)
            except ImportError:
                raise LLMError(
                    "anthropic パッケージが必要です。pip install anthropic を実行してください。"
                )
        return self._client

    def extract(self, messages: List[Dict[str, str]], temperature: float = 0.1) -> Dict[str, Any]:
        """Send extraction request to LLM and parse JSON response.

        Raises LLMError on failure instead of returning empty results silently.

        Parameters
        ----------
        messages : list[dict]
            Chat messages in OpenAI format: [{"role": "system"|"user"|"assistant", "content": "..."}]
            The system message is extracted and passed as Claude's system parameter.
        temperature : float
            Sampling temperature.
        """
        content = ""
        try:
            # Separate system message from conversation messages
            system_text = ""
            conversation = []
            for msg in messages:
                if msg["role"] == "system":
                    system_text = msg["content"]
                else:
                    conversation.append(msg)

            # Ensure JSON output instruction in system prompt
            if "JSON" not in system_text and "json" not in system_text:
                system_text += "\n\n有効なJSONのみを返してください。マークダウンや説明文は不要です。"

            kwargs: Dict[str, Any] = {
                "model": self.model,
                "max_tokens": 8192,
                "temperature": temperature,
                "messages": conversation,
            }
            if system_text:
                kwargs["system"] = system_text

            response = self.client.messages.create(**kwargs)
            content = response.content[0].text

            result = json.loads(content)
            return result
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            # Try to extract JSON from response
            return self._try_extract_json(content)
        except LLMError:
            raise  # Re-raise our own errors
        except Exception as e:
            raise LLMError(f"LLM API 呼び出しに失敗しました: {e}") from e

    def _try_extract_json(self, text: str) -> Dict[str, Any]:
        """Try to extract JSON from text that may contain markdown or other formatting."""
        # Try finding JSON block in markdown
        patterns = [r'```json\s*(.*?)\s*```', r'```\s*(.*?)\s*```', r'\{.*\}']
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1) if '```' in pattern else match.group(0))
                except json.JSONDecodeError:
                    continue
        raise LLMError(f"LLM応答からJSONを抽出できませんでした。応答先頭200文字: {text[:200]}")

    def process_instruction(self, instruction: str, parameters_json: str) -> Dict[str, Any]:
        """Process a text customization instruction into proposed changes."""
        from .prompts import INSTRUCTION_TO_CHANGES_PROMPT

        prompt = INSTRUCTION_TO_CHANGES_PROMPT.format(
            parameters_json=parameters_json,
            instruction=instruction
        )
        messages = [
            {"role": "system", "content": "You are a financial model assistant. Return valid JSON only."},
            {"role": "user", "content": prompt}
        ]
        return self.extract(messages)
