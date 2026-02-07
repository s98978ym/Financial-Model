"""Model Designer Agent (Phase 4).

Takes confirmed BM Analysis + Template Structure and maps business concepts
to specific template cells.  This is about WHAT each cell should represent,
not WHAT VALUE it should have.

This agent answers: "Which cell corresponds to which business concept?"
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Output models
# ---------------------------------------------------------------------------

class CellAssignment(BaseModel):
    """Maps a template cell to a business concept."""
    sheet: str
    cell: str
    label: str = Field(default="", description="Cell's template label")
    assigned_concept: str = Field(default="", description="What this cell represents")
    segment: str = Field(default="", description="Which segment this belongs to")
    period: str = Field(default="", description="FY/month if applicable")
    unit: str = Field(default="", description="Expected unit")
    derivation: str = Field(default="direct", description="'direct' / 'calculated' / 'assumption'")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reasoning: str = Field(default="")


class ModelDesignResult(BaseModel):
    """Output of the Model Designer."""
    cell_assignments: List[CellAssignment] = Field(default_factory=list)
    unmapped_cells: List[Dict[str, str]] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    raw_json: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

MD_SYSTEM_PROMPT = """\
あなたは投資銀行のシニアFMスペシャリストです。
確定したビジネスモデル分析とテンプレート構造をもとに、
各入力セルがどのビジネス概念に対応するかを決定します。

ここでは値の抽出は行いません。各セルが「何を表すか」の概念マッピングのみを行います。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【マッピングの原則】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. **セルラベルとビジネス概念の照合**
   - 同義語対応：「受講者数」=「顧客数」=「ユーザー数」
   - 略語対応：「MRR」=「月間経常収益」

2. **セグメントへの帰属**
   - 各セルがどのビジネスセグメントに属するか
   - 共通項目（人件費等）はセグメント横断で記載

3. **期間の特定**
   - FY1/FY2/月次/四半期の区別

4. **単位の確認**
   - 千円 vs 円、% vs 小数、人数 vs 比率

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【出力ルール】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 全入力セルに対して assignment または unmapped を返す
- assigned_concept は日本語で簡潔に
- 有効なJSONのみを返す
"""

MD_USER_PROMPT = """\
以下の情報をもとに、各入力セルが表すビジネス概念を決定してください。
値の抽出は不要です。「何を入れるべきか」の概念マッピングのみ行ってください。

━━━ ① 事業分析結果（確定済み） ━━━
{business_analysis_json}

━━━ ② テンプレート構造（確定済み） ━━━
{template_structure_json}

━━━ ③ 入力セル一覧 ━━━
{catalog_json}

{feedback_section}\
━━━ 出力形式（JSON） ━━━
{{
  "cell_assignments": [
    {{
      "sheet": "シート名",
      "cell": "B5",
      "label": "セルのラベル",
      "assigned_concept": "このセルが表す概念（例: 月間顧客数）",
      "segment": "セグメント名",
      "period": "FY1",
      "unit": "人",
      "derivation": "direct / calculated / assumption",
      "confidence": 0.9,
      "reasoning": "判定理由"
    }}
  ],
  "unmapped_cells": [
    {{"sheet": "シート名", "cell": "C10", "label": "ラベル", "reason": "対応する概念なし"}}
  ],
  "warnings": ["注意事項"]
}}
"""


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class ModelDesigner:
    """Agent 3 (Phase 4): Maps business concepts to specific cells."""

    def __init__(self, llm_client: Any) -> None:
        self.llm = llm_client

    def design(
        self,
        analysis_json: Dict[str, Any],
        template_structure_json: Dict[str, Any],
        catalog_items: List[Dict[str, Any]],
        feedback: str = "",
    ) -> ModelDesignResult:
        """Map business concepts to template cells.

        Parameters
        ----------
        analysis_json : dict
            Confirmed BM Analysis as raw JSON.
        template_structure_json : dict
            Confirmed Template Structure as raw JSON.
        catalog_items : list[dict]
            Writable template cells.
        feedback : str
            Optional user feedback.
        """
        analysis_str = json.dumps(analysis_json, ensure_ascii=False, indent=2)
        structure_str = json.dumps(template_structure_json, ensure_ascii=False, indent=2)
        catalog_str = json.dumps(catalog_items, ensure_ascii=False, indent=2)

        feedback_section = ""
        if feedback:
            feedback_section = (
                f"━━━ ユーザーフィードバック ━━━\n"
                f"{feedback}\n\n"
                f"上記のフィードバックを考慮して、マッピングを修正してください。\n\n"
            )

        messages = [
            {"role": "system", "content": MD_SYSTEM_PROMPT},
            {"role": "user", "content": MD_USER_PROMPT.format(
                business_analysis_json=analysis_str,
                template_structure_json=structure_str,
                catalog_json=catalog_str,
                feedback_section=feedback_section,
            )},
        ]

        logger.info(
            "ModelDesigner: sending %d catalog items to LLM",
            len(catalog_items),
        )
        result = self.llm.extract(messages)
        logger.info(
            "ModelDesigner: received %d assignments, %d unmapped",
            len(result.get("cell_assignments", [])),
            len(result.get("unmapped_cells", [])),
        )
        return self._parse_result(result)

    def _parse_result(self, raw: Dict[str, Any]) -> ModelDesignResult:
        assignments = []
        for ca in raw.get("cell_assignments", []):
            assignments.append(CellAssignment(
                sheet=ca.get("sheet", ""),
                cell=ca.get("cell", ""),
                label=ca.get("label", ""),
                assigned_concept=ca.get("assigned_concept", ""),
                segment=ca.get("segment", ""),
                period=ca.get("period", ""),
                unit=ca.get("unit", ""),
                derivation=ca.get("derivation", "direct"),
                confidence=float(ca.get("confidence", 0.5)),
                reasoning=ca.get("reasoning", ""),
            ))
        return ModelDesignResult(
            cell_assignments=assignments,
            unmapped_cells=raw.get("unmapped_cells", []),
            warnings=raw.get("warnings", []),
            raw_json=raw,
        )
