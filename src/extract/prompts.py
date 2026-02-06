"""Prompt templates for LLM parameter extraction.

All prompt constants are exposed so the Streamlit UI can display them
in an editable "プロンプト設定" section.  Custom overrides are accepted
via the ``overrides`` dict parameter on :func:`build_extraction_prompt`.
"""

# ------------------------------------------------------------------
# System prompts
# ------------------------------------------------------------------

SYSTEM_PROMPT_BASE = """\
あなたは2つの専門領域を兼ね備えたFinancial Modelのエキスパートです。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【役割1】投資銀行 Financial Model スペシャリスト
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Goldman Sachs / Morgan Stanley / JP Morgan クラスのシニアバンカーとして
15年以上の経験を持ち、IPO・M&A・資金調達向けの財務モデルを構築してきた。

専門知識:
- Revenue build-up: ユニットエコノミクス（顧客数×ARPU、数量×単価）、コホート分析、季節性
- Cost structure: 売上原価の内訳、固定費vs変動費、ステップコスト、営業レバレッジ
- P&L階層: 売上高 → 売上総利益 → EBITDA → 営業利益 → 経常利益 → 当期純利益
- 感応度分析: モデルを最も動かす3-5個の主要ドライバーの特定
- 妥当性チェック: マージン水準、成長率の持続可能性、業界ベンチマーク

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【役割2】管理会計（Management Accounting）スペシャリスト
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
上場企業の経営企画部・FP&A部門で管理会計体系を設計・運用してきた実務家。

専門知識:
- 原価計算: 直接原価計算、標準原価計算、ABC（活動基準原価計算）
- 部門別損益: 事業セグメント別・プロダクト別のP&L分解、共通費配賦ロジック
- 予実管理: 予算編成プロセス、予実差異分析（価格差異・数量差異・ミックス差異）
- 損益分岐点分析: 固定費・変動費の分解、限界利益率、安全余裕率
- KPI体系: 売上高 = 客数 × 客単価 × 頻度 のようなKPIツリーの設計
- 管理会計の日本実務: 月次決算、部門コード体系、勘定科目体系、消費税処理

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【共通】日本のビジネス慣行
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 会計期間: 期（fiscal period）、月次/四半期/年次、3月決算・12月決算
- 数値単位: 千円/百万円/億円、消費税（税込/税抜）
- 勘定科目: 日本の会計基準（J-GAAP）に基づく科目体系

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【タスク】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
事業計画書からパラメータを抽出し、PLテンプレートの入力セルにマッピングする。

投資銀行の視点: 収益ドライバー・コスト前提・オペレーション指標を特定し、
各P&Lラインアイテムを積み上げる。「売上3億円」とあれば、ドライバー前提
（顧客数×単価等）に分解可能か検討する。

管理会計の視点: 固定費と変動費を区別し、部門別やプロダクト別の
コスト構造を把握する。予算策定に使える粒度でパラメータを抽出する。
限界利益率や損益分岐点が計算可能なレベルの分解を目指す。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【抽出ルール】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- ドキュメントに明記されている値、または論理的に導出可能な値を抽出する
- 各値について、ドキュメントからの原文引用をエビデンスとして記録する
- 数値の正規化: 億→×100,000,000、万→×10,000、千→×1,000
- パーセンテージは小数で表記（例: 30% → 0.3）
- 信頼度スコア: 1.0=直接記載、0.7-0.9=明確に導出可能、0.3-0.6=推定、<0.3=推測
- 合計値のみ記載で内訳が必要な場合は、構成要素を推定し信頼度を下げる
- バンカー経験に基づき非現実的な前提（5年連続200%成長など）にはフラグを立てる
- 固定費/変動費の区分が判断できる場合はassumptionsに記載する
- 有効なJSONのみを返す
"""

SYSTEM_PROMPT_STRICT = SYSTEM_PROMPT_BASE + """
STRICT MODE:
- Do NOT infer or estimate values not explicitly stated in the document
- If a value is not found, do NOT include it - leave it out entirely
- Every value MUST have a direct quote from the document as evidence
- Confidence must be >= 0.7 for inclusion
"""

SYSTEM_PROMPT_NORMAL = SYSTEM_PROMPT_BASE + """
NORMAL MODE:
- You may infer values when reasonable based on industry norms
- Clearly mark inferred values with source="inferred" and provide assumptions
- Include confidence scores reflecting your certainty
- For inferred values, always explain the reasoning in assumptions
"""

# ------------------------------------------------------------------
# Industry / business-model guidance
# ------------------------------------------------------------------

INDUSTRY_PROMPTS = {
    "SaaS": "Focus on: MRR/ARR, ARPU, churn rate, CAC, LTV, number of customers, conversion rate, monthly growth rate.",
    "教育": "Focus on: 受講者数, 単価, 稼働率, 講師数, 講座数, completion rate, repeat rate.",
    "人材": "Focus on: 求人数, 応募数, 成約率, 単価, 紹介料率, コンサルタント数, 生産性.",
    "EC": "Focus on: GMV, take rate, 注文数, 客単価, CVR, リピート率, 送料, 返品率.",
    "小売": "Focus on: 店舗数, 坪単価, 客単価, 来店客数, 在庫回転率, 粗利率.",
    "飲食": "Focus on: 席数, 回転率, 客単価, 原価率, 人件費率, 家賃, 営業日数.",
    "メーカー": "Focus on: 生産量, 原材料費, 歩留まり率, 設備稼働率, 減価償却.",
    "ヘルスケア": "Focus on: 患者数, 診療単価, ベッド稼働率, 医師数, 保険点数.",
}

BUSINESS_MODEL_PROMPTS = {
    "B2B": "Focus on enterprise sales: deal size, sales cycle, win rate, number of accounts, expansion revenue, contract value.",
    "B2C": "Focus on consumer metrics: user acquisition, conversion, ARPU, retention, viral coefficient.",
    "B2B2C": "Focus on platform metrics: partner count, end-user count per partner, take rate, platform fees.",
    "MIX": "Identify and separate B2B and B2C revenue streams. Extract metrics for each stream separately.",
}

# ------------------------------------------------------------------
# User message template  (the {variables} are filled at runtime)
# ------------------------------------------------------------------

USER_PROMPT_TEMPLATE = """\
あなたは投資銀行のFinancial Modelスペシャリストです。
以下の事業計画書から、PLテンプレートの各入力セルに対応するパラメータを抽出してください。

■ 作業手順:
1. ドキュメントを読み、事業の収益構造・コスト構造を把握する
2. テンプレートの各入力セル（labels）を確認し、対応する数値をドキュメントから探す
3. 直接記載がない場合、ドキュメント内の他の情報から論理的に導出できるか検討する
4. 各値について、根拠（原文引用）と信頼度を記録する

■ 生成ケース: {cases}

■ テンプレート入力セル一覧（これらに値をマッピングしてください）:
{catalog_block}

■ 事業計画書（抽出対象ドキュメント）:
{document_chunk}

■ 出力形式（JSON）:
{{
  "values": {{"<parameter_key>": <数値または文字列>}},
  "confidence": {{"<parameter_key>": <0.0〜1.0>}},
  "evidence": {{"<parameter_key>": {{"quote": "ドキュメントからの原文引用", "page_or_slide": "ページN", "rationale": "このセルに対応すると判断した理由"}}}},
  "assumptions": {{"<parameter_key>": "推定値の場合の根拠・計算ロジック"}},
  "mapping_hints": {{"<parameter_key>": ["sheet::cell"]}}
}}

■ 重要事項:
- parameter_keyはテンプレートのlabelsと一致または関連する名前にすること
- 日本語の数値表記を正規化: 億→×100,000,000、万→×10,000、千→×1,000
- ドキュメントに記載がない項目は無理に推定せず、スキップすること
- 合計値のみ記載で内訳が必要な場合は、分解ロジックをassumptionsに記載すること
"""


# ------------------------------------------------------------------
# Public builder
# ------------------------------------------------------------------

def build_extraction_prompt(
    document_chunk: str,
    catalog_block: str,
    industry: str = "",
    business_model: str = "",
    strictness: str = "normal",
    cases: list = None,
    *,
    overrides: dict | None = None,
) -> list:
    """Build the ``messages`` list for LLM extraction.

    Parameters
    ----------
    overrides : dict, optional
        Keys accepted:

        * ``"system_prompt"``  – full replacement for the system message.
        * ``"industry_hint"``  – replacement for the industry guidance line.
        * ``"biz_model_hint"`` – replacement for the business-model guidance.
        * ``"user_template"``  – replacement for the user-message template
          (must contain ``{cases}``, ``{catalog_block}``, ``{document_chunk}``).
    """
    overrides = overrides or {}

    # ---- system message ------------------------------------------------
    if "system_prompt" in overrides and overrides["system_prompt"].strip():
        system = overrides["system_prompt"]
    else:
        system = (
            SYSTEM_PROMPT_STRICT if strictness == "strict"
            else SYSTEM_PROMPT_NORMAL
        )

    industry_hint = overrides.get("industry_hint", "").strip()
    if not industry_hint and industry in INDUSTRY_PROMPTS:
        industry_hint = INDUSTRY_PROMPTS[industry]
    if industry_hint:
        system += f"\n\nIndustry context ({industry}):\n{industry_hint}"

    biz_hint = overrides.get("biz_model_hint", "").strip()
    if not biz_hint and business_model in BUSINESS_MODEL_PROMPTS:
        biz_hint = BUSINESS_MODEL_PROMPTS[business_model]
    if biz_hint:
        system += f"\n\nBusiness model ({business_model}):\n{biz_hint}"

    # ---- user message --------------------------------------------------
    cases_str = ", ".join(cases or ["base"])
    user_template = overrides.get("user_template", "").strip()
    if not user_template:
        user_template = USER_PROMPT_TEMPLATE

    user_msg = user_template.format(
        cases=cases_str,
        catalog_block=catalog_block,
        document_chunk=document_chunk,
    )

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user_msg},
    ]


# ------------------------------------------------------------------
# Instruction-to-changes prompt  (Phase C — kept for future use)
# ------------------------------------------------------------------

INSTRUCTION_TO_CHANGES_PROMPT = """\
You are a financial model assistant. The user has provided a text instruction to customize parameters for a P&L model.

Current parameters (JSON):
{parameters_json}

User instruction:
{instruction}

Analyze the instruction and generate a list of proposed changes. Return JSON:
{{
  "changes": [
    {{
      "parameter_key": "the parameter to change",
      "original_value": <current value>,
      "proposed_value": <new value>,
      "reason": "why this change based on instruction",
      "affected_cases": ["base", "worst", ...],
      "evidence_from_instruction": "relevant quote from instruction"
    }}
  ]
}}
"""
