"""Template Structure Mapper Agent (Phase 3).

Takes the confirmed Business Model Analysis and the Excel template catalog,
and produces a high-level mapping: which template sheet corresponds to
which business segment and what is each sheet's purpose.

This agent answers: "How does this template's structure relate to the
business model?"
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

class SheetMapping(BaseModel):
    """Maps a template sheet to a business segment/function."""
    sheet_name: str
    mapped_segment: str = Field(default="", description="Which business segment this sheet models")
    sheet_purpose: str = Field(default="", description="e.g. 'revenue_model', 'cost_detail', 'pl_summary'")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reasoning: str = Field(default="", description="Why this mapping was chosen")

    @field_validator("mapped_segment", "sheet_purpose", "reasoning", mode="before")
    @classmethod
    def _none_to_empty(cls, v: Any) -> str:
        if v is None:
            return ""
        return str(v)


class TemplateStructureResult(BaseModel):
    """Output of the Template Structure Mapper."""
    overall_structure: str = Field(default="", description="High-level description of the template")
    sheet_mappings: List[SheetMapping] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list, description="Suggestions for improvement")
    raw_json: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

TS_SYSTEM_PROMPT = """\
あなたは投資銀行のシニアFMスペシャリストです。
ビジネスモデル分析結果とExcelテンプレートのシート構造を照合し、
各シートがどのビジネスセグメント・機能に対応するかを判定します。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【判定の観点】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. **シート名・ブロック名・ラベルから目的を推定**
   - 「収益モデルN」→ 事業セグメントNの収益モデル（汎用スロット）
   - 「費用リスト」→ 全セグメント共通のコスト一覧
   - 「前提条件」→ 基本前提
   - 「PL」「損益」→ PL集計シート
   - テンプレートのシート名は汎用的であり、特定業種に紐づかない

2. **事業分析のセグメントとの対応**
   - 各セグメントがどのシートに対応するか
   - 1つのシートが複数セグメントをカバーする場合も記載

3. **シートの役割分類**
   - revenue_model（売上モデル）
   - cost_detail（コスト明細）
   - pl_summary（PL集計）
   - assumptions（前提条件）
   - headcount（人員計画）
   - capex（設備投資）
   - other（その他）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【出力ルール】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 必ず全シートに対してマッピングを返す
- マッピング先が不明なシートも reasoning で理由を記載
- 有効なJSONのみを返す
"""

TS_USER_PROMPT = """\
以下の情報をもとに、テンプレートの各シートがどのセグメント・機能に対応するかを判定してください。

━━━ ① 事業分析結果（確定済み） ━━━
{business_analysis_json}

━━━ ② テンプレートのシート・セル概要 ━━━
{template_summary_json}

{feedback_section}\
━━━ 出力形式（JSON） ━━━
{{
  "overall_structure": "テンプレート全体の構造説明（1-2文）",
  "sheet_mappings": [
    {{
      "sheet_name": "シート名",
      "mapped_segment": "対応するセグメント名",
      "sheet_purpose": "revenue_model / cost_detail / pl_summary / assumptions / headcount / capex / other",
      "confidence": 0.9,
      "reasoning": "判定理由"
    }}
  ],
  "suggestions": ["改善提案があれば"]
}}
"""


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class TemplateMapper:
    """Agent 2 (Phase 3): Maps template sheets to business segments."""

    def __init__(
        self,
        llm_client: Any,
        system_prompt: Optional[str] = None,
        user_prompt: Optional[str] = None,
    ) -> None:
        self.llm = llm_client
        self._system_prompt = system_prompt or TS_SYSTEM_PROMPT
        self._user_prompt = user_prompt or TS_USER_PROMPT

    def map_structure(
        self,
        analysis_json: Dict[str, Any],
        catalog_items: List[Dict[str, Any]],
        feedback: str = "",
    ) -> TemplateStructureResult:
        """Map template sheets to business segments.

        Parameters
        ----------
        analysis_json : dict
            Confirmed Business Model Analysis as raw JSON.
        catalog_items : list[dict]
            Writable template cells as dicts.
        feedback : str
            Optional user feedback to incorporate.
        """
        # Build per-sheet summary for the prompt
        sheet_summary: Dict[str, Dict[str, Any]] = {}
        for item in catalog_items:
            sheet = item.get("sheet", "?")
            if sheet not in sheet_summary:
                sheet_summary[sheet] = {"cell_count": 0, "sample_cells": []}
            sheet_summary[sheet]["cell_count"] += 1
            if len(sheet_summary[sheet]["sample_cells"]) < 10:
                labels = ", ".join(item.get("labels", [])[:3]) or item.get("cell", "")
                sheet_summary[sheet]["sample_cells"].append(
                    f"{item.get('cell', '?')}: {labels}"
                )

        analysis_str = json.dumps(analysis_json, ensure_ascii=False, indent=2)
        summary_str = json.dumps(sheet_summary, ensure_ascii=False, indent=2)

        feedback_section = ""
        if feedback:
            feedback_section = (
                f"━━━ ユーザーフィードバック ━━━\n"
                f"{feedback}\n\n"
                f"上記のフィードバックを考慮して、マッピングを修正してください。\n\n"
            )

        messages = [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": self._user_prompt.format(
                business_analysis_json=analysis_str,
                template_summary_json=summary_str,
                feedback_section=feedback_section,
            )},
        ]

        logger.info(
            "TemplateMapper: sending %d sheets to LLM",
            len(sheet_summary),
        )
        result = self.llm.extract(messages)
        logger.info("TemplateMapper: received %d mappings", len(result.get("sheet_mappings", [])))
        return self._parse_result(result)

    def _parse_result(self, raw: Dict[str, Any]) -> TemplateStructureResult:
        mappings = []
        for sm in raw.get("sheet_mappings", []):
            mappings.append(SheetMapping(
                sheet_name=sm.get("sheet_name", ""),
                mapped_segment=sm.get("mapped_segment", ""),
                sheet_purpose=sm.get("sheet_purpose", ""),
                confidence=float(sm.get("confidence", 0.5)),
                reasoning=sm.get("reasoning", ""),
            ))
        return TemplateStructureResult(
            overall_structure=raw.get("overall_structure", ""),
            sheet_mappings=mappings,
            suggestions=raw.get("suggestions", []),
            raw_json=raw,
        )
