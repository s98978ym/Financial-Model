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
            system_text += (
                "\n\n【出力形式の厳守】JSONのみを返してください。"
                "```json等のマークダウン記法で囲まないでください。"
                "説明文やコメントも不要です。最初の文字は { で始めてください。"
            )

            kwargs: Dict[str, Any] = {
                "model": self.model,
                "max_tokens": 16384,
                "temperature": temperature,
                "messages": conversation,
            }
            if system_text:
                kwargs["system"] = system_text

            response = self.client.messages.create(**kwargs)
            content = response.content[0].text
            stop_reason = getattr(response, "stop_reason", "unknown")

            # Strip markdown code block wrapper if present
            stripped = content.strip()
            if stripped.startswith("```"):
                first_newline = stripped.find("\n")
                if first_newline > 0:
                    stripped = stripped[first_newline + 1:]
                if stripped.rstrip().endswith("```"):
                    stripped = stripped.rstrip()[:-3].rstrip()
                content = stripped

            try:
                result = json.loads(content)
                return result
            except json.JSONDecodeError:
                # If response was truncated (max_tokens), try to repair
                if stop_reason == "max_tokens":
                    logger.warning("Response truncated at max_tokens, attempting JSON repair")
                    repaired = self._repair_truncated_json(content)
                    if repaired is not None:
                        return repaired
                return self._try_extract_json(content)
        except json.JSONDecodeError:
            # Already handled above
            raise
        except LLMError:
            raise  # Re-raise our own errors
        except Exception as e:
            raise LLMError(f"LLM API 呼び出しに失敗しました: {e}") from e

    @staticmethod
    def _repair_truncated_json(text: str) -> Optional[Dict[str, Any]]:
        """Attempt to repair JSON that was truncated at max_tokens.

        Strategy: find the first '{', then try closing open brackets/braces
        from the end until json.loads succeeds.
        """
        start = text.find("{")
        if start < 0:
            return None

        candidate = text[start:]

        # Count open/close brackets to figure out what's missing
        open_braces = candidate.count("{") - candidate.count("}")
        open_brackets = candidate.count("[") - candidate.count("]")

        # Trim trailing incomplete value (after last comma or colon)
        # Find last complete entry
        for trim_char in (",", "{", "["):
            last_pos = candidate.rfind(trim_char)
            if last_pos > 0:
                trimmed = candidate[:last_pos]
                # Close all open brackets/braces
                suffix = "]" * (trimmed.count("[") - trimmed.count("]"))
                suffix += "}" * (trimmed.count("{") - trimmed.count("}"))
                try:
                    result = json.loads(trimmed + suffix)
                    logger.info("Repaired truncated JSON (trimmed at '%s', added '%s')", trim_char, suffix)
                    return result
                except json.JSONDecodeError:
                    continue

        # Simple approach: just close all open brackets
        suffix = "]" * max(0, open_brackets) + "}" * max(0, open_braces)
        try:
            return json.loads(candidate + suffix)
        except json.JSONDecodeError:
            return None

    def _try_extract_json(self, text: str) -> Dict[str, Any]:
        """Try to extract JSON from text that may contain markdown or other formatting."""
        # Strategy 1: Regex patterns for well-formed responses
        patterns = [r'```json\s*(.*?)\s*```', r'```\s*(.*?)\s*```', r'\{.*\}']
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1) if '```' in pattern else match.group(0))
                except json.JSONDecodeError:
                    continue

        # Strategy 2: Strip markdown wrapper and try direct parse
        stripped = text.strip()
        if stripped.startswith("```"):
            first_nl = stripped.find("\n")
            if first_nl > 0:
                stripped = stripped[first_nl + 1:]
            if stripped.rstrip().endswith("```"):
                stripped = stripped.rstrip()[:-3].rstrip()
            try:
                return json.loads(stripped)
            except json.JSONDecodeError:
                pass

        # Strategy 3: Find first { and try to parse from there
        brace_pos = text.find("{")
        if brace_pos >= 0:
            candidate = text[brace_pos:]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                # Truncated response: try to repair by closing brackets
                pass

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
