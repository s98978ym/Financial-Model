"""LLM client for parameter extraction."""
import json
import os
import logging
import re
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for LLM API calls (OpenAI-compatible)."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o", base_url: Optional[str] = None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.model = model
        self.base_url = base_url or "https://api.openai.com/v1"
        self._client = None

    @property
    def client(self):
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            except ImportError:
                raise ImportError("openai package required. Install with: pip install openai")
        return self._client

    def extract(self, messages: List[Dict[str, str]], temperature: float = 0.1) -> Dict[str, Any]:
        """Send extraction request to LLM and parse JSON response."""
        content = ""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            # Try to extract JSON from response
            return self._try_extract_json(content)
        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            return {"values": {}, "confidence": {}, "evidence": {}, "assumptions": {}, "mapping_hints": {}}

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
        return {"values": {}, "confidence": {}, "evidence": {}, "assumptions": {}, "mapping_hints": {}}

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
