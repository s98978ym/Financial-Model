"""
PL Generator -- PL Blueprint Wizard (Streamlit UI)
===================================================

A two-phase wizard for generating P&L Excel models from business-plan
documents.  The "PL Blueprint" view shows the template structure as the
organising principle, with extracted values filling slots and gaps
clearly visible.

* **Phase A** -- Upload & Analysis  (アップロード & 分析)
* **Phase B** -- PL Blueprint       (PL 設計図 & 生成)

Run with::

    streamlit run src/app/streamlit_app.py
"""

from __future__ import annotations

import html as html_mod
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

# Phase definitions (2-phase flow)
PHASES = {
    "A": {"label": "アップロード & 分析", "en": "Upload", "icon": "1"},
    "B": {"label": "PL 設計図", "en": "Blueprint", "icon": "2"},
}


# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------

def _inject_custom_css() -> None:
    st.markdown("""
    <style>
    /* Step indicator bar */
    .step-bar {
        display: flex; justify-content: center; gap: 0;
        margin: 0 auto 1.5rem auto; max-width: 720px;
    }
    .step-item {
        flex: 1; text-align: center; padding: 0.75rem 0.5rem;
        font-size: 0.85rem; color: #888;
        border-bottom: 3px solid #e0e0e0; transition: all 0.2s;
    }
    .step-item.active {
        color: #0f5132; font-weight: 700;
        border-bottom: 3px solid #198754;
    }
    .step-item.completed {
        color: #198754; border-bottom: 3px solid #198754;
    }
    .step-num {
        display: inline-block; width: 24px; height: 24px;
        line-height: 24px; border-radius: 50%;
        background: #e0e0e0; color: #666;
        font-weight: 700; font-size: 0.8rem; margin-right: 0.4rem;
    }
    .step-item.active .step-num,
    .step-item.completed .step-num {
        background: #198754; color: white;
    }

    /* Metric cards */
    .metric-card {
        background: linear-gradient(135deg, #f8fffe 0%, #f0faf6 100%);
        border: 1px solid #d4edda; border-radius: 12px;
        padding: 1.2rem; text-align: center;
    }
    .metric-value {
        font-size: 2rem; font-weight: 800;
        color: #0f5132; line-height: 1.2;
    }
    .metric-label { font-size: 0.8rem; color: #666; margin-top: 0.25rem; }

    /* Gap metric (red accent) */
    .metric-card-gap {
        background: linear-gradient(135deg, #fff8f8 0%, #fef0f0 100%);
        border: 1px solid #f5c6cb; border-radius: 12px;
        padding: 1.2rem; text-align: center;
    }
    .metric-card-gap .metric-value { color: #842029; }

    /* Confidence badges */
    .badge-high {
        display: inline-block; padding: 2px 10px; border-radius: 12px;
        font-size: 0.75rem; font-weight: 600;
        background: #d4edda; color: #0f5132;
    }
    .badge-medium {
        display: inline-block; padding: 2px 10px; border-radius: 12px;
        font-size: 0.75rem; font-weight: 600;
        background: #fff3cd; color: #856404;
    }
    .badge-low {
        display: inline-block; padding: 2px 10px; border-radius: 12px;
        font-size: 0.75rem; font-weight: 600;
        background: #f8d7da; color: #842029;
    }
    .badge-gap {
        display: inline-block; padding: 2px 10px; border-radius: 12px;
        font-size: 0.75rem; font-weight: 600;
        background: #e2e3e5; color: #41464b;
    }

    /* File upload feedback */
    .file-ok {
        background: #d4edda; border: 1px solid #c3e6cb;
        border-radius: 8px; padding: 0.6rem 1rem;
        color: #155724; font-size: 0.9rem; margin: 0.5rem 0;
    }

    /* KPI banner */
    .kpi-banner {
        background: linear-gradient(135deg, #e8f4fd 0%, #f0f7ff 100%);
        border-left: 4px solid #0d6efd; border-radius: 8px;
        padding: 1rem; margin-bottom: 1rem;
    }
    .kpi-banner-title {
        font-weight: 700; color: #0d47a1;
        margin-bottom: 0.5rem; font-size: 0.95rem;
    }
    .kpi-banner ul {
        margin: 0; padding-left: 1.2rem;
        font-size: 0.88rem; line-height: 1.7;
    }
    .kpi-banner li { color: #333; }
    .kpi-dep { color: #666; font-size: 0.78rem; }

    /* Navigation hint */
    .nav-hint {
        text-align: center; color: #999;
        font-size: 0.8rem; margin-top: 0.5rem;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f0faf6 0%, #ffffff 100%);
    }
    </style>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Lightweight local dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ColorConfig:
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
    current = st.session_state["phase"]
    phase_order = ["A", "B"]
    current_idx = phase_order.index(current) if current in phase_order else 0

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


def _render_gap_metric_card(value: str, label: str) -> str:
    return (
        f'<div class="metric-card-gap">'
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


def _esc(text: str) -> str:
    """HTML-escape a string for safe embedding in markdown."""
    return html_mod.escape(str(text)) if text else ""


# ===================================================================
# Phase A: Upload & Analysis
# ===================================================================

def _render_phase_a() -> None:
    st.markdown("#### 事業計画書をアップロードしてください")
    doc_file = st.file_uploader(
        "事業計画書", type=ALLOWED_DOC_EXTENSIONS,
        key="doc_upload", label_visibility="collapsed",
    )

    if doc_file:
        ext = doc_file.name.split(".")[-1].upper()
        size_kb = len(doc_file.getvalue()) / 1024
        st.markdown(
            f'<div class="file-ok">&#10003; {doc_file.name} ({ext}, {size_kb:.0f} KB) アップロード済み</div>',
            unsafe_allow_html=True,
        )

        if st.button(
            "分析開始",
            type="primary",
            use_container_width=True,
            key="btn_start_analysis",
        ):
            industry = st.session_state.get("industry_select", "SaaS")
            if "その他" in industry:
                industry = st.session_state.get("industry_freetext", "その他") or "その他"
            business_model = st.session_state.get("biz_model_select", "B2B")
            strictness_label = st.session_state.get("strictness_select", "ノーマル (normal)")
            strictness = "strict" if "厳密" in strictness_label else "normal"
            cases_raw = st.session_state.get("case_multiselect", ["Base"])
            if not cases_raw:
                cases_raw = ["Base"]
            run_simulation = st.session_state.get("sim_checkbox", False)

            _run_phase_a_analysis(
                industry=industry, business_model=business_model,
                strictness=strictness, cases=[c.lower() for c in cases_raw],
                run_simulation=run_simulation,
                input_color=st.session_state.get("color_input", DEFAULT_INPUT_COLOR),
                formula_color=st.session_state.get("color_formula", DEFAULT_FORMULA_COLOR),
                total_color=st.session_state.get("color_total", DEFAULT_TOTAL_COLOR),
                apply_formula_color=st.session_state.get("toggle_formula_color", False),
                apply_total_color=st.session_state.get("toggle_total_color", False),
                doc_file=doc_file,
                template_file=st.session_state.get("template_upload_file", None),
            )

        st.caption("通常 30〜60 秒かかります")

    else:
        st.markdown(
            '<div style="text-align:center; padding:3rem 1rem; '
            'color:#999; border:2px dashed #ddd; border-radius:12px; '
            'margin:1rem 0;">'
            '<p style="font-size:1.2rem;">PDF / DOCX / PPTX ファイルを'
            'ドラッグ＆ドロップ</p>'
            '<p style="font-size:0.85rem;">またはクリックしてファイルを選択</p>'
            '</div>',
            unsafe_allow_html=True,
        )

    # Optional settings (collapsed)
    st.markdown("")
    with st.expander("設定をカスタマイズ（任意 - デフォルトでも動作します）", expanded=False):
        st.caption("通常は変更不要です。必要な場合のみ調整してください。")

        col1, col2 = st.columns(2)
        with col1:
            industry_choice = st.selectbox(
                "業種", options=INDUSTRY_OPTIONS, index=0,
                key="industry_select",
            )
            if "その他" in industry_choice:
                st.text_input("業種を入力", value="", key="industry_freetext", placeholder="例: フィンテック")
            st.selectbox(
                "ビジネスモデル", options=BUSINESS_MODEL_OPTIONS, index=0,
                key="biz_model_select",
            )
        with col2:
            st.selectbox(
                "厳密度",
                options=["ノーマル (normal)", "厳密 (strict)"],
                index=0, key="strictness_select",
                help="厳密: エビデンス必須。ノーマル: LLM推定で補完。",
            )
            st.multiselect(
                "生成ケース", options=CASE_OPTIONS, default=["Base"],
                key="case_multiselect",
            )
            st.checkbox(
                "Monte Carlo シミュレーション", value=False, key="sim_checkbox",
            )

        st.markdown("---")
        template_file = st.file_uploader(
            "Excel テンプレート（任意 - 未指定ならデフォルト使用）", type=["xlsx"],
            key="template_upload",
        )
        if template_file:
            st.session_state["template_upload_file"] = template_file

        st.markdown("---")
        st.caption("セル色設定")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.color_picker("入力セル色", value=DEFAULT_INPUT_COLOR, key="color_input")
        with c2:
            st.color_picker("数式フォント色", value=DEFAULT_FORMULA_COLOR, key="color_formula")
        with c3:
            st.color_picker("合計セル色", value=DEFAULT_TOTAL_COLOR, key="color_total")
        tc1, tc2 = st.columns(2)
        with tc1:
            st.toggle("数式色を適用", value=False, key="toggle_formula_color")
        with tc2:
            st.toggle("合計色を適用", value=False, key="toggle_total_color")


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

        # Clear old blueprint state
        for key in list(st.session_state.keys()):
            if key.startswith("bp_"):
                del st.session_state[key]

        # Clear old generation outputs
        st.session_state["generation_outputs"] = {}

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
# Phase B: PL Blueprint
# ===================================================================

def _build_param_cell_map(parameters: list) -> Dict[str, Any]:
    """Build a lookup from 'Sheet!Cell' address to ExtractedParameter."""
    cell_map: Dict[str, Any] = {}
    for p in parameters:
        for target in getattr(p, "mapped_targets", []):
            addr = f"{target.sheet}!{target.cell}"
            cell_map[addr] = p
    return cell_map


def _count_sheet_items(sheet_name: str, catalog: InputCatalog) -> int:
    return sum(1 for item in catalog.items
               if item.sheet == sheet_name and not item.has_formula)


def _count_sheet_filled(sheet_name: str, catalog: InputCatalog, param_map: dict) -> int:
    count = 0
    for item in catalog.items:
        if item.sheet != sheet_name or item.has_formula:
            continue
        addr = f"{item.sheet}!{item.cell}"
        if addr in param_map:
            count += 1
    return count


def _render_phase_b() -> None:
    """PL Blueprint -- the template structure IS the UI."""
    analysis: AnalysisReport | None = st.session_state.get("analysis")
    catalog: InputCatalog | None = st.session_state.get("catalog")
    parameters: list = st.session_state.get("parameters", [])
    config: PhaseAConfig | None = st.session_state.get("config")

    if analysis is None or catalog is None:
        st.warning("分析データがありません。Phase A に戻ってください。")
        if st.button("Phase A に戻る"):
            st.session_state["phase"] = "A"
            st.rerun()
        return

    param_map = _build_param_cell_map(parameters)

    # --- Summary Dashboard ---
    _render_blueprint_summary(catalog, parameters, analysis, param_map)

    st.markdown("")

    # --- Action buttons ---
    col_gen, col_back = st.columns([3, 1])
    with col_gen:
        generate_clicked = st.button(
            "Excel を生成する",
            type="primary",
            use_container_width=True,
            key="btn_blueprint_generate",
        )
    with col_back:
        if st.button("← やり直す", key="b_back", use_container_width=True):
            st.session_state["phase"] = "A"
            st.rerun()

    # --- Download section (if already generated) ---
    gen_outputs = st.session_state.get("generation_outputs", {})
    if gen_outputs:
        _render_download_section(gen_outputs)

    st.divider()

    # --- Blueprint: Sheet tabs ---
    st.markdown("### PL 設計図")
    st.caption(
        "テンプレートの構造に沿って、抽出された値と未入力の項目を確認・編集できます。"
        "値を変更してから「Excel を生成する」をクリックしてください。"
    )

    sheets = catalog.sheets()
    if not sheets:
        st.info("テンプレートにシートが見つかりませんでした。")
        return

    sheet_tabs = st.tabs([
        f"{s} ({_count_sheet_filled(s, catalog, param_map)}/{_count_sheet_items(s, catalog)})"
        for s in sheets
    ])

    for idx, sheet_name in enumerate(sheets):
        with sheet_tabs[idx]:
            _render_sheet_blueprint(sheet_name, catalog, parameters, analysis, param_map)

    # --- Optional detail info (collapsed) ---
    st.divider()
    with st.expander("詳細情報（モデル構造・エビデンス）", expanded=False):
        _render_detail_section(analysis, catalog, parameters)

    # --- Run generation if clicked (after rendering so all widgets exist) ---
    if generate_clicked:
        _run_generation_from_blueprint()


def _render_blueprint_summary(
    catalog: InputCatalog,
    parameters: list,
    analysis: AnalysisReport,
    param_map: dict,
) -> None:
    """Dashboard cards showing blueprint completion status."""
    writable_items = [i for i in catalog.items if not i.has_formula]
    total_inputs = len(writable_items)
    filled = sum(1 for i in writable_items
                 if f"{i.sheet}!{i.cell}" in param_map)
    gaps = total_inputs - filled
    kpi_count = len(analysis.kpis) if analysis.kpis else 0
    pct = int(filled / total_inputs * 100) if total_inputs > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            _render_metric_card(f"{filled}/{total_inputs}", "入力済み"),
            unsafe_allow_html=True,
        )
    with c2:
        if gaps > 0:
            st.markdown(
                _render_gap_metric_card(str(gaps), "未入力 (GAP)"),
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                _render_metric_card("0", "未入力 (GAP)"),
                unsafe_allow_html=True,
            )
    with c3:
        st.markdown(
            _render_metric_card(str(kpi_count), "算出指標 (KPI)"),
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            _render_metric_card(f"{pct}%", "完成度"),
            unsafe_allow_html=True,
        )

    if total_inputs > 0:
        st.progress(filled / total_inputs, text=f"{filled}/{total_inputs} 項目入力済み")


def _render_sheet_blueprint(
    sheet_name: str,
    catalog: InputCatalog,
    parameters: list,
    analysis: AnalysisReport,
    param_map: dict,
) -> None:
    """Render one sheet tab in the blueprint view."""

    # --- KPI banner (what this sheet calculates) ---
    sheet_kpis = [k for k in (analysis.kpis or []) if k.sheet == sheet_name]
    if sheet_kpis:
        _render_kpi_banner(sheet_kpis)

    # --- Group writable items by block ---
    blocks: Dict[str, List[CatalogItem]] = {}
    for item in catalog.items:
        if item.sheet != sheet_name:
            continue
        if item.has_formula:
            continue
        block = item.block or "その他"
        blocks.setdefault(block, []).append(item)

    if not blocks:
        st.info("このシートには入力セルがありません。")
        return

    for block_name, items in blocks.items():
        filled_count = sum(
            1 for i in items if f"{i.sheet}!{i.cell}" in param_map
        )
        total_count = len(items)
        is_complete = (filled_count == total_count)

        if is_complete:
            status_icon = "&#9989;"   # green check
        elif filled_count > 0:
            status_icon = "&#9888;"   # warning
        else:
            status_icon = "&#10060;"  # red X

        with st.expander(
            f"{block_name}  ({filled_count}/{total_count} 入力済み)",
            expanded=not is_complete,
        ):
            _render_block_inputs(items, param_map)


def _render_kpi_banner(kpis: List[KPIDefinition]) -> None:
    """Show KPIs as a banner explaining what the inputs calculate."""
    li_items: List[str] = []
    for kpi in kpis:
        formula = (
            kpi.human_readable_formula
            or kpi.human_formula
            or kpi.raw_formula
            or ""
        )
        name_esc = _esc(kpi.name)
        formula_esc = _esc(formula)

        line = f"<strong>{name_esc}</strong>"
        if formula_esc:
            line += f" = <code>{formula_esc}</code>"

        # Show dependencies (which inputs feed this KPI)
        if kpi.dependencies:
            dep_labels = []
            for d in kpi.dependencies[:6]:
                # Dependencies are in "label (address)" format; extract label
                if " (" in d:
                    dep_labels.append(_esc(d.split(" (")[0]))
                else:
                    dep_labels.append(_esc(d))
            deps_str = ", ".join(dep_labels)
            if len(kpi.dependencies) > 6:
                deps_str += f" ... (+{len(kpi.dependencies) - 6})"
            line += f'<br><span class="kpi-dep">&#8678; {deps_str}</span>'

        li_items.append(f"<li>{line}</li>")

    kpi_html = "\n".join(li_items)
    st.markdown(f"""
    <div class="kpi-banner">
        <div class="kpi-banner-title">
            算出指標 &#8212; 入力値から自動計算されます
        </div>
        <ul>{kpi_html}</ul>
    </div>
    """, unsafe_allow_html=True)


def _render_block_inputs(
    items: List[CatalogItem],
    param_map: Dict[str, Any],
) -> None:
    """Render editable input rows for a block of catalog items."""
    for item in items:
        addr = f"{item.sheet}!{item.cell}"
        param = param_map.get(addr)

        label = item.primary_label()
        unit = item.unit_candidates[0] if item.unit_candidates else ""
        period = item.year_or_period or ""

        # Build display label
        label_display = label
        if period:
            label_display += f" ({period})"

        state_key = f"bp_{item.sheet}_{item.cell}"

        cols = st.columns([3, 2.5, 0.8, 1.2])

        with cols[0]:
            st.markdown(f"**{label_display}**")
            st.caption(f"`{item.cell}`")

        with cols[1]:
            if param:
                current_val = param.value
                if isinstance(current_val, (int, float)):
                    st.number_input(
                        label_display,
                        value=float(current_val),
                        key=state_key,
                        label_visibility="collapsed",
                        format="%.2f",
                    )
                else:
                    st.text_input(
                        label_display,
                        value=str(current_val) if current_val is not None else "",
                        key=state_key,
                        label_visibility="collapsed",
                    )
            else:
                # GAP cell -- allow user to type a value
                if (
                    item.current_value is not None
                    and isinstance(item.current_value, (int, float))
                ):
                    st.number_input(
                        label_display,
                        value=float(item.current_value),
                        key=state_key,
                        label_visibility="collapsed",
                        format="%.2f",
                    )
                else:
                    st.text_input(
                        label_display,
                        value="",
                        key=state_key,
                        label_visibility="collapsed",
                        placeholder="値を入力...",
                    )

        with cols[2]:
            if unit:
                st.markdown(f"<br><small>{_esc(unit)}</small>", unsafe_allow_html=True)

        with cols[3]:
            if param:
                conf = getattr(param, "confidence", 0)
                st.markdown(
                    f"<br>{_confidence_badge(conf)}",
                    unsafe_allow_html=True,
                )
                src = getattr(param, "source", "")
                if src == "inferred":
                    st.caption("(推定値)")
            else:
                st.markdown(
                    '<br><span class="badge-gap">未入力</span>',
                    unsafe_allow_html=True,
                )


def _render_kpi_banner_inline(kpis: List[KPIDefinition]) -> None:
    """Alternative inline KPI display within model details."""
    for kpi in kpis:
        formula = kpi.raw_formula or kpi.excel_formula or ""
        human = kpi.human_readable_formula or kpi.human_formula or ""
        with st.expander(f"{kpi.name} ({kpi.sheet}!{kpi.cell})"):
            if formula:
                st.code(formula, language=None)
            if human:
                st.caption(human)
            if kpi.dependencies:
                st.markdown(
                    "依存先: " + ", ".join(f"`{d}`" for d in kpi.dependencies)
                )


def _render_detail_section(
    analysis: AnalysisReport,
    catalog: InputCatalog,
    parameters: list,
) -> None:
    """Optional detailed info: model structure, evidence, parameter table."""
    tab_model, tab_evidence, tab_params = st.tabs([
        "モデル構造",
        "エビデンス",
        f"全パラメータ ({len(parameters)})",
    ])

    with tab_model:
        if analysis.summary:
            st.markdown(f"**モデル概要:** {analysis.summary}")

        sheet_names = sorted({item.sheet for item in catalog.items if item.sheet})
        if sheet_names:
            st.markdown("**シート構成:**")
            import pandas as pd
            sheet_data = []
            for sn in sheet_names:
                items_count = sum(
                    1 for item in catalog.items if item.sheet == sn
                )
                kpi_count = sum(
                    1 for k in (analysis.kpis or [])
                    if getattr(k, "sheet", None) == sn
                )
                sheet_data.append({
                    "シート": sn, "入力セル数": items_count, "KPI数": kpi_count
                })
            st.dataframe(
                pd.DataFrame(sheet_data),
                use_container_width=True, hide_index=True,
            )

        st.markdown("**KPI 定義:**")
        if analysis.kpis:
            _render_kpi_banner_inline(analysis.kpis)
        else:
            st.info("KPI が検出されませんでした。")

    with tab_evidence:
        has_evidence = [
            p for p in parameters
            if getattr(getattr(p, "evidence", None), "quote", "")
        ]
        if not has_evidence:
            st.info("エビデンスが記録されたパラメータはありません。")
        else:
            st.caption(f"{len(has_evidence)} 件のパラメータにエビデンスあり")
            for p in has_evidence:
                ev = p.evidence
                conf = getattr(p, "confidence", 0.0)
                with st.expander(f"{getattr(p, 'label', p.key)}"):
                    st.markdown(f"> {ev.quote}")
                    ev_cols = st.columns(3)
                    with ev_cols[0]:
                        st.markdown(
                            _confidence_badge(conf), unsafe_allow_html=True
                        )
                    with ev_cols[1]:
                        if getattr(ev, "page_or_slide", ""):
                            st.caption(f"ページ: {ev.page_or_slide}")
                    with ev_cols[2]:
                        if getattr(ev, "rationale", ""):
                            st.caption(f"根拠: {ev.rationale}")

    with tab_params:
        if not parameters:
            st.info("抽出されたパラメータがありません。")
        else:
            import pandas as pd
            rows: List[Dict[str, Any]] = []
            for p in parameters:
                mapped = ", ".join(
                    f"{t.sheet}!{t.cell}"
                    for t in getattr(p, "mapped_targets", [])
                )
                conf = getattr(p, "confidence", 0.0)
                rows.append({
                    "パラメータ": getattr(p, "label", ""),
                    "値": getattr(p, "value", ""),
                    "単位": getattr(p, "unit", "") or "",
                    "信頼度": _confidence_text(conf),
                    "ソース": getattr(p, "source", ""),
                    "マッピング先": mapped,
                })
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)


def _render_download_section(gen_outputs: Dict[str, bytes]) -> None:
    """Render download buttons for generated files."""
    st.markdown("")
    st.markdown("#### 生成完了 - ダウンロード")
    cols = st.columns(min(len(gen_outputs), 3))
    for idx, (fname, fbytes) in enumerate(gen_outputs.items()):
        with cols[idx % len(cols)]:
            mime = (
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                if fname.endswith(".xlsx")
                else "text/csv"
            )
            st.download_button(
                label=f"{fname}",
                data=fbytes, file_name=fname, mime=mime,
                use_container_width=True, key=f"dl_{fname}",
            )
    st.markdown(
        '<p class="nav-hint">ファイルが正しく生成されました</p>',
        unsafe_allow_html=True,
    )


# ===================================================================
# Blueprint parameter collection & generation
# ===================================================================

def _collect_blueprint_parameters() -> list:
    """Collect parameter values from the blueprint UI state."""
    parameters = st.session_state.get("parameters", [])
    catalog: InputCatalog | None = st.session_state.get("catalog")

    adjusted = deepcopy(parameters)

    # Update existing parameters with edited values from the blueprint
    for p in adjusted:
        for target in getattr(p, "mapped_targets", []):
            state_key = f"bp_{target.sheet}_{target.cell}"
            if state_key in st.session_state:
                new_val = st.session_state[state_key]
                if new_val is not None and str(new_val).strip() != "":
                    try:
                        p.adjusted_value = new_val
                    except (AttributeError, TypeError):
                        pass

    # Handle GAP cells where the user typed values in the blueprint
    if catalog:
        param_map = _build_param_cell_map(adjusted)
        for item in catalog.items:
            if item.has_formula:
                continue
            addr = f"{item.sheet}!{item.cell}"
            if addr in param_map:
                continue  # Already has a parameter
            state_key = f"bp_{item.sheet}_{item.cell}"
            if state_key in st.session_state:
                val = st.session_state[state_key]
                if val is not None and str(val).strip() != "":
                    new_param = ExtractedParameter(
                        key=f"manual_{item.sheet}_{item.cell}",
                        label=item.primary_label(),
                        value=val,
                        unit=(
                            item.unit_candidates[0]
                            if item.unit_candidates
                            else None
                        ),
                        mapped_targets=[
                            CellTarget(sheet=item.sheet, cell=item.cell)
                        ],
                        confidence=1.0,
                        source="document",
                        selected=True,
                    )
                    adjusted.append(new_param)

    return adjusted


def _run_generation_from_blueprint() -> None:
    """Run Excel generation using values from the blueprint."""
    config: PhaseAConfig | None = st.session_state.get("config")
    catalog: InputCatalog | None = st.session_state.get("catalog")
    cc: ColorConfig = st.session_state.get("color_config", ColorConfig())

    if config is None:
        st.error("設定がありません。Phase A からやり直してください。")
        return

    progress = st.progress(0, text="生成を開始中...")
    output_files: Dict[str, bytes] = {}

    try:
        adjusted_params = _collect_blueprint_parameters()
        if not adjusted_params:
            st.warning("パラメータがありません。値を入力してから生成してください。")
            progress.empty()
            return

        cases = config.cases if config.cases else ["base"]
        total_steps = len(cases) + 2
        step = 0

        for case_name in cases:
            step += 1
            progress.progress(
                int(step / total_steps * 80),
                text=f"{case_name.title()} ケースを生成中...",
            )

            case_params = deepcopy(adjusted_params)

            # Apply case multipliers for non-base cases
            if case_name != "base" and len(cases) > 1:
                try:
                    gen = CaseGenerator(config)
                    case_sets = gen.generate_cases(case_params)
                    if case_name in case_sets:
                        case_params = case_sets[case_name]
                except Exception as exc:
                    st.warning(f"{case_name} ケース生成に問題: {exc}")

            with tempfile.TemporaryDirectory() as tmp_dir:
                output_path = str(Path(tmp_dir) / f"PL_{case_name}.xlsx")
                try:
                    try:
                        config.colors = cc  # type: ignore[attr-defined]
                    except (AttributeError, TypeError):
                        pass

                    writer = PLWriter(
                        template_path=config.template_path,
                        output_path=output_path,
                        config=config,
                    )
                    writer.generate(case_params)

                    # Validate
                    try:
                        validator = PLValidator(config.template_path, output_path)
                        val_result = validator.validate()
                        if not val_result.passed:
                            st.warning(
                                f"{case_name.title()}: バリデーション警告 "
                                f"({len(val_result.errors_found)} 件)"
                            )
                            with st.expander(
                                f"{case_name.title()} バリデーション詳細"
                            ):
                                for err in val_result.errors_found:
                                    st.error(err)
                                for warn in val_result.warnings:
                                    st.warning(warn)
                        else:
                            st.success(f"{case_name.title()}: バリデーション OK")
                    except Exception as ve:
                        st.warning(f"バリデーション失敗: {ve}")

                    output_files[f"PL_{case_name}.xlsx"] = (
                        Path(output_path).read_bytes()
                    )
                except Exception as exc:
                    st.error(f"{case_name.title()} ケース生成エラー: {exc}")
                    with st.expander("エラー詳細"):
                        st.code(traceback.format_exc())

        # Simulation
        run_sim = st.session_state.get("run_simulation", False)
        if run_sim and adjusted_params and SimulationEngine is not None:
            step += 1
            progress.progress(
                int(step / total_steps * 95),
                text="シミュレーション実行中 (500回)...",
            )
            try:
                sim_engine = SimulationEngine(iterations=500)
                sim_report = sim_engine.run(
                    adjusted_params, template_path=config.template_path,
                )
                with tempfile.TemporaryDirectory() as sim_dir:
                    sim_path = str(Path(sim_dir) / "simulation_summary.xlsx")
                    export_simulation_summary(sim_report, sim_path)
                    output_files["simulation_summary.xlsx"] = (
                        Path(sim_path).read_bytes()
                    )
                st.success("シミュレーション完了")
                with st.expander("シミュレーション結果サマリー"):
                    for s in sim_report.summaries:
                        st.markdown(
                            f"**{s.kpi_name}**: 平均={s.mean:,.0f}, "
                            f"P10={s.p10:,.0f}, P50={s.p50:,.0f}, "
                            f"P90={s.p90:,.0f}"
                        )
            except Exception as exc:
                st.warning(f"シミュレーション失敗: {exc}")

        # Needs-review CSV
        try:
            with tempfile.NamedTemporaryFile(
                suffix=".csv", delete=False, mode="w"
            ) as tmp_csv:
                csv_path = generate_needs_review_csv(
                    adjusted_params, tmp_csv.name,
                )
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
                mime = (
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    if fname.endswith(".xlsx")
                    else "text/csv"
                )
                st.download_button(
                    label=fname, data=fbytes, file_name=fname,
                    mime=mime,
                    key=f"sidebar_dl_{fname}", use_container_width=True,
                )

        st.divider()
        if not st.session_state.get("reset_confirm", False):
            if st.button(
                "リセット (Reset)", key="btn_reset", use_container_width=True,
            ):
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
    st.set_page_config(
        page_title="PL Generator",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    _init_session_state()
    _inject_custom_css()
    _render_sidebar()
    _render_step_indicator()

    phase = st.session_state["phase"]
    if phase == "A":
        _render_phase_a()
    elif phase == "B":
        _render_phase_b()
    else:
        st.session_state["phase"] = "A"
        st.rerun()


if __name__ == "__main__":
    main()
