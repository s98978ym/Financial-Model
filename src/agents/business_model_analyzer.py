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


class RDThemeItem(BaseModel):
    """A single R&D development theme category with sub-items."""
    name: str = Field(description="e.g. 'アカデミーサービス', 'ミールサービス', '共通'")
    items: List[str] = Field(default_factory=list, description="e.g. ['栄養士DX化', 'コンテンツ高度化']")


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

    # --- R&D development themes (v2) ---
    rd_themes: List[RDThemeItem] = Field(default_factory=list, description="Development cost themes extracted from document")

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
            "rd_themes": [t.model_dump() for t in self.rd_themes],
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
            rd_themes=self.rd_themes,
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
  - 2〜3つの合理的な解釈パターンを提案する（速度重視）
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

■ STEP 6: 開発費テーマ（rd_themes）を抽出する
  - 文書に記載された開発投資・システム開発・技術投資の項目を抽出する
  - 事業ライン別（サービス別）の開発テーマをグルーピングする
  - 各事業ラインに紐づく具体的な開発項目（DX化、システム構築等）を列挙する
  - 複数サービスに共通する開発（CS基盤、共通インフラ等）は「共通」カテゴリにまとめる
  - 文書に開発費の記載がない場合は空配列を返す（でっち上げない）
  - 出力形式: [{"name": "事業ライン名", "items": ["開発テーマ1", "開発テーマ2"]}]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【出力ルール】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- proposals（パターン案）は2〜3件返すこと（速度重視で簡潔に）
- 各proposalのsegmentsは必ず1件以上
- evidenceフィールドは文書の原文を「」で囲んで引用すること
- 文書に記載がない項目のevidenceは「文書に記載なし」とすること
- estimated_valueは文書に数値がある場合のみ記入。ない場合はnullとする
- is_from_document: 文書から直接読み取った値はtrue、推定はfalse
- 日本語の数値表記を正規化: 億=×100,000,000、万=×10,000
- 有効なJSONのみを返す
"""

BM_ANALYZER_USER_PROMPT = """\
以下の事業計画書を読み、ビジネスモデルを分析してください。

■ 事業計画書:
---
{document_text}
---

■ 出力JSON形式:
{{
  "company_name": "会社名（文書に明記なければ「記載なし」）",
  "document_narrative": "文書の事実のみに基づくビジネス概要",
  "key_facts": ["「原文引用」に基づく事実（推定は【推定】と明記）"],
  "proposals": [
    {{
      "label": "パターンA: [モデル名]",
      "industry": "業種",
      "business_model_type": "B2B/B2C/B2B2C/marketplace等",
      "executive_summary": "この解釈の要約（1-3文）",
      "diagram": "[顧客]--課金-->[サービス]--収益-->[売上]",
      "segments": [
        {{
          "name": "セグメント名",
          "model_type": "subscription/transaction/project/marketplace/license/advertising/freemium等",
          "revenue_formula": "売上 = ドライバー1 × ドライバー2",
          "revenue_drivers": [
            {{"name": "名前", "description": "説明", "unit": "単位", "estimated_value": "文書記載値またはnull", "evidence": "「原文引用」または「文書に記載なし」", "is_from_document": true}}
          ],
          "key_assumptions": ["前提"]
        }}
      ],
      "shared_costs": [
        {{"name": "コスト名", "category": "fixed/variable", "description": "説明", "estimated_value": "文書記載値またはnull", "evidence": "「原文引用」または「文書に記載なし」", "is_from_document": true}}
      ],
      "growth_trajectory": "成長計画（なければ「文書に記載なし」）",
      "risk_factors": ["リスク要因"],
      "time_horizon": "計画期間（なければ「文書に記載なし」）",
      "confidence": 0.8,
      "reasoning": "この解釈の根拠"
    }}
  ],
  "financial_targets": {{
    "horizon_years": 5,
    "revenue_targets": [{{"year": "FY1", "value": 10000000, "evidence": "「原文引用」", "source": "document"}}],
    "op_targets": [{{"year": "FY1", "value": -5000000, "evidence": "「原文引用」", "source": "document"}}],
    "single_year_breakeven": {{"year": "FY3", "evidence": "「3年目に単月黒字化」", "source": "document"}},
    "cumulative_breakeven": {{"year": "FY5", "evidence": "「5年目に累積黒字」", "source": "document"}}
  }},
  "rd_themes": [
    {{"name": "事業ライン名（例: アカデミーサービス）", "items": ["開発テーマ1（例: 栄養士DX化）", "開発テーマ2"]}},
    {{"name": "共通", "items": ["CSシステム構築"]}}
  ],
  "currency": "JPY"
}}

proposalsは2〜3件（速度重視、簡潔に）。各proposalは独立した解釈。confidenceの高い順に並べる。financial_targetsは文書に記載があれば抽出、なければ空配列/null。数値は円単位に正規化（億→×1億、万→×1万）。rd_themesは文書に開発費・システム投資の記載があればサービス別にグルーピングして抽出、なければ空配列。
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

    def analyze(self, document_text: str, feedback: str = "", progress_callback=None) -> BusinessModelAnalysis:
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
        from core.providers.base import LLMConfig
        extract_kwargs: dict = {
            "config": LLMConfig(max_tokens=12288),
        }
        if progress_callback is not None:
            extract_kwargs["progress_callback"] = progress_callback
        result = self.llm.extract(messages, **extract_kwargs)
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

        # Fallback: if LLM returned data but no proposals, create one from available fields
        if result and not result.get("proposals"):
            logger.warning(
                "BusinessModelAnalyzer: LLM returned no proposals (keys=%s). "
                "Creating fallback proposal from available data.",
                list(result.keys()),
            )
            result = self._create_fallback_proposal(result)

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
    def _smart_truncate(text: str, max_chars: int = 20000) -> str:
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

    @staticmethod
    def _create_fallback_proposal(raw: Dict[str, Any]) -> Dict[str, Any]:
        """Create a single fallback proposal when LLM omits proposals entirely.

        This handles the case where the LLM returns company_name, document_narrative,
        key_facts etc. but fails to include the proposals array.
        """
        # Try to extract any useful structural info from the response
        industry = raw.get("industry", "")
        bm_type = raw.get("business_model_type", "")
        narrative = raw.get("document_narrative", "") or raw.get("executive_summary", "")
        company = raw.get("company_name", "")

        label_suffix = industry or bm_type or company or "自動生成"

        proposal = {
            "label": f"パターンA: {label_suffix}",
            "industry": industry,
            "business_model_type": bm_type,
            "executive_summary": narrative[:300] if narrative else "文書から構造を自動推定",
            "segments": raw.get("segments", []) or [{
                "name": "メインセグメント",
                "model_type": "unknown",
                "revenue_formula": "要確認",
                "revenue_drivers": [],
                "key_assumptions": [],
            }],
            "shared_costs": raw.get("shared_costs", []),
            "growth_trajectory": raw.get("growth_trajectory", ""),
            "risk_factors": raw.get("risk_factors", []),
            "time_horizon": raw.get("time_horizon", ""),
            "confidence": 0.4,
            "reasoning": "LLMがproposals形式で返さなかったため、利用可能なデータからフォールバック生成",
        }
        return {
            **raw,
            "proposals": [proposal],
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

        # Parse R&D development themes
        rd_themes = self._parse_rd_themes(raw.get("rd_themes"))

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
            rd_themes=rd_themes,
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
    def _parse_rd_themes(rd_raw: Optional[List[Dict[str, Any]]]) -> List[RDThemeItem]:
        """Parse rd_themes from LLM response."""
        if not rd_raw or not isinstance(rd_raw, list):
            return []
        themes = []
        for item in rd_raw:
            if not isinstance(item, dict):
                continue
            name = item.get("name", "")
            items = item.get("items", [])
            if not name:
                continue
            # Ensure items are strings
            items = [str(i) for i in items if i]
            if items:
                themes.append(RDThemeItem(name=name, items=items))
        return themes

    # Pre-compiled pattern for extracting quoted text (「…」)
    _QUOTE_RE = re.compile(r'「(.+?)」')

    @staticmethod
    def _check_evidence(evidence: str, doc_lower: str) -> bool:
        """Check if an evidence string is grounded in the document.

        Returns True if grounded, False otherwise.
        """
        quotes = BusinessModelAnalyzer._QUOTE_RE.findall(evidence)
        if quotes:
            for quote in quotes:
                if quote.lower() in doc_lower:
                    return True
            return False
        # No quoted text — check if first 30 chars of evidence appear
        return evidence[:30].lower() in doc_lower

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
        _check = BusinessModelAnalyzer._check_evidence

        for proposal in analysis.proposals:
            total_evidence = 0
            grounded_evidence = 0

            # Check drivers and costs in a single pass
            evidence_items = []
            for seg in proposal.segments:
                for driver in seg.revenue_drivers:
                    evidence_items.append(driver)
            for cost in proposal.shared_costs:
                evidence_items.append(cost)

            for item in evidence_items:
                if not item.evidence or item.evidence == "文書に記載なし":
                    continue
                total_evidence += 1
                if _check(item.evidence, doc_lower):
                    grounded_evidence += 1
                    item.is_from_document = True
                else:
                    item.is_from_document = False

            # Calculate grounding score
            proposal.grounding_score = (grounded_evidence / total_evidence) if total_evidence > 0 else 0.0

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
