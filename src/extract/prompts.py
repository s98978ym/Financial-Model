"""Prompt templates for LLM parameter extraction."""

SYSTEM_PROMPT_BASE = """You are a financial analyst AI that extracts business parameters from planning documents.
You extract numerical values, growth rates, costs, and other business metrics that can be mapped to a P&L model.

IMPORTANT RULES:
- Extract ONLY values explicitly stated or clearly derivable from the document
- For each value, provide the exact quote from the document as evidence
- Normalize all numbers: 億→multiply by 100000000, 万→multiply by 10000, etc.
- Percentages should be expressed as decimals (e.g., 30% → 0.3)
- Confidence score: 1.0 = directly stated, 0.7-0.9 = clearly derivable, 0.3-0.6 = inferred, <0.3 = guessed
- Return valid JSON only
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

# Industry-specific extraction guidance
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

def build_extraction_prompt(
    document_chunk: str,
    catalog_block: str,  # JSON of catalog items for this block
    industry: str = "",
    business_model: str = "",
    strictness: str = "normal",
    cases: list = None,
) -> list:
    """Build the messages list for LLM extraction."""
    # Combine system prompt based on strictness
    system = SYSTEM_PROMPT_STRICT if strictness == "strict" else SYSTEM_PROMPT_NORMAL

    if industry in INDUSTRY_PROMPTS:
        system += f"\n\nIndustry context ({industry}):\n{INDUSTRY_PROMPTS[industry]}"
    if business_model in BUSINESS_MODEL_PROMPTS:
        system += f"\n\nBusiness model ({business_model}):\n{BUSINESS_MODEL_PROMPTS[business_model]}"

    cases_str = ", ".join(cases or ["base"])

    user_msg = f"""Extract business parameters from the following document section.
Map them to the template input cells listed below.

TARGET CASES: {cases_str}

TEMPLATE INPUT CELLS (catalog):
{catalog_block}

DOCUMENT SECTION:
{document_chunk}

Return a JSON object with this exact structure:
{{
  "values": {{"<parameter_key>": <number_or_string>}},
  "confidence": {{"<parameter_key>": <0.0-1.0>}},
  "evidence": {{"<parameter_key>": {{"quote": "exact text from document", "page_or_slide": "page N", "rationale": "why this maps to the parameter"}}}},
  "assumptions": {{"<parameter_key>": "reasoning for inferred values"}},
  "mapping_hints": {{"<parameter_key>": ["sheet::cell suggestions"]}}
}}

IMPORTANT: parameter_key should match or relate to the catalog cell labels. Normalize Japanese numbers (億/万/千).
"""

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user_msg}
    ]


INSTRUCTION_TO_CHANGES_PROMPT = """You are a financial model assistant. The user has provided a text instruction to customize parameters for a P&L model.

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
