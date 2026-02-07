"""Business Model Analyzer Agent.

Reads a business plan document and produces a deep narrative understanding
of the business, then proposes 3-5 structural interpretations (patterns)
for the user to choose from.

Approach:
  1. Read ALL the document — understand the big picture, create a story
  2. Categorize by industry & business model type
  3. Propose 3-5 reasonable structural patterns
  4. User selects/refines → confirmed model feeds downstream phases
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
    name: str = Field(description="e.g. 'SaaSサブスクリプション', 'EC販売', '広告事業'")
    model_type: str = Field(description="e.g. 'subscription', 'transaction', 'project', 'marketplace'")
    revenue_formula: str = Field(description="e.g. '顧客数 × 単価 × 月数'")
    revenue_drivers: List[RevenueDriver] = Field(default_factory=list)
    key_assumptions: List[str] = Field(default_factory=list)


class BusinessModelProposal(BaseModel):
    """One possible structural interpretation of the business model."""
    label: str = Field(description="e.g. 'パターンA: SaaS型サブスクリプションモデル'")
    industry: str = Field(default="")
    business_model_type: str = Field(default="", description="B2B / B2C / B2B2C / marketplace / etc.")
    executive_summary: str = Field(default="", description="1-3 sentence summary for this interpretation")
    diagram: str = Field(default="", description="Text-based business model diagram")
    segments: List[BusinessSegment] = Field(default_factory=list)
    shared_costs: List[CostItem] = Field(default_factory=list)
    growth_trajectory: str = Field(default="")
    risk_factors: List[str] = Field(default_factory=list)
    time_horizon: str = Field(default="")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="How confident in this interpretation")
    reasoning: str = Field(default="", description="Why this interpretation is plausible")


class BusinessModelAnalysis(BaseModel):
    """Complete analysis: narrative understanding + multiple proposals.

    The main fields (industry, segments, etc.) are populated from the
    currently selected proposal for backward compatibility with downstream
    phases that rely on ``bm.raw_json``.
    """
    # --- core fields (populated from selected proposal) ---
    company_name: str = Field(default="")
    industry: str = Field(default="", description="Auto-detected industry")
    business_model_type: str = Field(default="", description="B2B / B2C / B2B2C / marketplace / etc.")
    executive_summary: str = Field(default="", description="1-3 sentence summary of the business")
    segments: List[BusinessSegment] = Field(default_factory=list)
    shared_costs: List[CostItem] = Field(default_factory=list)
    growth_trajectory: str = Field(default="", description="Description of growth assumptions")
    risk_factors: List[str] = Field(default_factory=list)
    time_horizon: str = Field(default="", description="e.g. '5年間 (FY1-FY5)'")
    currency: str = Field(default="JPY")
    raw_json: Dict[str, Any] = Field(default_factory=dict, description="Full LLM response")

    # --- NEW: deep analysis fields ---
    document_narrative: str = Field(default="", description="Deep narrative understanding of the business")
    key_facts: List[str] = Field(default_factory=list, description="Key facts/figures extracted from document")
    proposals: List[BusinessModelProposal] = Field(default_factory=list, description="3-5 structural interpretations")
    selected_index: int = Field(default=0, description="Which proposal is selected")

    def select_proposal(self, index: int) -> "BusinessModelAnalysis":
        """Select a proposal and populate main fields from it.

        Returns a new instance with the main fields updated.
        """
        if not self.proposals or index < 0 or index >= len(self.proposals):
            return self
        p = self.proposals[index]
        # Build a raw_json that matches the old format for downstream compat
        compat_raw = {
            "company_name": self.company_name,
            "industry": p.industry,
            "business_model_type": p.business_model_type,
            "executive_summary": p.executive_summary,
            "segments": [seg.model_dump() for seg in p.segments],
            "shared_costs": [c.model_dump() for c in p.shared_costs],
            "growth_trajectory": p.growth_trajectory,
            "risk_factors": p.risk_factors,
            "time_horizon": p.time_horizon,
            "currency": self.currency,
            "document_narrative": self.document_narrative,
            "key_facts": self.key_facts,
        }
        return BusinessModelAnalysis(
            company_name=self.company_name,
            industry=p.industry,
            business_model_type=p.business_model_type,
            executive_summary=p.executive_summary,
            segments=p.segments,
            shared_costs=p.shared_costs,
            growth_trajectory=p.growth_trajectory,
            risk_factors=p.risk_factors,
            time_horizon=p.time_horizon,
            currency=self.currency,
            raw_json=compat_raw,
            document_narrative=self.document_narrative,
            key_facts=self.key_facts,
            proposals=self.proposals,
            selected_index=index,
        )


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

BM_ANALYZER_SYSTEM_PROMPT = """\
あなたは投資銀行のシニアバンカー兼管理会計のエキスパートです。
事業計画書を深く読み込み、ビジネスモデルの本質を理解する専門家です。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【あなたの思考プロセス（この順番で分析せよ）】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

■ STEP 1: 資料を徹底的に読み込む
  - 全ページを丁寧に読み、会社が何をしているか全体像を把握する
  - 数字、固有名詞、製品名、サービス名、ターゲット顧客の記述を全て拾う
  - 図表やグラフの説明文からも情報を読み取る
  - 行間を読む：明示されていなくても文脈から推測できることを考える

■ STEP 2: ストーリーを組み立てる
  - 「この会社は何者で、誰に、何を、どうやって提供し、どう稼いでいるか」
    を自分の言葉で語れるレベルまで理解する
  - 創業の背景、解決している課題、市場でのポジション、競合優位性を把握する
  - 資料に明記されていなくても、断片情報から合理的に推論する

■ STEP 3: 複数のビジネスモデル解釈を検討する
  - 同じ事業でも見方によって異なるモデルとして解釈できる
  - 例：飲食チェーンは「直営型」「FC型」「プラットフォーム型」等の解釈がありうる
  - 例：SaaSでも「ホリゾンタルSaaS」「バーティカルSaaS」「SaaS+コンサル複合」等
  - 3〜5つの合理的な解釈パターンを提案する

■ STEP 4: 各パターンを構造化する
  - 各解釈パターンごとに、セグメント分割・収益モデル・コスト構造を具体的に定義する
  - 各パターンの確信度（confidence）と「なぜこの解釈が合理的か」を明記する

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【重要ルール】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 「不明」「情報不足」で済ませることは禁止。断片情報からでも最善の推論を行え
- proposals（パターン案）は必ず3件以上返すこと
- 各proposalのsegmentsは必ず1件以上
- 情報が限定的な場合でも、業種の一般的な知識を動員して合理的に推定せよ
- 推定した場合はreasoningに「推定根拠」を明記する
- 日本語の数値表記を正規化: 億=×100,000,000、万=×10,000
- 有効なJSONのみを返す
"""

BM_ANALYZER_USER_PROMPT = """\
以下の事業計画書を深く読み込み、ビジネスモデルを分析してください。

■ 事業計画書:
{document_text}

■ 出力形式（JSON）:
{{
  "company_name": "会社名（推定でもよい）",
  "document_narrative": "この会社のビジネスについて、投資銀行のバンカーとして深く理解した内容を日本語で詳細に記述する。会社が何をしているか、誰に価値を提供しているか、どうやって収益を得ているか、成長の仮説は何か、を自分の言葉でストーリーとして語る。最低300文字以上。",
  "key_facts": [
    "資料から読み取れた重要な事実や数値（例: '月間アクティブユーザー5万人'）",
    "推定した場合は【推定】と明記（例: '【推定】従業員数50-100名規模'）"
  ],
  "proposals": [
    {{
      "label": "パターンA: [簡潔なモデル名]",
      "industry": "業種",
      "business_model_type": "B2B / B2C / B2B2C / marketplace / etc.",
      "executive_summary": "この解釈の要約（1-3文）",
      "diagram": "テキストベースのビジネスモデル図解。収益の流れ・価値の流れを視覚的に示す。\\n例:\\n[顧客企業] --月額課金--> [SaaSプラットフォーム] --サブスク収益--> [売上]\\n                              |\\n                        [導入支援] --プロジェクト収益-->\\n\\n矢印(-->)、ボックス([])、パイプ(|)を使ってフローを表現する。",
      "segments": [
        {{
          "name": "セグメント名",
          "model_type": "subscription / transaction / project / marketplace / license / advertising / freemium / etc.",
          "revenue_formula": "売上 = ドライバー1 × ドライバー2 × ...",
          "revenue_drivers": [
            {{
              "name": "ドライバー名",
              "description": "説明",
              "unit": "単位",
              "estimated_value": "文書から読み取った値（推定の場合は【推定】と付記）",
              "evidence": "文書からの引用 or 推定根拠"
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
          "evidence": "引用 or 推定根拠"
        }}
      ],
      "growth_trajectory": "成長シナリオの説明",
      "risk_factors": ["リスク1", "リスク2"],
      "time_horizon": "計画期間（推定でもよい）",
      "confidence": 0.8,
      "reasoning": "なぜこの解釈が合理的と考えるか"
    }},
    {{
      "label": "パターンB: [別の解釈]",
      "...": "（同じ構造で別の解釈を提案）"
    }},
    {{
      "label": "パターンC: [さらに別の解釈]",
      "...": "（同じ構造で別の解釈を提案）"
    }}
  ],
  "currency": "JPY"
}}

【注意】
- proposalsは必ず3〜5件。少なすぎても多すぎてもいけない。
- 各proposalは完全に独立した1つの解釈（セグメント構成もコスト構造も異なりうる）。
- confidenceの高い順に並べる。
- document_narrativeは資料全体を深く理解した上でのストーリー。テンプレ的な回答は禁止。
"""


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class BusinessModelAnalyzer:
    """Agent 1: Deeply analyzes a business plan to understand the business model.

    Instead of shallow template matching, this agent:
    1. Reads the entire document to build a narrative understanding
    2. Proposes 3-5 structural interpretations (patterns)
    3. Lets the user select/refine the best interpretation
    """

    def __init__(
        self,
        llm_client: Any,
        system_prompt: Optional[str] = None,
        user_prompt: Optional[str] = None,
    ) -> None:
        self.llm = llm_client
        self._system_prompt = system_prompt or BM_ANALYZER_SYSTEM_PROMPT
        self._user_prompt = user_prompt or BM_ANALYZER_USER_PROMPT

    def analyze(self, document_text: str, feedback: str = "") -> BusinessModelAnalysis:
        """Analyze a business plan document and return narrative + proposals.

        Parameters
        ----------
        document_text : str
            Full text of the business plan document.
        feedback : str
            Optional user feedback to incorporate into re-analysis.

        Returns
        -------
        BusinessModelAnalysis
            Deep analysis with narrative and 3-5 proposals.

        Raises
        ------
        RuntimeError
            If the LLM returns an empty or unusable response.
        """
        if not document_text or not document_text.strip():
            raise RuntimeError("事業計画書のテキストが空です。PDFが正しく読み取れているか確認してください。")

        # Truncate if too long for a single call (keep first 15K chars)
        max_chars = 15000
        if len(document_text) > max_chars:
            truncated = document_text[:max_chars]
            truncated += f"\n\n[... 文書は {len(document_text):,} 文字中、先頭 {max_chars:,} 文字を分析しています ...]"
        else:
            truncated = document_text

        user_content = self._user_prompt.format(document_text=truncated)

        if feedback:
            user_content += (
                f"\n\n━━━ ユーザーフィードバック ━━━\n"
                f"{feedback}\n\n"
                f"上記のフィードバックを考慮して、分析を修正してください。"
                f"document_narrativeも更新し、proposalsも再検討してください。"
            )

        messages = [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": user_content},
        ]

        logger.info("BusinessModelAnalyzer: sending document (%d chars) to LLM", len(truncated))
        result = self.llm.extract(messages)
        logger.info("BusinessModelAnalyzer: received response keys=%s", list(result.keys()))

        # Auto-unwrap: LLM sometimes wraps in a container key
        if result and not result.get("proposals"):
            for _wrap_key in ("result", "analysis", "response", "data", "output"):
                _inner = result.get(_wrap_key)
                if isinstance(_inner, dict) and _inner.get("proposals"):
                    logger.info("BusinessModelAnalyzer: unwrapped from '%s' key", _wrap_key)
                    result = _inner
                    break

        # Backward compat: if LLM returned old format (segments at top level),
        # wrap it as a single proposal
        if result and result.get("segments") and not result.get("proposals"):
            logger.info("BusinessModelAnalyzer: old format detected, wrapping as single proposal")
            result = self._wrap_legacy_format(result)

        # Validate proposals exist
        proposals_raw = result.get("proposals") if result else None
        if not result or not proposals_raw or not isinstance(proposals_raw, list):
            raw_keys = list(result.keys()) if result else []
            raise RuntimeError(
                f"LLMがビジネスモデル分析を返しませんでした。"
                f"レスポンスkeys: {raw_keys}, "
                f"proposals type: {type(proposals_raw).__name__ if proposals_raw else 'None'}。"
                f"ドキュメント先頭100文字: {document_text[:100]!r}"
            )

        return self._parse_result(result)

    @staticmethod
    def _wrap_legacy_format(raw: Dict[str, Any]) -> Dict[str, Any]:
        """Convert old single-result format into new proposals format."""
        proposal = {
            "label": f"パターンA: {raw.get('industry', '不明')}",
            "industry": raw.get("industry", ""),
            "business_model_type": raw.get("business_model_type", ""),
            "executive_summary": raw.get("executive_summary", ""),
            "segments": raw.get("segments", []),
            "shared_costs": raw.get("shared_costs", []),
            "growth_trajectory": raw.get("growth_trajectory", ""),
            "risk_factors": raw.get("risk_factors", []),
            "time_horizon": raw.get("time_horizon", ""),
            "confidence": 0.7,
            "reasoning": "LLMが単一解釈として返したパターン",
        }
        return {
            "company_name": raw.get("company_name", ""),
            "document_narrative": raw.get("executive_summary", ""),
            "key_facts": [],
            "proposals": [proposal],
            "currency": raw.get("currency", "JPY"),
        }

    def _parse_result(self, raw: Dict[str, Any]) -> BusinessModelAnalysis:
        """Parse LLM JSON response into BusinessModelAnalysis model."""
        proposals = []
        for p_data in raw.get("proposals", []):
            segments = self._parse_segments(p_data.get("segments", []))
            costs = self._parse_costs(p_data.get("shared_costs", []))
            proposals.append(BusinessModelProposal(
                label=p_data.get("label", ""),
                industry=p_data.get("industry", ""),
                business_model_type=p_data.get("business_model_type", ""),
                executive_summary=p_data.get("executive_summary", ""),
                diagram=p_data.get("diagram", ""),
                segments=segments,
                shared_costs=costs,
                growth_trajectory=p_data.get("growth_trajectory", ""),
                risk_factors=p_data.get("risk_factors", []),
                time_horizon=p_data.get("time_horizon", ""),
                confidence=min(1.0, max(0.0, float(p_data.get("confidence", 0.5)))),
                reasoning=p_data.get("reasoning", ""),
            ))

        # Sort by confidence descending
        proposals.sort(key=lambda p: p.confidence, reverse=True)

        # Build initial analysis with first proposal selected
        analysis = BusinessModelAnalysis(
            company_name=raw.get("company_name", ""),
            document_narrative=raw.get("document_narrative", ""),
            key_facts=raw.get("key_facts", []),
            proposals=proposals,
            selected_index=0,
            currency=raw.get("currency", "JPY"),
            raw_json=raw,
        )

        # Auto-select first proposal to populate main fields
        if proposals:
            analysis = analysis.select_proposal(0)

        return analysis

    @staticmethod
    def _parse_segments(segments_raw: List[Dict[str, Any]]) -> List[BusinessSegment]:
        """Parse segment data from LLM response."""
        segments = []
        for seg_data in segments_raw:
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
        return segments

    @staticmethod
    def _parse_costs(costs_raw: List[Dict[str, Any]]) -> List[CostItem]:
        """Parse cost data from LLM response."""
        costs = []
        for c in costs_raw:
            costs.append(CostItem(
                name=c.get("name", ""),
                category=c.get("category", "fixed"),
                description=c.get("description", ""),
                estimated_value=c.get("estimated_value"),
                evidence=c.get("evidence", ""),
            ))
        return costs
