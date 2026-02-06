"""
PL Generator - Industry-Specific Configuration
===============================================

Provides lookup dictionaries that guide the LLM extraction and mapping
phases with industry-aware synonym resolution, priority ordering, and
business-model hints.

Three main data structures:

* **INDUSTRY_SYNONYMS** -- maps each industry label to a dict of
  ``canonical_key -> list[synonym]``.  Used during Phase B extraction so
  the LLM (and fuzzy-matching post-processor) can recognise domain jargon
  in both Japanese and English.

* **INDUSTRY_PRIORITY_PARAMS** -- ordered list of parameter keys that
  should be extracted first for a given industry.  The LLM prompt is
  constructed to emphasise these.

* **BUSINESS_MODEL_HINTS** -- extraction-time hints keyed by business
  model (B2B, B2C, …).  Each hint tells the LLM what revenue / cost
  patterns to expect.
"""

from __future__ import annotations

from typing import Dict, List, Optional


# ====================================================================
# 1.  Industry Synonyms
# ====================================================================
# Structure:  industry -> { canonical_key: [synonym, ...] }
#
# - canonical_key is the English snake_case name used in
#   ExtractedParameter.key
# - synonyms include both Japanese labels and common English aliases
# ====================================================================

INDUSTRY_SYNONYMS: Dict[str, Dict[str, List[str]]] = {
    # ----------------------------------------------------------------
    # SaaS
    # ----------------------------------------------------------------
    "SaaS": {
        "arpu": [
            "客単価",
            "ARPU",
            "average revenue per user",
            "平均単価",
            "ユーザー単価",
            "月額単価",
            "average revenue per account",
            "ARPA",
        ],
        "churn_rate": [
            "解約率",
            "churn rate",
            "チャーンレート",
            "月次解約率",
            "monthly churn",
            "離脱率",
            "退会率",
        ],
        "mrr": [
            "月次経常収益",
            "MRR",
            "monthly recurring revenue",
            "月額売上",
            "月次定額売上",
        ],
        "arr": [
            "年次経常収益",
            "ARR",
            "annual recurring revenue",
            "年間売上",
        ],
        "cac": [
            "顧客獲得コスト",
            "CAC",
            "customer acquisition cost",
            "獲得単価",
            "CPA",
        ],
        "ltv": [
            "顧客生涯価値",
            "LTV",
            "lifetime value",
            "ライフタイムバリュー",
            "CLV",
            "customer lifetime value",
        ],
        "nrr": [
            "NRR",
            "net revenue retention",
            "ネットレベニューリテンション",
            "売上維持率",
        ],
        "paying_users": [
            "課金ユーザー数",
            "有料ユーザー数",
            "paying customers",
            "有料会員数",
            "契約社数",
            "アカウント数",
        ],
        "expansion_rate": [
            "エクスパンション率",
            "expansion revenue rate",
            "アップセル率",
            "拡大率",
        ],
        "server_cost": [
            "サーバーコスト",
            "インフラコスト",
            "AWS費用",
            "クラウド費用",
            "hosting cost",
        ],
    },

    # ----------------------------------------------------------------
    # 教育
    # ----------------------------------------------------------------
    "教育": {
        "students": [
            "生徒数",
            "受講生数",
            "学生数",
            "受講者数",
            "enrollment",
            "在籍者数",
        ],
        "tuition": [
            "授業料",
            "受講料",
            "学費",
            "tuition fee",
            "月謝",
            "受講費",
        ],
        "retention_rate": [
            "継続率",
            "retention rate",
            "リテンション率",
            "在籍継続率",
        ],
        "course_completion_rate": [
            "修了率",
            "completion rate",
            "完了率",
            "卒業率",
        ],
        "teachers": [
            "講師数",
            "教員数",
            "instructor count",
            "先生数",
            "チューター数",
        ],
        "teacher_cost": [
            "講師人件費",
            "教員人件費",
            "instructor cost",
            "講師報酬",
        ],
        "facility_cost": [
            "施設費",
            "教室費",
            "facility cost",
            "場所代",
            "スペース費用",
        ],
        "courses": [
            "コース数",
            "講座数",
            "クラス数",
            "course count",
            "プログラム数",
        ],
    },

    # ----------------------------------------------------------------
    # 人材
    # ----------------------------------------------------------------
    "人材": {
        "placements": [
            "成約件数",
            "紹介成約数",
            "placement count",
            "決定数",
            "成約数",
        ],
        "placement_fee": [
            "紹介手数料",
            "成功報酬",
            "placement fee",
            "フィー単価",
            "手数料単価",
        ],
        "fee_rate": [
            "手数料率",
            "フィー率",
            "fee rate",
            "成果報酬率",
        ],
        "candidates": [
            "候補者数",
            "求職者数",
            "candidate count",
            "登録者数",
            "エントリー数",
        ],
        "clients": [
            "求人企業数",
            "クライアント数",
            "client count",
            "取引先企業数",
        ],
        "conversion_rate": [
            "成約率",
            "conversion rate",
            "決定率",
            "コンバージョン率",
        ],
        "consultants": [
            "コンサルタント数",
            "キャリアアドバイザー数",
            "consultant count",
            "営業担当者数",
            "RA/CA数",
        ],
        "avg_annual_salary": [
            "平均年収",
            "平均想定年収",
            "average annual salary",
            "理論年収",
        ],
    },

    # ----------------------------------------------------------------
    # EC (E-Commerce)
    # ----------------------------------------------------------------
    "EC": {
        "gmv": [
            "流通総額",
            "GMV",
            "gross merchandise value",
            "取扱高",
        ],
        "orders": [
            "注文件数",
            "受注件数",
            "order count",
            "オーダー数",
        ],
        "aov": [
            "平均注文単価",
            "AOV",
            "average order value",
            "客単価",
            "注文単価",
        ],
        "take_rate": [
            "テイクレート",
            "take rate",
            "手数料率",
            "マージン率",
        ],
        "cogs": [
            "原価",
            "仕入原価",
            "COGS",
            "cost of goods sold",
            "売上原価",
            "商品原価",
        ],
        "shipping_cost": [
            "配送費",
            "送料",
            "shipping cost",
            "物流コスト",
            "運送費",
        ],
        "return_rate": [
            "返品率",
            "return rate",
            "キャンセル率",
        ],
        "customer_count": [
            "顧客数",
            "購入者数",
            "buyer count",
            "ユーザー数",
            "会員数",
        ],
        "repeat_rate": [
            "リピート率",
            "repeat purchase rate",
            "再購入率",
            "リピーター率",
        ],
    },

    # ----------------------------------------------------------------
    # 小売 (Retail)
    # ----------------------------------------------------------------
    "小売": {
        "stores": [
            "店舗数",
            "出店数",
            "store count",
            "拠点数",
        ],
        "revenue_per_store": [
            "店舗あたり売上",
            "revenue per store",
            "坪効率",
            "店あたり月商",
        ],
        "foot_traffic": [
            "来店客数",
            "来客数",
            "foot traffic",
            "入客数",
        ],
        "conversion_rate": [
            "購買率",
            "conversion rate",
            "買上率",
            "コンバージョン率",
        ],
        "basket_size": [
            "客単価",
            "basket size",
            "平均購入金額",
            "一人あたり購入額",
        ],
        "inventory_turnover": [
            "在庫回転率",
            "inventory turnover",
            "商品回転率",
        ],
        "rent_cost": [
            "賃料",
            "テナント料",
            "rent",
            "店舗賃借料",
            "家賃",
        ],
        "staff_per_store": [
            "店舗あたり人員",
            "staff per store",
            "スタッフ数",
        ],
    },

    # ----------------------------------------------------------------
    # 飲食 (Food & Beverage / Restaurant)
    # ----------------------------------------------------------------
    "飲食": {
        "stores": [
            "店舗数",
            "出店数",
            "store count",
            "拠点数",
        ],
        "seats": [
            "座席数",
            "席数",
            "seating capacity",
            "キャパシティ",
        ],
        "seat_turnover": [
            "回転率",
            "seat turnover",
            "テーブル回転率",
        ],
        "check_average": [
            "客単価",
            "average check",
            "一人あたり単価",
            "平均単価",
        ],
        "food_cost_ratio": [
            "原価率",
            "food cost ratio",
            "FL比率",
            "フードコスト率",
        ],
        "labor_cost_ratio": [
            "人件費率",
            "labor cost ratio",
            "レイバーコスト率",
        ],
        "occupancy_rate": [
            "稼働率",
            "occupancy rate",
            "座席稼働率",
        ],
        "rent_cost": [
            "賃料",
            "家賃",
            "rent",
            "店舗賃借料",
        ],
        "delivery_ratio": [
            "デリバリー比率",
            "delivery ratio",
            "テイクアウト比率",
        ],
    },

    # ----------------------------------------------------------------
    # メーカー (Manufacturing)
    # ----------------------------------------------------------------
    "メーカー": {
        "units_produced": [
            "生産数量",
            "production volume",
            "製造数量",
            "出荷数量",
        ],
        "unit_price": [
            "製品単価",
            "unit price",
            "販売単価",
            "平均販売価格",
            "ASP",
        ],
        "material_cost": [
            "原材料費",
            "material cost",
            "資材費",
            "部品費",
        ],
        "manufacturing_cost": [
            "製造原価",
            "manufacturing cost",
            "生産コスト",
            "加工費",
        ],
        "yield_rate": [
            "歩留まり率",
            "yield rate",
            "良品率",
        ],
        "capacity_utilization": [
            "稼働率",
            "capacity utilization",
            "設備稼働率",
            "ライン稼働率",
        ],
        "inventory_months": [
            "在庫月数",
            "months of inventory",
            "棚卸資産月数",
        ],
        "capex": [
            "設備投資",
            "CAPEX",
            "capital expenditure",
            "設備投資額",
        ],
        "depreciation": [
            "減価償却費",
            "depreciation",
            "償却費",
        ],
    },

    # ----------------------------------------------------------------
    # ヘルスケア (Healthcare)
    # ----------------------------------------------------------------
    "ヘルスケア": {
        "patients": [
            "患者数",
            "利用者数",
            "patient count",
            "受診者数",
            "会員数",
        ],
        "arpu": [
            "一人あたり単価",
            "ARPU",
            "average revenue per user",
            "利用者単価",
            "診療単価",
        ],
        "visits_per_patient": [
            "来院回数",
            "visits per patient",
            "受診回数",
            "利用回数",
        ],
        "practitioners": [
            "医師数",
            "専門家数",
            "practitioner count",
            "施術者数",
        ],
        "equipment_cost": [
            "機器費用",
            "equipment cost",
            "医療機器費",
            "設備リース料",
        ],
        "regulatory_cost": [
            "許認可費用",
            "regulatory cost",
            "薬事費用",
            "コンプライアンス費用",
        ],
        "insurance_revenue_ratio": [
            "保険適用比率",
            "insurance coverage ratio",
            "保険収入割合",
        ],
        "clinical_cost": [
            "臨床費用",
            "clinical cost",
            "治験費用",
            "研究開発費",
            "R&D費",
        ],
    },

    # ----------------------------------------------------------------
    # その他 (Other / generic)
    # ----------------------------------------------------------------
    "その他": {
        "revenue": [
            "売上高",
            "revenue",
            "売上",
            "トップライン",
            "sales",
        ],
        "cogs": [
            "売上原価",
            "COGS",
            "cost of goods sold",
            "原価",
        ],
        "gross_profit": [
            "粗利",
            "gross profit",
            "売上総利益",
            "粗利益",
        ],
        "operating_expense": [
            "販管費",
            "SGA",
            "operating expense",
            "営業費用",
            "販売費及び一般管理費",
        ],
        "operating_profit": [
            "営業利益",
            "operating profit",
            "営業損益",
        ],
        "headcount": [
            "人員数",
            "従業員数",
            "headcount",
            "社員数",
            "FTE",
        ],
        "salary": [
            "人件費",
            "給与",
            "salary",
            "給与手当",
            "報酬",
        ],
        "marketing_cost": [
            "広告宣伝費",
            "マーケティング費",
            "marketing cost",
            "販促費",
        ],
    },
}


# ====================================================================
# 2.  Industry Priority Parameters
# ====================================================================
# Ordered list of parameter keys to prioritise during extraction.
# The LLM prompt is constructed to ask for these first, ensuring the
# most critical inputs are not missed even under token-budget pressure.
# ====================================================================

INDUSTRY_PRIORITY_PARAMS: Dict[str, List[str]] = {
    "SaaS": [
        "mrr",
        "arr",
        "arpu",
        "paying_users",
        "churn_rate",
        "cac",
        "ltv",
        "nrr",
        "expansion_rate",
        "server_cost",
    ],
    "教育": [
        "students",
        "tuition",
        "retention_rate",
        "teachers",
        "teacher_cost",
        "courses",
        "course_completion_rate",
        "facility_cost",
    ],
    "人材": [
        "placements",
        "placement_fee",
        "fee_rate",
        "candidates",
        "clients",
        "conversion_rate",
        "consultants",
        "avg_annual_salary",
    ],
    "EC": [
        "gmv",
        "orders",
        "aov",
        "take_rate",
        "cogs",
        "customer_count",
        "repeat_rate",
        "shipping_cost",
        "return_rate",
    ],
    "小売": [
        "stores",
        "revenue_per_store",
        "foot_traffic",
        "conversion_rate",
        "basket_size",
        "rent_cost",
        "staff_per_store",
        "inventory_turnover",
    ],
    "飲食": [
        "stores",
        "seats",
        "seat_turnover",
        "check_average",
        "food_cost_ratio",
        "labor_cost_ratio",
        "occupancy_rate",
        "rent_cost",
        "delivery_ratio",
    ],
    "メーカー": [
        "units_produced",
        "unit_price",
        "material_cost",
        "manufacturing_cost",
        "yield_rate",
        "capacity_utilization",
        "capex",
        "depreciation",
        "inventory_months",
    ],
    "ヘルスケア": [
        "patients",
        "arpu",
        "visits_per_patient",
        "practitioners",
        "equipment_cost",
        "clinical_cost",
        "regulatory_cost",
        "insurance_revenue_ratio",
    ],
    "その他": [
        "revenue",
        "cogs",
        "gross_profit",
        "operating_expense",
        "operating_profit",
        "headcount",
        "salary",
        "marketing_cost",
    ],
}


# ====================================================================
# 3.  Business Model Hints
# ====================================================================
# Mapping from business model type to extraction guidance strings.
# Each entry provides contextual hints that are injected into the LLM
# extraction prompt so the model knows what revenue / cost patterns
# to look for.
# ====================================================================

BUSINESS_MODEL_HINTS: Dict[str, Dict[str, str]] = {
    "B2B": {
        "revenue_pattern": (
            "Revenue is typically contract-based with annual or multi-year "
            "terms.  Look for ARR/MRR, contract value, number of client "
            "companies, and average deal size.  Upsell / cross-sell and "
            "net revenue retention are important growth drivers."
        ),
        "cost_pattern": (
            "Cost structure is usually sales-heavy: enterprise sales team "
            "salaries, SDR/AE headcount, customer success managers.  "
            "Marketing spend is focused on events, content, and ABM.  "
            "Look for CAC and sales cycle length."
        ),
        "key_metrics": (
            "Key metrics: ARR, MRR, NRR, ACV (annual contract value), "
            "number of enterprise clients, CAC, LTV, LTV/CAC ratio, "
            "sales cycle length, logo churn vs revenue churn."
        ),
        "pricing_model": (
            "Pricing is often per-seat, per-usage, or tiered.  "
            "Look for seat count, usage volume, and tier breakdowns.  "
            "Discounting for annual prepay is common."
        ),
    },
    "B2C": {
        "revenue_pattern": (
            "Revenue driven by individual consumers.  Key drivers are "
            "total user base, conversion to paid, ARPU, and frequency "
            "of purchase.  Subscription and freemium models are common."
        ),
        "cost_pattern": (
            "Marketing and user acquisition dominate the cost structure.  "
            "Look for digital advertising spend (CPC/CPM), influencer "
            "costs, referral programme costs.  Variable costs scale with "
            "user count (infrastructure, support)."
        ),
        "key_metrics": (
            "Key metrics: MAU/DAU, conversion rate (free-to-paid), ARPU, "
            "churn rate, CAC, LTV, retention cohorts, "
            "app store ratings (if mobile)."
        ),
        "pricing_model": (
            "Pricing is typically subscription (monthly/annual), "
            "one-time purchase, or in-app purchase.  Free tier or trial "
            "is common.  Look for pricing tiers and upgrade rates."
        ),
    },
    "B2B2C": {
        "revenue_pattern": (
            "Dual revenue streams: platform fees from business partners "
            "AND consumer-facing revenue (transactions, subscriptions).  "
            "Look for both enterprise contract values and consumer "
            "transaction metrics (GMV, take rate)."
        ),
        "cost_pattern": (
            "Costs split between partner acquisition/management and "
            "consumer acquisition.  Platform infrastructure costs tend "
            "to be significant.  Look for both B2B sales costs and "
            "B2C marketing costs separately."
        ),
        "key_metrics": (
            "Key metrics: number of partner businesses, consumer users "
            "per partner, platform GMV, take rate, partner churn, "
            "consumer engagement metrics, blended CAC."
        ),
        "pricing_model": (
            "Pricing combines platform subscription for business partners "
            "with transaction-based or usage-based fees.  Revenue share "
            "and commission models are common."
        ),
    },
    "MIX": {
        "revenue_pattern": (
            "Multiple revenue models coexist (e.g. subscription + "
            "professional services + marketplace).  Each stream should "
            "be identified and modelled separately with its own drivers."
        ),
        "cost_pattern": (
            "Cost structure varies by revenue stream.  Look for "
            "segment-level cost breakdowns.  Shared costs (G&A, "
            "infrastructure) need allocation methodology."
        ),
        "key_metrics": (
            "Key metrics depend on each revenue stream.  Identify and "
            "extract metrics for each segment independently.  "
            "Blended metrics (overall CAC, blended margin) are also "
            "relevant."
        ),
        "pricing_model": (
            "Mixed pricing: combination of subscriptions, transactions, "
            "professional services (time & materials or fixed fee), "
            "and potentially licensing.  Extract each model separately."
        ),
    },
    "Other": {
        "revenue_pattern": (
            "Revenue model is non-standard or not clearly categorised.  "
            "Look for any description of how the company generates "
            "income and extract the core unit economics."
        ),
        "cost_pattern": (
            "Extract both fixed and variable cost components.  "
            "Look for headcount-driven costs, infrastructure costs, "
            "and any volume-dependent expenses."
        ),
        "key_metrics": (
            "Focus on universal financial metrics: revenue, gross margin, "
            "operating margin, headcount, burn rate, and runway."
        ),
        "pricing_model": (
            "Extract whatever pricing information is available.  "
            "Look for unit prices, fee structures, and discount policies."
        ),
    },
}


# ====================================================================
# Convenience lookup helpers
# ====================================================================


def get_synonyms(industry: str) -> Dict[str, List[str]]:
    """Return synonym dictionary for *industry*, falling back to その他."""
    return INDUSTRY_SYNONYMS.get(industry, INDUSTRY_SYNONYMS["その他"])


def get_priority_params(industry: str) -> List[str]:
    """Return ordered priority parameters for *industry*, falling back to その他."""
    return INDUSTRY_PRIORITY_PARAMS.get(industry, INDUSTRY_PRIORITY_PARAMS["その他"])


def get_business_model_hints(business_model: str) -> Dict[str, str]:
    """Return extraction hints for *business_model*, falling back to Other."""
    return BUSINESS_MODEL_HINTS.get(business_model, BUSINESS_MODEL_HINTS["Other"])


def find_canonical_key(industry: str, term: str) -> Optional[str]:
    """Reverse-lookup: given a Japanese/English *term*, find its canonical key.

    Performs case-insensitive matching across all synonyms for the given
    industry.  Returns ``None`` if no match is found.
    """
    synonyms = get_synonyms(industry)
    term_lower = term.lower().strip()
    for key, aliases in synonyms.items():
        if term_lower == key:
            return key
        for alias in aliases:
            if term_lower == alias.lower():
                return key
    return None


def all_industries() -> List[str]:
    """Return list of all supported industry labels."""
    return list(INDUSTRY_SYNONYMS.keys())
