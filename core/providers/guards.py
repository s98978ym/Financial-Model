"""Output guards for LLM responses.

These guards enforce the absolute rules:
- JSON output starts with '{'
- Evidence is grounded in the source document
- Confidence penalties for low-quality extractions
- Extractions are never empty
- Numeric labels are caught
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# JSON Output Guard
# ---------------------------------------------------------------------------

class JSONOutputGuard:
    """Ensure LLM output is valid JSON starting with '{'."""

    @staticmethod
    def system_prompt_suffix() -> str:
        return (
            "\n\n【出力形式の厳守】JSONのみを返してください。"
            "```json等のマークダウン記法で囲まないでください。"
            "説明文やコメントも不要です。最初の文字は { で始めてください。"
        )

    @staticmethod
    def enforce(raw_text: str, stop_reason: str = "") -> Dict[str, Any]:
        """Parse raw LLM text into a JSON dict, with repair for truncated output."""
        text = raw_text.strip()

        # Strip markdown code block wrapper
        if text.startswith("```"):
            first_nl = text.find("\n")
            if first_nl > 0:
                text = text[first_nl + 1:]
            if text.rstrip().endswith("```"):
                text = text.rstrip()[:-3].rstrip()

        # Find first '{'
        brace_pos = text.find("{")
        if brace_pos < 0:
            from .base import LLMJSONError
            raise LLMJSONError(
                "LLM応答にJSONオブジェクトが含まれていません",
                raw_text=raw_text,
            )
        text = text[brace_pos:]

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            if stop_reason == "max_tokens":
                logger.warning(
                    "Response truncated at max_tokens (%d chars). Attempting repair.",
                    len(text),
                )
                repaired = JSONOutputGuard._repair_truncated(text)
                if repaired is not None:
                    return repaired

            # Fallback: try regex extraction
            return JSONOutputGuard._try_extract(raw_text)

    @staticmethod
    def _repair_truncated(text: str) -> Optional[Dict[str, Any]]:
        """Repair JSON truncated at max_tokens by closing open brackets."""
        in_string = False
        escape = False
        brace_depth = 0
        bracket_depth = 0
        trim_points: list = []

        for i, ch in enumerate(text):
            if escape:
                escape = False
                continue
            if ch == '\\' and in_string:
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue

            if ch == '{':
                brace_depth += 1
            elif ch == '}':
                brace_depth -= 1
                trim_points.append((i, ch, brace_depth, bracket_depth))
            elif ch == '[':
                bracket_depth += 1
            elif ch == ']':
                bracket_depth -= 1
                trim_points.append((i, ch, brace_depth, bracket_depth))
            elif ch == ',':
                trim_points.append((i, ch, brace_depth, bracket_depth))

        for pos, ch, bd, bkd in reversed(trim_points[-30:]):
            if bd < 0 or bkd < 0:
                continue
            sub = text[:pos] if ch == ',' else text[:pos + 1]
            suffix = ']' * bkd + '}' * bd
            try:
                result = json.loads(sub + suffix)
                logger.info("Repaired truncated JSON at pos %d", pos)
                return result
            except json.JSONDecodeError:
                continue
        return None

    @staticmethod
    def _try_extract(text: str) -> Dict[str, Any]:
        """Last-resort extraction strategies."""
        patterns = [r'```json\s*(.*?)\s*```', r'```\s*(.*?)\s*```', r'\{.*\}']
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                try:
                    candidate = match.group(1) if '```' in pattern else match.group(0)
                    return json.loads(candidate)
                except (json.JSONDecodeError, IndexError):
                    continue

        from .base import LLMJSONError
        raise LLMJSONError(
            f"LLM応答からJSONを抽出できませんでした。先頭200文字: {text[:200]}",
            raw_text=text,
        )


# ---------------------------------------------------------------------------
# Evidence Verification Guard
# ---------------------------------------------------------------------------

class EvidenceGuard:
    """Verify that evidence quotes actually appear in the source document."""

    @staticmethod
    def verify(
        extractions: List[Dict[str, Any]],
        document_text: str,
        threshold: float = 0.6,
    ) -> List[Dict[str, Any]]:
        """Check evidence grounding and apply confidence penalties."""
        if not document_text:
            return extractions

        doc_lower = document_text.lower()

        for ext in extractions:
            evidence = ext.get("evidence")
            if not evidence or not evidence.get("quote"):
                ext["confidence"] = min(ext.get("confidence", 0.0), 0.3)
                ext.setdefault("warnings", []).append("evidence_missing")
                continue

            quote = evidence["quote"]
            if not _fuzzy_match(quote, doc_lower, threshold):
                ext["confidence"] = ext.get("confidence", 0.5) * 0.5
                ext.setdefault("warnings", []).append("evidence_not_found_in_document")

        return extractions


def _fuzzy_match(quote: str, document_lower: str, threshold: float) -> bool:
    """Check if enough of the quote's characters appear in the document."""
    if not quote:
        return False

    quote_lower = quote.lower().strip()

    # Exact substring match
    if quote_lower in document_lower:
        return True

    # Fuzzy: split into words, check how many appear
    words = quote_lower.split()
    if not words:
        return False
    found = sum(1 for w in words if w in document_lower)
    return (found / len(words)) >= threshold


# ---------------------------------------------------------------------------
# Confidence Penalty
# ---------------------------------------------------------------------------

class ConfidencePenalty:
    """Apply confidence penalties based on source quality and evidence."""

    RULES: Dict[str, float] = {
        "evidence_missing": -0.4,
        "evidence_not_found_in_document": -0.3,
        "source_default": -0.2,
        "source_inferred": -0.1,
        "numeric_label": -0.15,
    }

    @staticmethod
    def apply(extraction: Dict[str, Any]) -> Dict[str, Any]:
        conf = extraction.get("confidence", 0.5)
        warnings = extraction.get("warnings", [])

        for rule, penalty in ConfidencePenalty.RULES.items():
            if rule in warnings:
                conf += penalty

        # Source-based penalties
        source = extraction.get("source", "")
        if source == "default" and "source_default" not in warnings:
            conf += ConfidencePenalty.RULES["source_default"]
        elif source == "inferred" and "source_inferred" not in warnings:
            conf += ConfidencePenalty.RULES["source_inferred"]

        extraction["confidence"] = max(0.0, min(1.0, conf))
        return extraction


# ---------------------------------------------------------------------------
# Numeric Label Guard
# ---------------------------------------------------------------------------

class NumericLabelGuard:
    """Prevent LLM from embedding numeric values in label/concept fields."""

    NUMERIC_PATTERN = re.compile(r'^\d[\d,\.]*[万億千百]?[円%]?$')

    @staticmethod
    def check(cell_assignments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        for assignment in cell_assignments:
            concept = assignment.get("concept", "")
            if NumericLabelGuard.NUMERIC_PATTERN.match(str(concept)):
                assignment.setdefault("warnings", []).append(
                    f"numeric_label_detected: '{concept}'"
                )
                assignment["concept"] = "NEEDS_REVIEW"
                assignment["confidence"] = min(assignment.get("confidence", 0.0), 0.2)
        return cell_assignments


# ---------------------------------------------------------------------------
# Extraction Completeness Guard
# ---------------------------------------------------------------------------

class ExtractionCompleteness:
    """Ensure Phase 5 always returns extractions (never empty)."""

    @staticmethod
    def ensure(
        result: Dict[str, Any],
        catalog_items: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if not result.get("extractions"):
            result["extractions"] = [
                {
                    "sheet": item.get("sheet", ""),
                    "cell": item.get("cell", ""),
                    "value": item.get("current_value"),
                    "source": "default",
                    "confidence": 0.1,
                    "evidence": {
                        "quote": "文書に記載なし",
                        "rationale": "デフォルト値を使用",
                    },
                }
                for item in catalog_items
            ]
            result.setdefault("warnings", []).append(
                "LLM returned empty extractions; populated with defaults"
            )
        return result


# ---------------------------------------------------------------------------
# Document Truncation
# ---------------------------------------------------------------------------

class DocumentTruncation:
    """Fixed truncation strategies per phase."""

    @staticmethod
    def for_phase2(text: str, max_chars: int = 30000) -> str:
        """Phase 2: First 70% + Last 25% (with overlap marker)."""
        if len(text) <= max_chars:
            return text
        head = int(max_chars * 0.70)
        tail = int(max_chars * 0.25)
        return text[:head] + "\n\n[...中略...]\n\n" + text[-tail:]

    @staticmethod
    def for_phase5(text: str, max_chars: int = 10000) -> str:
        """Phase 5: First 10,000 characters only."""
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "\n\n[...以降省略...]"
