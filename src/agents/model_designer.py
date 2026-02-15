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

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Output models
# ---------------------------------------------------------------------------

class CellAssignment(BaseModel):
    """Maps a template cell to a business concept."""
    sheet: str
    cell: str
    category: str = Field(default="", description="High-level PL category (e.g. 売上, 販管費, LTV)")
    label: str = Field(default="", description="Cell's template label")
    assigned_concept: str = Field(default="", description="What this cell represents")
    segment: str = Field(default="", description="Which segment this belongs to")
    period: str = Field(default="", description="FY/month if applicable")
    unit: str = Field(default="", description="Expected unit")
    derivation: str = Field(default="direct", description="'direct' / 'calculated' / 'assumption'")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reasoning: str = Field(default="")

    @field_validator(
        "category", "label", "assigned_concept", "segment", "period",
        "unit", "derivation", "reasoning",
        mode="before",
    )
    @classmethod
    def _none_to_empty(cls, v: Any) -> str:
        if v is None:
            return ""
        return str(v)


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

1. **PLカテゴリの分類（category）**
   - 各セルをPLの大分類にカテゴライズする
   - 典型的なカテゴリ:
     - 収益系: 「売上」「LTV」「MRR」「取引収益」
     - 費用系: 「人件費」「販管費」「広告宣伝費」「開発費」「減価償却費」
     - その他: 「前提条件」「成長率」「KPI」
   - テンプレートのブロック構造（block）をヒントに分類
   - 同じblock内のセルは同じcategoryにする

2. **セルラベルとビジネス概念の照合**
   - 同義語対応：「受講者数」=「顧客数」=「ユーザー数」
   - 略語対応：「MRR」=「月間経常収益」

3. **セグメントへの帰属**
   - 各セルがどのビジネスセグメントに属するか
   - 共通項目（人件費等）はセグメント横断で記載

4. **期間の特定**
   - FY1/FY2/月次/四半期の区別

5. **単位の確認**
   - 千円 vs 円、% vs 小数、人数 vs 比率

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【出力ルール】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 全入力セルに対して assignment または unmapped を返す
- assigned_concept は日本語で簡潔に
- category はPLの大分類を日本語で（例: 売上、人件費、販管費）
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
⚠ 重要: "label"にはセルの見出しテキスト（例: 顧客数/取引数、単価（円））を記載してください。
  数値やcurrent_valueを入れないでください。テンプレートの左端（B列）やヘッダー行にある
  項目名を使用してください。同じ行の入力セル（C列〜F列等）のlabelは、対応するB列の
  項目名と同じにしてください。

{{
  "cell_assignments": [
    {{
      "sheet": "シート名",
      "cell": "B5",
      "category": "PLの大分類（例: 売上, 人件費, 販管費, LTV, 前提条件）",
      "label": "セルの見出しテキスト（数値ではなく項目名）",
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

    def __init__(
        self,
        llm_client: Any,
        system_prompt: Optional[str] = None,
        user_prompt: Optional[str] = None,
    ) -> None:
        self.llm = llm_client
        self._system_prompt = system_prompt or MD_SYSTEM_PROMPT
        self._user_prompt = user_prompt or MD_USER_PROMPT

    def design(
        self,
        analysis_json: Dict[str, Any],
        template_structure_json: Dict[str, Any],
        catalog_items: List[Dict[str, Any]],
        feedback: str = "",
        estimation_mode: bool = False,
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
        estimation_mode : bool
            If True, Phase 3 was empty — use LLM to generate estimated mappings.
        """
        # Estimation mode: Phase 3 succeeded but empty — use LLM for higher accuracy
        if estimation_mode:
            logger.info("ModelDesigner: estimation mode — using LLM to generate concept mappings")
            return self._generate_llm_estimation(analysis_json, template_structure_json, feedback)

        # Fallback: generate estimated assignments when no input cells found
        if not catalog_items:
            logger.info("ModelDesigner: catalog_items is empty, generating estimated assignments")
            return self._generate_fallback_assignments(analysis_json, template_structure_json)

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
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": self._user_prompt.format(
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
        return self._parse_result(result, catalog_items)

    def _parse_result(
        self,
        raw: Dict[str, Any],
        catalog_items: Optional[List[Dict[str, Any]]] = None,
    ) -> ModelDesignResult:
        # Build lookups from catalog: label and block
        catalog_label_map: Dict[str, str] = {}
        catalog_block_map: Dict[str, str] = {}
        for item in (catalog_items or []):
            sheet = item.get("sheet", "")
            cell = item.get("cell", "")
            labels = item.get("label_candidates", [])
            block = item.get("block", "")
            addr = f"{sheet}!{cell}"
            if sheet and cell:
                if labels:
                    catalog_label_map[addr] = labels[0]
                if block:
                    catalog_block_map[addr] = block

        assignments = []
        for ca in raw.get("cell_assignments", []):
            sheet = ca.get("sheet", "")
            cell = ca.get("cell", "")
            llm_label = ca.get("label", "")
            llm_category = ca.get("category", "")

            addr = f"{sheet}!{cell}"

            # Fix: if LLM returned a numeric value as label, use catalog label
            actual_label = llm_label
            if addr in catalog_label_map:
                cat_label = catalog_label_map[addr]
                try:
                    float(str(llm_label).replace(",", ""))
                    actual_label = cat_label
                except (ValueError, TypeError):
                    if not llm_label:
                        actual_label = cat_label

            # Category: use LLM's category, fallback to catalog block
            actual_category = llm_category
            if not actual_category and addr in catalog_block_map:
                actual_category = catalog_block_map[addr]

            assignments.append(CellAssignment(
                sheet=sheet,
                cell=cell,
                category=actual_category,
                label=actual_label,
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

    # ------------------------------------------------------------------
    # LLM-based estimation (when Phase 3 succeeded but was empty)
    # ------------------------------------------------------------------

    _ESTIMATION_SYSTEM_PROMPT = """\
あなたは投資銀行のシニアFMスペシャリストです。
テンプレート構造が取得できなかった場合でも、事業分析結果から
PL（損益計算書）の概念マッピングを推定します。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【推定モードの原則】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

テンプレートのセル情報がないため、標準的なPL構造を仮定して
ビジネス概念を配置します。

1. **シート構造の推定**
   - セグメント毎に「収益モデル」シートを想定
   - 共通の「費用リスト」「前提条件」シートを想定

2. **セル位置の推定**
   - C列を入力列、B列をラベル列と仮定
   - 行番号は3から連番

3. **PLカテゴリは必ず設定**
   - 売上、変動費、固定費、人件費、販管費、前提条件 等

4. **derivation は全て "estimated" に設定**

5. **confidence は内容の確からしさに応じて 0.2〜0.6 の範囲で設定**
   - 文書に明示的記載あり → 0.5-0.6
   - 文書から推測 → 0.3-0.4
   - 一般的なビジネスモデルから想定 → 0.2-0.3
"""

    _ESTIMATION_USER_PROMPT = """\
テンプレート構造が取得できませんでした（Phase 3の結果が空）。
以下の事業分析結果から、PLモデルの概念マッピングを推定してください。

━━━ 事業分析結果 ━━━
{business_analysis_json}

━━━ テンプレート構造（参考、空の可能性あり） ━━━
{template_structure_json}

{feedback_section}\
━━━ 出力形式（JSON） ━━━
推定モードのため、全てのassignmentの derivation を "estimated" にしてください。

{{
  "cell_assignments": [
    {{
      "sheet": "推定シート名",
      "cell": "C3",
      "category": "PLの大分類",
      "label": "項目名",
      "assigned_concept": "概念名【推定】",
      "segment": "セグメント名",
      "period": "FY1-FY5",
      "unit": "単位",
      "derivation": "estimated",
      "confidence": 0.4,
      "reasoning": "推定理由"
    }}
  ],
  "unmapped_cells": [],
  "warnings": ["推定モードに関する注意事項"]
}}
"""

    def _generate_llm_estimation(
        self,
        analysis_json: Dict[str, Any],
        template_structure_json: Dict[str, Any],
        feedback: str = "",
    ) -> ModelDesignResult:
        """Use LLM to generate estimated concept mappings when Phase 3 is empty.

        This produces higher-quality estimates than the static fallback by
        leveraging the LLM's understanding of the business model.
        """
        analysis_str = json.dumps(analysis_json, ensure_ascii=False, indent=2)
        structure_str = json.dumps(template_structure_json, ensure_ascii=False, indent=2)

        feedback_section = ""
        if feedback:
            feedback_section = (
                f"━━━ ユーザーフィードバック ━━━\n"
                f"{feedback}\n\n"
            )

        messages = [
            {"role": "system", "content": self._ESTIMATION_SYSTEM_PROMPT},
            {"role": "user", "content": self._ESTIMATION_USER_PROMPT.format(
                business_analysis_json=analysis_str,
                template_structure_json=structure_str,
                feedback_section=feedback_section,
            )},
        ]

        logger.info("ModelDesigner: sending estimation request to LLM")
        try:
            raw = self.llm.extract(messages)
        except Exception:
            logger.exception("ModelDesigner: LLM estimation failed, falling back to static")
            return self._generate_fallback_assignments(analysis_json, template_structure_json)

        # Ensure all assignments have derivation="estimated"
        for ca in raw.get("cell_assignments", []):
            ca["derivation"] = "estimated"

        # Add standard estimation warnings
        warnings = raw.get("warnings", [])
        warnings.insert(0, "【推定モード】Phase 3のテンプレート構造が空のため、LLMによる推定マッピングを生成しました。")
        warnings.insert(1, "セル位置は仮配置です。テンプレートExcelの実際のセル位置を確認してください。")
        raw["warnings"] = warnings

        logger.info(
            "ModelDesigner: LLM estimation generated %d assignments",
            len(raw.get("cell_assignments", [])),
        )

        return self._parse_result(raw)

    def _generate_fallback_assignments(
        self,
        analysis_json: Dict[str, Any],
        template_structure_json: Dict[str, Any],
    ) -> ModelDesignResult:
        """Generate estimated cell assignments from business analysis when catalog is empty.

        When no input cells are detected from the template, this method creates
        recommended concept mappings based on the business model analysis so
        the user can see what should be configured.
        """
        assignments: List[CellAssignment] = []
        warnings = [
            "【推定モード】テンプレートの入力セルが検出されなかったため、事業分析結果から推定マッピングを生成しました。",
            "各項目は推定値です。ユーザー側でテンプレートの入力セルを確認し、値を設定してください。",
        ]

        # --- Determine sheet names from Phase 3 structure ---
        revenue_sheets: List[str] = []
        cost_sheet = "費用リスト"
        assumption_sheet = "前提条件"

        for sm in template_structure_json.get("sheet_mappings", []):
            purpose = sm.get("sheet_purpose", "other")
            name = sm.get("sheet_name", "")
            if not name:
                continue
            if purpose == "revenue_model":
                revenue_sheets.append(name)
            elif purpose == "cost_detail":
                cost_sheet = name
            elif purpose == "assumptions":
                assumption_sheet = name

        # --- Extract business data ---
        segments = analysis_json.get("segments", [])
        shared_costs = analysis_json.get("shared_costs", [])
        ft = analysis_json.get("financial_targets") or {}
        horizon = ft.get("horizon_years", 5)

        # Period range label
        rev_targets = ft.get("revenue_targets", [])
        if rev_targets and len(rev_targets) >= 2:
            first_yr = rev_targets[0].get("year", "FY1")
            last_yr = rev_targets[-1].get("year", f"FY{horizon}")
            period_label = f"{first_yr}-{last_yr}"
        else:
            period_label = f"FY1-FY{horizon}"

        # --- Revenue drivers per segment ---
        for seg_idx, seg in enumerate(segments):
            seg_name = seg.get("name", f"セグメント{seg_idx + 1}")
            sheet = revenue_sheets[seg_idx] if seg_idx < len(revenue_sheets) else f"収益モデル{seg_idx + 1}"
            row = 3

            for drv in seg.get("revenue_drivers", []):
                drv_name = drv.get("name", "")
                est_value = drv.get("estimated_value")
                unit = drv.get("unit", "")
                ref_text = f" 文書参考値: {est_value}{unit}" if est_value else ""

                assignments.append(CellAssignment(
                    sheet=sheet,
                    cell=f"C{row}",
                    category="売上",
                    label=drv_name,
                    assigned_concept=f"{drv_name}【推定】",
                    segment=seg_name,
                    period=period_label,
                    unit=unit,
                    derivation="estimated",
                    confidence=0.3,
                    reasoning=f"【推定】事業分析の{seg_name}から推定。ユーザー設定推奨。{ref_text}",
                ))
                row += 1

            # Revenue formula summary
            formula = seg.get("revenue_formula", "")
            if formula:
                assignments.append(CellAssignment(
                    sheet=sheet,
                    cell=f"C{row}",
                    category="売上",
                    label="売上高",
                    assigned_concept=f"売上高（{formula}）【推定】",
                    segment=seg_name,
                    period=period_label,
                    unit="円",
                    derivation="estimated",
                    confidence=0.3,
                    reasoning=f"【推定】算式: {formula}",
                ))

        # --- Shared costs ---
        row = 3
        for cost in shared_costs:
            cost_name = cost.get("name", "")
            est_value = cost.get("estimated_value")
            cost_cat = "変動費" if cost.get("category") == "variable" else "固定費"
            ref_text = f" 文書参考値: {est_value}" if est_value else ""

            assignments.append(CellAssignment(
                sheet=cost_sheet,
                cell=f"C{row}",
                category=cost_cat,
                label=cost_name,
                assigned_concept=f"{cost_name}（{cost_cat}）【推定】",
                segment="共通",
                period=period_label,
                unit="円",
                derivation="estimated",
                confidence=0.3,
                reasoning=f"【推定】事業分析のコスト項目から推定。ユーザー設定推奨。{ref_text}",
            ))
            row += 1

        # --- Financial targets as assumptions ---
        row = 3
        for rt in rev_targets:
            year = rt.get("year", "")
            value = rt.get("value")
            source = rt.get("source", "")
            evidence = rt.get("evidence", "")
            val_text = f"{value:,.0f}円" if value else "未設定"

            assignments.append(CellAssignment(
                sheet=assumption_sheet,
                cell=f"C{row}",
                category="前提条件",
                label=f"売上目標（{year}）",
                assigned_concept=f"売上目標 {year}: {val_text}【推定】",
                segment="全体",
                period=year,
                unit="円",
                derivation="estimated",
                confidence=0.4 if source == "document" else 0.2,
                reasoning=f"【推定】{evidence or '事業分析から推定'}。ユーザー設定推奨。",
            ))
            row += 1

        if not assignments:
            warnings.append("事業分析からも推定可能な項目が見つかりませんでした。事業分析（Phase 2）を再実行してください。")

        raw = {
            "cell_assignments": [a.model_dump() for a in assignments],
            "unmapped_cells": [],
            "warnings": warnings,
        }

        logger.info(
            "ModelDesigner: generated %d fallback assignments from business analysis",
            len(assignments),
        )

        return ModelDesignResult(
            cell_assignments=assignments,
            unmapped_cells=[],
            warnings=warnings,
            raw_json=raw,
        )
