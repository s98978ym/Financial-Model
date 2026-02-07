"""Business Model Analyzer Agent.

Reads a business plan document and produces a structured analysis of the
business model -- segments, revenue drivers, cost structure, key
assumptions -- BEFORE any cell-level extraction begins.

This agent answers the question: "What kind of business is this and
how does it make money?"
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

class RevenueDriver(BaseModel):
    """A single revenue driver for a business segment."""
    name: str = Field(description="e.g. '顧客数', 'ARPU', '稼働率'")
    description: str = Field(default="")
    unit: str = Field(default="", description="e.g. '人', '円', '%'")
    estimated_value: Optional[str] = Field(default=None, description="Value from document if found")
    evidence: str = Field(default="", description="Quote from document")


class CostItem(BaseModel):
    """A cost element with fixed/variable classification."""
    name: str
    category: str = Field(description="'fixed' or 'variable'")
    description: str = Field(default="")
    estimated_value: Optional[str] = Field(default=None)
    evidence: str = Field(default="")


class BusinessSegment(BaseModel):
    """A distinct business line / revenue stream."""
    name: str = Field(description="e.g. 'ミール配送事業', 'SaaSサブスクリプション'")
    model_type: str = Field(description="e.g. 'subscription', 'transaction', 'project', 'marketplace'")
    revenue_formula: str = Field(description="e.g. '顧客数 × 単価 × 月数'")
    revenue_drivers: List[RevenueDriver] = Field(default_factory=list)
    key_assumptions: List[str] = Field(default_factory=list)


class BusinessModelAnalysis(BaseModel):
    """Complete analysis of a business model from a business plan."""
    company_name: str = Field(default="")
    industry: str = Field(default="", description="Auto-detected industry")
    business_model_type: str = Field(default="", description="B2B / B2C / B2B2C / marketplace / platform / etc.")
    executive_summary: str = Field(default="", description="1-3 sentence summary of the business")
    segments: List[BusinessSegment] = Field(default_factory=list)
    shared_costs: List[CostItem] = Field(default_factory=list)
    growth_trajectory: str = Field(default="", description="Description of growth assumptions")
    risk_factors: List[str] = Field(default_factory=list)
    time_horizon: str = Field(default="", description="e.g. '5年間 (FY1-FY5)'")
    currency: str = Field(default="JPY")
    raw_json: Dict[str, Any] = Field(default_factory=dict, description="Full LLM response")


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

BM_ANALYZER_SYSTEM_PROMPT = """\
あなたは投資銀行のシニアバンカー兼管理会計のエキスパートです。
事業計画書を読み、ビジネスモデルの構造分析を行います。

あなたの仕事は「この会社はどのようなビジネスで、どうやって収益を上げているか」を
完全に理解し、構造化されたJSON形式で出力することです。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【分析の観点】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. **事業セグメントの特定**
   - 単一事業か複数事業か
   - 各セグメントの収益モデル（サブスクリプション/トランザクション/プロジェクト/マーケットプレイス/ライセンス/広告/フリーミアム等）
   - セグメント間のシナジーや相互依存

2. **収益ドライバーの分解**
   - 各セグメントの売上を数式で表現: 例「売上 = 顧客数 × ARPU × 12ヶ月」
   - 各ドライバーの具体値（文書に記載があれば）
   - ドライバー間の関係性

3. **コスト構造の理解**
   - 固定費 vs 変動費の区分
   - セグメント固有のコスト vs 共通コスト（配賦が必要）
   - 主要コスト項目とその性質

4. **成長シナリオ**
   - 成長の前提（市場規模、獲得戦略、季節性）
   - 計画期間（何年分の予測か）
   - リスク要因

5. **業種の自動判定**
   - SaaS / EC / 教育 / 飲食 / 小売 / メーカー / ヘルスケア / 人材
   - 不動産 / 金融 / 広告・メディア / 物流 / エネルギー / 農業
   - プラットフォーム / マーケットプレイス / D2C / フランチャイズ
   - 上記に当てはまらない場合は最も近いものを選択

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【重要ルール】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- **segmentsは必ず1件以上返すこと（最重要ルール）**
  - 情報が限定的でも、文書全体を1つのセグメントとして分析する
  - 「情報不足」「分析不可」等の理由でsegments: []にしてはいけない
  - 文書からわかる範囲で最善の分析を行う
- 推定値には根拠を示す
- 文書に明確な記載がない場合は、文脈から合理的に推定し、evidenceに「推定」と記載する
- 日本語の数値表記を正規化: 億=×100,000,000、万=×10,000
- 複数セグメントがある場合は必ず全セグメントを列挙する
- 有効なJSONのみを返す
- segmentsを空配列[]にすることは禁止
"""

BM_ANALYZER_USER_PROMPT = """\
以下の事業計画書を分析し、ビジネスモデルの構造をJSON形式で出力してください。

■ 事業計画書:
{document_text}

■ 出力形式（JSON）:
{{
  "company_name": "会社名",
  "industry": "自動判定した業種",
  "business_model_type": "B2B / B2C / B2B2C / marketplace / etc.",
  "executive_summary": "事業の要約（1-3文）",
  "segments": [
    {{
      "name": "セグメント名",
      "model_type": "subscription / transaction / project / etc.",
      "revenue_formula": "売上 = ドライバー1 × ドライバー2 × ...",
      "revenue_drivers": [
        {{
          "name": "ドライバー名",
          "description": "説明",
          "unit": "単位",
          "estimated_value": "文書から読み取った値",
          "evidence": "文書からの引用"
        }}
      ],
      "key_assumptions": ["前提1", "前提2"]
    }}
  ],
  "shared_costs": [
    {{
      "name": "コスト名",
      "category": "fixed / variable",
      "description": "説明",
      "estimated_value": "値",
      "evidence": "引用"
    }}
  ],
  "growth_trajectory": "成長シナリオの説明",
  "risk_factors": ["リスク1", "リスク2"],
  "time_horizon": "計画期間",
  "currency": "JPY"
}}
"""


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class BusinessModelAnalyzer:
    """Agent 1: Analyzes a business plan to understand the business model.

    This runs BEFORE any cell-level extraction.  It gives the system
    a semantic understanding of what the business does, enabling
    intelligent parameter mapping later.
    """

    def __init__(self, llm_client: Any) -> None:
        self.llm = llm_client

    def analyze(self, document_text: str, feedback: str = "") -> BusinessModelAnalysis:
        """Analyze a business plan document and return structured analysis.

        Parameters
        ----------
        document_text : str
            Full text of the business plan document.
        feedback : str
            Optional user feedback to incorporate into re-analysis.

        Returns
        -------
        BusinessModelAnalysis
            Structured analysis of the business model.

        Raises
        ------
        RuntimeError
            If the LLM returns an empty or unusable response.
        """
        if not document_text or not document_text.strip():
            raise RuntimeError("事業計画書のテキストが空です。PDFが正しく読み取れているか確認してください。")

        # Truncate if too long for a single call (keep first 12K chars)
        max_chars = 12000
        if len(document_text) > max_chars:
            truncated = document_text[:max_chars]
            truncated += f"\n\n[... 文書は {len(document_text):,} 文字中、先頭 {max_chars:,} 文字を分析しています ...]"
        else:
            truncated = document_text

        user_content = BM_ANALYZER_USER_PROMPT.format(document_text=truncated)

        if feedback:
            user_content += (
                f"\n\n━━━ ユーザーフィードバック ━━━\n"
                f"{feedback}\n\n"
                f"上記のフィードバックを考慮して、分析を修正してください。"
            )

        messages = [
            {"role": "system", "content": BM_ANALYZER_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

        logger.info("BusinessModelAnalyzer: sending document (%d chars) to LLM", len(truncated))
        result = self.llm.extract(messages)
        logger.info("BusinessModelAnalyzer: received response keys=%s", list(result.keys()))

        # Auto-unwrap: LLM sometimes wraps response in a container key
        if result and not result.get("segments"):
            for _wrap_key in ("result", "analysis", "response", "data", "output"):
                _inner = result.get(_wrap_key)
                if isinstance(_inner, dict) and _inner.get("segments"):
                    logger.info("BusinessModelAnalyzer: unwrapped response from '%s' key", _wrap_key)
                    result = _inner
                    break

        # Validate: if the LLM returned nothing useful, raise an error
        segments_raw = result.get("segments") if result else None
        if not result or not segments_raw:
            raw_keys = list(result.keys()) if result else []
            raise RuntimeError(
                f"LLMがビジネスモデル分析を返しませんでした。"
                f"レスポンスkeys: {raw_keys}, "
                f"segments type: {type(segments_raw).__name__}, "
                f"segments value: {str(segments_raw)[:200]}。"
                f"ドキュメント先頭100文字: {document_text[:100]!r}"
            )

        # Ensure segments is a list
        if not isinstance(segments_raw, list):
            raise RuntimeError(
                f"LLMが不正な形式のsegmentsを返しました: "
                f"type={type(segments_raw).__name__}, "
                f"value={str(segments_raw)[:200]}"
            )

        return self._parse_result(result)

    def _parse_result(self, raw: Dict[str, Any]) -> BusinessModelAnalysis:
        """Parse LLM JSON response into BusinessModelAnalysis model."""
        segments = []
        for seg_data in raw.get("segments", []):
            drivers = []
            for d in seg_data.get("revenue_drivers", []):
                drivers.append(RevenueDriver(
                    name=d.get("name", ""),
                    description=d.get("description", ""),
                    unit=d.get("unit", ""),
                    estimated_value=d.get("estimated_value"),
                    evidence=d.get("evidence", ""),
                ))
            segments.append(BusinessSegment(
                name=seg_data.get("name", ""),
                model_type=seg_data.get("model_type", ""),
                revenue_formula=seg_data.get("revenue_formula", ""),
                revenue_drivers=drivers,
                key_assumptions=seg_data.get("key_assumptions", []),
            ))

        costs = []
        for c in raw.get("shared_costs", []):
            costs.append(CostItem(
                name=c.get("name", ""),
                category=c.get("category", "fixed"),
                description=c.get("description", ""),
                estimated_value=c.get("estimated_value"),
                evidence=c.get("evidence", ""),
            ))

        return BusinessModelAnalysis(
            company_name=raw.get("company_name", ""),
            industry=raw.get("industry", ""),
            business_model_type=raw.get("business_model_type", ""),
            executive_summary=raw.get("executive_summary", ""),
            segments=segments,
            shared_costs=costs,
            growth_trajectory=raw.get("growth_trajectory", ""),
            risk_factors=raw.get("risk_factors", []),
            time_horizon=raw.get("time_horizon", ""),
            currency=raw.get("currency", "JPY"),
            raw_json=raw,
        )
