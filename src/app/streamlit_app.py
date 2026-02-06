"""
PL Generator -- 3-Phase Wizard (Streamlit UI)
=============================================

A three-phase wizard for generating P&L Excel models from business-plan
documents.  UX designed following financial-SaaS best practices (Stripe,
Ramp, Mercury) and Japanese UI conventions.

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
    "その他 (自由入力)",
]

BUSINESS_MODEL_OPTIONS: List[str] = ["B2B", "B2C", "B2B2C", "MIX", "Other"]
CASE_OPTIONS: List[str] = ["Best", "Base", "Worst"]
ALLOWED_DOC_EXTENSIONS: List[str] = ["pdf", "docx", "pptx"]
DEFAULT_TEMPLATE_PATH = "templates/base.xlsx"

# Default colour values
DEFAULT_INPUT_COLOR = "#FFF2CC"
DEFAULT_FORMULA_COLOR = "#4472C4"
DEFAULT_TOTAL_COLOR = "#D9E2F3"

# Phase definitions
PHASES = {
    "A": {"label": "事前カスタマイズ", "en": "Setup", "icon": "1"},
    "B": {"label": "分析結果", "en": "Analysis", "icon": "2"},
    "C": {"label": "カスタマイズ & 生成", "en": "Generate", "icon": "3"},
}


# ---------------------------------------------------------------------------
# Custom CSS for financial-grade UI
# ---------------------------------------------------------------------------

def _inject_custom_css() -> None:
    """Inject custom CSS for professional financial UI."""
    st.markdown("""
    <style>
    /* Step indicator bar */
    .step-bar {
        display: flex;
        justify-content: center;
        gap: 0;
        margin: 0 auto 1.5rem auto;
        max-width: 720px;
    }
    .step-item {
        flex: 1;
        text-align: center;
        padding: 0.75rem 0.5rem;
        font-size: 0.85rem;
        color: #888;
        border-bottom: 3px solid #e0e0e0;
        transition: all 0.2s;
    }
    .step-item.active {
        color: #0f5132;
        font-weight: 700;
        border-bottom: 3px solid #198754;
    }
    .step-item.completed {
        color: #198754;
        border-bottom: 3px solid #198754;
    }
    .step-num {
        display: inline-block;
        width: 24px; height: 24px; line-height: 24px;
        border-radius: 50%;
        background: #e0e0e0; color: #666;
        font-weight: 700; font-size: 0.8rem;
        margin-right: 0.4rem;
    }
    .step-item.active .step-num,
    .step-item.completed .step-num {
        background: #198754; color: white;
    }

    /* Metric cards */
    .metric-card {
        background: linear-gradient(135deg, #f8fffe 0%, #f0faf6 100%);
        border: 1px solid #d4edda;
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
    }
    .metric-value {
        font-size: 2rem; font-weight: 800;
        color: #0f5132; line-height: 1.2;
    }
    .metric-label {
        font-size: 0.8rem; color: #666; margin-top: 0.25rem;
    }

    /* Confidence badges */
    .badge-high {
        display: inline-block; padding: 2px 10px;
        border-radius: 12px; font-size: 0.75rem; font-weight: 600;
        background: #d4edda; color: #0f5132;
    }
    .badge-medium {
        display: inline-block; padding: 2px 10px;
        border-radius: 12px; font-size: 0.75rem; font-weight: 600;
        background: #fff3cd; color: #856404;
    }
    .badge-low {
        display: inline-block; padding: 2px 10px;
        border-radius: 12px; font-size: 0.75rem; font-weight: 600;
        background: #f8d7da; color: #842029;
    }

    /* File upload feedback */
    .file-ok {
        background: #d4edda; border: 1px solid #c3e6cb;
        border-radius: 8px; padding: 0.6rem 1rem;
        color: #155724; font-size: 0.9rem; margin: 0.5rem 0;
    }

    /* Navigation hint */
    .nav-hint {
        text-align: center; color: #999;
        font-size: 0.8rem; margin-top: 0.5rem;
    }

    /* Sidebar polish */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f0faf6 0%, #ffffff 100%);
    }
    </style>
    """, unsafe_allow_html=True)


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
    defaults = {
        "phase": "A",
        "config": None,
        "color_config": ColorConfig(),
        "document": None,
        "catalog": None,
        "analysis": None,
        "parameters": [],
        "extraction_result": None,
        "proposed_changes": [],
        "custom_instruction_text": "",
        "generation_outputs": {},
        "error_message": "",
        "success_message": "",
        "reset_confirm": False,
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default


# ---------------------------------------------------------------------------
# UI Components
# ---------------------------------------------------------------------------

def _render_step_indicator() -> None:
    """Render horizontal 3-step progress indicator."""
    current = st.session_state["phase"]
    phase_order = ["A", "B", "C"]
    current_idx = phase_order.index(current)

    html_parts = ['<div class="step-bar">']
    for idx, code in enumerate(phase_order):
        info = PHASES[code]
        if idx < current_idx:
            cls = "completed"
            check = "&#10003;"
        elif idx == current_idx:
            cls = "active"
            check = info["icon"]
        else:
            cls = ""
            check = info["icon"]

        html_parts.append(
            f'<div class="step-item {cls}">'
            f'<span class="step-num">{check}</span>'
            f'{info["label"]}'
            f'</div>'
        )
    html_parts.append('</div>')
    st.markdown("".join(html_parts), unsafe_allow_html=True)


def _render_metric_card(value: str, label: str) -> str:
    return (
        f'<div class="metric-card">'
        f'<div class="metric-value">{value}</div>'
        f'<div class="metric-label">{label}</div>'
        f'</div>'
    )


def _confidence_badge(confidence: float) -> str:
    if confidence >= 0.7:
        return f'<span class="badge-high">HIGH {confidence:.0%}</span>'
    if confidence >= 0.4:
        return f'<span class="badge-medium">MED {confidence:.0%}</span>'
    return f'<span class="badge-low">LOW {confidence:.0%}</span>'


def _confidence_text(confidence: float) -> str:
    if confidence >= 0.7:
        return "HIGH"
    if confidence >= 0.4:
        return "MED"
    return "LOW"


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _save_uploaded_file(uploaded_file) -> str:
    tmp_dir = tempfile.mkdtemp()
    dest = Path(tmp_dir) / uploaded_file.name
    dest.write_bytes(uploaded_file.getvalue())
    return str(dest)


def _render_dependency_tree_text(node, indent: int = 0) -> str:
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
            colour = "#FFF2CC"
        elif getattr(node, "is_kpi", False):
            shape = "doubleoctagon"
            colour = "#d4edda"
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
# Phase A: Pre-Customisation
# ===================================================================

def _render_phase_a() -> None:
    st.markdown("業種・ビジネスモデルを設定し、事業計画書をアップロードしてください。")

    # -- Section 1: Business Context --
    st.markdown("#### 事業情報 (Business Context)")
    col1, col2, col3 = st.columns(3)

    with col1:
        industry_choice = st.selectbox(
            "業種 (Industry)", options=INDUSTRY_OPTIONS, index=0,
            key="industry_select",
        )
        if "その他" in industry_choice:
            industry = st.text_input(
                "業種を入力", value="", key="industry_freetext",
                placeholder="例: フィンテック",
            )
            if not industry.strip():
                industry = "その他"
        else:
            industry = industry_choice

    with col2:
        business_model = st.selectbox(
            "ビジネスモデル", options=BUSINESS_MODEL_OPTIONS, index=0,
            key="biz_model_select",
        )

    with col3:
        strictness_label = st.selectbox(
            "モデル厳密度",
            options=["ノーマル (normal)", "厳密 (strict)"],
            index=0, key="strictness_select",
            help="厳密: エビデンス必須。ノーマル: LLM推定で補完。",
        )
        strictness = "strict" if "厳密" in strictness_label else "normal"

    # -- Section 2: Case & Options --
    st.markdown("#### ケース設定 (Scenario)")
    col_case, col_sim = st.columns([3, 1])
    with col_case:
        cases = st.multiselect(
            "生成ケース", options=CASE_OPTIONS, default=["Base"],
            key="case_multiselect",
        )
        if not cases:
            cases = ["Base"]
    with col_sim:
        run_simulation = st.checkbox(
            "Monte Carlo", value=False, key="sim_checkbox",
            help="500回のモンテカルロシミュレーションを実行",
        )

    # -- Section 3: File Uploads --
    st.markdown("#### ファイル (Files)")
    col_doc, col_tmpl = st.columns(2)

    with col_doc:
        doc_file = st.file_uploader(
            "事業計画書 (Business Plan)", type=ALLOWED_DOC_EXTENSIONS,
            key="doc_upload", help="PDF / DOCX / PPTX",
        )
        if doc_file:
            ext = doc_file.name.split(".")[-1].upper()
            size_kb = len(doc_file.getvalue()) / 1024
            st.markdown(
                f'<div class="file-ok">&#10003; {doc_file.name} ({ext}, {size_kb:.0f} KB)</div>',
                unsafe_allow_html=True,
            )

    with col_tmpl:
        template_file = st.file_uploader(
            "Excel テンプレート (任意)", type=["xlsx"],
            key="template_upload", help="未指定ならデフォルト使用",
        )
        if template_file:
            size_kb = len(template_file.getvalue()) / 1024
            st.markdown(
                f'<div class="file-ok">&#10003; {template_file.name} ({size_kb:.0f} KB)</div>',
                unsafe_allow_html=True,
            )
        else:
            st.caption("デフォルト: templates/base.xlsx")

    # -- Advanced Settings --
    with st.expander("詳細設定 (Advanced)", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            input_color = st.color_picker("入力セル色", value=DEFAULT_INPUT_COLOR, key="color_input")
        with c2:
            formula_color = st.color_picker("数式フォント色", value=DEFAULT_FORMULA_COLOR, key="color_formula")
        with c3:
            total_color = st.color_picker("合計セル色", value=DEFAULT_TOTAL_COLOR, key="color_total")
        tc1, tc2 = st.columns(2)
        with tc1:
            apply_formula_color = st.toggle("数式色を適用", value=False, key="toggle_formula_color")
        with tc2:
            apply_total_color = st.toggle("合計色を適用", value=False, key="toggle_total_color")

    # -- Start button --
    st.divider()
    if doc_file is None:
        st.info("事業計画書をアップロードすると分析を開始できます。")

    col_s1, col_btn, col_s2 = st.columns([1, 2, 1])
    with col_btn:
        if st.button(
            "分析開始 (Start Analysis)", type="primary",
            disabled=(doc_file is None), use_container_width=True,
            key="btn_start_analysis",
        ):
            _run_phase_a_analysis(
                industry=industry, business_model=business_model,
                strictness=strictness, cases=[c.lower() for c in cases],
                run_simulation=run_simulation,
                input_color=st.session_state.get("color_input", DEFAULT_INPUT_COLOR),
                formula_color=st.session_state.get("color_formula", DEFAULT_FORMULA_COLOR),
                total_color=st.session_state.get("color_total", DEFAULT_TOTAL_COLOR),
                apply_formula_color=st.session_state.get("toggle_formula_color", False),
                apply_total_color=st.session_state.get("toggle_total_color", False),
                doc_file=doc_file, template_file=template_file,
            )

    if doc_file is not None:
        st.markdown('<p class="nav-hint">通常 30〜60 秒かかります</p>', unsafe_allow_html=True)


def _run_phase_a_analysis(
    *, industry: str, business_model: str, strictness: str,
    cases: List[str], run_simulation: bool,
    input_color: str, formula_color: str, total_color: str,
    apply_formula_color: bool, apply_total_color: bool,
    doc_file, template_file,
) -> None:
    progress = st.progress(0, text="準備中...")

    try:
        progress.progress(5, text="ファイルを保存中...")
        doc_path = _save_uploaded_file(doc_file)

        if template_file is not None:
            template_path = _save_uploaded_file(template_file)
        else:
            template_path = DEFAULT_TEMPLATE_PATH
            if not Path(template_path).exists():
                st.error("デフォルトテンプレートが見つかりません。テンプレートをアップロードしてください。")
                progress.empty()
                return

        progress.progress(10, text="設定を構築中...")
        config = PhaseAConfig(
            industry=industry, business_model=business_model,
            strictness=strictness, cases=cases,
            template_path=template_path, document_paths=[doc_path],
        )
        st.session_state["config"] = config
        st.session_state["run_simulation"] = run_simulation

        cc = ColorConfig(
            input_color=input_color, formula_color=formula_color,
            total_color=total_color, apply_formula_color=apply_formula_color,
            apply_total_color=apply_total_color,
        )
        st.session_state["color_config"] = cc

        progress.progress(20, text="事業計画書を読み取り中...")
        document = read_document(doc_path)
        st.session_state["document"] = document

        progress.progress(40, text="テンプレートをスキャン中...")
        input_color_hex = input_color.lstrip("#")
        if len(input_color_hex) == 6:
            input_color_hex = "FF" + input_color_hex
        catalog = scan_template(template_path, input_color=input_color_hex)
        st.session_state["catalog"] = catalog

        progress.progress(55, text="数式構造を分析中...")
        analysis = analyze_model(template_path, catalog)
        st.session_state["analysis"] = analysis

        progress.progress(70, text="LLM パラメータ抽出中...")
        llm_client = LLMClient()
        extractor = ParameterExtractor(config, llm_client=llm_client)
        parameters = extractor.extract_parameters(document, catalog)
        st.session_state["parameters"] = parameters

        progress.progress(100, text="分析完了!")
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
        st.error("分析中にエラーが発生しました")
        with st.expander("エラー詳細"):
            st.code(traceback.format_exc())


# ===================================================================
# Phase B: Analysis Results
# ===================================================================

def _render_phase_b() -> None:
    analysis: AnalysisReport | None = st.session_state.get("analysis")
    catalog: InputCatalog | None = st.session_state.get("catalog")
    parameters: list = st.session_state.get("parameters", [])

    if analysis is None or catalog is None:
        st.warning("分析データがありません。Phase A に戻ってください。")
        if st.button("Phase A に戻る"):
            st.session_state["phase"] = "A"
            st.rerun()
        return

    # -- Summary Dashboard --
    _render_analysis_summary(analysis, catalog, parameters)

    st.divider()

    # -- Tabs --
    tab_model, tab_params, tab_evidence = st.tabs([
        "モデル構造",
        f"抽出パラメータ ({len(parameters)})",
        "エビデンス",
    ])
    with tab_model:
        _render_model_content_tab(analysis, catalog)
    with tab_params:
        _render_extracted_parameters_tab(parameters)
    with tab_evidence:
        _render_evidence_tab(parameters)

    # -- Navigation --
    st.divider()
    col_back, col_spacer, col_fwd = st.columns([1, 2, 1])
    with col_back:
        if st.button("← Phase A", key="b_back"):
            st.session_state["phase"] = "A"
            st.rerun()
    with col_fwd:
        if st.button("カスタマイズへ →", type="primary", use_container_width=True, key="b_forward"):
            st.session_state["phase"] = "C"
            st.rerun()


def _render_analysis_summary(analysis, catalog, parameters) -> None:
    total_params = len(parameters)
    total_kpis = len(analysis.kpis) if analysis.kpis else 0
    total_inputs = len(catalog.items)
    sheet_count = len({item.sheet for item in catalog.items if item.sheet})

    high_conf = sum(1 for p in parameters if getattr(p, "confidence", 0) >= 0.7)
    med_conf = sum(1 for p in parameters if 0.4 <= getattr(p, "confidence", 0) < 0.7)
    low_conf = sum(1 for p in parameters if getattr(p, "confidence", 0) < 0.4)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(_render_metric_card(str(total_params), "抽出パラメータ"), unsafe_allow_html=True)
    with c2:
        st.markdown(_render_metric_card(str(total_kpis), "KPI 検出"), unsafe_allow_html=True)
    with c3:
        st.markdown(_render_metric_card(str(total_inputs), "入力セル"), unsafe_allow_html=True)
    with c4:
        st.markdown(_render_metric_card(str(sheet_count), "シート数"), unsafe_allow_html=True)

    if total_params > 0:
        st.markdown("")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f'<span class="badge-high">HIGH: {high_conf}</span> ({high_conf/total_params:.0%})', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<span class="badge-medium">MED: {med_conf}</span> ({med_conf/total_params:.0%})', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<span class="badge-low">LOW: {low_conf}</span> ({low_conf/total_params:.0%})', unsafe_allow_html=True)


def _render_model_content_tab(analysis, catalog) -> None:
    if analysis.summary:
        st.markdown(f"**モデル概要:** {analysis.summary}")

    sheet_names = sorted({item.sheet for item in catalog.items if item.sheet})
    if sheet_names:
        st.markdown("**シート構成:**")
        import pandas as pd
        sheet_data = []
        for sn in sheet_names:
            items_count = sum(1 for item in catalog.items if item.sheet == sn)
            kpi_count = sum(1 for k in (analysis.kpis or []) if getattr(k, "sheet", None) == sn)
            sheet_data.append({"シート": sn, "入力セル数": items_count, "KPI数": kpi_count})
        st.dataframe(pd.DataFrame(sheet_data), use_container_width=True, hide_index=True)

    st.markdown("**KPI 定義:**")
    if analysis.kpis:
        for kpi in analysis.kpis:
            formula = kpi.raw_formula or kpi.excel_formula or ""
            human = kpi.human_readable_formula or kpi.human_formula or ""
            with st.expander(f"{kpi.name} ({kpi.sheet}!{kpi.cell})"):
                if formula:
                    st.code(formula, language=None)
                if human:
                    st.caption(human)
                if kpi.dependencies:
                    st.markdown("依存先: " + ", ".join(f"`{d}`" for d in kpi.dependencies))
    else:
        st.info("KPI が検出されませんでした。")

    if analysis.dependency_tree:
        st.markdown("**依存関係ツリー:**")
        view_mode = st.radio("表示形式", options=["テキスト", "Graphviz"], horizontal=True, key="dep_tree_mode")
        for addr, node in analysis.dependency_tree.items():
            label = getattr(node, "label", "") or addr
            with st.expander(f"Tree: {label}"):
                if view_mode == "Graphviz":
                    try:
                        dot_body = _dep_tree_to_dot(node)
                        st.graphviz_chart(f"digraph {{\n  rankdir=LR;\n{dot_body}\n}}")
                    except Exception:
                        st.code(_render_dependency_tree_text(node))
                else:
                    st.code(_render_dependency_tree_text(node))


def _render_extracted_parameters_tab(parameters: list) -> None:
    if not parameters:
        st.info("抽出されたパラメータがありません。")
        return

    rows: List[Dict[str, Any]] = []
    for p in parameters:
        mapped_cells = ", ".join(f"{t.sheet}!{t.cell}" for t in getattr(p, "mapped_targets", []))
        conf = getattr(p, "confidence", 0.0)
        rows.append({
            "key": getattr(p, "key", ""),
            "label": getattr(p, "label", ""),
            "value": getattr(p, "value", ""),
            "unit": getattr(p, "unit", "") or "",
            "confidence": conf,
            "level": _confidence_text(conf),
            "source": getattr(p, "source", ""),
            "mapped_cells": mapped_cells,
        })

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        source_filter = st.multiselect(
            "ソースで絞り込み",
            options=sorted({r["source"] for r in rows if r["source"]}),
            default=[], key="param_source_filter",
        )
    with col_f2:
        conf_filter = st.select_slider(
            "最低信頼度", options=["ALL", "LOW+", "MED+", "HIGH"],
            value="ALL", key="param_conf_filter",
        )

    filtered = rows
    if source_filter:
        filtered = [r for r in filtered if r["source"] in source_filter]
    conf_thresholds = {"ALL": 0.0, "LOW+": 0.0, "MED+": 0.4, "HIGH": 0.7}
    threshold = conf_thresholds.get(conf_filter, 0.0)
    filtered = [r for r in filtered if r["confidence"] >= threshold]

    st.caption(f"{len(filtered)} / {len(rows)} パラメータ表示中")

    import pandas as pd
    df = pd.DataFrame(filtered)
    if not df.empty:
        display_cols = ["label", "value", "unit", "level", "source", "mapped_cells"]
        display_df = df[display_cols].rename(columns={
            "label": "パラメータ", "value": "値", "unit": "単位",
            "level": "信頼度", "source": "ソース", "mapped_cells": "マッピング先",
        })
        styled = display_df.style.applymap(
            lambda val: (
                "background-color: #d4edda; color: #0f5132" if val == "HIGH"
                else "background-color: #fff3cd; color: #856404" if val == "MED"
                else "background-color: #f8d7da; color: #842029" if val == "LOW"
                else ""
            ),
            subset=["信頼度"],
        )
        st.dataframe(styled, use_container_width=True, height=500, hide_index=True)
    else:
        st.info("フィルタ条件に一致するパラメータがありません。")


def _render_evidence_tab(parameters: list) -> None:
    has_evidence = [p for p in parameters if getattr(getattr(p, "evidence", None), "quote", "")]
    if not has_evidence:
        st.info("エビデンスが記録されたパラメータはありません。")
        return

    st.caption(f"{len(has_evidence)} 件のパラメータにエビデンスあり")
    for p in has_evidence:
        ev = p.evidence
        conf = getattr(p, "confidence", 0.0)
        with st.expander(f"{getattr(p, 'label', p.key)}"):
            st.markdown(f"> {ev.quote}")
            cols = st.columns(3)
            with cols[0]:
                st.markdown(_confidence_badge(conf), unsafe_allow_html=True)
            with cols[1]:
                if getattr(ev, "page_or_slide", ""):
                    st.caption(f"ページ: {ev.page_or_slide}")
            with cols[2]:
                if getattr(ev, "rationale", ""):
                    st.caption(f"根拠: {ev.rationale}")


# ===================================================================
# Phase C: Pre-Generation Customisation
# ===================================================================

def _render_phase_c() -> None:
    parameters: list = st.session_state.get("parameters", [])
    config: PhaseAConfig | None = st.session_state.get("config")
    catalog: InputCatalog | None = st.session_state.get("catalog")

    if not parameters or config is None:
        st.warning("パラメータがありません。Phase A に戻ってください。")
        if st.button("Phase A に戻る", key="c_back_warn"):
            st.session_state["phase"] = "A"
            st.rerun()
        return

    # -- Pre-flight summary --
    _render_preflight_summary(parameters, config)
    st.divider()

    # -- Case customisation --
    multiple_cases = config and len(config.cases) > 1
    if multiple_cases:
        case_tabs = st.tabs([f"{c.title()} ケース" for c in config.cases])
        for idx, case_name in enumerate(config.cases):
            with case_tabs[idx]:
                _render_case_customisation(parameters, case_name, catalog, suffix=f"_{case_name}")
    else:
        _render_case_customisation(
            parameters, config.cases[0] if config.cases else "base",
            catalog, suffix="_single",
        )

    # -- Custom Instructions --
    st.divider()
    _render_custom_instructions_section(parameters)

    # -- Navigation --
    st.divider()
    col_back, col_spacer, col_gen = st.columns([1, 1, 2])
    with col_back:
        if st.button("← Phase B", key="c_back"):
            st.session_state["phase"] = "B"
            st.rerun()
    with col_gen:
        if st.button("Excel 生成 (Generate)", type="primary", use_container_width=True, key="btn_generate"):
            _run_generation()


def _render_preflight_summary(parameters, config) -> None:
    total = len(parameters)
    mapped = sum(1 for p in parameters if getattr(p, "mapped_targets", []))
    high_conf = sum(1 for p in parameters if getattr(p, "confidence", 0) >= 0.7)
    low_conf = sum(1 for p in parameters if getattr(p, "confidence", 0) < 0.4)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("パラメータ数", total)
    with c2:
        st.metric("マッピング済み", f"{mapped}/{total}")
    with c3:
        st.metric("高信頼度", high_conf)
    with c4:
        if low_conf > 0:
            st.metric("要確認", low_conf, delta=f"-{low_conf}", delta_color="inverse")
        else:
            st.metric("要確認", 0)

    if low_conf > 0:
        st.warning(f"{low_conf} 件の低信頼度パラメータがあります。値を確認してから生成してください。")


def _render_case_customisation(parameters, case_name, catalog, suffix="") -> None:
    grouped: Dict[str, List] = {}
    for p in parameters:
        targets = getattr(p, "mapped_targets", [])
        group_key = targets[0].sheet if targets else "未分類"
        grouped.setdefault(group_key, []).append(p)

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

    diff_rows: List[Dict[str, Any]] = []

    for group_name, group_params in grouped.items():
        with st.expander(f"{group_name} ({len(group_params)} パラメータ)", expanded=False):
            for p in group_params:
                sel_key = f"sel_{p.key}{suffix}"
                adj_key = f"adj_{p.key}{suffix}"
                mul_key = f"mul_{p.key}{suffix}"
                original_value = p.value if p.value is not None else 0
                is_numeric = isinstance(original_value, (int, float))

                cols = st.columns([0.5, 3, 2, 1.5])
                with cols[0]:
                    selected = st.checkbox("on", value=st.session_state.get(sel_key, True), key=sel_key, label_visibility="collapsed")
                with cols[1]:
                    label = getattr(p, "label", p.key)
                    conf = getattr(p, "confidence", 0)
                    st.markdown(f"**{label}** {_confidence_badge(conf)}", unsafe_allow_html=True)
                if not selected:
                    with cols[2]:
                        st.caption("(除外)")
                    continue
                with cols[2]:
                    if is_numeric:
                        new_val = st.number_input("値", value=float(original_value), key=adj_key, format="%.2f", label_visibility="collapsed")
                    else:
                        new_val = st.text_input("値", value=str(original_value), key=adj_key, label_visibility="collapsed")
                with cols[3]:
                    if is_numeric:
                        multiplier = st.number_input("倍率", min_value=0.1, max_value=5.0, value=st.session_state.get(mul_key, 1.0), step=0.05, key=mul_key, label_visibility="collapsed")
                    else:
                        multiplier = 1.0

                if is_numeric:
                    effective = float(new_val) * multiplier
                    if abs(effective - float(original_value)) > 0.001:
                        change_pct = ((effective - float(original_value)) / float(original_value) * 100) if float(original_value) != 0 else 0
                        diff_rows.append({
                            "パラメータ": getattr(p, "label", p.key),
                            "旧値": f"{float(original_value):,.2f}",
                            "新値": f"{effective:,.2f}",
                            "変化率": f"{change_pct:+.1f}%",
                        })
                elif str(new_val) != str(original_value):
                    diff_rows.append({
                        "パラメータ": getattr(p, "label", p.key),
                        "旧値": str(original_value),
                        "新値": str(new_val),
                        "変化率": "-",
                    })

    if diff_rows:
        st.markdown(f"**変更プレビュー ({len(diff_rows)} 件):**")
        import pandas as pd
        st.dataframe(pd.DataFrame(diff_rows), use_container_width=True, hide_index=True)


def _render_custom_instructions_section(parameters: list) -> None:
    st.markdown("#### カスタマイズ指示 (Custom Instructions)")
    st.caption("自然言語で指示するとLLMがパラメータ変更に変換します。")

    instruction = st.text_area(
        "指示", value=st.session_state.get("custom_instruction_text", ""),
        height=100, key="custom_instruction_area",
        placeholder="例: 売上を20%増加。人件費を月額50万円に設定。",
        label_visibility="collapsed",
    )
    st.session_state["custom_instruction_text"] = instruction

    if st.button("指示を解析", key="btn_parse_instr", disabled=not instruction.strip()):
        _parse_custom_instruction(instruction, parameters)

    proposed: List[ProposedChange] = st.session_state.get("proposed_changes", [])
    if proposed:
        st.markdown(f"**提案された変更 ({len(proposed)} 件):**")
        for idx, pc in enumerate(proposed):
            col_desc, col_toggle = st.columns([5, 1])
            with col_desc:
                st.markdown(f"`{pc.parameter_key}`: {pc.original_value} → **{pc.proposed_value}**")
                if pc.reason:
                    st.caption(pc.reason)
            with col_toggle:
                accepted = st.toggle("適用", value=pc.accepted, key=f"pc_accept_{idx}")
                proposed[idx].accepted = accepted
        st.session_state["proposed_changes"] = proposed


def _parse_custom_instruction(instruction: str, parameters: list) -> None:
    try:
        with st.spinner("指示を解析中..."):
            llm = LLMClient()
            params_json = json.dumps(
                [{"key": p.key, "label": getattr(p, "label", ""), "value": p.value, "unit": getattr(p, "unit", "")} for p in parameters],
                ensure_ascii=False, indent=2,
            )
            result = llm.process_instruction(instruction, params_json)

        changes_raw = result.get("changes", [])
        proposed: List[ProposedChange] = []
        for ch in changes_raw:
            proposed.append(ProposedChange(
                parameter_key=ch.get("parameter_key", ""),
                original_value=ch.get("original_value"),
                proposed_value=ch.get("proposed_value"),
                reason=ch.get("reason", ""),
                affected_cases=ch.get("affected_cases", []),
                evidence_from_instruction=ch.get("evidence_from_instruction", ""),
                accepted=True,
            ))
        st.session_state["proposed_changes"] = proposed

        if proposed:
            st.success(f"{len(proposed)} 件の変更を提案しました")
        else:
            st.info("指示から変更を検出できませんでした。")
    except Exception as exc:  # noqa: BLE001
        st.error(f"指示の解析中にエラー: {exc}")


# ===================================================================
# Generation
# ===================================================================

def _apply_adjustments_to_parameters(parameters: list, suffix: str) -> list:
    adjusted = deepcopy(parameters)
    for p in adjusted:
        sel_key = f"sel_{p.key}{suffix}"
        adj_key = f"adj_{p.key}{suffix}"
        mul_key = f"mul_{p.key}{suffix}"

        selected = st.session_state.get(sel_key, True)
        try:
            p.selected = selected  # type: ignore[attr-defined]
        except (AttributeError, TypeError):
            pass
        if not selected:
            continue

        adj_val = st.session_state.get(adj_key, p.value)
        multiplier = st.session_state.get(mul_key, 1.0)
        if isinstance(adj_val, (int, float)) and isinstance(multiplier, (int, float)):
            effective = float(adj_val) * float(multiplier)
        else:
            effective = adj_val
        try:
            p.adjusted_value = effective  # type: ignore[attr-defined]
        except (AttributeError, TypeError):
            pass

    proposed: List[ProposedChange] = st.session_state.get("proposed_changes", [])
    param_map = {p.key: p for p in adjusted}
    for pc in proposed:
        if not pc.accepted:
            continue
        if pc.parameter_key in param_map:
            try:
                param_map[pc.parameter_key].adjusted_value = pc.proposed_value  # type: ignore[attr-defined]
            except (AttributeError, TypeError):
                pass

    return adjusted


def _run_generation() -> None:
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
        cases = config.cases if config.cases else ["base"]
        total_steps = len(cases) + 2
        step = 0

        for case_name in cases:
            step += 1
            progress.progress(int(step / total_steps * 80), text=f"{case_name.title()} ケースを生成中...")

            suffix = f"_{case_name}" if len(cases) > 1 else "_single"
            adjusted_params = _apply_adjustments_to_parameters(parameters, suffix)

            if case_name != "base" and len(cases) > 1:
                try:
                    gen = CaseGenerator(config)
                    case_sets = gen.generate_cases(adjusted_params)
                    if case_name in case_sets:
                        adjusted_params = case_sets[case_name]
                except Exception as exc:
                    st.warning(f"{case_name} ケース生成に問題: {exc}")

            with tempfile.TemporaryDirectory() as tmp_dir:
                output_path = str(Path(tmp_dir) / f"PL_{case_name}.xlsx")
                try:
                    try:
                        config.colors = cc  # type: ignore[attr-defined]
                    except (AttributeError, TypeError):
                        pass

                    writer = PLWriter(template_path=config.template_path, output_path=output_path, config=config)
                    writer.generate(adjusted_params)

                    try:
                        validator = PLValidator(config.template_path, output_path)
                        val_result = validator.validate()
                        if not val_result.passed:
                            st.warning(f"{case_name.title()}: バリデーション警告 ({len(val_result.errors_found)} 件)")
                            with st.expander(f"{case_name.title()} バリデーション詳細"):
                                for err in val_result.errors_found:
                                    st.error(err)
                                for warn in val_result.warnings:
                                    st.warning(warn)
                        else:
                            st.success(f"{case_name.title()}: バリデーション OK")
                    except Exception as ve:
                        st.warning(f"バリデーション失敗: {ve}")

                    output_files[f"PL_{case_name}.xlsx"] = Path(output_path).read_bytes()

                except Exception as exc:
                    st.error(f"{case_name.title()} ケース生成エラー: {exc}")
                    with st.expander("エラー詳細"):
                        st.code(traceback.format_exc())

        # Simulation
        run_sim = st.session_state.get("run_simulation", False)
        if run_sim and parameters and SimulationEngine is not None:
            step += 1
            progress.progress(int(step / total_steps * 95), text="シミュレーション実行中 (500回)...")
            try:
                sim_engine = SimulationEngine(iterations=500)
                sim_params = _apply_adjustments_to_parameters(parameters, "_single" if len(cases) <= 1 else f"_{cases[0]}")
                sim_report = sim_engine.run(sim_params, template_path=config.template_path)

                with tempfile.TemporaryDirectory() as sim_dir:
                    sim_path = str(Path(sim_dir) / "simulation_summary.xlsx")
                    export_simulation_summary(sim_report, sim_path)
                    output_files["simulation_summary.xlsx"] = Path(sim_path).read_bytes()

                st.success("シミュレーション完了")
                with st.expander("シミュレーション結果サマリー"):
                    for s in sim_report.summaries:
                        st.markdown(f"**{s.kpi_name}**: 平均={s.mean:,.0f}, P10={s.p10:,.0f}, P50={s.p50:,.0f}, P90={s.p90:,.0f}")
            except Exception as exc:
                st.warning(f"シミュレーション失敗: {exc}")

        # needs_review CSV
        try:
            with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as tmp_csv:
                csv_path = generate_needs_review_csv(parameters, tmp_csv.name)
                output_files["needs_review.csv"] = Path(csv_path).read_bytes()
        except Exception:
            pass

        progress.progress(100, text="生成完了!")
        st.session_state["generation_outputs"] = output_files

    except Exception as exc:  # noqa: BLE001
        progress.empty()
        st.error("生成中にエラーが発生しました")
        with st.expander("エラー詳細"):
            st.code(traceback.format_exc())
        return

    # Download
    st.divider()
    st.markdown("#### ダウンロード")
    if output_files:
        cols = st.columns(min(len(output_files), 3))
        for idx, (fname, fbytes) in enumerate(output_files.items()):
            with cols[idx % len(cols)]:
                st.download_button(
                    label=f"{'📊' if fname.endswith('.xlsx') else '📋'} {fname}",
                    data=fbytes, file_name=fname,
                    mime=("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if fname.endswith(".xlsx") else "text/csv"),
                    use_container_width=True, key=f"dl_{fname}",
                )
        st.markdown('<p class="nav-hint">ファイルが正しく生成されました</p>', unsafe_allow_html=True)
    else:
        st.info("生成ファイルがありません。")


# ===================================================================
# Sidebar
# ===================================================================

def _render_sidebar() -> None:
    with st.sidebar:
        st.markdown("# PL Generator")
        st.caption("事業計画書 → P&L Excel 自動生成")

        if _IMPORT_ERRORS:
            with st.expander("Import Warnings", expanded=False):
                for ie in _IMPORT_ERRORS:
                    st.warning(ie)

        st.divider()

        cfg = st.session_state.get("config")
        if cfg:
            st.markdown("**セッション情報**")
            st.caption(f"業種: {cfg.industry}")
            st.caption(f"モデル: {cfg.business_model}")
            st.caption(f"厳密度: {cfg.strictness}")
            st.caption(f"ケース: {', '.join(c.title() for c in cfg.cases)}")
            params = st.session_state.get("parameters", [])
            if params:
                st.caption(f"パラメータ: {len(params)} 件")

        gen_outputs = st.session_state.get("generation_outputs", {})
        if gen_outputs:
            st.divider()
            st.markdown("**生成済みファイル**")
            for fname, fbytes in gen_outputs.items():
                st.download_button(
                    label=fname, data=fbytes, file_name=fname,
                    mime=("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if fname.endswith(".xlsx") else "text/csv"),
                    key=f"sidebar_dl_{fname}", use_container_width=True,
                )

        st.divider()
        if not st.session_state.get("reset_confirm", False):
            if st.button("リセット (Reset)", key="btn_reset", use_container_width=True):
                st.session_state["reset_confirm"] = True
                st.rerun()
        else:
            st.warning("本当にリセットしますか？")
            col_yes, col_no = st.columns(2)
            with col_yes:
                if st.button("はい", key="btn_reset_yes", type="primary"):
                    for k in list(st.session_state.keys()):
                        del st.session_state[k]
                    st.rerun()
            with col_no:
                if st.button("キャンセル", key="btn_reset_no"):
                    st.session_state["reset_confirm"] = False
                    st.rerun()


# ===================================================================
# Main
# ===================================================================

def main() -> None:
    st.set_page_config(page_title="PL Generator", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

    _init_session_state()
    _inject_custom_css()
    _render_sidebar()
    _render_step_indicator()

    phase = st.session_state["phase"]
    if phase == "A":
        _render_phase_a()
    elif phase == "B":
        _render_phase_b()
    elif phase == "C":
        _render_phase_c()
    else:
        st.session_state["phase"] = "A"
        st.rerun()


if __name__ == "__main__":
    main()
