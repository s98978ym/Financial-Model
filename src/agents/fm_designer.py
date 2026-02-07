"""Investment Banking Financial Model Designer Agent.

Takes the output of the Business Model Analyzer (Agent 1) plus the
scanned Excel template catalog, and produces an intelligent mapping:
which template sheet/block corresponds to which business segment,
and what value should go into each input cell.

This agent answers: "Given this business model and this Excel template,
how should each cell be filled?"
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .business_model_analyzer import BusinessModelAnalysis

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Output models
# ---------------------------------------------------------------------------

class TemplateSheetMapping(BaseModel):
    """Maps a template sheet to a business segment or function."""
    sheet_name: str
    mapped_segment: str = Field(default="", description="Which business segment this sheet models")
    sheet_purpose: str = Field(default="", description="e.g. 'revenue build-up', 'cost detail', 'P&L summary'")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class CellExtraction(BaseModel):
    """Extracted value for a specific template cell."""
    sheet: str
    cell: str
    label: str = Field(default="")
    value: Any = Field(default=None)
    unit: str = Field(default="")
    source: str = Field(default="document", description="'document' / 'inferred' / 'template_default'")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence: str = Field(default="", description="Quote from document or reasoning")
    segment: str = Field(default="", description="Which business segment this belongs to")
    period: str = Field(default="", description="FY/month/quarter if applicable")


class FMDesignResult(BaseModel):
    """Complete output of the FM Designer agent."""
    sheet_mappings: List[TemplateSheetMapping] = Field(default_factory=list)
    extractions: List[CellExtraction] = Field(default_factory=list)
    unmapped_cells: List[Dict[str, str]] = Field(default_factory=list, description="Cells with no matching data")
    warnings: List[str] = Field(default_factory=list)
    raw_json: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

FM_DESIGNER_SYSTEM_PROMPT = """\
あなたは投資銀行のシニアFMスペシャリストです。
事業分析結果とExcelテンプレートの構造を理解し、各入力セルに適切な値をマッピングします。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【あなたの能力】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. **テンプレート構造の理解**
   - シート名・ブロック名・ラベルから、そのシートが何をモデル化しているか判断
   - 「収益モデルN」→ 事業セグメントNの収益モデル（汎用スロット）
   - 「費用リスト」→ 全セグメント共通のコスト一覧
   - 「前提条件」→ 全セグメントに適用される基本前提
   - テンプレートのシート名は汎用的（業種非依存）なため、事業分析結果のセグメントと動的にマッチングする

2. **セグメント→シートのマッピング**
   - 事業分析の各セグメントが、テンプレートのどの「収益モデルN」シートに対応するか判定
   - 1つのシートが複数セグメントをカバーする場合もある
   - 「費用」「共通」系シートは複数セグメントにまたがる

3. **入力セルへの値マッピング**
   - セルのラベル（日本語/英語）と事業分析のドライバーを照合
   - テンプレートのラベルは汎用的（例:「顧客数/取引数」「単価」「頻度/回数」）
   - 事業分析のドライバーとの同義語対応（例:「受講者数」=「顧客数」=「ユーザー数」=「取引先数」）
   - 期間（FY1/FY2/月次）ごとの値の区別

4. **経済的妥当性の検証**
   - マージン水準が業界標準から大きく外れていないか
   - 成長率の持続可能性
   - 単位の整合性（千円 vs 円、% vs 小数）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【出力ルール】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- **必ずextractionsを返すこと（最重要ルール）**
  - 事業分析結果が空・不完全でも、文書とテンプレートから直接抽出を行う
  - 「スキップ」「分析不可」等の理由で空のextractionsを返してはいけない
  - Agent 1の分析が失敗していても、文書の原文から情報を読み取って抽出する
- 文書に明記された値: confidence 0.8-1.0, source="document"
- 論理的に導出した値: confidence 0.5-0.8, source="inferred"
- マッピングできないセル: unmapped_cellsに記録
- 数値の正規化: 億→×100,000,000、万→×10,000
- %は小数表記（30% → 0.3）
- 有効なJSONのみを返す
- 絶対にスキップしない。必ず全テンプレートセルに対して抽出またはunmapped記録を行う
"""

FM_DESIGNER_USER_PROMPT = """\
以下の情報を使って、Excelテンプレートの各入力セルに値をマッピングしてください。

━━━ ① 事業分析結果（Agent 1の出力） ━━━
{business_analysis_json}

━━━ ② テンプレート構造（入力セル一覧） ━━━
{template_catalog_json}

━━━ ③ 事業計画書（原文） ━━━
{document_chunk}

━━━ 出力形式（JSON） ━━━
{{
  "sheet_mappings": [
    {{
      "sheet_name": "シート名",
      "mapped_segment": "対応するセグメント名（事業分析結果から）",
      "sheet_purpose": "revenue_model / cost_detail / pl_summary / assumptions / etc.",
      "confidence": 0.9
    }}
  ],
  "extractions": [
    {{
      "sheet": "シート名",
      "cell": "B5",
      "label": "セルのラベル",
      "value": 12345,
      "unit": "円",
      "source": "document",
      "confidence": 0.9,
      "evidence": "事業計画書からの引用 or 推定根拠",
      "segment": "対応セグメント名",
      "period": "FY1"
    }}
  ],
  "unmapped_cells": [
    {{"sheet": "シート名", "cell": "C10", "label": "ラベル", "reason": "文書に該当情報なし"}}
  ],
  "warnings": [
    "粗利率が95%と異常に高い — 確認が必要"
  ]
}}
"""


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class FMDesigner:
    """Agent 2: Maps business model analysis to Excel template cells.

    Uses the structured output of BusinessModelAnalyzer plus the
    scanned template catalog to produce intelligent cell-level mappings.
    """

    def __init__(self, llm_client: Any) -> None:
        self.llm = llm_client

    def design(
        self,
        analysis: BusinessModelAnalysis,
        catalog_items: List[Dict[str, Any]],
        document_text: str,
    ) -> FMDesignResult:
        """Map analysis to template cells.

        Parameters
        ----------
        analysis : BusinessModelAnalysis
            Output from Agent 1.
        catalog_items : list[dict]
            Flattened catalog items (sheet, cell, labels, units, etc.)
        document_text : str
            Original document text for evidence extraction.
        """
        # If analysis is empty/default, provide minimal context instead of empty {}
        _raw = analysis.raw_json if analysis.raw_json else {}
        if not _raw or not _raw.get("segments"):
            _raw = {
                "note": "Agent 1の分析結果が利用できません。文書から直接抽出してください。",
                "segments": [],
                "industry": analysis.industry or "不明",
            }
        analysis_json = json.dumps(_raw, ensure_ascii=False, indent=2)
        catalog_json = json.dumps(catalog_items, ensure_ascii=False, indent=2)

        # Truncate document if needed
        max_doc = 8000
        if len(document_text) > max_doc:
            doc_chunk = document_text[:max_doc]
            doc_chunk += f"\n\n[... {len(document_text):,} 文字中、先頭 {max_doc:,} 文字を表示 ...]"
        else:
            doc_chunk = document_text

        messages = [
            {"role": "system", "content": FM_DESIGNER_SYSTEM_PROMPT},
            {"role": "user", "content": FM_DESIGNER_USER_PROMPT.format(
                business_analysis_json=analysis_json,
                template_catalog_json=catalog_json,
                document_chunk=doc_chunk,
            )},
        ]

        logger.info(
            "FMDesigner: sending %d catalog items + analysis (%d segments) to LLM",
            len(catalog_items),
            len(analysis.segments),
        )
        result = self.llm.extract(messages)

        # Auto-unwrap: LLM sometimes wraps response in a container key
        if result and not result.get("extractions") and not result.get("sheet_mappings"):
            for _wrap_key in ("result", "response", "data", "output", "design"):
                _inner = result.get(_wrap_key)
                if isinstance(_inner, dict) and (_inner.get("extractions") or _inner.get("sheet_mappings")):
                    logger.info("FMDesigner: unwrapped response from '%s' key", _wrap_key)
                    result = _inner
                    break

        logger.info(
            "FMDesigner: received %d extractions, %d unmapped, keys=%s",
            len(result.get("extractions", [])),
            len(result.get("unmapped_cells", [])),
            list(result.keys()),
        )

        return self._parse_result(result)

    def _catalog_to_dicts(self, items: list) -> List[Dict[str, Any]]:
        """Convert CatalogItem objects to simple dicts for the prompt."""
        result = []
        for item in items:
            if hasattr(item, 'has_formula') and item.has_formula:
                continue
            result.append({
                "sheet": getattr(item, 'sheet', ''),
                "cell": getattr(item, 'cell', ''),
                "labels": getattr(item, 'label_candidates', []),
                "units": getattr(item, 'unit_candidates', []),
                "period": getattr(item, 'year_or_period', ''),
                "block": getattr(item, 'block', ''),
                "current_value": getattr(item, 'current_value', None),
            })
        return result

    def _parse_result(self, raw: Dict[str, Any]) -> FMDesignResult:
        """Parse LLM JSON response into FMDesignResult."""
        sheet_mappings = []
        for sm in raw.get("sheet_mappings", []):
            sheet_mappings.append(TemplateSheetMapping(
                sheet_name=sm.get("sheet_name", ""),
                mapped_segment=sm.get("mapped_segment", ""),
                sheet_purpose=sm.get("sheet_purpose", ""),
                confidence=float(sm.get("confidence", 0.5)),
            ))

        extractions = []
        for ex in raw.get("extractions", []):
            extractions.append(CellExtraction(
                sheet=ex.get("sheet", ""),
                cell=ex.get("cell", ""),
                label=ex.get("label", ""),
                value=ex.get("value"),
                unit=ex.get("unit", ""),
                source=ex.get("source", "document"),
                confidence=float(ex.get("confidence", 0.5)),
                evidence=ex.get("evidence", ""),
                segment=ex.get("segment", ""),
                period=ex.get("period", ""),
            ))

        return FMDesignResult(
            sheet_mappings=sheet_mappings,
            extractions=extractions,
            unmapped_cells=raw.get("unmapped_cells", []),
            warnings=raw.get("warnings", []),
            raw_json=raw,
        )
