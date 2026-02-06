"""
PL Generator -- 3-Phase Wizard (Streamlit UI)
=============================================

A three-phase wizard for generating P&L Excel models from business-plan
documents.

* **Phase A** -- Pre-Customisation  (事前カスタマイズ)
* **Phase B** -- Analysis Results    (分析結果)
* **Phase C** -- Pre-Generation Customisation  (生成前カスタマイズ)

Run with::

    streamlit run src/app/streamlit_app.py
"""

from __future__ import annotations

import io
import json
import logging
import os
import sys
import tempfile
import traceback
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure project root is on sys.path (needed for Streamlit Cloud deployment)
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import streamlit as st

# ---------------------------------------------------------------------------
# Project imports
# ---------------------------------------------------------------------------

from src.config.models import (
    PhaseAConfig,
    InputCatalog,
    CatalogItem,
    AnalysisReport,
    KPIDefinition,
    DependencyNode,
    FormulaInfo,
    ExtractedParameter,
    ExtractionResult,
    Evidence,
    CellTarget,
)
from src.ingest.reader import read_document
from src.ingest.base import DocumentContent
from src.catalog.scanner import scan_template, export_catalog_json
from src.modelmap.analyzer import analyze_model, generate_model_report_md
from src.extract.extractor import ParameterExtractor
from src.extract.llm_client import LLMClient
from src.excel.writer import PLWriter
from src.excel.validator import PLValidator, generate_needs_review_csv
from src.excel.case_generator import CaseGenerator

_IMPORT_ERRORS: List[str] = []
try:
    from src.simulation.engine import (
        SimulationEngine,
        export_simulation_summary,
    )
except ImportError as exc:
    _IMPORT_ERRORS.append(f"simulation.engine: {exc}")
    SimulationEngine = None  # type: ignore[assignment,misc]
    export_simulation_summary = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

INDUSTRY_OPTIONS: List[str] = [
    "SaaS",
    "教育",
    "人材",
    "EC",
    "小売",
    "飲食",
    "メーカー",
    "ヘルスケア",
    "その他",
]

BUSINESS_MODEL_OPTIONS: List[str] = ["B2B", "B2C", "B2B2C", "MIX", "Other"]
CASE_OPTIONS: List[str] = ["Best", "Base", "Worst"]
ALLOWED_DOC_EXTENSIONS: List[str] = ["pdf", "docx", "pptx"]
DEFAULT_TEMPLATE_PATH = "templates/base.xlsx"

# Default colour values (ARGB hex without leading #)
DEFAULT_INPUT_COLOR = "#FFF2CC"
DEFAULT_FORMULA_COLOR = "#4472C4"
DEFAULT_TOTAL_COLOR = "#D9E2F3"


# ---------------------------------------------------------------------------
# Lightweight local dataclass for proposed changes (Phase C)
# ---------------------------------------------------------------------------

@dataclass
class ProposedChange:
    """A single proposed change from custom instruction parsing."""

    parameter_key: str = ""
    original_value: Any = None
    proposed_value: Any = None
    reason: str = ""
    affected_cases: List[str] = field(default_factory=list)
    evidence_from_instruction: str = ""
    accepted: bool = True


# ---------------------------------------------------------------------------
# Helper: colour config container (simple dict wrapper kept in session_state)
# ---------------------------------------------------------------------------

@dataclass
class ColorConfig:
    """Lightweight colour configuration for the template."""

    input_color: str = DEFAULT_INPUT_COLOR
    formula_color: str = DEFAULT_FORMULA_COLOR
    total_color: str = DEFAULT_TOTAL_COLOR
    apply_formula_color: bool = False
    apply_total_color: bool = False


# ---------------------------------------------------------------------------
# Session-state initialisation
# ---------------------------------------------------------------------------

def _init_session_state() -> None:
    """Ensure every required session-state key exists."""
    defaults = {
        "phase": "A",
        # Phase A outputs
        "config": None,
        "color_config": ColorConfig(),
        "document": None,
        "catalog": None,
        "analysis": None,
        "parameters": [],
        "extraction_result": None,
        # Phase C
        "proposed_changes": [],
        "custom_instruction_text": "",
        "generation_outputs": {},
        # Misc
        "error_message": "",
        "success_message": "",
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _save_uploaded_file(uploaded_file) -> str:
    """Persist an uploaded file to a temp directory and return its path."""
    tmp_dir = tempfile.mkdtemp()
    dest = Path(tmp_dir) / uploaded_file.name
    dest.write_bytes(uploaded_file.getvalue())
    return str(dest)


def _confidence_color(confidence: float) -> str:
    """Return a CSS colour string based on confidence level."""
    if confidence >= 0.7:
        return "green"
    if confidence >= 0.4:
        return "orange"
    return "red"


def _confidence_emoji_text(confidence: float) -> str:
    """Return a text label for the confidence band."""
    if confidence >= 0.7:
        return "HIGH"
    if confidence >= 0.4:
        return "MEDIUM"
    return "LOW"


def _render_dependency_tree_text(node, indent: int = 0) -> str:
    """Recursively render a DependencyNode as indented text."""
    prefix = "  " * indent
    tag = ""
    if getattr(node, "is_input", False):
        tag = " [INPUT]"
    elif getattr(node, "is_kpi", False):
        tag = " [KPI]"
    label = getattr(node, "label", "") or getattr(node, "address", "?")
    line = f"{prefix}- {label}{tag}\n"
    for child in getattr(node, "children", []):
        line += _render_dependency_tree_text(child, indent + 1)
    return line


def _dep_tree_to_dot(node, seen: set | None = None) -> str:
    """Convert a DependencyNode tree to Graphviz DOT source."""
    if seen is None:
        seen = set()
    lines: List[str] = []
    addr = getattr(node, "address", "?")
    label = getattr(node, "label", "") or addr
    node_id = addr.replace("'", "").replace("!", "_").replace(" ", "_")

    if node_id not in seen:
        seen.add(node_id)
        shape = "box"
        colour = "lightgrey"
        if getattr(node, "is_input", False):
            shape = "ellipse"
            colour = "lightyellow"
        elif getattr(node, "is_kpi", False):
            shape = "doubleoctagon"
            colour = "lightblue"
        safe_label = label.replace('"', '\\"')
        lines.append(
            f'  "{node_id}" [label="{safe_label}", shape={shape}, '
            f'style=filled, fillcolor="{colour}"];'
        )

    for child in getattr(node, "children", []):
        c_addr = getattr(child, "address", "?")
        c_id = c_addr.replace("'", "").replace("!", "_").replace(" ", "_")
        edge = f'  "{node_id}" -> "{c_id}";'
        if edge not in lines:
            lines.append(edge)
        child_lines = _dep_tree_to_dot(child, seen)
        if child_lines:
            lines.append(child_lines)

    return "\n".join(lines)


# ===================================================================
# Phase A: Pre-Customisation  (事前カスタマイズ)
# ===================================================================

def _render_phase_a() -> None:
    st.header("Phase A: 事前カスタマイズ (Pre-Customisation)")
    st.markdown(
        "業種、ビジネスモデル、厳密度、ケースを設定し、事業計画書と"
        "テンプレートをアップロードしてください。"
    )

    # --- Industry selector ------------------------------------------------
    col_ind, col_free = st.columns([2, 1])
    with col_ind:
        industry_choice = st.selectbox(
            "業種 (Industry)",
            options=INDUSTRY_OPTIONS,
            index=0,
            key="industry_select",
        )
    with col_free:
        industry_freetext = st.text_input(
            "業種 (自由入力)",
            value="",
            key="industry_freetext",
            help="ドロップダウンに該当しない場合、自由入力してください。",
        )
    industry = industry_freetext.strip() if industry_freetext.strip() else industry_choice

    # --- Business model ---------------------------------------------------
    business_model = st.selectbox(
        "ビジネスモデル (Business Model)",
        options=BUSINESS_MODEL_OPTIONS,
        index=0,
        key="biz_model_select",
    )

    # --- Strictness -------------------------------------------------------
    strictness_label = st.radio(
        "モデル厳密度 (Model Strictness)",
        options=["厳密 (strict)", "ノーマル (normal)"],
        index=1,
        horizontal=True,
        key="strictness_radio",
    )
    strictness = "strict" if "厳密" in strictness_label else "normal"

    # --- Cases ------------------------------------------------------------
    cases = st.multiselect(
        "ケース (Cases)",
        options=CASE_OPTIONS,
        default=["Base"],
        key="case_multiselect",
    )
    if not cases:
        cases = ["Base"]

    # --- Simulation -------------------------------------------------------
    run_simulation = st.checkbox(
        "シミュレーションあり (Run Simulation)",
        value=False,
        key="sim_checkbox",
    )

    # --- Colour settings --------------------------------------------------
    with st.expander("カラー設定 (Colour Settings)", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            input_color = st.color_picker(
                "入力セル色 (Input colour)",
                value=DEFAULT_INPUT_COLOR,
                key="color_input",
            )
        with c2:
            formula_color = st.color_picker(
                "数式フォント色 (Formula colour)",
                value=DEFAULT_FORMULA_COLOR,
                key="color_formula",
            )
        with c3:
            total_color = st.color_picker(
                "合計セル色 (Total colour)",
                value=DEFAULT_TOTAL_COLOR,
                key="color_total",
            )

        tc1, tc2 = st.columns(2)
        with tc1:
            apply_formula_color = st.toggle(
                "数式色を適用 (Apply formula colour)",
                value=False,
                key="toggle_formula_color",
            )
        with tc2:
            apply_total_color = st.toggle(
                "合計色を適用 (Apply total colour)",
                value=False,
                key="toggle_total_color",
            )

    # --- File upload: business plan ---------------------------------------
    st.subheader("事業計画書アップロード (Business Plan Upload)")
    doc_file = st.file_uploader(
        "PDF / DOCX / PPTX ファイルを選択",
        type=ALLOWED_DOC_EXTENSIONS,
        key="doc_upload",
    )

    # --- File upload: Excel template (optional) ---------------------------
    st.subheader("Excel テンプレート (任意)")
    template_file = st.file_uploader(
        "Excel テンプレート (.xlsx) -- 未指定の場合はデフォルトを使用",
        type=["xlsx"],
        key="template_upload",
    )

    # --- Start button -----------------------------------------------------
    st.divider()
    start_disabled = doc_file is None
    if start_disabled:
        st.info("事業計画書をアップロードしてください。")

    if st.button(
        "分析開始 (Start Analysis)",
        type="primary",
        disabled=start_disabled,
        use_container_width=True,
        key="btn_start_analysis",
    ):
        _run_phase_a_analysis(
            industry=industry,
            business_model=business_model,
            strictness=strictness,
            cases=[c.lower() for c in cases],
            run_simulation=run_simulation,
            input_color=input_color,
            formula_color=formula_color,
            total_color=total_color,
            apply_formula_color=apply_formula_color,
            apply_total_color=apply_total_color,
            doc_file=doc_file,
            template_file=template_file,
        )


def _run_phase_a_analysis(
    *,
    industry: str,
    business_model: str,
    strictness: str,
    cases: List[str],
    run_simulation: bool,
    input_color: str,
    formula_color: str,
    total_color: str,
    apply_formula_color: bool,
    apply_total_color: bool,
    doc_file,
    template_file,
) -> None:
    """Execute the Phase-A analysis pipeline and transition to Phase B."""

    progress = st.progress(0, text="準備中...")
    status_area = st.empty()

    try:
        # ---- 1. Save uploaded files ---------------------------------
        progress.progress(5, text="ファイルを保存中...")
        doc_path = _save_uploaded_file(doc_file)

        if template_file is not None:
            template_path = _save_uploaded_file(template_file)
        else:
            template_path = DEFAULT_TEMPLATE_PATH
            if not Path(template_path).exists():
                st.error(
                    f"デフォルトテンプレートが見つかりません: {template_path}\n"
                    "テンプレートをアップロードしてください。"
                )
                progress.empty()
                return

        # ---- 2. Build PhaseAConfig ----------------------------------
        progress.progress(10, text="設定を構築中...")
        config = PhaseAConfig(
            industry=industry,
            business_model=business_model,
            strictness=strictness,
            cases=cases,
            template_path=template_path,
            document_paths=[doc_path],
        )
        st.session_state["config"] = config
        st.session_state["run_simulation"] = run_simulation

        # Store colour config
        cc = ColorConfig(
            input_color=input_color,
            formula_color=formula_color,
            total_color=total_color,
            apply_formula_color=apply_formula_color,
            apply_total_color=apply_total_color,
        )
        st.session_state["color_config"] = cc

        # ---- 3. Read document ---------------------------------------
        progress.progress(20, text="事業計画書を読み取り中...")
        with st.spinner("ドキュメントを解析中..."):
            document = read_document(doc_path)
        st.session_state["document"] = document
        status_area.success(
            f"ドキュメント読み取り完了: {document.total_pages} ページ"
        )

        # ---- 4. Scan Excel template ---------------------------------
        progress.progress(35, text="テンプレートをスキャン中...")
        # Convert hex colour picker value (#FFF2CC) to openpyxl format
        input_color_hex = input_color.lstrip("#")
        if len(input_color_hex) == 6:
            input_color_hex = "FF" + input_color_hex
        with st.spinner("テンプレートのスキャン中..."):
            catalog = scan_template(template_path, input_color=input_color_hex)
        st.session_state["catalog"] = catalog

        # ---- 5. Analyse model (formula graph / KPIs) ----------------
        progress.progress(50, text="モデルを分析中...")
        with st.spinner("数式構造を解析中..."):
            analysis = analyze_model(template_path, catalog)
        st.session_state["analysis"] = analysis

        # ---- 6. Extract parameters via LLM --------------------------
        progress.progress(65, text="パラメータを抽出中...")
        with st.spinner("LLM によるパラメータ抽出中..."):
            llm_client = LLMClient()
            extractor = ParameterExtractor(config, llm_client=llm_client)
            parameters = extractor.extract_parameters(document, catalog)
        st.session_state["parameters"] = parameters

        progress.progress(100, text="分析完了")
        st.session_state["phase"] = "B"
        st.rerun()

    except FileNotFoundError as exc:
        progress.empty()
        st.error(f"ファイルが見つかりません: {exc}")
    except ValueError as exc:
        progress.empty()
        st.error(f"値エラー: {exc}")
    except Exception as exc:  # noqa: BLE001
        progress.empty()
        st.error(f"分析中にエラーが発生しました:\n\n{exc}")
        with st.expander("詳細なエラー情報"):
            st.code(traceback.format_exc())


# ===================================================================
# Phase B: Analysis Results  (分析結果)
# ===================================================================

def _render_phase_b() -> None:
    st.header("Phase B: 分析結果 (Analysis Results)")

    analysis: AnalysisReport | None = st.session_state.get("analysis")
    catalog: InputCatalog | None = st.session_state.get("catalog")
    parameters: list = st.session_state.get("parameters", [])

    if analysis is None or catalog is None:
        st.warning("分析データがありません。Phase A に戻ってください。")
        if st.button("Phase A に戻る"):
            st.session_state["phase"] = "A"
            st.rerun()
        return

    tab_model, tab_params = st.tabs([
        "モデル内容 (Model Content)",
        "抽出パラメーター (Extracted Parameters)",
    ])

    # ------------------------------------------------------------------
    # Tab 1: Model Content
    # ------------------------------------------------------------------
    with tab_model:
        _render_model_content_tab(analysis, catalog)

    # ------------------------------------------------------------------
    # Tab 2: Extracted Parameters
    # ------------------------------------------------------------------
    with tab_params:
        _render_extracted_parameters_tab(parameters)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    st.divider()
    col_back, col_fwd = st.columns(2)
    with col_back:
        if st.button("Phase A に戻る", key="b_back"):
            st.session_state["phase"] = "A"
            st.rerun()
    with col_fwd:
        if st.button(
            "カスタマイズへ進む (Proceed to Customise)",
            type="primary",
            use_container_width=True,
            key="b_forward",
        ):
            st.session_state["phase"] = "C"
            st.rerun()


# --- Tab 1 helpers ---

def _render_model_content_tab(
    analysis: AnalysisReport,
    catalog: InputCatalog,
) -> None:
    """Render the Model Content tab inside Phase B."""

    # Model overview
    st.subheader("モデル概要 (Model Overview)")
    st.text(analysis.summary)

    # Sheets overview
    sheet_names = catalog.metadata.get("sheet_names", [])
    if sheet_names:
        st.markdown("**シート一覧:**")
        for sn in sheet_names:
            items_count = len(catalog.items_for_sheet(sn))
            formula_kpis = [
                k for k in analysis.kpis if k.sheet == sn
            ]
            st.markdown(
                f"- **{sn}** -- 入力セル: {items_count}, KPI数: {len(formula_kpis)}"
            )

    # KPI definitions
    st.subheader("KPI 定義 (KPI Definitions)")
    if analysis.kpis:
        for kpi in analysis.kpis:
            with st.expander(f"{kpi.name}  ({kpi.sheet}!{kpi.cell})"):
                if kpi.raw_formula:
                    st.markdown(f"**Excel数式:** `{kpi.raw_formula}`")
                if kpi.human_readable_formula:
                    st.markdown(f"**読みやすい形:** {kpi.human_readable_formula}")
                if kpi.unit:
                    st.markdown(f"**単位:** {kpi.unit}")
                if kpi.dependencies:
                    st.markdown("**依存先 (Dependencies):**")
                    for dep in kpi.dependencies:
                        st.markdown(f"  - {dep}")
    else:
        st.info("KPI が検出されませんでした。")

    # Dependency tree visualisation
    st.subheader("依存関係ツリー (Dependency Tree)")
    if analysis.dependency_tree:
        view_mode = st.radio(
            "表示形式",
            options=["テキストツリー", "Graphviz"],
            horizontal=True,
            key="dep_tree_mode",
        )
        for addr, node in analysis.dependency_tree.items():
            label = getattr(node, "label", "") or addr
            with st.expander(f"Tree: {label}"):
                if view_mode == "Graphviz":
                    try:
                        dot_body = _dep_tree_to_dot(node)
                        dot_src = f"digraph {{\n  rankdir=LR;\n{dot_body}\n}}"
                        st.graphviz_chart(dot_src)
                    except Exception:
                        st.code(_render_dependency_tree_text(node))
                else:
                    st.code(_render_dependency_tree_text(node))
    else:
        st.info("依存関係ツリーがありません。")

    # Case / scenario structure
    config: PhaseAConfig | None = st.session_state.get("config")
    if config and len(config.cases) > 1:
        st.subheader("ケース構成 (Case Structure)")
        for case_name in config.cases:
            st.markdown(f"- **{case_name.title()}** ケース")


# --- Tab 2 helpers ---

def _render_extracted_parameters_tab(parameters: list) -> None:
    """Render the Extracted Parameters tab inside Phase B."""

    if not parameters:
        st.info("抽出されたパラメータがありません。")
        return

    st.subheader("抽出パラメーター一覧")

    # Build a list-of-dicts for display
    rows: List[Dict[str, Any]] = []
    for p in parameters:
        mapped_cells = ", ".join(
            f"{t.sheet}!{t.cell}" for t in getattr(p, "mapped_targets", [])
        )
        evidence_quote = ""
        evidence_page = ""
        evidence_rationale = ""
        ev = getattr(p, "evidence", None)
        if ev:
            evidence_quote = getattr(ev, "quote", "")
            evidence_page = getattr(ev, "page_or_slide", "")
            evidence_rationale = getattr(ev, "rationale", "")

        rows.append({
            "key": getattr(p, "key", ""),
            "label": getattr(p, "label", ""),
            "value": getattr(p, "value", ""),
            "unit": getattr(p, "unit", "") or "",
            "confidence": getattr(p, "confidence", 0.0),
            "source": getattr(p, "source", ""),
            "evidence": evidence_quote[:80] if evidence_quote else "",
            "mapped_cells": mapped_cells,
        })

    # Filters
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        source_filter = st.multiselect(
            "ソースで絞り込み",
            options=sorted({r["source"] for r in rows if r["source"]}),
            default=[],
            key="param_source_filter",
        )
    with col_f2:
        conf_threshold = st.slider(
            "最低信頼度",
            min_value=0.0,
            max_value=1.0,
            value=0.0,
            step=0.1,
            key="param_conf_filter",
        )

    filtered = rows
    if source_filter:
        filtered = [r for r in filtered if r["source"] in source_filter]
    filtered = [r for r in filtered if r["confidence"] >= conf_threshold]

    st.markdown(f"**{len(filtered)}** / {len(rows)} パラメータ表示中")

    # Render as a dataframe with colour-coded confidence
    import pandas as pd

    df = pd.DataFrame(filtered)
    if not df.empty:

        def _style_confidence(val):
            """Return a background colour for confidence cells."""
            try:
                v = float(val)
            except (TypeError, ValueError):
                return ""
            if v >= 0.7:
                return "background-color: #c6efce; color: #006100"
            if v >= 0.4:
                return "background-color: #ffeb9c; color: #9c6500"
            return "background-color: #ffc7ce; color: #9c0006"

        styled = df.style.applymap(
            _style_confidence, subset=["confidence"]
        )
        st.dataframe(styled, use_container_width=True, height=500)
    else:
        st.info("フィルタ条件に一致するパラメータがありません。")

    # Expandable evidence details
    st.subheader("エビデンス詳細 (Evidence Details)")
    for p in parameters:
        ev = getattr(p, "evidence", None)
        if ev and getattr(ev, "quote", ""):
            with st.expander(
                f"{getattr(p, 'key', '?')} -- 信頼度: "
                f"{getattr(p, 'confidence', 0):.0%}"
            ):
                st.markdown(f"**引用:** {ev.quote}")
                if getattr(ev, "page_or_slide", ""):
                    st.markdown(f"**ページ/スライド:** {ev.page_or_slide}")
                if getattr(ev, "rationale", ""):
                    st.markdown(f"**根拠:** {ev.rationale}")


# ===================================================================
# Phase C: Pre-Generation Customisation  (生成前カスタマイズ)
# ===================================================================

def _render_phase_c() -> None:
    st.header("Phase C: 生成前カスタマイズ (Pre-Generation Customisation)")

    parameters: list = st.session_state.get("parameters", [])
    config: PhaseAConfig | None = st.session_state.get("config")
    catalog: InputCatalog | None = st.session_state.get("catalog")

    if not parameters or config is None:
        st.warning("パラメータがありません。Phase A に戻ってください。")
        if st.button("Phase A に戻る", key="c_back_warn"):
            st.session_state["phase"] = "A"
            st.rerun()
        return

    multiple_cases = config and len(config.cases) > 1

    # If multiple cases, show tabs per case; otherwise single view
    if multiple_cases:
        case_tabs = st.tabs([c.title() for c in config.cases])
        for idx, case_name in enumerate(config.cases):
            with case_tabs[idx]:
                _render_case_customisation(
                    parameters, case_name, catalog, suffix=f"_{case_name}"
                )
    else:
        _render_case_customisation(
            parameters, config.cases[0] if config.cases else "base",
            catalog, suffix="_single",
        )

    # --- Section 3: Custom Instructions (global) -------------------------
    st.divider()
    _render_custom_instructions_section(parameters)

    # --- Generate button --------------------------------------------------
    st.divider()
    col_back, col_gen = st.columns(2)
    with col_back:
        if st.button("Phase B に戻る", key="c_back"):
            st.session_state["phase"] = "B"
            st.rerun()
    with col_gen:
        if st.button(
            "生成 (Generate)",
            type="primary",
            use_container_width=True,
            key="btn_generate",
        ):
            _run_generation()


def _render_case_customisation(
    parameters: list,
    case_name: str,
    catalog: InputCatalog | None,
    suffix: str = "",
) -> None:
    """Render Sections 1 and 2 for a single case."""

    st.subheader(f"パラメーター選択 -- {case_name.title()} ケース")

    # Group parameters by block/sheet
    grouped: Dict[str, List] = {}
    for p in parameters:
        targets = getattr(p, "mapped_targets", [])
        if targets:
            group_key = targets[0].sheet
        else:
            group_key = "未分類"
        grouped.setdefault(group_key, []).append(p)

    # Initialise per-parameter session state
    for p in parameters:
        sel_key = f"sel_{p.key}{suffix}"
        adj_key = f"adj_{p.key}{suffix}"
        mul_key = f"mul_{p.key}{suffix}"
        if sel_key not in st.session_state:
            st.session_state[sel_key] = True
        if adj_key not in st.session_state:
            st.session_state[adj_key] = p.value if p.value is not None else 0
        if mul_key not in st.session_state:
            st.session_state[mul_key] = 1.0

    # ---- Section 1: Parameter Selection --------------------------------
    for group_name, group_params in grouped.items():
        with st.expander(f"[{group_name}] -- {len(group_params)} パラメータ", expanded=True):
            for p in group_params:
                sel_key = f"sel_{p.key}{suffix}"
                st.checkbox(
                    f"{getattr(p, 'label', p.key)} ({getattr(p, 'key', '')})",
                    value=st.session_state.get(sel_key, True),
                    key=sel_key,
                )

    # ---- Section 2: Parameter Adjustment --------------------------------
    st.subheader(f"パラメータ調整 -- {case_name.title()} ケース")

    diff_rows: List[Dict[str, Any]] = []

    for group_name, group_params in grouped.items():
        with st.expander(f"[{group_name}] 調整", expanded=False):
            for p in group_params:
                sel_key = f"sel_{p.key}{suffix}"
                if not st.session_state.get(sel_key, True):
                    continue

                adj_key = f"adj_{p.key}{suffix}"
                mul_key = f"mul_{p.key}{suffix}"

                st.markdown(f"**{getattr(p, 'label', p.key)}**")
                c_val, c_mul, c_unit = st.columns([2, 2, 1])

                original_value = p.value if p.value is not None else 0
                is_numeric = isinstance(original_value, (int, float))

                with c_val:
                    if is_numeric:
                        new_val = st.number_input(
                            "値 (Value)",
                            value=float(original_value),
                            key=adj_key,
                            format="%.4f",
                        )
                    else:
                        new_val = st.text_input(
                            "値 (Value)",
                            value=str(original_value),
                            key=adj_key,
                        )

                with c_mul:
                    if is_numeric:
                        multiplier = st.slider(
                            "倍率 (Multiplier)",
                            min_value=0.5,
                            max_value=2.0,
                            value=st.session_state.get(mul_key, 1.0),
                            step=0.05,
                            key=mul_key,
                        )
                    else:
                        multiplier = 1.0

                with c_unit:
                    unit = getattr(p, "unit", "") or ""
                    st.text_input("単位", value=unit, disabled=True, key=f"unit_{p.key}{suffix}")

                # Compute effective value
                if is_numeric:
                    effective = float(new_val) * multiplier
                else:
                    effective = new_val

                # Show if changed
                if is_numeric and effective != float(original_value):
                    diff_rows.append({
                        "パラメータ": getattr(p, "label", p.key),
                        "旧値": original_value,
                        "新値": round(effective, 4),
                        "セル": ", ".join(
                            f"{t.sheet}!{t.cell}"
                            for t in getattr(p, "mapped_targets", [])
                        ),
                    })

    # Diff Preview
    if diff_rows:
        st.subheader("Diff プレビュー (変更一覧)")
        import pandas as pd

        st.dataframe(pd.DataFrame(diff_rows), use_container_width=True)
    else:
        st.info("変更はありません。")


# --- Section 3: Custom Instructions ---

def _render_custom_instructions_section(parameters: list) -> None:
    """Render the free-form instruction section."""
    st.subheader("カスタマイズ指示 (Custom Instructions)")

    instruction = st.text_area(
        "自由形式の指示を入力してください",
        value=st.session_state.get("custom_instruction_text", ""),
        height=150,
        key="custom_instruction_area",
        placeholder="例: 売上を20%増加させてください。人件費を月額50万円に設定してください。",
    )
    st.session_state["custom_instruction_text"] = instruction

    if st.button("指示を解析 (Parse Instructions)", key="btn_parse_instr"):
        if not instruction.strip():
            st.warning("指示を入力してください。")
        else:
            _parse_custom_instruction(instruction, parameters)

    # Display proposed changes
    proposed: List[ProposedChange] = st.session_state.get("proposed_changes", [])
    if proposed:
        st.subheader("提案された変更 (Proposed Changes)")
        for idx, pc in enumerate(proposed):
            col_desc, col_toggle = st.columns([4, 1])
            with col_desc:
                st.markdown(
                    f"**{pc.parameter_key}**: {pc.original_value} -> "
                    f"**{pc.proposed_value}**"
                )
                st.caption(pc.reason)
                if pc.evidence_from_instruction:
                    st.caption(f"根拠: \"{pc.evidence_from_instruction}\"")
            with col_toggle:
                accepted = st.toggle(
                    "適用",
                    value=pc.accepted,
                    key=f"pc_accept_{idx}",
                )
                proposed[idx].accepted = accepted
        st.session_state["proposed_changes"] = proposed


def _parse_custom_instruction(instruction: str, parameters: list) -> None:
    """Use LLM to parse free-form instruction into proposed changes."""
    try:
        with st.spinner("指示を解析中..."):
            llm = LLMClient()
            params_json = json.dumps(
                [
                    {
                        "key": p.key,
                        "label": getattr(p, "label", ""),
                        "value": p.value,
                        "unit": getattr(p, "unit", ""),
                    }
                    for p in parameters
                ],
                ensure_ascii=False,
                indent=2,
            )
            result = llm.process_instruction(instruction, params_json)

        changes_raw = result.get("changes", [])
        proposed: List[ProposedChange] = []
        for ch in changes_raw:
            proposed.append(
                ProposedChange(
                    parameter_key=ch.get("parameter_key", ""),
                    original_value=ch.get("original_value"),
                    proposed_value=ch.get("proposed_value"),
                    reason=ch.get("reason", ""),
                    affected_cases=ch.get("affected_cases", []),
                    evidence_from_instruction=ch.get(
                        "evidence_from_instruction", ""
                    ),
                    accepted=True,
                )
            )
        st.session_state["proposed_changes"] = proposed

        if proposed:
            st.success(f"{len(proposed)} 件の変更が提案されました。")
        else:
            st.info("指示から変更を検出できませんでした。")
    except Exception as exc:  # noqa: BLE001
        st.error(f"指示の解析中にエラーが発生しました: {exc}")


# ===================================================================
# Generation
# ===================================================================

def _apply_adjustments_to_parameters(
    parameters: list,
    suffix: str,
) -> list:
    """Return a copy of *parameters* with user adjustments applied.

    For each parameter the user has selected, compute the effective value
    from the direct-edit and multiplier controls.  Parameters the user
    deselected are marked as not-selected.
    """
    adjusted = deepcopy(parameters)
    for p in adjusted:
        sel_key = f"sel_{p.key}{suffix}"
        adj_key = f"adj_{p.key}{suffix}"
        mul_key = f"mul_{p.key}{suffix}"

        selected = st.session_state.get(sel_key, True)

        # Attach runtime attributes used by the writer
        try:
            p.selected = selected  # type: ignore[attr-defined]
        except (AttributeError, TypeError):
            pass

        if not selected:
            continue

        adj_val = st.session_state.get(adj_key, p.value)
        multiplier = st.session_state.get(mul_key, 1.0)

        if isinstance(adj_val, (int, float)) and isinstance(
            multiplier, (int, float)
        ):
            effective = float(adj_val) * float(multiplier)
        else:
            effective = adj_val

        try:
            p.adjusted_value = effective  # type: ignore[attr-defined]
        except (AttributeError, TypeError):
            pass

    # Apply accepted proposed changes
    proposed: List[ProposedChange] = st.session_state.get(
        "proposed_changes", []
    )
    param_map = {p.key: p for p in adjusted}
    for pc in proposed:
        if not pc.accepted:
            continue
        if pc.parameter_key in param_map:
            target = param_map[pc.parameter_key]
            try:
                target.adjusted_value = pc.proposed_value  # type: ignore[attr-defined]
            except (AttributeError, TypeError):
                pass

    return adjusted


def _run_generation() -> None:
    """Execute the Excel generation pipeline."""
    config: PhaseAConfig | None = st.session_state.get("config")
    catalog: InputCatalog | None = st.session_state.get("catalog")
    parameters: list = st.session_state.get("parameters", [])
    cc: ColorConfig = st.session_state.get("color_config", ColorConfig())

    if config is None or not parameters:
        st.error("必要なデータが不足しています。Phase A からやり直してください。")
        return

    progress = st.progress(0, text="生成を開始中...")
    output_files: Dict[str, bytes] = {}

    try:
        # Determine case suffixes
        cases = config.cases if config.cases else ["base"]
        total_steps = len(cases) + 2  # +1 for validation, +1 for simulation
        step = 0

        for case_name in cases:
            step += 1
            progress.progress(
                int(step / total_steps * 80),
                text=f"{case_name.title()} ケースを生成中...",
            )

            suffix = f"_{case_name}" if len(cases) > 1 else "_single"
            adjusted_params = _apply_adjustments_to_parameters(
                parameters, suffix
            )

            # For non-base cases, apply case multipliers
            if case_name != "base" and len(cases) > 1:
                try:
                    gen = CaseGenerator(config)
                    case_sets = gen.generate_cases(adjusted_params)
                    if case_name in case_sets:
                        adjusted_params = case_sets[case_name]
                except Exception as exc:
                    st.warning(
                        f"{case_name} ケース生成に問題が発生しました: {exc}"
                    )

            # Generate the Excel
            with tempfile.TemporaryDirectory() as tmp_dir:
                output_path = str(
                    Path(tmp_dir) / f"PL_{case_name}.xlsx"
                )

                try:
                    # Attach colour config to PhaseAConfig if the writer expects it
                    try:
                        config.colors = cc  # type: ignore[attr-defined]
                    except (AttributeError, TypeError):
                        pass

                    writer = PLWriter(
                        template_path=config.template_path,
                        output_path=output_path,
                        config=config,
                    )
                    writer.generate(adjusted_params)

                    # Validate
                    try:
                        validator = PLValidator(
                            config.template_path, output_path
                        )
                        val_result = validator.validate()
                        if not val_result.passed:
                            st.warning(
                                f"{case_name.title()}: バリデーション警告あり "
                                f"(エラー数: {len(val_result.errors_found)})"
                            )
                            with st.expander(
                                f"{case_name.title()} バリデーション詳細"
                            ):
                                for err in val_result.errors_found:
                                    st.error(err)
                                for warn in val_result.warnings:
                                    st.warning(warn)
                        else:
                            st.success(
                                f"{case_name.title()}: バリデーション OK"
                            )
                    except Exception as ve:
                        st.warning(f"バリデーション実行失敗: {ve}")

                    # Read generated file into memory for download
                    output_files[f"PL_{case_name}.xlsx"] = Path(
                        output_path
                    ).read_bytes()

                except Exception as exc:
                    st.error(
                        f"{case_name.title()} ケース生成エラー: {exc}"
                    )
                    with st.expander("エラー詳細"):
                        st.code(traceback.format_exc())

        # ---- Optional simulation ----------------------------------------
        run_sim = st.session_state.get("run_simulation", False)
        if run_sim and parameters:
            step += 1
            progress.progress(
                int(step / total_steps * 95),
                text="シミュレーション実行中...",
            )
            try:
                with st.spinner("Monte Carlo シミュレーション実行中..."):
                    sim_engine = SimulationEngine(iterations=500)
                    sim_params = _apply_adjustments_to_parameters(
                        parameters, "_single" if len(cases) <= 1 else f"_{cases[0]}"
                    )
                    sim_report = sim_engine.run(
                        sim_params,
                        template_path=config.template_path,
                    )

                    with tempfile.TemporaryDirectory() as sim_dir:
                        sim_path = str(
                            Path(sim_dir) / "simulation_summary.xlsx"
                        )
                        export_simulation_summary(sim_report, sim_path)
                        output_files["simulation_summary.xlsx"] = Path(
                            sim_path
                        ).read_bytes()

                st.success("シミュレーション完了")

                # Display summary
                with st.expander("シミュレーション結果サマリー"):
                    for s in sim_report.summaries:
                        st.markdown(
                            f"**{s.kpi_name}**: "
                            f"平均={s.mean:,.0f}, "
                            f"P10={s.p10:,.0f}, "
                            f"P50={s.p50:,.0f}, "
                            f"P90={s.p90:,.0f}"
                        )
                    if sim_report.warnings:
                        for w in sim_report.warnings:
                            st.caption(w)

            except Exception as exc:
                st.warning(f"シミュレーション実行失敗: {exc}")

        # ---- needs_review CSV -------------------------------------------
        try:
            with tempfile.NamedTemporaryFile(
                suffix=".csv", delete=False, mode="w"
            ) as tmp_csv:
                csv_path = generate_needs_review_csv(parameters, tmp_csv.name)
                output_files["needs_review.csv"] = Path(csv_path).read_bytes()
        except Exception:
            pass  # not critical

        progress.progress(100, text="生成完了!")

        # Store for download
        st.session_state["generation_outputs"] = output_files

    except Exception as exc:  # noqa: BLE001
        progress.empty()
        st.error(f"生成中にエラーが発生しました: {exc}")
        with st.expander("エラー詳細"):
            st.code(traceback.format_exc())
        return

    # ---- Download buttons -----------------------------------------------
    st.divider()
    st.subheader("ダウンロード (Downloads)")
    if output_files:
        cols = st.columns(min(len(output_files), 3))
        for idx, (fname, fbytes) in enumerate(output_files.items()):
            with cols[idx % len(cols)]:
                st.download_button(
                    label=f"Download {fname}",
                    data=fbytes,
                    file_name=fname,
                    mime=(
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        if fname.endswith(".xlsx")
                        else "text/csv"
                    ),
                    key=f"dl_{fname}",
                )
    else:
        st.info("生成ファイルがありません。")


# ===================================================================
# Main application
# ===================================================================

def main() -> None:
    """Entry point for the Streamlit PL Generator wizard."""

    st.set_page_config(
        page_title="PL Generator Wizard",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    _init_session_state()

    # -- Sidebar -----------------------------------------------------------
    with st.sidebar:
        st.title("PL Generator")
        st.caption("3-Phase Wizard")

        # Show import errors if any
        if _IMPORT_ERRORS:
            with st.expander("Import Warnings", expanded=False):
                for ie in _IMPORT_ERRORS:
                    st.warning(ie)

        st.divider()
        current_phase = st.session_state["phase"]
        st.markdown(f"**現在のフェーズ:** Phase {current_phase}")

        phase_labels = {
            "A": "事前カスタマイズ",
            "B": "分析結果",
            "C": "生成前カスタマイズ",
        }
        for code, label in phase_labels.items():
            marker = " <<" if code == current_phase else ""
            st.markdown(f"- Phase {code}: {label}{marker}")

        st.divider()
        st.markdown("**セッション情報:**")
        cfg = st.session_state.get("config")
        if cfg:
            st.caption(f"業種: {cfg.industry}")
            st.caption(f"モデル: {cfg.business_model}")
            st.caption(f"厳密度: {cfg.strictness}")
            st.caption(f"ケース: {', '.join(cfg.cases)}")

        params = st.session_state.get("parameters", [])
        if params:
            st.caption(f"抽出パラメータ数: {len(params)}")

        # Download section (if files are available from Phase C)
        gen_outputs = st.session_state.get("generation_outputs", {})
        if gen_outputs:
            st.divider()
            st.markdown("**生成済みファイル:**")
            for fname, fbytes in gen_outputs.items():
                st.download_button(
                    label=fname,
                    data=fbytes,
                    file_name=fname,
                    mime=(
                        "application/vnd.openxmlformats-officedocument"
                        ".spreadsheetml.sheet"
                        if fname.endswith(".xlsx")
                        else "text/csv"
                    ),
                    key=f"sidebar_dl_{fname}",
                )

        st.divider()
        if st.button("リセット (Reset)", key="btn_reset"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

    # -- Main area ---------------------------------------------------------
    phase = st.session_state["phase"]

    if phase == "A":
        _render_phase_a()
    elif phase == "B":
        _render_phase_b()
    elif phase == "C":
        _render_phase_c()
    else:
        st.error(f"不明なフェーズ: {phase}")
        st.session_state["phase"] = "A"
        st.rerun()


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()
