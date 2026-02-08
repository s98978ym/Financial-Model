"""Parameter Extractor Agent (Phase 5).

Takes the confirmed model design (cell-to-concept mapping) and extracts
actual values from the business plan document for each cell.

This agent answers: "What value should go in each cell?"
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Output models
# ---------------------------------------------------------------------------

class ExtractedValue(BaseModel):
    """Extracted value for a specific cell."""
    sheet: str
    cell: str
    label: str = Field(default="")
    concept: str = Field(default="", description="From model design")
    value: Any = Field(default=None)
    unit: str = Field(default="")
    source: str = Field(default="document", description="'document' / 'inferred' / 'default'")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence: str = Field(default="", description="Quote from document or reasoning")
    segment: str = Field(default="")
    period: str = Field(default="")

    @field_validator(
        "label", "concept", "unit", "source", "evidence", "segment", "period",
        mode="before",
    )
    @classmethod
    def _none_to_empty(cls, v: Any) -> str:
        if v is None:
            return ""
        return str(v)


class ParameterExtractionResult(BaseModel):
    """Output of the Parameter Extractor."""
    extractions: List[ExtractedValue] = Field(default_factory=list)
    unmapped_cells: List[Dict[str, str]] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    raw_json: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

PE_SYSTEM_PROMPT = """\
あなたは投資銀行のシニアFMスペシャリストです。
確定済みのモデル設計に基づいて、事業計画書から各セルの具体的な値を抽出します。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【抽出ルール】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. **文書に明記された値** → confidence 0.8-1.0, source="document"
2. **文脈から推定した値** → confidence 0.5-0.8, source="inferred"
3. **業界標準からのデフォルト** → confidence 0.3-0.5, source="default"
4. **抽出不可** → unmapped_cellsに記録

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【数値の正規化】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 億→×100,000,000、万→×10,000
- %は小数表記（30% → 0.3）
- 通貨単位の統一（千円→円に変換）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【重要ルール】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- **必ずextractionsを返す（最重要ルール）**
- 全セルについて抽出を試みる
- 推定値でもよいので値を埋める（sourceとconfidenceで区別）
- 有効なJSONのみを返す
"""

PE_USER_PROMPT = """\
以下の確定済み情報をもとに、各セルの値を事業計画書から抽出してください。

━━━ ① モデル設計（確定済み: 各セルの概念マッピング） ━━━
{model_design_json}

━━━ ② 事業計画書（原文） ━━━
{document_text}

{feedback_section}\
━━━ 出力形式（JSON） ━━━
{{
  "extractions": [
    {{
      "sheet": "シート名",
      "cell": "B5",
      "label": "セルのラベル",
      "concept": "モデル設計で決定された概念",
      "value": 12345,
      "unit": "円",
      "source": "document / inferred / default",
      "confidence": 0.9,
      "evidence": "文書からの引用・根拠",
      "segment": "セグメント名",
      "period": "FY1"
    }}
  ],
  "unmapped_cells": [
    {{"sheet": "シート名", "cell": "C10", "label": "ラベル", "reason": "文書に該当情報なし"}}
  ],
  "warnings": ["注意事項"]
}}
"""


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class ParameterExtractorAgent:
    """Agent 4 (Phase 5): Extracts actual values from document."""

    def __init__(
        self,
        llm_client: Any,
        system_prompt: Optional[str] = None,
        user_prompt: Optional[str] = None,
    ) -> None:
        self.llm = llm_client
        self._system_prompt = system_prompt or PE_SYSTEM_PROMPT
        self._user_prompt = user_prompt or PE_USER_PROMPT

    def extract_values(
        self,
        model_design_json: Dict[str, Any],
        document_text: str,
        feedback: str = "",
    ) -> ParameterExtractionResult:
        """Extract values for each cell from the document.

        Parameters
        ----------
        model_design_json : dict
            Confirmed Model Design as raw JSON.
        document_text : str
            Full text of the business plan.
        feedback : str
            Optional user feedback.
        """
        design_str = json.dumps(model_design_json, ensure_ascii=False, indent=2)

        # Truncate document if needed
        max_doc = 10000
        if len(document_text) > max_doc:
            doc_chunk = document_text[:max_doc]
            doc_chunk += f"\n\n[... {len(document_text):,} 文字中、先頭 {max_doc:,} 文字を表示 ...]"
        else:
            doc_chunk = document_text

        feedback_section = ""
        if feedback:
            feedback_section = (
                f"━━━ ユーザーフィードバック ━━━\n"
                f"{feedback}\n\n"
                f"上記のフィードバックを考慮して、抽出を修正してください。\n\n"
            )

        messages = [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": self._user_prompt.format(
                model_design_json=design_str,
                document_text=doc_chunk,
                feedback_section=feedback_section,
            )},
        ]

        logger.info("ParameterExtractor: sending model design + document to LLM")
        result = self.llm.extract(messages)
        logger.info(
            "ParameterExtractor: received %d extractions, %d unmapped",
            len(result.get("extractions", [])),
            len(result.get("unmapped_cells", [])),
        )
        return self._parse_result(result, model_design_json)

    def _parse_result(
        self,
        raw: Dict[str, Any],
        model_design_json: Optional[Dict[str, Any]] = None,
    ) -> ParameterExtractionResult:
        # Build label lookup from model design (already corrected in Phase 4)
        design_label_map: Dict[str, str] = {}
        if model_design_json:
            for ca in model_design_json.get("cell_assignments", []):
                sheet = ca.get("sheet", "")
                cell = ca.get("cell", "")
                label = ca.get("label", "")
                if sheet and cell and label:
                    design_label_map[f"{sheet}!{cell}"] = label

        extractions = []
        for ex in raw.get("extractions", []):
            sheet = ex.get("sheet", "")
            cell = ex.get("cell", "")
            llm_label = ex.get("label", "")

            # Fix numeric labels using model design's label
            addr = f"{sheet}!{cell}"
            actual_label = llm_label
            if addr in design_label_map:
                design_lbl = design_label_map[addr]
                try:
                    float(str(llm_label).replace(",", ""))
                    actual_label = design_lbl
                except (ValueError, TypeError):
                    if not llm_label:
                        actual_label = design_lbl

            extractions.append(ExtractedValue(
                sheet=sheet,
                cell=cell,
                label=actual_label,
                concept=ex.get("concept", ""),
                value=ex.get("value"),
                unit=ex.get("unit", ""),
                source=ex.get("source", "document"),
                confidence=float(ex.get("confidence", 0.5)),
                evidence=ex.get("evidence", ""),
                segment=ex.get("segment", ""),
                period=ex.get("period", ""),
            ))
        return ParameterExtractionResult(
            extractions=extractions,
            unmapped_cells=raw.get("unmapped_cells", []),
            warnings=raw.get("warnings", []),
            raw_json=raw,
        )
