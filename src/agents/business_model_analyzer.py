"""Business Model Analyzer Agent.

Reads a business plan document and produces a GROUNDED analysis
of the business, then proposes 3-5 structural interpretations (patterns)
for the user to choose from.

Anti-hallucination design:
  - Every claim MUST cite a verbatim quote from the document
  - "I don't know" is preferred over fabrication
  - Grounding validation checks evidence against source text
  - Smart truncation preserves both start and end of long documents
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

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
    evidence: str = Field(default="", description="Verbatim quote from document")
    is_from_document: bool = Field(default=False, description="True if value is directly from document text")

    @field_validator("estimated_value", mode="before")
    @classmethod
    def coerce_estimated_value(cls, v: Any) -> Optional[str]:
        if v is not None and not isinstance(v, str):
            return str(v)
        return v


class CostItem(BaseModel):
    """A cost element with fixed/variable classification."""
    name: str
    category: str = Field(description="'fixed' or 'variable'")
    description: str = Field(default="")
    estimated_value: Optional[str] = Field(default=None)
    evidence: str = Field(default="", description="Verbatim quote from document")
    is_from_document: bool = Field(default=False, description="True if value is directly from document text")

    @field_validator("estimated_value", mode="before")
    @classmethod
    def coerce_estimated_value(cls, v: Any) -> Optional[str]:
        if v is not None and not isinstance(v, str):
            return str(v)
        return v


class BusinessSegment(BaseModel):
    """A distinct business line / revenue stream."""
    name: str = Field(description="e.g. 'SaaSサブスクリプション', 'EC販売', '広告事業'")
    model_type: str = Field(description="e.g. 'subscription', 'transaction', 'project', 'marketplace'")
    revenue_formula: str = Field(description="e.g. '顧客数 × 単価 × 月数'")
    revenue_drivers: List[RevenueDriver] = Field(default_factory=list)
    key_assumptions: List[str] = Field(default_factory=list)


class YearTarget(BaseModel):
    """A single year's financial target value."""
    year: str = Field(default="", description="e.g. 'FY1', 'FY26'")
    value: Optional[float] = Field(default=None, description="Target value (normalised to yen)")
    evidence: str = Field(default="", description="Verbatim quote from document")
    source: str = Field(default="document", description="document / inferred / default")


class BreakevenTarget(BaseModel):
    """Breakeven timing target."""
    year: str = Field(default="", description="e.g. 'FY3', '3年目'")
    evidence: str = Field(default="", description="Verbatim quote from document")
    source: str = Field(default="document", description="document / inferred / default")


class FinancialTargets(BaseModel):
    """Financial targets extracted from the business plan."""
    horizon_years: int = Field(default=5, description="Planning horizon in years")
    revenue_targets: List[YearTarget] = Field(default_factory=list, description="Revenue targets per year")
    op_targets: List[YearTarget] = Field(default_factory=list, description="Operating profit targets per year")
    single_year_breakeven: Optional[BreakevenTarget] = Field(default=None, description="Single-year breakeven target")
    cumulative_breakeven: Optional[BreakevenTarget] = Field(default=None, description="Cumulative breakeven target")


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
    grounding_score: float = Field(default=0.0, description="Fraction of claims backed by document evidence")


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

    # --- deep analysis fields ---
    document_narrative: str = Field(default="", description="Grounded summary of the business from document")
    key_facts: List[str] = Field(default_factory=list, description="Key facts/figures extracted from document")
    proposals: List[BusinessModelProposal] = Field(default_factory=list, description="3-5 structural interpretations")
    selected_index: int = Field(default=0, description="Which proposal is selected")

    # --- financial targets (v2) ---
    financial_targets: Optional[FinancialTargets] = Field(default=None, description="Revenue/OP targets and breakeven timing from document")

    def select_proposal(self, index: int) -> "BusinessModelAnalysis":
        """Select a proposal and populate main fields from it.

        Returns a new instance with the main fields updated.
        """
        if not self.proposals or index < 0 or index >= len(self.proposals):
            return self
        p = self.proposals[index]
        # Build a raw_json that matches the old format for downstream compat
        ft_dump = self.financial_targets.model_dump() if self.financial_targets else None
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
            "financial_targets": ft_dump,
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
            financial_targets=self.financial_targets,
        )


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

BM_ANALYZER_SYSTEM_PROMPT = """\
あなたは投資銀行のシニアバンカー兼管理会計のエキスパートです。
事業計画書を正確に読み取り、ビジネスモデルを構造化する専門家です。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【最重要原則：ハルシネーション厳禁】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

★ 文書に書かれていない情報を「でっち上げ」ることは絶対に禁止。
★ すべての事実・数値は、必ず文書からの「原文引用」(evidence)で裏付けよ。
★ 文書に書かれていない場合は、正直に「文書に記載なし」と書け。
★ 推定・推測を行う場合は【推定】と必ず明記し、推定根拠を述べよ。
  ただし推定は最小限に留め、文書からの直接抽出を優先せよ。
★ 会社名が文書に明記されていなければ「記載なし」とせよ。勝手に命名するな。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【思考プロセス（この順番で分析せよ）】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

■ STEP 1: 文書の事実を抽出する
  - 文書に明示的に書かれている事実だけを拾い上げる
  - 会社名、事業内容、製品名、サービス名、顧客像、数値（売上、顧客数等）
  - 各事実に対して「文書のどこに書いてあるか」を原文引用で記録する
  - 図表の説明文やキャプションの文字列も情報源として使う

■ STEP 2: 抽出した事実のみに基づいて全体像を構成する
  - STEP 1で抽出した事実だけを使い、ビジネスの概要を組み立てる
  - 文書にない情報を補完してはいけない
  - 事実が少ない場合は、少ないまま記述する（無理に膨らませない）

■ STEP 3: 事実に基づいて複数のビジネスモデル解釈を検討する
  - 同じ事実から、異なるセグメント分割・収益構造の解釈がありうる
  - 各解釈は文書の事実に基づくこと（空想のモデルを提案しない）
  - 3〜5つの合理的な解釈パターンを提案する
  - 各パターンの違いは「同じ事実をどう構造化するか」の違いであること

■ STEP 4: 各パターンを構造化する
  - 各解釈パターンごとに、セグメント分割・収益モデル・コスト構造を定義
  - revenue_driversのevidenceには必ず文書からの原文引用を入れる
  - 文書に記載のないドライバーは「文書に記載なし」と明記する

■ STEP 5: 財務ターゲットを抽出する
  - 文書に記載された売上目標・営業利益目標（年度別）を抽出する
  - 黒字化時期（単年黒字・累積黒字）の記載があれば抽出する
  - 計画期間（何年分か）を特定する
  - 文書に記載がない場合は空配列またはnullを返す（でっち上げない）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【出力ルール】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- proposals（パターン案）は必ず3件以上返すこと
- 各proposalのsegmentsは必ず1件以上
- evidenceフィールドは文書の原文を「」で囲んで引用すること
- 文書に記載がない項目のevidenceは「文書に記載なし」とすること
- estimated_valueは文書に数値がある場合のみ記入。ない場合はnullとする
- is_from_document: 文書から直接読み取った値はtrue、推定はfalse
- 日本語の数値表記を正規化: 億=×100,000,000、万=×10,000
- 有効なJSONのみを返す
"""

BM_ANALYZER_USER_PROMPT = """\
以下の事業計画書の文書テキストを読み、ビジネスモデルを分析してください。

【絶対ルール】
- 以下の文書テキストに書かれている内容だけを根拠として使うこと
- 文書にない情報を勝手に補完しないこと
- すべてのevidenceフィールドに文書からの原文引用を入れること

■ 事業計画書の文書テキスト:
---
{document_text}
---

■ 出力形式（JSON）:
{{
  "company_name": "文書に明記されている会社名（なければ「記載なし」）",
  "document_narrative": "文書から読み取れた事実だけに基づくビジネスの概要。文書に書いてあることだけを述べ、推測で補完しない。各主張の根拠を文書から示せること。",
  "key_facts": [
    "「〜〜」（原文引用）に基づく事実",
    "文書に明記された数値や情報のみ記載",
    "推定した場合は【推定】と明記し、推定根拠を付記"
  ],
  "proposals": [
    {{
      "label": "パターンA: [簡潔なモデル名]",
      "industry": "業種（文書から読み取れるもの）",
      "business_model_type": "B2B / B2C / B2B2C / marketplace / etc.",
      "executive_summary": "文書の事実に基づくこの解釈の要約（1-3文）",
      "diagram": "テキストベースのビジネスモデル図解。\\n[顧客] --課金方法--> [サービス] --収益--> [売上]\\n矢印(-->)、ボックス([])、パイプ(|)を使ってフローを表現する。",
      "segments": [
        {{
          "name": "セグメント名（文書に基づく）",
          "model_type": "subscription / transaction / project / marketplace / license / advertising / freemium / etc.",
          "revenue_formula": "売上 = ドライバー1 × ドライバー2 × ...",
          "revenue_drivers": [
            {{
              "name": "ドライバー名",
              "description": "説明",
              "unit": "単位",
              "estimated_value": "文書に記載の値（なければnull）",
              "evidence": "「文書からの原文引用」（なければ「文書に記載なし」）",
              "is_from_document": true
            }}
          ],
          "key_assumptions": ["文書に基づく前提"]
        }}
      ],
      "shared_costs": [
        {{
          "name": "コスト名",
          "category": "fixed / variable",
          "description": "説明",
          "estimated_value": "文書に記載の値（なければnull）",
          "evidence": "「文書からの原文引用」（なければ「文書に記載なし」）",
          "is_from_document": true
        }}
      ],
      "growth_trajectory": "文書に記載の成長計画・見通し（なければ「文書に記載なし」）",
      "risk_factors": ["文書に記載のリスク要因"],
      "time_horizon": "文書に記載の計画期間（なければ「文書に記載なし」）",
      "confidence": 0.8,
      "reasoning": "文書のどの記述からこの解釈が導かれるかの説明"
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
  "financial_targets": {{
    "horizon_years": 5,
    "revenue_targets": [
      {{"year": "FY1", "value": 10000000, "evidence": "「文書からの原文引用」", "source": "document"}},
      {{"year": "FY2", "value": null, "evidence": "文書に記載なし", "source": "default"}}
    ],
    "op_targets": [
      {{"year": "FY1", "value": -5000000, "evidence": "「文書からの原文引用」", "source": "document"}}
    ],
    "single_year_breakeven": {{"year": "FY3", "evidence": "「3年目に単月黒字化」", "source": "document"}},
    "cumulative_breakeven": {{"year": "FY5", "evidence": "「5年目に累積黒字」", "source": "document"}}
  }},
  "currency": "JPY"
}}

【注意】
- proposalsは必ず3〜5件。少なすぎても多すぎてもいけない。
- 各proposalは完全に独立した1つの解釈（セグメント構成が異なりうる）。
- confidenceの高い順に並べる。
- document_narrativeは文書の事実に基づく。文書にない情報を補完してはいけない。
- evidenceフィールドには必ず文書からの「原文引用」を入れること。推測の場合は「文書に記載なし・【推定】〜」と記載。
- financial_targets: 文書に売上目標・利益目標・黒字化時期の記載があれば抽出する。なければ空配列/nullを返す。数値は円単位に正規化（億→×1億、万→×1万）。
"""


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class BusinessModelAnalyzer:
    """Agent 1: Analyzes a business plan with anti-hallucination safeguards.

    Grounding principles:
    1. Every fact must cite the source document
    2. Missing information is stated honestly, not fabricated
    3. Post-hoc grounding validation checks evidence against document
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
            Grounded analysis with narrative and 3-5 proposals.

        Raises
        ------
        RuntimeError
            If the LLM returns an empty or unusable response.
        """
        if not document_text or not document_text.strip():
            raise RuntimeError("事業計画書のテキストが空です。PDFが正しく読み取れているか確認してください。")

        # Smart truncation: preserve start + end of document
        truncated = self._smart_truncate(document_text)

        user_content = self._user_prompt.format(document_text=truncated)

        if feedback:
            user_content += (
                f"\n\n━━━ ユーザーフィードバック ━━━\n"
                f"{feedback}\n\n"
                f"上記のフィードバックを考慮して、分析を修正してください。"
                f"ただし文書に基づくことは維持してください。"
            )

        messages = [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": user_content},
        ]

        logger.info("BusinessModelAnalyzer: sending document (%d chars, original %d) to LLM",
                     len(truncated), len(document_text))
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

        analysis = self._parse_result(result)

        # Post-hoc grounding validation
        analysis = self._validate_grounding(analysis, document_text)

        return analysis

    @staticmethod
    def _smart_truncate(text: str, max_chars: int = 30000) -> str:
        """Smart truncation that preserves start and end of document.

        Instead of blindly cutting at max_chars, this keeps:
        - First 70% of budget: beginning of document (usually most important)
        - Last 30% of budget: end of document (often contains financials, plans)
        - Middle section noted as omitted

        This ensures key sections at both ends are preserved.
        """
        if len(text) <= max_chars:
            return text

        head_budget = int(max_chars * 0.7)
        tail_budget = int(max_chars * 0.25)
        # Reserve ~5% for the separator message
        omitted_chars = len(text) - head_budget - tail_budget

        head = text[:head_budget]
        tail = text[-tail_budget:]

        separator = (
            f"\n\n[... 中間部分 約{omitted_chars:,}文字を省略 "
            f"(全{len(text):,}文字中、先頭{head_budget:,}文字+末尾{tail_budget:,}文字を分析) ...]\n\n"
        )

        return head + separator + tail

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

        # Parse financial targets
        ft = self._parse_financial_targets(raw.get("financial_targets"))

        # Build initial analysis with first proposal selected
        analysis = BusinessModelAnalysis(
            company_name=raw.get("company_name", ""),
            document_narrative=raw.get("document_narrative", ""),
            key_facts=raw.get("key_facts", []),
            proposals=proposals,
            selected_index=0,
            currency=raw.get("currency", "JPY"),
            raw_json=raw,
            financial_targets=ft,
        )

        # Auto-select first proposal to populate main fields
        if proposals:
            analysis = analysis.select_proposal(0)

        return analysis

    @staticmethod
    def _parse_financial_targets(ft_raw: Optional[Dict[str, Any]]) -> Optional[FinancialTargets]:
        """Parse financial_targets from LLM response."""
        if not ft_raw or not isinstance(ft_raw, dict):
            return None
        try:
            rev_targets = []
            for rt in ft_raw.get("revenue_targets", []):
                if isinstance(rt, dict):
                    rev_targets.append(YearTarget(
                        year=str(rt.get("year", "")),
                        value=rt.get("value"),
                        evidence=str(rt.get("evidence", "")),
                        source=str(rt.get("source", "document")),
                    ))

            op_targets = []
            for ot in ft_raw.get("op_targets", []):
                if isinstance(ot, dict):
                    op_targets.append(YearTarget(
                        year=str(ot.get("year", "")),
                        value=ot.get("value"),
                        evidence=str(ot.get("evidence", "")),
                        source=str(ot.get("source", "document")),
                    ))

            sy_be = None
            sy_raw = ft_raw.get("single_year_breakeven")
            if isinstance(sy_raw, dict) and sy_raw.get("year"):
                sy_be = BreakevenTarget(
                    year=str(sy_raw.get("year", "")),
                    evidence=str(sy_raw.get("evidence", "")),
                    source=str(sy_raw.get("source", "document")),
                )

            cum_be = None
            cum_raw = ft_raw.get("cumulative_breakeven")
            if isinstance(cum_raw, dict) and cum_raw.get("year"):
                cum_be = BreakevenTarget(
                    year=str(cum_raw.get("year", "")),
                    evidence=str(cum_raw.get("evidence", "")),
                    source=str(cum_raw.get("source", "document")),
                )

            return FinancialTargets(
                horizon_years=int(ft_raw.get("horizon_years") or 5),
                revenue_targets=rev_targets,
                op_targets=op_targets,
                single_year_breakeven=sy_be,
                cumulative_breakeven=cum_be,
            )
        except Exception as e:
            logger.warning("Failed to parse financial_targets: %s", e)
            return None

    @staticmethod
    def _validate_grounding(
        analysis: BusinessModelAnalysis,
        document_text: str,
    ) -> BusinessModelAnalysis:
        """Post-hoc grounding validation.

        Checks how well the LLM's output is grounded in the actual document.
        Calculates a grounding_score for each proposal based on how many
        evidence fields actually match text found in the document.
        """
        doc_lower = document_text.lower()

        for proposal in analysis.proposals:
            total_evidence = 0
            grounded_evidence = 0

            for seg in proposal.segments:
                for driver in seg.revenue_drivers:
                    if driver.evidence and driver.evidence != "文書に記載なし":
                        total_evidence += 1
                        # Extract quoted text from evidence (between 「」)
                        quotes = re.findall(r'「(.+?)」', driver.evidence)
                        if quotes:
                            for quote in quotes:
                                if quote.lower() in doc_lower:
                                    grounded_evidence += 1
                                    driver.is_from_document = True
                                    break
                            else:
                                driver.is_from_document = False
                                logger.warning(
                                    "Grounding check: evidence quote not found in document: %s",
                                    driver.evidence[:80],
                                )
                        else:
                            # No quoted text — check if evidence text appears
                            evidence_snippet = driver.evidence[:30]
                            if evidence_snippet.lower() in doc_lower:
                                grounded_evidence += 1
                                driver.is_from_document = True
                            else:
                                driver.is_from_document = False

            for cost in proposal.shared_costs:
                if cost.evidence and cost.evidence != "文書に記載なし":
                    total_evidence += 1
                    quotes = re.findall(r'「(.+?)」', cost.evidence)
                    if quotes:
                        for quote in quotes:
                            if quote.lower() in doc_lower:
                                grounded_evidence += 1
                                cost.is_from_document = True
                                break
                        else:
                            cost.is_from_document = False
                    else:
                        evidence_snippet = cost.evidence[:30]
                        if evidence_snippet.lower() in doc_lower:
                            grounded_evidence += 1
                            cost.is_from_document = True
                        else:
                            cost.is_from_document = False

            # Calculate grounding score
            if total_evidence > 0:
                proposal.grounding_score = grounded_evidence / total_evidence
            else:
                proposal.grounding_score = 0.0

            # Penalize confidence if grounding is low
            if proposal.grounding_score < 0.5:
                original_conf = proposal.confidence
                proposal.confidence = min(
                    proposal.confidence,
                    proposal.grounding_score + 0.1,
                )
                if proposal.confidence != original_conf:
                    logger.info(
                        "Grounding penalty: %s confidence %.2f -> %.2f (grounding=%.2f)",
                        proposal.label, original_conf, proposal.confidence, proposal.grounding_score,
                    )

        # Also validate company name
        if analysis.company_name and analysis.company_name not in ("記載なし", ""):
            if analysis.company_name not in document_text:
                logger.warning(
                    "Grounding check: company_name '%s' not found in document text",
                    analysis.company_name,
                )

        # Re-sort by confidence (may have changed after penalties)
        analysis.proposals.sort(key=lambda p: p.confidence, reverse=True)

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
                    is_from_document=d.get("is_from_document", False),
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
                is_from_document=c.get("is_from_document", False),
            ))
        return costs
