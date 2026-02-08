"""
PL Generator -- Multi-Phase Wizard (Streamlit UI)
==================================================

A 6-phase interactive wizard for generating P&L Excel models from
business-plan documents, with user feedback at each stage.

* **Phase 1** -- Upload & Scan       (アップロード & スキャン)
* **Phase 2** -- BM Analysis          (ビジネスモデル分析)
* **Phase 3** -- Template Structure   (テンプレート構造)
* **Phase 4** -- Model Design         (モデル設計)
* **Phase 5** -- Parameters           (パラメーター抽出)
* **Phase 6** -- Final Output         (最終出力 & Excel生成)

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
# Bridge Streamlit Secrets → os.environ  (Streamlit Cloud does NOT do this
# automatically, but LLMClient reads from os.environ)
# ---------------------------------------------------------------------------
_API_KEY_SOURCE = "not found"
try:
    if os.environ.get("ANTHROPIC_API_KEY"):
        _API_KEY_SOURCE = "os.environ (pre-set)"
    else:
        # Try flat format: ANTHROPIC_API_KEY = "sk-ant-..."
        try:
            _val = st.secrets.get("ANTHROPIC_API_KEY", "")
            if _val:
                os.environ["ANTHROPIC_API_KEY"] = str(_val)
                _API_KEY_SOURCE = "st.secrets (bridged)"
        except (KeyError, FileNotFoundError, AttributeError):
            pass
        # Also try nested TOML format: [anthropic]\n api_key = "..."
        if _API_KEY_SOURCE == "not found":
            try:
                _val = st.secrets.get("anthropic", {}).get("api_key", "")
                if _val:
                    os.environ["ANTHROPIC_API_KEY"] = str(_val)
                    _API_KEY_SOURCE = "st.secrets.anthropic.api_key (bridged)"
            except (KeyError, FileNotFoundError, AttributeError):
                pass
except Exception:
    pass  # st.secrets may not be available outside Streamlit

# ---------------------------------------------------------------------------
# Project imports  (wrapped so Streamlit Cloud shows the real error)
# ---------------------------------------------------------------------------

try:
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
    from src.ingest.base import DocumentContent, PageContent
    from src.catalog.scanner import scan_template, export_catalog_json
    from src.modelmap.analyzer import analyze_model, generate_model_report_md
    from src.extract.extractor import ParameterExtractor
    from src.extract.prompts import build_extraction_prompt  # noqa: F401
    from src.excel.writer import PLWriter
    from src.excel.validator import PLValidator, generate_needs_review_csv
    from src.excel.case_generator import CaseGenerator

    # Compat layer: centralised fallbacks for names that may not exist
    # in older deployments.
    try:
        from src.app.compat import (  # noqa: F811
            LLMClient, LLMError,
            SYSTEM_PROMPT_NORMAL, SYSTEM_PROMPT_STRICT,
            INDUSTRY_PROMPTS, BUSINESS_MODEL_PROMPTS,
            USER_PROMPT_TEMPLATE,
        )
    except ImportError:
        from src.extract.llm_client import LLMClient  # noqa: F811
        try:
            from src.extract.llm_client import LLMError  # noqa: F811
        except ImportError:
            class LLMError(Exception):  # type: ignore[no-redef]
                """Raised when the LLM API call fails."""
        try:
            from src.extract.prompts import SYSTEM_PROMPT_NORMAL  # noqa: F811
        except ImportError:
            SYSTEM_PROMPT_NORMAL = "You are a financial model specialist."  # type: ignore[assignment]
        try:
            from src.extract.prompts import SYSTEM_PROMPT_STRICT  # noqa: F811
        except ImportError:
            SYSTEM_PROMPT_STRICT = SYSTEM_PROMPT_NORMAL + "\nSTRICT MODE."  # type: ignore[assignment]
        try:
            from src.extract.prompts import INDUSTRY_PROMPTS  # noqa: F811
        except ImportError:
            INDUSTRY_PROMPTS = {}  # type: ignore[assignment]
        try:
            from src.extract.prompts import BUSINESS_MODEL_PROMPTS  # noqa: F811
        except ImportError:
            BUSINESS_MODEL_PROMPTS = {}  # type: ignore[assignment]
        try:
            from src.extract.prompts import USER_PROMPT_TEMPLATE  # noqa: F811
        except ImportError:
            USER_PROMPT_TEMPLATE = (  # type: ignore[assignment]
                "事業計画書からパラメータを抽出してください。\n\n"
                "■ ケース: {cases}\n■ セル:\n{catalog_block}\n■ 文書:\n{document_chunk}\n"
            )
except Exception as _import_exc:
    st.error(
        f"モジュール読み込みエラー: {type(_import_exc).__name__}: {_import_exc}\n\n"
        f"```\n{traceback.format_exc()}\n```"
    )
    st.stop()

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

# Agent imports (new multi-phase pipeline)
try:
    from src.agents.orchestrator import AgentOrchestrator
    from src.agents.business_model_analyzer import BusinessModelAnalysis
    from src.agents.template_mapper import TemplateStructureResult
    from src.agents.model_designer import ModelDesignResult
    from src.agents.parameter_extractor import ParameterExtractionResult
except ImportError as exc:
    _IMPORT_ERRORS.append(f"agents: {exc}")

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ALLOWED_DOC_EXTENSIONS: List[str] = ["pdf", "docx", "pptx"]
DEFAULT_TEMPLATE_PATH = "templates/base.xlsx"

DEFAULT_INPUT_COLOR = "#FFF2CC"
DEFAULT_FORMULA_COLOR = "#4472C4"
DEFAULT_TOTAL_COLOR = "#D9E2F3"

# Phase definitions (6-phase flow)
PHASES = [
    {"key": 1, "label": "アップロード", "short": "Upload"},
    {"key": 2, "label": "BM分析", "short": "BM Analysis"},
    {"key": 3, "label": "テンプレ構造", "short": "Template"},
    {"key": 4, "label": "モデル設計", "short": "Model"},
    {"key": 5, "label": "パラメーター", "short": "Params"},
    {"key": 6, "label": "最終出力", "short": "Output"},
]

CASE_OPTIONS: List[str] = ["Best", "Base", "Worst"]


# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------

def _inject_custom_css() -> None:
    st.markdown("""
    <style>
    /* ══════════════════════════════════════════════════════
       freee-inspired clean design system
       Primary: #2563EB (blue)  Accent: #3B82F6
       ══════════════════════════════════════════════════════ */

    /* ── Global resets ── */
    .block-container { max-width: 960px; }
    section[data-testid="stSidebar"] {
        background: #f8fafc;
        border-right: 1px solid #e2e8f0;
    }
    section[data-testid="stSidebar"] button {
        font-size: 0.8rem !important;
        padding: 0.3rem 0.6rem !important;
        border-radius: 6px !important;
    }
    .sidebar-section-label {
        font-size: 0.7rem; font-weight: 600; color: #94a3b8;
        text-transform: uppercase; letter-spacing: 0.06em;
        margin-bottom: 0.3rem;
    }

    /* ── Step indicator ── */
    .step-bar {
        display: flex; justify-content: center; gap: 0;
        margin: 0 auto 1.5rem auto; max-width: 720px;
        border-bottom: 2px solid #e2e8f0;
    }
    .step-item {
        flex: 1; text-align: center; padding: 0.7rem 0.2rem;
        font-size: 0.76rem; color: #94a3b8;
        border-bottom: 2px solid transparent;
        margin-bottom: -2px; transition: all 0.15s;
    }
    .step-item.active {
        color: #2563eb; font-weight: 700;
        border-bottom-color: #2563eb;
    }
    .step-item.completed {
        color: #2563eb; border-bottom-color: #2563eb;
    }
    .step-num {
        display: inline-flex; align-items: center; justify-content: center;
        width: 20px; height: 20px; border-radius: 50%;
        background: #e2e8f0; color: #94a3b8;
        font-weight: 700; font-size: 0.68rem; margin-right: 4px;
    }
    .step-item.active .step-num { background: #2563eb; color: #fff; }
    .step-item.completed .step-num { background: #2563eb; color: #fff; }

    /* ── Phase header (unified, clean card) ── */
    .phase-header {
        border-bottom: 2px solid #e2e8f0;
        padding-bottom: 1rem;
        margin-bottom: 1.5rem;
    }
    .phase-header h2 {
        font-size: 1.25rem; font-weight: 700; color: #1e293b;
        margin: 0 0 0.3rem 0;
    }
    .phase-header p {
        font-size: 0.82rem; color: #64748b;
        margin: 0; line-height: 1.5;
    }

    /* ── Metric / stat cards ── */
    .metric-card {
        background: #fff; border: 1px solid #e2e8f0;
        border-radius: 8px; padding: 1rem; text-align: center;
        border-top: 3px solid #2563eb;
    }
    .metric-value {
        font-size: 1.6rem; font-weight: 700;
        color: #1e293b; line-height: 1.2;
    }
    .metric-label {
        font-size: 0.75rem; color: #64748b; margin-top: 0.2rem;
    }
    .metric-card-gap {
        background: #fff; border: 1px solid #fecaca;
        border-radius: 8px; padding: 1rem; text-align: center;
        border-top: 3px solid #ef4444;
    }
    .metric-card-gap .metric-value { color: #dc2626; }

    .grid-stats {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
        gap: 10px; margin-bottom: 1.2rem;
    }
    .grid-stat {
        background: #fff; border: 1px solid #e2e8f0;
        border-radius: 8px; padding: 0.9rem 0.6rem;
        text-align: center;
    }
    .grid-stat-val {
        font-size: 1.4rem; font-weight: 700; line-height: 1.2;
        color: #1e293b;
    }
    .grid-stat-val.clr-green { color: #16a34a; }
    .grid-stat-val.clr-amber { color: #d97706; }
    .grid-stat-val.clr-red { color: #dc2626; }
    .grid-stat-val.clr-blue { color: #2563eb; }
    .grid-stat-lbl {
        font-size: 0.7rem; color: #94a3b8; margin-top: 0.2rem;
    }

    /* ── Badges ── */
    .badge-high {
        display: inline-block; padding: 2px 8px; border-radius: 4px;
        font-size: 0.72rem; font-weight: 600;
        background: #dcfce7; color: #166534;
    }
    .badge-medium {
        display: inline-block; padding: 2px 8px; border-radius: 4px;
        font-size: 0.72rem; font-weight: 600;
        background: #fef3c7; color: #92400e;
    }
    .badge-low {
        display: inline-block; padding: 2px 8px; border-radius: 4px;
        font-size: 0.72rem; font-weight: 600;
        background: #fee2e2; color: #991b1b;
    }
    .badge-gap {
        display: inline-block; padding: 2px 8px; border-radius: 4px;
        font-size: 0.72rem; font-weight: 600;
        background: #f1f5f9; color: #64748b;
    }

    /* ── File upload indicator ── */
    .file-ok {
        background: #f0fdf4; border: 1px solid #bbf7d0;
        border-radius: 6px; padding: 0.5rem 0.8rem;
        color: #166534; font-size: 0.85rem; margin: 0.5rem 0;
    }

    /* ── KPI banner ── */
    .kpi-banner {
        background: #f8fafc; border-left: 3px solid #2563eb;
        border-radius: 0 6px 6px 0; padding: 0.8rem 1rem;
        margin-bottom: 0.8rem;
    }
    .kpi-banner-title {
        font-weight: 700; color: #1e40af;
        margin-bottom: 0.3rem; font-size: 0.88rem;
    }
    .kpi-banner ul {
        margin: 0; padding-left: 1rem;
        font-size: 0.82rem; line-height: 1.6;
    }
    .kpi-banner li { color: #334155; }
    .kpi-dep { color: #94a3b8; font-size: 0.75rem; }

    /* ── Section titles ── */
    .section-title {
        font-size: 0.7rem; font-weight: 700; color: #94a3b8;
        text-transform: uppercase; letter-spacing: 0.06em;
        margin: 1.2rem 0 0.6rem 0;
        padding-bottom: 0.3rem;
        border-bottom: 1px solid #f1f5f9;
    }

    /* ── Clean card (universal) ── */
    .clean-card {
        background: #fff; border: 1px solid #e2e8f0;
        border-radius: 8px; padding: 1rem 1.2rem;
        margin-bottom: 8px; transition: border-color 0.15s;
    }
    .clean-card:hover { border-color: #93c5fd; }
    .clean-card-top {
        display: flex; justify-content: space-between;
        align-items: center; margin-bottom: 0.4rem;
    }
    .clean-card-title {
        font-size: 0.95rem; font-weight: 600; color: #1e293b;
    }
    .clean-tag {
        display: inline-flex; padding: 2px 10px;
        border-radius: 4px; font-size: 0.68rem; font-weight: 600;
    }
    .clean-tag.revenue { background: #eff6ff; color: #2563eb; }
    .clean-tag.cost { background: #fef2f2; color: #dc2626; }
    .clean-tag.assumptions { background: #f5f3ff; color: #7c3aed; }
    .clean-tag.summary { background: #f0fdfa; color: #0d9488; }
    .clean-tag.other { background: #f8fafc; color: #64748b; }

    .clean-seg {
        font-size: 0.82rem; color: #475569; margin-bottom: 0.5rem;
    }
    .clean-seg .arr { color: #94a3b8; margin-right: 4px; }

    /* ── Confidence bar ── */
    .conf-bar {
        display: flex; align-items: center; gap: 8px;
        margin-bottom: 0.4rem;
    }
    .conf-bg {
        flex: 1; height: 4px; background: #e2e8f0;
        border-radius: 2px; overflow: hidden;
    }
    .conf-fill { height: 100%; border-radius: 2px; }
    .conf-fill.high { background: #22c55e; }
    .conf-fill.med  { background: #f59e0b; }
    .conf-fill.low  { background: #ef4444; }
    .conf-pct {
        font-size: 0.75rem; font-weight: 600; min-width: 34px;
        text-align: right; font-variant-numeric: tabular-nums;
    }
    .conf-pct.high { color: #16a34a; }
    .conf-pct.med  { color: #d97706; }
    .conf-pct.low  { color: #dc2626; }

    .clean-reason {
        font-size: 0.75rem; color: #94a3b8; line-height: 1.5;
        border-top: 1px solid #f1f5f9; padding-top: 0.5rem;
        margin-top: 0.3rem;
    }

    /* ── Info / suggest cards ── */
    .overview-card {
        background: #f8fafc; border: 1px solid #e2e8f0;
        border-radius: 6px; padding: 0.8rem 1rem;
        margin-bottom: 0.8rem; font-size: 0.82rem;
        line-height: 1.7; color: #334155;
    }
    .suggest-card {
        background: #eff6ff; border-left: 3px solid #3b82f6;
        border-radius: 0 6px 6px 0; padding: 0.6rem 1rem;
        margin-bottom: 6px; font-size: 0.82rem;
        line-height: 1.5; color: #1e40af;
    }

    /* ── Start card (dashed) ── */
    .start-card {
        border: 1px dashed #cbd5e1; border-radius: 8px;
        padding: 2.5rem 1.5rem; text-align: center;
        margin-bottom: 1rem; background: #fafbfc;
    }
    .start-card-title {
        font-size: 1rem; font-weight: 600; color: #2563eb;
        margin-bottom: 0.3rem;
    }
    .start-card-desc {
        font-size: 0.82rem; color: #94a3b8; line-height: 1.5;
        max-width: 440px; margin: 0 auto;
    }

    /* ── Unmapped / error section ── */
    .unmapped-section {
        background: #fef2f2; border: 1px solid #fecaca;
        border-radius: 6px; padding: 0.6rem 0.8rem;
        margin-top: 0.6rem;
    }
    .unmapped-title {
        font-size: 0.78rem; font-weight: 600; color: #dc2626;
        margin-bottom: 0.3rem;
    }

    /* ── Feedback area ── */
    .feedback-section {
        margin-top: 1.5rem; padding-top: 1rem;
        border-top: 1px solid #e2e8f0;
    }
    .fb-label {
        font-size: 0.82rem; font-weight: 600; color: #334155;
        margin-bottom: 0.1rem;
    }
    .fb-hint {
        font-size: 0.7rem; color: #94a3b8; margin-bottom: 0.5rem;
    }

    /* ── Revenue model configurator ── */
    .rm-section {
        background: #fff; border: 1px solid #e2e8f0;
        border-radius: 8px; padding: 1rem 1.2rem;
        margin-top: 0.8rem;
    }
    .rm-title {
        font-size: 0.88rem; font-weight: 600; color: #2563eb;
        margin-bottom: 0.6rem;
    }

    .nav-hint {
        text-align: center; color: #94a3b8;
        font-size: 0.75rem; margin-top: 0.5rem;
    }
    .feedback-card {
        background: #f8fafc; border: 1px solid #e2e8f0;
        border-radius: 8px; padding: 0.8rem; margin: 0.8rem 0;
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
        "wizard_phase": 1,
        "color_config": ColorConfig(),
        # Phase 1 data
        "config": None,
        "document": None,
        "catalog": None,
        "analysis": None,  # Template formula structure
        "writable_items": [],
        # Phase 2 data
        "bm_result": None,
        "bm_error": "",
        # Phase 3 data
        "ts_result": None,
        "ts_error": "",
        # Phase 4 data
        "md_result": None,
        "md_error": "",
        # Phase 5 data
        "pe_result": None,
        "pe_error": "",
        # Phase 6 data
        "parameters": [],
        "generation_outputs": {},
        # Common
        "error_message": "",
        "reset_confirm": False,
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default


# ---------------------------------------------------------------------------
# UI Components
# ---------------------------------------------------------------------------

def _render_step_indicator() -> None:
    current = st.session_state["wizard_phase"]
    html_parts = ['<div class="step-bar">']
    for p in PHASES:
        idx = p["key"]
        if idx < current:
            cls = "completed"
            check = "&#10003;"
        elif idx == current:
            cls = "active"
            check = str(idx)
        else:
            cls = ""
            check = str(idx)
        html_parts.append(
            f'<div class="step-item {cls}">'
            f'<span class="step-num">{check}</span>'
            f'{p["label"]}'
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


def _esc(text: str) -> str:
    return html_mod.escape(str(text)) if text else ""


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _save_uploaded_file(uploaded_file) -> str:
    tmp_dir = tempfile.mkdtemp()
    dest = Path(tmp_dir) / uploaded_file.name
    dest.write_bytes(uploaded_file.getvalue())
    return str(dest)


def _get_llm_client() -> Any:
    """Create LLMClient with pre-flight API check."""
    import time as _time

    _api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not _api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY が見つかりません。\n"
            f"APIキー検索結果: {_API_KEY_SOURCE}\n"
            "Streamlit Cloud: Settings → Secrets で ANTHROPIC_API_KEY を設定してください。"
        )

    # Direct API connectivity test
    _preflight_start = _time.time()
    try:
        from anthropic import Anthropic as _Anthropic
        _test_client = _Anthropic(api_key=_api_key)
        _test_resp = _test_client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=16,
            messages=[{"role": "user", "content": "Reply with exactly: OK"}],
        )
        _test_content = (_test_resp.content[0].text or "").strip()
        if not _test_content:
            raise RuntimeError("Claude API応答が空です。")
    except ImportError:
        raise RuntimeError("anthropic パッケージが見つかりません。")
    except RuntimeError:
        raise
    except Exception as _pf_exc:
        _elapsed = _time.time() - _preflight_start
        raise RuntimeError(
            f"Claude API 接続失敗: {type(_pf_exc).__name__}: {_pf_exc}\n"
            f"時間={_elapsed:.1f}秒, APIキーソース: {_API_KEY_SOURCE}"
        ) from _pf_exc

    return LLMClient()


def _get_prompt_registry():
    """Get or create the PromptRegistry from session state."""
    if "prompt_registry" not in st.session_state:
        try:
            from src.agents.prompt_registry import PromptRegistry
            st.session_state["prompt_registry"] = PromptRegistry()
        except Exception:
            return None
    return st.session_state["prompt_registry"]


def _get_orchestrator() -> Any:
    """Create AgentOrchestrator with prompt overrides from registry."""
    llm = _get_llm_client()
    registry = _get_prompt_registry()
    prompt_overrides = None
    if registry:
        # Collect custom prompts from registry
        customized = {}
        for entry in registry.list_entries():
            if entry.is_customized:
                customized[entry.key] = entry.content
        if customized:
            prompt_overrides = customized
    return AgentOrchestrator(llm, prompt_overrides=prompt_overrides)


# ===================================================================
# Phase 1: Upload & Scan
# ===================================================================

def _render_phase_1() -> None:
    st.markdown(
        '<div class="phase-header">'
        '<h2>アップロード &amp; スキャン</h2>'
        '<p>事業計画書とExcelテンプレートをアップロードしてください</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    # --- Input method tabs: file upload or text paste ---
    input_tab1, input_tab2 = st.tabs(["ファイルアップロード", "テキスト貼り付け"])

    doc_file = None
    pasted_text = ""

    with input_tab1:
        doc_file = st.file_uploader(
            "事業計画書 (PDF / DOCX / PPTX)", type=ALLOWED_DOC_EXTENSIONS,
            key="doc_upload", label_visibility="collapsed",
        )

        if doc_file:
            ext = doc_file.name.split(".")[-1].upper()
            size_kb = len(doc_file.getvalue()) / 1024
            st.markdown(
                f'<div class="file-ok">&#10003; {doc_file.name} ({ext}, {size_kb:.0f} KB)</div>',
                unsafe_allow_html=True,
            )

    with input_tab2:
        st.caption(
            "NotebookLMやPDFからテキストを抽出できない場合、"
            "事業計画書の内容を直接貼り付けてください。"
        )
        pasted_text = st.text_area(
            "事業計画書テキスト",
            height=300,
            key="doc_text_paste",
            placeholder="ここに事業計画書のテキストを貼り付けてください...\n\n"
                        "例: NotebookLMのノート画面からテキストをコピー (Ctrl+A → Ctrl+C)",
        )
        if pasted_text and pasted_text.strip():
            char_count = len(pasted_text.strip())
            st.success(f"{char_count:,} 文字のテキストが入力されました。")

    with st.expander("設定（任意）", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.multiselect("生成ケース", options=CASE_OPTIONS, default=["Base"], key="case_multiselect")
            st.checkbox("Monte Carlo シミュレーション", value=False, key="sim_checkbox")
        with col2:
            template_file = st.file_uploader(
                "Excel テンプレート（任意）", type=["xlsx"], key="template_upload",
            )
            if template_file:
                st.session_state["template_upload_file"] = template_file

        st.caption("セル色設定")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.color_picker("入力セル色", value=DEFAULT_INPUT_COLOR, key="color_input")
        with c2:
            st.color_picker("数式フォント色", value=DEFAULT_FORMULA_COLOR, key="color_formula")
        with c3:
            st.color_picker("合計セル色", value=DEFAULT_TOTAL_COLOR, key="color_total")

    has_input = doc_file or (pasted_text and pasted_text.strip())
    if has_input:
        if st.button("スキャン開始 →", type="primary", width="stretch", key="btn_scan"):
            if pasted_text and pasted_text.strip():
                _run_phase_1_scan_from_text(pasted_text.strip())
            else:
                _run_phase_1_scan(doc_file)
    else:
        st.markdown(
            '<div style="text-align:center; padding:3rem 1rem; '
            'color:#999; border:2px dashed #ddd; border-radius:12px;">'
            '<p style="font-size:1.2rem;">PDF / DOCX / PPTX をドラッグ＆ドロップ</p>'
            '<p style="font-size:0.9rem;">またはテキスト貼り付けタブからテキストを直接入力</p>'
            '</div>',
            unsafe_allow_html=True,
        )


def _run_phase_1_scan(doc_file) -> None:
    progress = st.progress(0, text="準備中...")
    try:
        progress.progress(10, text="ファイルを保存中...")
        doc_path = _save_uploaded_file(doc_file)

        template_file = st.session_state.get("template_upload_file", None)
        if template_file is not None:
            template_path = _save_uploaded_file(template_file)
        else:
            template_path = DEFAULT_TEMPLATE_PATH
            if not Path(template_path).exists():
                st.error("デフォルトテンプレートが見つかりません。テンプレートをアップロードしてください。")
                progress.empty()
                return

        cases_raw = st.session_state.get("case_multiselect", ["Base"])
        if not cases_raw:
            cases_raw = ["Base"]

        progress.progress(20, text="設定を構築中...")
        config = PhaseAConfig(
            industry="auto", business_model="Other",
            strictness="normal", cases=[c.lower() for c in cases_raw],
            template_path=template_path, document_paths=[doc_path],
        )
        st.session_state["config"] = config
        st.session_state["run_simulation"] = st.session_state.get("sim_checkbox", False)

        cc = ColorConfig(
            input_color=st.session_state.get("color_input", DEFAULT_INPUT_COLOR),
            formula_color=st.session_state.get("color_formula", DEFAULT_FORMULA_COLOR),
            total_color=st.session_state.get("color_total", DEFAULT_TOTAL_COLOR),
        )
        st.session_state["color_config"] = cc

        progress.progress(40, text="事業計画書を読み取り中（OCR自動フォールバック付き）...")
        document = read_document(doc_path)
        # Store source filename for sidebar display
        if not getattr(document, "source_filename", ""):
            document.source_filename = doc_file.name
        st.session_state["document"] = document

        # --- Extraction diagnostics ---
        char_count = getattr(document, "text_char_count", 0)
        pages_with = getattr(document, "pages_with_content", 0)
        is_image = getattr(document, "is_likely_image_pdf", False)

        if char_count == 0 or pages_with == 0:
            progress.empty()
            st.error(
                f"⚠ PDFからテキストを抽出できませんでした（{document.total_pages}ページ中 {pages_with}ページで抽出成功）。\n\n"
                "テキスト抽出（5ライブラリ）＋OCR（画像認識）を含む全手法で抽出に失敗しました。\n\n"
                "**対処法:**\n"
                '- **「テキスト貼り付け」タブ** を使って事業計画書のテキストを直接貼り付けてください\n'
                "- NotebookLMの場合: ノート画面でテキストをコピー → 「テキスト貼り付け」タブに貼り付け\n"
                "- PowerPoint(.pptx)やWord(.docx)の元ファイルがあればそちらをアップロード"
            )
            with st.expander("抽出結果の詳細"):
                summary = getattr(document, "extraction_summary", lambda: "N/A")
                st.code(summary() if callable(summary) else str(summary))
            return

        if is_image:
            st.warning(
                f"⚠ テキスト抽出率が低いです（{pages_with}/{document.total_pages}ページ、{char_count:,}文字）。"
                "画像ベースのPDFの可能性があります。分析精度が低下する場合があります。"
            )

        progress.progress(60, text="テンプレートをスキャン中...")
        input_color_hex = cc.input_color.lstrip("#")
        if len(input_color_hex) == 6:
            input_color_hex = "FF" + input_color_hex
        catalog = scan_template(template_path, input_color=input_color_hex)
        st.session_state["catalog"] = catalog

        progress.progress(80, text="数式構造を分析中...")
        analysis = analyze_model(template_path, catalog)
        st.session_state["analysis"] = analysis

        # Pre-compute writable items
        writable_items = [
            {
                "sheet": item.sheet,
                "cell": item.cell,
                "labels": item.label_candidates,
                "units": item.unit_candidates,
                "period": item.year_or_period,
                "block": item.block,
                "current_value": item.current_value,
            }
            for item in catalog.items
            if not item.has_formula
        ]
        st.session_state["writable_items"] = writable_items

        progress.progress(100, text="スキャン完了!")
        st.session_state["wizard_phase"] = 2
        st.rerun()

    except Exception as exc:
        progress.empty()
        st.error(f"スキャン中にエラーが発生しました: {exc}")
        with st.expander("エラー詳細"):
            st.code(traceback.format_exc())


def _run_phase_1_scan_from_text(pasted_text: str) -> None:
    """Run Phase 1 scan using directly pasted text (bypasses PDF extraction)."""
    progress = st.progress(0, text="準備中...")
    try:
        template_file = st.session_state.get("template_upload_file", None)
        if template_file is not None:
            template_path = _save_uploaded_file(template_file)
        else:
            template_path = DEFAULT_TEMPLATE_PATH
            if not Path(template_path).exists():
                st.error("デフォルトテンプレートが見つかりません。テンプレートをアップロードしてください。")
                progress.empty()
                return

        cases_raw = st.session_state.get("case_multiselect", ["Base"])
        if not cases_raw:
            cases_raw = ["Base"]

        progress.progress(20, text="設定を構築中...")
        config = PhaseAConfig(
            industry="auto", business_model="Other",
            strictness="normal", cases=[c.lower() for c in cases_raw],
            template_path=template_path, document_paths=["(テキスト貼り付け)"],
        )
        st.session_state["config"] = config
        st.session_state["run_simulation"] = st.session_state.get("sim_checkbox", False)

        cc = ColorConfig(
            input_color=st.session_state.get("color_input", DEFAULT_INPUT_COLOR),
            formula_color=st.session_state.get("color_formula", DEFAULT_FORMULA_COLOR),
            total_color=st.session_state.get("color_total", DEFAULT_TOTAL_COLOR),
        )
        st.session_state["color_config"] = cc

        progress.progress(40, text="テキストを処理中...")

        # Build DocumentContent directly from pasted text
        pages = [
            PageContent(
                page_number=1,
                text=pasted_text,
                tables=[],
                source_type="text_paste",
            )
        ]
        document = DocumentContent(
            file_path="(テキスト貼り付け)",
            file_type="text_paste",
            pages=pages,
            total_pages=1,
            metadata={},
            source_filename="テキスト貼り付け",
        )
        st.session_state["document"] = document

        st.success(f"テキスト入力: {len(pasted_text):,} 文字を受け付けました。")

        progress.progress(60, text="テンプレートをスキャン中...")
        input_color_hex = cc.input_color.lstrip("#")
        if len(input_color_hex) == 6:
            input_color_hex = "FF" + input_color_hex
        catalog = scan_template(template_path, input_color=input_color_hex)
        st.session_state["catalog"] = catalog

        progress.progress(80, text="数式構造を分析中...")
        analysis = analyze_model(template_path, catalog)
        st.session_state["analysis"] = analysis

        # Pre-compute writable items
        writable_items = [
            {
                "sheet": item.sheet,
                "cell": item.cell,
                "labels": item.label_candidates,
                "units": item.unit_candidates,
                "period": item.year_or_period,
                "block": item.block,
                "current_value": item.current_value,
            }
            for item in catalog.items
            if not item.has_formula
        ]
        st.session_state["writable_items"] = writable_items

        progress.progress(100, text="スキャン完了!")
        st.session_state["wizard_phase"] = 2
        st.rerun()

    except Exception as exc:
        progress.empty()
        st.error(f"スキャン中にエラーが発生しました: {exc}")
        with st.expander("エラー詳細"):
            st.code(traceback.format_exc())


# ===================================================================
# Phase 2: Business Model Analysis
# ===================================================================

def _render_phase_2() -> None:
    st.markdown(
        '<div class="phase-header">'
        '<h2>ビジネスモデル分析</h2>'
        '<p>事業計画書を深く読み込み、ビジネスモデルを分析します。'
        '複数の解釈パターンから最適なものを選択してください</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    bm = st.session_state.get("bm_result")
    bm_error = st.session_state.get("bm_error", "")

    # Show run button if no result yet
    if bm is None and not bm_error:
        if st.button("分析開始", type="primary", width="stretch", key="btn_bm_run"):
            _run_bm_analysis()
            st.rerun()
        return

    # Show error
    if bm_error:
        st.error(f"分析エラー: {bm_error}")

    # Show results
    if bm is not None:
        _render_bm_results(bm)

    st.divider()

    # Feedback section
    st.markdown("**フィードバック**")
    st.caption("分析結果に修正が必要な場合、指示を入力して「再分析」してください。パターンを選択して「確定」してください。")
    feedback = st.text_area(
        "フィードバック",
        value="",
        placeholder="例: SaaS事業だけでなくコンサルティング収益もあります / パターンBが近いがセグメントをもう1つ追加してほしい",
        key="bm_feedback",
        label_visibility="collapsed",
    )

    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        if st.button("再分析 (フィードバック反映)", width="stretch", key="btn_bm_rerun"):
            _run_bm_analysis(feedback=feedback)
            st.rerun()
    with col2:
        can_confirm = bm is not None
        if st.button("確定 → テンプレ構造へ", type="primary", width="stretch",
                      disabled=not can_confirm, key="btn_bm_confirm"):
            # Apply the selected proposal before moving to Phase 3
            selected_idx = st.session_state.get("bm_selected_proposal", 0)
            if bm is not None and hasattr(bm, "select_proposal"):
                bm = bm.select_proposal(selected_idx)
                st.session_state["bm_result"] = bm
            st.session_state["wizard_phase"] = 3
            st.rerun()
    with col3:
        if st.button("← 戻る", width="stretch", key="btn_bm_back"):
            st.session_state["wizard_phase"] = 1
            st.rerun()


def _run_bm_analysis(feedback: str = "") -> None:
    document = st.session_state.get("document")
    if not document:
        st.session_state["bm_error"] = "ドキュメントがありません。Phase 1に戻ってください。"
        return

    with st.spinner("ビジネスモデルを深く分析中... (30秒〜1分程度)"):
        try:
            orch = _get_orchestrator()
            bm = orch.run_bm_analysis(document.full_text, feedback=feedback)
            st.session_state["bm_result"] = bm
            st.session_state["bm_error"] = ""
            st.session_state["bm_selected_proposal"] = 0
        except Exception as exc:
            st.session_state["bm_error"] = str(exc)
            logger.error("BM analysis failed: %s", exc)


def _render_bm_results(bm: Any) -> None:
    # --- Header ---
    num_proposals = len(bm.proposals) if hasattr(bm, "proposals") else 0
    if num_proposals > 0:
        st.success(f"分析完了: {bm.company_name} / {num_proposals}パターン提案")
    else:
        st.success(f"分析完了: {bm.industry} / {bm.business_model_type} / {len(bm.segments)}セグメント")

    # --- Narrative (story) ---
    narrative = getattr(bm, "document_narrative", "")
    if narrative:
        st.markdown("#### ビジネス理解 (ストーリー)")
        st.info(narrative)

    # --- Key facts ---
    key_facts = getattr(bm, "key_facts", [])
    if key_facts:
        st.markdown("#### 読み取った重要事実")
        for fact in key_facts:
            st.markdown(f"- {fact}")

    # --- Proposals (3-5 pattern selection) ---
    proposals = getattr(bm, "proposals", [])
    if proposals:
        st.markdown("---")
        st.markdown("#### ビジネスモデル解釈パターン")
        st.caption("以下のパターンから最も近いものを選択してください。選択したパターンを元に次フェーズでテンプレート構造を設計します。")

        # Radio selection for proposals
        proposal_labels = []
        for i, p in enumerate(proposals):
            conf_pct = int(p.confidence * 100)
            grounding_pct = int(getattr(p, "grounding_score", 0) * 100)
            proposal_labels.append(f"{p.label} (確信度: {conf_pct}% / 文書根拠: {grounding_pct}%)")

        selected_idx = st.radio(
            "パターン選択",
            options=list(range(len(proposals))),
            format_func=lambda i: proposal_labels[i],
            index=st.session_state.get("bm_selected_proposal", 0),
            key="bm_proposal_radio",
            label_visibility="collapsed",
        )
        st.session_state["bm_selected_proposal"] = selected_idx

        # Show all proposals as expandable cards
        for i, p in enumerate(proposals):
            is_selected = (i == selected_idx)
            icon = ">> " if is_selected else ""
            with st.expander(
                f"{icon}{p.label}",
                expanded=is_selected,
            ):
                # Grounding score indicator
                grounding = getattr(p, "grounding_score", 0)
                if grounding >= 0.7:
                    gs_label = f"文書根拠率: {grounding:.0%} (高)"
                elif grounding >= 0.4:
                    gs_label = f"文書根拠率: {grounding:.0%} (中)"
                elif grounding > 0:
                    gs_label = f"文書根拠率: {grounding:.0%} (低 - 推定が多い)"
                else:
                    gs_label = "文書根拠率: 未検証"
                st.caption(gs_label)

                st.markdown(f"**解釈の根拠:** {p.reasoning}")
                st.markdown(f"**業種:** {p.industry} | **モデル:** {p.business_model_type} | **期間:** {p.time_horizon}")
                st.markdown(f"**概要:** {p.executive_summary}")

                # Business model diagram
                diagram = getattr(p, "diagram", "")
                if diagram:
                    st.markdown("**ビジネスモデル図解:**")
                    st.code(diagram, language=None)

                # Segments
                if p.segments:
                    st.markdown("**セグメント構成:**")
                    for j, seg in enumerate(p.segments):
                        st.markdown(f"  **{j+1}. {seg.name}** ({seg.model_type})")
                        st.markdown(f"  収益公式: `{seg.revenue_formula}`")
                        if seg.revenue_drivers:
                            import pandas as pd
                            driver_data = []
                            for d in seg.revenue_drivers:
                                src_icon = "文書" if getattr(d, "is_from_document", False) else "推定"
                                driver_data.append({
                                    "ドライバー": d.name,
                                    "単位": d.unit,
                                    "推定値": d.estimated_value or "-",
                                    "出典": src_icon,
                                    "根拠": d.evidence[:80] if d.evidence else "-",
                                })
                            st.dataframe(pd.DataFrame(driver_data), width="stretch", hide_index=True)
                        if seg.key_assumptions:
                            st.markdown("  前提条件: " + " / ".join(seg.key_assumptions))

                # Shared costs
                if p.shared_costs:
                    st.markdown("**共通コスト:**")
                    import pandas as pd
                    cost_data = []
                    for c in p.shared_costs:
                        cost_data.append({
                            "項目": c.name,
                            "区分": c.category,
                            "推定値": c.estimated_value or "-",
                            "根拠": c.evidence[:80] if c.evidence else "-",
                        })
                    st.dataframe(pd.DataFrame(cost_data), width="stretch", hide_index=True)

                if p.growth_trajectory:
                    st.markdown(f"**成長シナリオ:** {p.growth_trajectory}")
                if p.risk_factors:
                    st.markdown(f"**リスク要因:** {', '.join(p.risk_factors)}")
    else:
        # Fallback: old-style single result (no proposals)
        st.markdown(f"**会社名:** {bm.company_name}")
        st.markdown(f"**事業概要:** {bm.executive_summary}")
        st.markdown(f"**業種:** {bm.industry} | **モデル:** {bm.business_model_type} | **期間:** {bm.time_horizon}")

        st.markdown("---")
        st.markdown("**事業セグメント:**")
        for i, seg in enumerate(bm.segments):
            with st.expander(f"#{i+1} {seg.name} ({seg.model_type})", expanded=True):
                st.markdown(f"**収益公式:** `{seg.revenue_formula}`")
                if seg.revenue_drivers:
                    import pandas as pd
                    driver_data = []
                    for d in seg.revenue_drivers:
                        driver_data.append({
                            "ドライバー": d.name,
                            "単位": d.unit,
                            "推定値": d.estimated_value or "-",
                            "根拠": d.evidence[:80] if d.evidence else "-",
                        })
                    st.dataframe(pd.DataFrame(driver_data), width="stretch", hide_index=True)
                if seg.key_assumptions:
                    st.markdown("**前提条件:** " + " / ".join(seg.key_assumptions))

        if bm.shared_costs:
            st.markdown("---")
            st.markdown("**共通コスト:**")
            import pandas as pd
            cost_data = []
            for c in bm.shared_costs:
                cost_data.append({
                    "項目": c.name,
                    "区分": c.category,
                    "推定値": c.estimated_value or "-",
                    "根拠": c.evidence[:80] if c.evidence else "-",
                })
            st.dataframe(pd.DataFrame(cost_data), width="stretch", hide_index=True)

        if bm.risk_factors:
            st.markdown(f"**リスク要因:** {', '.join(bm.risk_factors)}")

    # Raw JSON (collapsed)
    with st.expander("Raw JSON", expanded=False):
        st.json(bm.raw_json)


# --- Phase 3 UI helpers ---------------------------------------------------

_PURPOSE_MAP: Dict[str, Tuple[str, str]] = {
    "revenue_model": ("収益モデル", "revenue"),
    "cost_detail": ("費用明細", "cost"),
    "assumptions": ("前提条件", "assumptions"),
    "pl_summary": ("PL集計", "summary"),
    "headcount": ("人員計画", "other"),
    "capex": ("設備投資", "other"),
}


def _conf_cls(confidence: float) -> str:
    """Return CSS class suffix for a confidence value."""
    if confidence >= 0.85:
        return "high"
    if confidence >= 0.6:
        return "med"
    return "low"


# ===================================================================
# Phase 3: Template Structure
# ===================================================================

def _render_phase_3() -> None:
    st.markdown(
        '<div class="phase-header">'
        '<h2>テンプレート構造マッピング</h2>'
        '<p>テンプレートの各シートをビジネスセグメントに自動マッピングし、'
        'PLモデルの構造を決定します</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    ts = st.session_state.get("ts_result")
    ts_error = st.session_state.get("ts_error", "")

    # --- Initial state: no results yet ---
    if ts is None and not ts_error:
        st.markdown(
            '<div class="start-card">'
            '<div class="start-card-title">マッピング準備完了</div>'
            '<div class="start-card-desc">'
            'BM分析の結果をもとに、テンプレートの各シートが'
            'どのビジネスセグメントに対応するかをAIが自動判定します'
            '</div></div>',
            unsafe_allow_html=True,
        )
        if st.button("マッピングを開始", type="primary", width="stretch", key="btn_ts_run"):
            _run_template_mapping()
            st.rerun()
        return

    if ts_error:
        st.error(f"エラー: {ts_error}")

    if ts is not None:
        _render_ts_results(ts)

    # --- Feedback section ---
    st.markdown(
        '<div class="feedback-section">'
        '<div class="fb-label">フィードバック</div>'
        '<div class="fb-hint">'
        'マッピングの修正指示があれば入力してください'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    feedback = st.text_area(
        "フィードバック",
        value="",
        placeholder="例: 「費用リスト」シートは人件費専用にしてください",
        key="ts_feedback",
        label_visibility="collapsed",
    )

    # --- Action buttons ---
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        if st.button("再検討", width="stretch", key="btn_ts_rerun"):
            _run_template_mapping(feedback=feedback)
            st.rerun()
    with col2:
        can_confirm = ts is not None
        if st.button("確定 → モデル設計へ", type="primary", width="stretch",
                      disabled=not can_confirm, key="btn_ts_confirm"):
            st.session_state["wizard_phase"] = 4
            st.rerun()
    with col3:
        if st.button("戻る", width="stretch", key="btn_ts_back"):
            st.session_state["wizard_phase"] = 2
            st.rerun()


def _run_template_mapping(feedback: str = "") -> None:
    bm = st.session_state.get("bm_result")
    writable_items = st.session_state.get("writable_items", [])
    if not bm:
        st.session_state["ts_error"] = "BM分析結果がありません。Phase 2に戻ってください。"
        return

    with st.spinner("テンプレート構造を検討中... （LLM応答を待機中）"):
        try:
            orch = _get_orchestrator()
            ts = orch.run_template_mapping(bm.raw_json, writable_items, feedback=feedback)
            st.session_state["ts_result"] = ts
            st.session_state["ts_error"] = ""
        except Exception as exc:
            tb = traceback.format_exc()
            st.session_state["ts_error"] = f"{exc}\n\n{tb}"
            logger.error("Template mapping failed: %s\n%s", exc, tb)


def _render_ts_results(ts: Any) -> None:
    mappings = ts.sheet_mappings
    n_sheets = len(mappings)

    avg_conf = sum(sm.confidence for sm in mappings) / max(n_sheets, 1)
    unique_segments = {
        sm.mapped_segment for sm in mappings
        if sm.mapped_segment and "未使用" not in sm.mapped_segment and "予備" not in sm.mapped_segment
    }
    n_active = len(unique_segments) or 1

    # --- Stats row ---
    st.markdown(
        f'<div class="grid-stats">'
        f'<div class="grid-stat">'
        f'<div class="grid-stat-val clr-blue">{n_sheets}</div>'
        f'<div class="grid-stat-lbl">シート検出</div></div>'
        f'<div class="grid-stat">'
        f'<div class="grid-stat-val clr-green">{avg_conf:.0%}</div>'
        f'<div class="grid-stat-lbl">平均信頼度</div></div>'
        f'<div class="grid-stat">'
        f'<div class="grid-stat-val clr-amber">{n_active}</div>'
        f'<div class="grid-stat-lbl">セグメント</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # --- Overall structure overview ---
    if ts.overall_structure:
        st.markdown(
            '<div class="section-title">全体構成</div>'
            f'<div class="overview-card">{_esc(ts.overall_structure)}</div>',
            unsafe_allow_html=True,
        )

    # --- Sheet mapping cards ---
    st.markdown(
        '<div class="section-title">シートマッピング</div>',
        unsafe_allow_html=True,
    )

    for sm in mappings:
        purpose_info = _PURPOSE_MAP.get(
            sm.sheet_purpose, (sm.sheet_purpose or "その他", "other"),
        )
        purpose_label, purpose_cls = purpose_info
        cls = _conf_cls(sm.confidence)
        pct_str = f"{sm.confidence:.0%}"
        width = f"{sm.confidence * 100:.0f}"

        card_html = (
            f'<div class="clean-card">'
            f'<div class="clean-card-top">'
            f'<span class="clean-card-title">{_esc(sm.sheet_name)}</span>'
            f'<span class="clean-tag {purpose_cls}">{_esc(purpose_label)}</span>'
            f'</div>'
            f'<div class="clean-seg">'
            f'<span class="arr">&rarr;</span> {_esc(sm.mapped_segment)}'
            f'</div>'
            f'<div class="conf-bar">'
            f'<div class="conf-bg">'
            f'<div class="conf-fill {cls}" style="width:{width}%"></div>'
            f'</div>'
            f'<span class="conf-pct {cls}">{pct_str}</span>'
            f'</div>'
        )
        if sm.reasoning:
            card_html += f'<div class="clean-reason">{_esc(sm.reasoning)}</div>'
        card_html += '</div>'

        st.markdown(card_html, unsafe_allow_html=True)

    # --- Suggestions ---
    if ts.suggestions:
        st.markdown(
            '<div class="section-title">提案</div>',
            unsafe_allow_html=True,
        )
        for s in ts.suggestions:
            st.markdown(
                f'<div class="suggest-card">{_esc(s)}</div>',
                unsafe_allow_html=True,
            )

    # --- Revenue model configuration ---
    _render_revenue_model_config(ts)

    # --- Raw JSON (debug) ---
    with st.expander("詳細データ (JSON)", expanded=False):
        st.json(ts.raw_json)


def _render_revenue_model_config(ts: Any) -> None:
    """Revenue model sheet configurator: map segments to revenue model slots."""
    mappings = ts.sheet_mappings

    # Find revenue model sheets and segments
    revenue_sheets = [
        sm for sm in mappings
        if sm.sheet_purpose == "revenue_model"
    ]
    bm = st.session_state.get("bm_result")
    segments = []
    if bm and hasattr(bm, "segments"):
        segments = [s.name for s in bm.segments if hasattr(s, "name")]

    if not revenue_sheets and not segments:
        return

    st.markdown(
        '<div class="p3-section-title">収益モデル設定</div>',
        unsafe_allow_html=True,
    )

    # Initialize active_revenue_sheets in session state
    if "active_revenue_sheets" not in st.session_state:
        initial_config = {}
        for i, rs in enumerate(revenue_sheets):
            seg_name = rs.mapped_segment or ""
            initial_config[rs.sheet_name] = {
                "active": bool(seg_name and "未使用" not in seg_name and "予備" not in seg_name),
                "segment": seg_name,
            }
        st.session_state["active_revenue_sheets"] = initial_config

    config = st.session_state["active_revenue_sheets"]

    # Ensure all revenue sheets are in config
    for rs in revenue_sheets:
        if rs.sheet_name not in config:
            config[rs.sheet_name] = {
                "active": False,
                "segment": rs.mapped_segment or "",
            }

    # Build segment options
    seg_options = ["(未割当)"] + segments

    html_parts = ['<div class="rm-section">']
    html_parts.append('<div class="rm-title">事業セグメント → 収益モデルシート</div>')
    html_parts.append('</div>')
    st.markdown("".join(html_parts), unsafe_allow_html=True)

    changed = False
    for rs in revenue_sheets:
        sheet_name = rs.sheet_name
        entry = config.get(sheet_name, {"active": False, "segment": ""})

        cols = st.columns([0.5, 2, 0.5, 3])
        with cols[0]:
            is_active = st.checkbox(
                "有効",
                value=entry.get("active", False),
                key=f"rm_active_{sheet_name}",
                label_visibility="collapsed",
            )
            if is_active != entry.get("active", False):
                entry["active"] = is_active
                changed = True

        with cols[1]:
            st.markdown(f"**{_esc(sheet_name)}**")

        with cols[2]:
            st.markdown("&rarr;", unsafe_allow_html=True)

        with cols[3]:
            current_seg = entry.get("segment", "")
            default_idx = 0
            for j, opt in enumerate(seg_options):
                if opt == current_seg:
                    default_idx = j
                    break

            selected = st.selectbox(
                f"セグメント ({sheet_name})",
                options=seg_options,
                index=default_idx,
                key=f"rm_seg_{sheet_name}",
                label_visibility="collapsed",
                disabled=not is_active,
            )
            new_seg = "" if selected == "(未割当)" else selected
            if new_seg != entry.get("segment", ""):
                entry["segment"] = new_seg
                changed = True

        config[sheet_name] = entry

    if changed:
        st.session_state["active_revenue_sheets"] = config

    # Summary
    active_count = sum(1 for v in config.values() if v.get("active"))
    mapped_count = sum(
        1 for v in config.values()
        if v.get("active") and v.get("segment")
    )
    st.caption(
        f"有効シート: {active_count} / {len(revenue_sheets)}　"
        f"セグメント割当済み: {mapped_count}"
    )


# ===================================================================
# Phase 4: Model Design
# ===================================================================

def _render_phase_4() -> None:
    st.markdown(
        '<div class="phase-header">'
        '<h2>モデル設計</h2>'
        '<p>各入力セルが表すビジネス概念を決定します。'
        'テンプレートの全セルに概念を割り当て、PLモデルの設計図を構築します</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    md = st.session_state.get("md_result")
    md_error = st.session_state.get("md_error", "")

    if md is None and not md_error:
        st.markdown(
            '<div class="start-card">'
            '<div class="start-card-title">モデル設計の準備完了</div>'
            '<div class="start-card-desc">'
            'BM分析とテンプレート構造をもとに、各入力セルに'
            'ビジネス概念を自動マッピングします</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        if st.button("モデル設計を開始", type="primary", width="stretch", key="btn_md_run"):
            _run_model_design()
            st.rerun()
        return

    if md_error:
        st.error(f"エラー: {md_error}")

    if md is not None:
        _render_md_results(md)

    # --- Feedback section ---
    st.markdown(
        '<div class="feedback-section">'
        '<div class="fb-label">フィードバック</div>'
        '<div class="fb-hint">'
        'セルの概念マッピングに修正が必要な場合、指示を入力してください'
        '</div></div>',
        unsafe_allow_html=True,
    )
    feedback = st.text_area(
        "フィードバック",
        value="",
        placeholder="例: B5セルは顧客数ではなく受講者数にしてください。",
        key="md_feedback",
        label_visibility="collapsed",
    )

    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        if st.button("再設計", width="stretch", key="btn_md_rerun"):
            _run_model_design(feedback=feedback)
            st.rerun()
    with col2:
        can_confirm = md is not None
        if st.button("確定 → パラメーターへ", type="primary", width="stretch",
                      disabled=not can_confirm, key="btn_md_confirm"):
            st.session_state["wizard_phase"] = 5
            st.rerun()
    with col3:
        if st.button("戻る", width="stretch", key="btn_md_back"):
            st.session_state["wizard_phase"] = 3
            st.rerun()


def _run_model_design(feedback: str = "") -> None:
    bm = st.session_state.get("bm_result")
    ts = st.session_state.get("ts_result")
    writable_items = st.session_state.get("writable_items", [])
    if not bm or not ts:
        st.session_state["md_error"] = "前フェーズの結果がありません。戻ってください。"
        return

    with st.spinner("モデル設計中... （LLM応答を待機中。30〜60秒かかる場合があります）"):
        try:
            orch = _get_orchestrator()
            logger.info("Model design: starting with %d writable items", len(writable_items))
            md = orch.run_model_design(
                bm.raw_json, ts.raw_json, writable_items, feedback=feedback,
            )
            st.session_state["md_result"] = md
            st.session_state["md_error"] = ""
            logger.info("Model design: success, %d assignments", len(md.cell_assignments))
        except Exception as exc:
            tb = traceback.format_exc()
            st.session_state["md_error"] = f"{exc}\n\n{tb}"
            logger.error("Model design failed: %s\n%s", exc, tb)


def _render_md_results(md: Any) -> None:
    import pandas as pd

    n_assigned = len(md.cell_assignments)
    n_unmapped = len(md.unmapped_cells)
    avg_conf = (
        sum(ca.confidence for ca in md.cell_assignments) / max(n_assigned, 1)
        if md.cell_assignments else 0
    )
    n_high = sum(1 for ca in md.cell_assignments if ca.confidence >= 0.7)

    # --- Stats cards ---
    st.markdown(
        f'<div class="grid-stats">'
        f'<div class="grid-stat">'
        f'<div class="grid-stat-val clr-green">{n_assigned}</div>'
        f'<div class="grid-stat-lbl">セル割当</div></div>'
        f'<div class="grid-stat">'
        f'<div class="grid-stat-val clr-blue">{avg_conf:.0%}</div>'
        f'<div class="grid-stat-lbl">平均信頼度</div></div>'
        f'<div class="grid-stat">'
        f'<div class="grid-stat-val clr-amber">{n_high}</div>'
        f'<div class="grid-stat-lbl">高信頼度</div></div>'
        f'<div class="grid-stat">'
        f'<div class="grid-stat-val clr-red">{n_unmapped}</div>'
        f'<div class="grid-stat-lbl">未割当</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # --- Editable grid per sheet (using tabs) ---
    if md.cell_assignments:
        sheets = sorted(set(ca.sheet for ca in md.cell_assignments))
        sheet_tabs = st.tabs([
            f"{s} ({sum(1 for ca in md.cell_assignments if ca.sheet == s)})"
            for s in sheets
        ])

        for idx, sheet in enumerate(sheets):
            with sheet_tabs[idx]:
                items = [ca for ca in md.cell_assignments if ca.sheet == sheet]
                # Sort by category for grouping
                items.sort(key=lambda x: (x.category or "zzz", x.cell))
                data = []
                for ca in items:
                    data.append({
                        "カテゴリ": ca.category or "",
                        "セル": ca.cell,
                        "ラベル": ca.label,
                        "割当概念": ca.assigned_concept,
                        "セグメント": ca.segment,
                        "期間": ca.period,
                        "単位": ca.unit,
                        "導出": ca.derivation,
                        "信頼度": ca.confidence,
                    })
                df = pd.DataFrame(data)

                column_config = {
                    "カテゴリ": st.column_config.TextColumn("カテゴリ", width="medium", disabled=True),
                    "セル": st.column_config.TextColumn("セル", width="small", disabled=True),
                    "ラベル": st.column_config.TextColumn("ラベル", width="medium", disabled=True),
                    "割当概念": st.column_config.TextColumn("割当概念", width="large"),
                    "セグメント": st.column_config.TextColumn("セグメント", width="medium"),
                    "期間": st.column_config.TextColumn("期間", width="small"),
                    "単位": st.column_config.TextColumn("単位", width="small"),
                    "導出": st.column_config.SelectboxColumn(
                        "導出", width="small",
                        options=["direct", "calculated", "assumption"],
                    ),
                    "信頼度": st.column_config.ProgressColumn(
                        "信頼度", min_value=0.0, max_value=1.0, format="%.0f%%",
                    ),
                }

                edited = st.data_editor(
                    df,
                    column_config=column_config,
                    width="stretch",
                    hide_index=True,
                    num_rows="fixed",
                    key=f"md_grid_{sheet}",
                )

                # Store edits back to md_result
                _sync_md_edits(md, sheet, edited)

    # --- Unmapped cells ---
    if md.unmapped_cells:
        st.markdown(
            f'<div class="unmapped-section">'
            f'<div class="unmapped-title">未割当セル ({n_unmapped}件)</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        unmap_data = []
        for uc in md.unmapped_cells:
            unmap_data.append({
                "シート": uc.get("sheet", ""),
                "セル": uc.get("cell", ""),
                "ラベル": uc.get("label", ""),
                "理由": uc.get("reason", ""),
            })
        st.dataframe(pd.DataFrame(unmap_data), width="stretch", hide_index=True)

    if md.warnings:
        for w in md.warnings:
            st.warning(w)

    with st.expander("詳細データ (JSON)", expanded=False):
        st.json(md.raw_json)


def _sync_md_edits(md: Any, sheet: str, edited_df: Any) -> None:
    """Sync data_editor edits back into the ModelDesignResult."""
    sheet_items = [ca for ca in md.cell_assignments if ca.sheet == sheet]
    for i, ca in enumerate(sheet_items):
        if i < len(edited_df):
            row = edited_df.iloc[i]
            ca.assigned_concept = str(row.get("割当概念", ca.assigned_concept))
            ca.segment = str(row.get("セグメント", ca.segment))
            ca.period = str(row.get("期間", ca.period))
            ca.unit = str(row.get("単位", ca.unit))
            ca.derivation = str(row.get("導出", ca.derivation))


# ===================================================================
# Phase 5: Parameter Extraction
# ===================================================================

def _render_phase_5() -> None:
    st.markdown(
        '<div class="phase-header">'
        '<h2>パラメーター抽出</h2>'
        '<p>確定したモデル設計に基づいて、事業計画書から各セルの実際の値を抽出します。'
        'グリッド上で値を直接編集できます</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    pe = st.session_state.get("pe_result")
    pe_error = st.session_state.get("pe_error", "")

    if pe is None and not pe_error:
        st.markdown(
            '<div class="start-card">'
            '<div class="start-card-title">パラメーター抽出の準備完了</div>'
            '<div class="start-card-desc">'
            'モデル設計をもとに、事業計画書から各セルの具体的な値を'
            'AIが自動抽出します</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        if st.button("パラメーター抽出開始", type="primary", width="stretch", key="btn_pe_run"):
            _run_parameter_extraction()
            st.rerun()
        return

    if pe_error:
        st.error(f"エラー: {pe_error}")

    if pe is not None:
        _render_pe_results(pe)

    # --- Feedback section ---
    st.markdown(
        '<div class="feedback-section">'
        '<div class="fb-label">フィードバック</div>'
        '<div class="fb-hint">'
        '抽出値に修正が必要な場合、指示を入力してください。'
        'グリッド上でも直接編集可能です'
        '</div></div>',
        unsafe_allow_html=True,
    )
    feedback = st.text_area(
        "フィードバック",
        value="",
        placeholder="例: 顧客数は100ではなく200です。",
        key="pe_feedback",
        label_visibility="collapsed",
    )

    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        if st.button("再抽出", width="stretch", key="btn_pe_rerun"):
            _run_parameter_extraction(feedback=feedback)
            st.rerun()
    with col2:
        can_confirm = pe is not None
        if st.button("確定 → 最終出力へ", type="primary", width="stretch",
                      disabled=not can_confirm, key="btn_pe_confirm"):
            _convert_extractions_to_parameters()
            st.session_state["wizard_phase"] = 6
            st.rerun()
    with col3:
        if st.button("戻る", width="stretch", key="btn_pe_back"):
            st.session_state["wizard_phase"] = 4
            st.rerun()


def _run_parameter_extraction(feedback: str = "") -> None:
    md = st.session_state.get("md_result")
    document = st.session_state.get("document")
    if not md or not document:
        st.session_state["pe_error"] = "前フェーズの結果がありません。戻ってください。"
        return

    with st.spinner("パラメーターを抽出中... （LLM応答を待機中）"):
        try:
            orch = _get_orchestrator()
            pe = orch.run_parameter_extraction(
                md.raw_json, document.full_text, feedback=feedback,
            )
            st.session_state["pe_result"] = pe
            st.session_state["pe_error"] = ""
        except Exception as exc:
            tb = traceback.format_exc()
            st.session_state["pe_error"] = f"{exc}\n\n{tb}"
            logger.error("Parameter extraction failed: %s\n%s", exc, tb)


def _render_pe_results(pe: Any) -> None:
    import pandas as pd

    n_ext = len(pe.extractions)
    n_unmapped = len(pe.unmapped_cells)
    n_doc = sum(1 for e in pe.extractions if e.source == "document")
    n_inf = sum(1 for e in pe.extractions if e.source == "inferred")
    n_def = sum(1 for e in pe.extractions if e.source == "default")
    avg_conf = (
        sum(e.confidence for e in pe.extractions) / max(n_ext, 1)
        if pe.extractions else 0
    )

    # --- Stats cards ---
    st.markdown(
        f'<div class="grid-stats">'
        f'<div class="grid-stat">'
        f'<div class="grid-stat-val clr-green">{n_ext}</div>'
        f'<div class="grid-stat-lbl">抽出済み</div></div>'
        f'<div class="grid-stat">'
        f'<div class="grid-stat-val clr-blue">{n_doc}</div>'
        f'<div class="grid-stat-lbl">文書から直接</div></div>'
        f'<div class="grid-stat">'
        f'<div class="grid-stat-val clr-amber">{n_inf + n_def}</div>'
        f'<div class="grid-stat-lbl">推定・デフォルト</div></div>'
        f'<div class="grid-stat">'
        f'<div class="grid-stat-val clr-red">{n_unmapped}</div>'
        f'<div class="grid-stat-lbl">未抽出</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # --- Build category lookup from Phase 4 model design ---
    md = st.session_state.get("md_result")
    category_map: Dict[str, str] = {}
    if md and hasattr(md, "cell_assignments"):
        for ca in md.cell_assignments:
            cat = getattr(ca, "category", "")
            if cat:
                category_map[f"{ca.sheet}!{ca.cell}"] = cat

    # --- Editable grid per sheet (using tabs) ---
    if pe.extractions:
        sheets = sorted(set(e.sheet for e in pe.extractions))
        sheet_tabs = st.tabs([
            f"{s} ({sum(1 for e in pe.extractions if e.sheet == s)})"
            for s in sheets
        ])

        for idx, sheet in enumerate(sheets):
            with sheet_tabs[idx]:
                items = [e for e in pe.extractions if e.sheet == sheet]
                # Sort by category for grouping
                items.sort(key=lambda x: (
                    category_map.get(f"{x.sheet}!{x.cell}", "zzz"), x.cell
                ))
                data = []
                for e in items:
                    val = e.value
                    if isinstance(val, str):
                        try:
                            val = float(val)
                        except (ValueError, TypeError):
                            pass
                    cat = category_map.get(f"{e.sheet}!{e.cell}", "")
                    data.append({
                        "カテゴリ": cat,
                        "セル": e.cell,
                        "ラベル": e.label or e.concept,
                        "値": val,
                        "単位": e.unit,
                        "ソース": e.source,
                        "信頼度": e.confidence,
                        "根拠": e.evidence or "",
                    })
                df = pd.DataFrame(data)

                column_config = {
                    "カテゴリ": st.column_config.TextColumn("カテゴリ", width="medium", disabled=True),
                    "セル": st.column_config.TextColumn("セル", width="small", disabled=True),
                    "ラベル": st.column_config.TextColumn("ラベル", width="medium", disabled=True),
                    "値": st.column_config.NumberColumn("値", width="medium", format="%.2f"),
                    "単位": st.column_config.TextColumn("単位", width="small", disabled=True),
                    "ソース": st.column_config.SelectboxColumn(
                        "ソース", width="small",
                        options=["document", "inferred", "default"],
                    ),
                    "信頼度": st.column_config.ProgressColumn(
                        "信頼度", min_value=0.0, max_value=1.0, format="%.0f%%",
                    ),
                    "根拠": st.column_config.TextColumn("根拠", width="large", disabled=True),
                }

                edited = st.data_editor(
                    df,
                    column_config=column_config,
                    width="stretch",
                    hide_index=True,
                    num_rows="fixed",
                    key=f"pe_grid_{sheet}",
                )

                # Sync edits back
                _sync_pe_edits(pe, sheet, edited)

    # --- Unmapped cells ---
    if pe.unmapped_cells:
        st.markdown(
            f'<div class="unmapped-section">'
            f'<div class="unmapped-title">未抽出セル ({n_unmapped}件)</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        unmap_data = [
            {"シート": uc.get("sheet", ""), "セル": uc.get("cell", ""),
             "ラベル": uc.get("label", ""), "理由": uc.get("reason", "")}
            for uc in pe.unmapped_cells
        ]
        st.dataframe(pd.DataFrame(unmap_data), width="stretch", hide_index=True)

    if pe.warnings:
        for w in pe.warnings:
            st.warning(w)

    with st.expander("詳細データ (JSON)", expanded=False):
        st.json(pe.raw_json)


def _sync_pe_edits(pe: Any, sheet: str, edited_df: Any) -> None:
    """Sync data_editor edits back into the ParameterExtractionResult."""
    sheet_items = [e for e in pe.extractions if e.sheet == sheet]
    for i, ext in enumerate(sheet_items):
        if i < len(edited_df):
            row = edited_df.iloc[i]
            new_val = row.get("値")
            if new_val is not None:
                ext.value = new_val
            new_src = row.get("ソース")
            if new_src and new_src in ("document", "inferred", "default"):
                ext.source = str(new_src)


def _convert_extractions_to_parameters() -> None:
    """Convert Phase 5 extractions to ExtractedParameter format for Phase 6."""
    pe = st.session_state.get("pe_result")
    if not pe:
        return

    parameters: List[ExtractedParameter] = []
    for ext in pe.extractions:
        if ext.value is not None:
            # Map Phase 5 source names to ExtractedParameter Literal values
            src = ext.source
            if src == "default":
                src = "template_default"
            elif src not in ("document", "inferred", "template_default"):
                src = "document"

            param = ExtractedParameter(
                key=f"{ext.sheet}::{ext.cell}",
                label=ext.label or ext.concept,
                value=ext.value,
                unit=ext.unit,
                mapped_targets=[CellTarget(sheet=ext.sheet, cell=ext.cell)],
                evidence=Evidence(
                    quote=ext.evidence or "",
                    page_or_slide="",
                    rationale=f"segment: {ext.segment}",
                ),
                confidence=ext.confidence,
                source=src,
            )
            parameters.append(param)

    st.session_state["parameters"] = parameters

    # Clear old blueprint state
    for key in list(st.session_state.keys()):
        if key.startswith("bp_"):
            del st.session_state[key]
    st.session_state["generation_outputs"] = {}


# ===================================================================
# Phase 6: Final Output & Blueprint
# ===================================================================

def _render_phase_6() -> None:
    st.markdown(
        '<div class="phase-header">'
        '<h2>最終出力</h2>'
        '<p>全フェーズの結果を確認し、Excel PLモデルを生成します</p>'
        '</div>',
        unsafe_allow_html=True,
    )
    analysis: Optional[AnalysisReport] = st.session_state.get("analysis")
    catalog: Optional[InputCatalog] = st.session_state.get("catalog")
    parameters: list = st.session_state.get("parameters", [])
    config: Optional[PhaseAConfig] = st.session_state.get("config")

    if analysis is None or catalog is None:
        st.warning("データがありません。Phase 1に戻ってください。")
        if st.button("Phase 1 に戻る"):
            st.session_state["wizard_phase"] = 1
            st.rerun()
        return

    param_map = _build_param_cell_map(parameters)

    # Summary from all phases
    bm = st.session_state.get("bm_result")
    ts = st.session_state.get("ts_result")
    md = st.session_state.get("md_result")
    pe = st.session_state.get("pe_result")

    st.success(f"**全フェーズ完了: {len(parameters)}件のパラメーターを抽出しました。**")

    # Phase summary
    with st.expander("フェーズサマリー", expanded=True):
        if bm:
            st.markdown(f"**BM分析:** {bm.industry} / {bm.business_model_type} / {len(bm.segments)}セグメント")
        if ts:
            st.markdown(f"**テンプレ構造:** {len(ts.sheet_mappings)}シート")
        if md:
            st.markdown(f"**モデル設計:** {len(md.cell_assignments)}セル割当")
        if pe:
            st.markdown(f"**パラメーター:** {len(pe.extractions)}件抽出 / {len(pe.unmapped_cells)}件未抽出")

    # Summary Dashboard
    _render_blueprint_summary(catalog, parameters, analysis, param_map)

    st.markdown("")

    # Action buttons
    col_gen, col_back = st.columns([3, 1])
    with col_gen:
        generate_clicked = st.button(
            "Excel を生成する",
            type="primary", width="stretch", key="btn_blueprint_generate",
        )
    with col_back:
        if st.button("← パラメーターに戻る", key="b_back", width="stretch"):
            st.session_state["wizard_phase"] = 5
            st.rerun()

    # Download section (if already generated)
    gen_outputs = st.session_state.get("generation_outputs", {})
    if gen_outputs:
        _render_download_section(gen_outputs)

    st.divider()

    # Blueprint: Sheet tabs
    st.markdown('<div class="section-title">PL 設計図</div>', unsafe_allow_html=True)
    st.caption("値を確認・編集してから「Excel を生成する」をクリックしてください。")

    sheets = catalog.sheets()
    if not sheets:
        st.info("テンプレートにシートが見つかりませんでした。")
    else:
        sheet_tabs = st.tabs([
            f"{s} ({_count_sheet_filled(s, catalog, param_map)}/{_count_sheet_items(s, catalog)})"
            for s in sheets
        ])
        for idx, sheet_name in enumerate(sheets):
            with sheet_tabs[idx]:
                _render_sheet_blueprint(sheet_name, catalog, parameters, analysis, param_map)

    # Detail info
    st.divider()
    with st.expander("詳細情報（モデル構造・エビデンス）", expanded=False):
        _render_detail_section(analysis, catalog, parameters)

    # Run generation if clicked
    if generate_clicked:
        _run_generation_from_blueprint()


# ===================================================================
# Blueprint helpers (shared with Phase 6)
# ===================================================================

def _build_param_cell_map(parameters: list) -> Dict[str, Any]:
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


def _render_blueprint_summary(
    catalog: InputCatalog, parameters: list,
    analysis: AnalysisReport, param_map: dict,
) -> None:
    writable_items = [i for i in catalog.items if not i.has_formula]
    total_inputs = len(writable_items)
    filled = sum(1 for i in writable_items
                 if f"{i.sheet}!{i.cell}" in param_map)
    gaps = total_inputs - filled
    kpi_count = len(analysis.kpis) if analysis.kpis else 0
    pct = int(filled / total_inputs * 100) if total_inputs > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(_render_metric_card(f"{filled}/{total_inputs}", "入力済み"), unsafe_allow_html=True)
    with c2:
        if gaps > 0:
            st.markdown(_render_gap_metric_card(str(gaps), "未入力 (GAP)"), unsafe_allow_html=True)
        else:
            st.markdown(_render_metric_card("0", "未入力 (GAP)"), unsafe_allow_html=True)
    with c3:
        st.markdown(_render_metric_card(str(kpi_count), "算出指標 (KPI)"), unsafe_allow_html=True)
    with c4:
        st.markdown(_render_metric_card(f"{pct}%", "完成度"), unsafe_allow_html=True)

    if total_inputs > 0:
        st.progress(filled / total_inputs, text=f"{filled}/{total_inputs} 項目入力済み")


def _render_sheet_blueprint(
    sheet_name: str, catalog: InputCatalog, parameters: list,
    analysis: AnalysisReport, param_map: dict,
) -> None:
    # KPI banner
    sheet_kpis = [k for k in (analysis.kpis or []) if k.sheet == sheet_name]
    if sheet_kpis:
        _render_kpi_banner(sheet_kpis)

    # Group writable items by block
    blocks: Dict[str, List[CatalogItem]] = {}
    for item in catalog.items:
        if item.sheet != sheet_name or item.has_formula:
            continue
        block = item.block or "その他"
        blocks.setdefault(block, []).append(item)

    if not blocks:
        st.info("このシートには入力セルがありません。")
        return

    for block_name, items in blocks.items():
        filled_count = sum(1 for i in items if f"{i.sheet}!{i.cell}" in param_map)
        total_count = len(items)
        is_complete = (filled_count == total_count)

        with st.expander(
            f"{block_name}  ({filled_count}/{total_count} 入力済み)",
            expanded=not is_complete,
        ):
            _render_block_inputs(items, param_map)


def _extract_dep_label(dep: str) -> str:
    if " (" in dep:
        return dep.split(" (")[0].strip()
    return dep.replace("'", "").strip()


def _render_kpi_banner(kpis: List[KPIDefinition]) -> None:
    li_items: List[str] = []
    for kpi in kpis:
        name_esc = _esc(kpi.name)
        line = f"<strong>{name_esc}</strong>"
        if kpi.dependencies:
            seen: set = set()
            dep_labels: list = []
            for d in kpi.dependencies:
                label = _extract_dep_label(d)
                if label and label not in seen:
                    seen.add(label)
                    dep_labels.append(_esc(label))
            if dep_labels:
                shown = dep_labels[:5]
                rest = len(dep_labels) - 5
                deps_str = "、".join(shown)
                if rest > 0:
                    deps_str += f" など（計 {len(dep_labels)} 項目）"
                line += f'<br><span class="kpi-dep">&#8592; {deps_str} から算出</span>'
        li_items.append(f"<li>{line}</li>")

    kpi_html = "\n".join(li_items)
    st.markdown(f"""
    <div class="kpi-banner">
        <div class="kpi-banner-title">
            計算結果（操作不要 &#8212; 下の入力値から自動計算されます）
        </div>
        <ul>{kpi_html}</ul>
    </div>
    """, unsafe_allow_html=True)


def _render_block_inputs(
    items: List[CatalogItem], param_map: Dict[str, Any],
) -> None:
    for item in items:
        addr = f"{item.sheet}!{item.cell}"
        param = param_map.get(addr)

        label = item.primary_label()
        unit = item.unit_candidates[0] if item.unit_candidates else ""
        period = item.year_or_period or ""

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
                        label_display, value=float(current_val),
                        key=state_key, label_visibility="collapsed", format="%.2f",
                    )
                else:
                    st.text_input(
                        label_display,
                        value=str(current_val) if current_val is not None else "",
                        key=state_key, label_visibility="collapsed",
                    )
            else:
                has_template_default = (
                    item.current_value is not None
                    and item.current_value != ""
                    and not (isinstance(item.current_value, str)
                             and item.current_value.startswith("="))
                )
                st.text_input(
                    label_display, value="", key=state_key,
                    label_visibility="collapsed",
                    placeholder=(
                        f"テンプレート参考値: {item.current_value}"
                        if has_template_default else "値を入力..."
                    ),
                )

        with cols[2]:
            if unit:
                st.markdown(f"<br><small>{_esc(unit)}</small>", unsafe_allow_html=True)

        with cols[3]:
            if param:
                conf = getattr(param, "confidence", 0)
                st.markdown(f"<br>{_confidence_badge(conf)}", unsafe_allow_html=True)
                src = getattr(param, "source", "")
                if src == "inferred":
                    st.caption("(推定値)")
            else:
                st.markdown(
                    '<br><span class="badge-gap">未入力</span>',
                    unsafe_allow_html=True,
                )


def _render_detail_section(
    analysis: AnalysisReport, catalog: InputCatalog, parameters: list,
) -> None:
    tab_model, tab_evidence, tab_params = st.tabs([
        "モデル構造", "エビデンス", f"全パラメータ ({len(parameters)})",
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
                items_count = sum(1 for item in catalog.items if item.sheet == sn)
                kpi_count = sum(1 for k in (analysis.kpis or [])
                                if getattr(k, "sheet", None) == sn)
                sheet_data.append({"シート": sn, "入力セル数": items_count, "KPI数": kpi_count})
            st.dataframe(pd.DataFrame(sheet_data), width="stretch", hide_index=True)

        st.markdown("**自動計算される指標:**")
        if analysis.kpis:
            for kpi in analysis.kpis:
                with st.expander(f"{kpi.name}（{kpi.sheet} シート）"):
                    if kpi.dependencies:
                        seen: set = set()
                        labels: list = []
                        for d in kpi.dependencies:
                            lbl = _extract_dep_label(d)
                            if lbl and lbl not in seen:
                                seen.add(lbl)
                                labels.append(lbl)
                        if labels:
                            st.markdown("**算出に使われる入力:** " + "、".join(labels))
                    else:
                        st.caption("依存する入力項目が見つかりませんでした")
        else:
            st.info("自動計算される指標が検出されませんでした。")

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
                        st.markdown(_confidence_badge(conf), unsafe_allow_html=True)
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
                    f"{t.sheet}!{t.cell}" for t in getattr(p, "mapped_targets", [])
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
            st.dataframe(df, width="stretch", hide_index=True)


def _render_download_section(gen_outputs: Dict[str, bytes]) -> None:
    st.markdown("")
    st.markdown("#### 生成完了 - ダウンロード")
    cols = st.columns(min(len(gen_outputs), 3))
    for idx, (fname, fbytes) in enumerate(gen_outputs.items()):
        with cols[idx % len(cols)]:
            mime = (
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                if fname.endswith(".xlsx") else "text/csv"
            )
            st.download_button(
                label=f"{fname}", data=fbytes, file_name=fname, mime=mime,
                width="stretch", key=f"dl_{fname}",
            )


# ===================================================================
# Blueprint parameter collection & generation
# ===================================================================

def _collect_blueprint_parameters() -> list:
    parameters = st.session_state.get("parameters", [])
    catalog: Optional[InputCatalog] = st.session_state.get("catalog")

    adjusted = deepcopy(parameters)

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

    if catalog:
        param_map = _build_param_cell_map(adjusted)
        for item in catalog.items:
            if item.has_formula:
                continue
            addr = f"{item.sheet}!{item.cell}"
            if addr in param_map:
                continue
            state_key = f"bp_{item.sheet}_{item.cell}"
            if state_key in st.session_state:
                val = st.session_state[state_key]
                if val is not None and str(val).strip() != "":
                    new_param = ExtractedParameter(
                        key=f"manual_{item.sheet}_{item.cell}",
                        label=item.primary_label(),
                        value=val,
                        unit=item.unit_candidates[0] if item.unit_candidates else None,
                        mapped_targets=[CellTarget(sheet=item.sheet, cell=item.cell)],
                        confidence=1.0,
                        source="document",
                        selected=True,
                    )
                    adjusted.append(new_param)

    return adjusted


def _run_generation_from_blueprint() -> None:
    config: Optional[PhaseAConfig] = st.session_state.get("config")
    catalog: Optional[InputCatalog] = st.session_state.get("catalog")
    cc: ColorConfig = st.session_state.get("color_config", ColorConfig())

    if config is None:
        st.error("設定がありません。Phase 1 からやり直してください。")
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

                    try:
                        validator = PLValidator(config.template_path, output_path)
                        val_result = validator.validate()
                        if not val_result.passed:
                            st.warning(
                                f"{case_name.title()}: バリデーション警告 "
                                f"({len(val_result.errors_found)} 件)"
                            )
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
        if run_sim and adjusted_params and SimulationEngine is not None:
            step += 1
            progress.progress(int(step / total_steps * 95), text="シミュレーション実行中...")
            try:
                sim_engine = SimulationEngine(iterations=500)
                sim_report = sim_engine.run(
                    adjusted_params, template_path=config.template_path,
                )
                with tempfile.TemporaryDirectory() as sim_dir:
                    sim_path = str(Path(sim_dir) / "simulation_summary.xlsx")
                    export_simulation_summary(sim_report, sim_path)
                    output_files["simulation_summary.xlsx"] = Path(sim_path).read_bytes()
                st.success("シミュレーション完了")
            except Exception as exc:
                st.warning(f"シミュレーション失敗: {exc}")

        # Needs-review CSV
        try:
            with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as tmp_csv:
                csv_path = generate_needs_review_csv(adjusted_params, tmp_csv.name)
                output_files["needs_review.csv"] = Path(csv_path).read_bytes()
        except Exception:
            pass

        progress.progress(100, text="生成完了!")
        st.session_state["generation_outputs"] = output_files

    except Exception as exc:
        progress.empty()
        st.error("生成中にエラーが発生しました")
        with st.expander("エラー詳細"):
            st.code(traceback.format_exc())


# ===================================================================
# Sidebar
# ===================================================================

def _render_sidebar() -> None:
    with st.sidebar:
        # --- App branding ---
        st.markdown(
            '<div style="text-align:center;padding:0.5rem 0 0.2rem 0;">'
            '<span style="font-size:2rem;">📊</span><br>'
            '<span style="font-size:1.1rem;font-weight:700;color:#0f5132;">PL Generator</span><br>'
            '<span style="font-size:0.72rem;color:#888;">事業計画書 → P&L Excel 自動生成</span>'
            '</div>',
            unsafe_allow_html=True,
        )

        if _IMPORT_ERRORS:
            with st.expander("Import Warnings", expanded=False):
                for ie in _IMPORT_ERRORS:
                    st.warning(ie)

        st.divider()

        # --- Phase navigation (clickable) ---
        current_phase = st.session_state.get("wizard_phase", 1)
        st.markdown(
            '<p style="font-size:0.72rem;font-weight:600;color:#999;'
            'text-transform:uppercase;letter-spacing:0.08em;margin-bottom:0.4rem;">'
            'ワークフロー</p>',
            unsafe_allow_html=True,
        )
        for p in PHASES:
            pk = p["key"]
            label = p["label"]
            if pk == current_phase:
                # Active phase — highlighted
                st.markdown(
                    f'<div style="background:#e8f5e9;border-left:3px solid #198754;'
                    f'padding:0.35rem 0.6rem;margin:2px 0;border-radius:0 6px 6px 0;'
                    f'font-size:0.82rem;font-weight:600;color:#0f5132;">'
                    f'{pk}. {label}</div>',
                    unsafe_allow_html=True,
                )
            elif pk < current_phase:
                # Completed — clickable to go back
                if st.button(
                    f"✓ {pk}. {label}",
                    key=f"nav_phase_{pk}",
                    width="stretch",
                ):
                    st.session_state["wizard_phase"] = pk
                    st.rerun()
            else:
                # Future phase — disabled appearance
                st.markdown(
                    f'<div style="padding:0.3rem 0.6rem;margin:2px 0;'
                    f'font-size:0.78rem;color:#bbb;">'
                    f'{pk}. {label}</div>',
                    unsafe_allow_html=True,
                )

        st.divider()

        # --- Session context ---
        cfg = st.session_state.get("config")
        bm = st.session_state.get("bm_result")
        ts = st.session_state.get("ts_result")
        pe = st.session_state.get("pe_result")

        st.markdown(
            '<p style="font-size:0.72rem;font-weight:600;color:#999;'
            'text-transform:uppercase;letter-spacing:0.08em;margin-bottom:0.4rem;">'
            'セッション情報</p>',
            unsafe_allow_html=True,
        )

        # Upload status
        doc = st.session_state.get("document")
        if doc:
            st.markdown(
                f'<div style="font-size:0.8rem;padding:0.2rem 0;">'
                f'📄 文書: <b>{getattr(doc, "source_filename", "uploaded")}</b></div>',
                unsafe_allow_html=True,
            )
        else:
            st.caption("📄 文書: 未アップロード")

        # Company name
        if bm:
            company = getattr(bm, "company_name", "")
            if company and company != "記載なし":
                st.markdown(
                    f'<div style="font-size:0.8rem;padding:0.2rem 0;">'
                    f'🏢 {company}</div>',
                    unsafe_allow_html=True,
                )
            industry = getattr(bm, "industry", "")
            if industry:
                st.markdown(
                    f'<div style="font-size:0.8rem;padding:0.2rem 0;">'
                    f'🏭 業種: {industry}</div>',
                    unsafe_allow_html=True,
                )
            n_seg = len(getattr(bm, "segments", []))
            if n_seg:
                st.markdown(
                    f'<div style="font-size:0.8rem;padding:0.2rem 0;">'
                    f'📊 セグメント: {n_seg}件</div>',
                    unsafe_allow_html=True,
                )

        if cfg:
            st.markdown(
                f'<div style="font-size:0.8rem;padding:0.2rem 0;">'
                f'📋 ケース: {", ".join(c.title() for c in cfg.cases)}</div>',
                unsafe_allow_html=True,
            )

        params = st.session_state.get("parameters", [])
        if params:
            st.markdown(
                f'<div style="font-size:0.8rem;padding:0.2rem 0;">'
                f'🔢 パラメータ: {len(params)}件</div>',
                unsafe_allow_html=True,
            )

        # --- Generated files ---
        gen_outputs = st.session_state.get("generation_outputs", {})
        if gen_outputs:
            st.divider()
            st.markdown(
                '<p style="font-size:0.72rem;font-weight:600;color:#999;'
                'text-transform:uppercase;letter-spacing:0.08em;margin-bottom:0.4rem;">'
                '生成済みファイル</p>',
                unsafe_allow_html=True,
            )
            for fname, fbytes in gen_outputs.items():
                mime = (
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    if fname.endswith(".xlsx") else "text/csv"
                )
                st.download_button(
                    label=f"📥 {fname}", data=fbytes, file_name=fname,
                    mime=mime, key=f"sidebar_dl_{fname}", width="stretch",
                )

        # --- Tools section ---
        st.divider()
        st.markdown(
            '<p style="font-size:0.72rem;font-weight:600;color:#999;'
            'text-transform:uppercase;letter-spacing:0.08em;margin-bottom:0.4rem;">'
            'ツール</p>',
            unsafe_allow_html=True,
        )

        if st.button("⚙ プロンプト管理", key="btn_prompt_mgmt", width="stretch"):
            st.session_state["show_prompt_mgmt"] = not st.session_state.get("show_prompt_mgmt", False)
            st.rerun()

        # Quick help toggle
        if st.button("❓ ヘルプ", key="btn_help", width="stretch"):
            st.session_state["show_help"] = not st.session_state.get("show_help", False)
            st.rerun()

        if st.session_state.get("show_help", False):
            st.info(
                "**使い方:**\n"
                "1. PDFをアップロード\n"
                "2. BM分析でパターンを選択\n"
                "3. 各フェーズで確認→次へ\n"
                "4. 最終フェーズでExcel生成\n\n"
                "**完了したフェーズ**はクリックで戻れます。\n"
                "**プロンプト管理**でLLMへの指示を編集できます。"
            )

        # --- Footer ---
        st.divider()
        try:
            from src.app.version import version_label
            ver = version_label()
        except Exception:
            ver = "dev"

        col_ver, col_reset = st.columns([2, 1])
        with col_ver:
            st.caption(f"v{ver}")
        with col_reset:
            if not st.session_state.get("reset_confirm", False):
                if st.button("🔄", key="btn_reset", help="セッションをリセット"):
                    st.session_state["reset_confirm"] = True
                    st.rerun()
            else:
                st.warning("リセット?")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Yes", key="btn_reset_yes", type="primary"):
                        for k in list(st.session_state.keys()):
                            del st.session_state[k]
                        st.rerun()
                with c2:
                    if st.button("No", key="btn_reset_no"):
                        st.session_state["reset_confirm"] = False
                        st.rerun()


# ===================================================================
# Prompt Management Page
# ===================================================================

_PHASE_LABELS = {2: "Phase 2: BM分析", 3: "Phase 3: テンプレ構造", 4: "Phase 4: モデル設計", 5: "Phase 5: パラメーター抽出", 0: "レガシー"}


def _render_prompt_management() -> None:
    """Render the prompt management page with tabbed interface."""

    # Header row
    col_title, col_actions = st.columns([3, 2])
    with col_title:
        st.markdown("## ⚙ プロンプト管理")
        st.caption("各フェーズのLLMプロンプトを確認・編集。編集はセッション中のみ有効。")
    with col_actions:
        st.markdown("")  # spacing
        if st.button("← ウィザードに戻る", key="btn_prompt_back", width="stretch"):
            st.session_state["show_prompt_mgmt"] = False
            st.rerun()

    registry = _get_prompt_registry()
    if not registry:
        st.error("プロンプトレジストリを初期化できませんでした。")
        return

    # Show customized count
    customized = registry.get_customized_keys()
    if customized:
        st.info(f"カスタマイズ中: {len(customized)}件  ({', '.join(customized)})")

    # Tabbed interface by phase (instead of long scrolling list)
    phase_keys = [2, 3, 4, 5, 0]
    tab_labels = [_PHASE_LABELS.get(pk, f"Phase {pk}") for pk in phase_keys]
    tabs = st.tabs(tab_labels)

    for tab, pk in zip(tabs, phase_keys):
        with tab:
            entries = registry.list_entries(phase=pk)
            if not entries:
                st.caption("このフェーズにはプロンプトがありません。")
                continue

            for entry in entries:
                prompt_type_icon = "🔧" if entry.prompt_type == "system" else "💬"
                prompt_type_label = "システム" if entry.prompt_type == "system" else "ユーザー"
                custom_badge = " 🟢" if entry.is_customized else ""

                with st.expander(
                    f"{prompt_type_icon} {prompt_type_label}: {entry.display_name}{custom_badge}",
                    expanded=False,
                ):
                    # Description + char count in header
                    st.caption(f"{entry.description}  |  文字数: {len(entry.content):,}")

                    # Two-column layout: editor + preview
                    new_content = st.text_area(
                        "プロンプト内容",
                        value=entry.content,
                        height=350,
                        key=f"prompt_edit_{entry.key}",
                        label_visibility="collapsed",
                    )

                    # Action buttons — each prompt has its own save + reset
                    c_save, c_reset, c_info = st.columns([1, 1, 2])
                    with c_save:
                        if st.button("💾 保存", key=f"btn_save_{entry.key}", width="stretch"):
                            if new_content != entry.content:
                                registry.set(entry.key, new_content)
                                st.success("保存しました。")
                                st.rerun()
                            else:
                                st.info("変更なし")
                    with c_reset:
                        if st.button(
                            "↩ デフォルトに戻す",
                            key=f"btn_reset_{entry.key}",
                            width="stretch",
                            disabled=not entry.is_customized,
                        ):
                            registry.reset(entry.key)
                            st.success(f"「{entry.display_name}」をデフォルトに戻しました。")
                            st.rerun()
                    with c_info:
                        if entry.is_customized:
                            orig_len = len(entry.default_content)
                            curr_len = len(entry.content)
                            diff = curr_len - orig_len
                            sign = "+" if diff > 0 else ""
                            st.caption(
                                f"🟢 カスタマイズ済 | {orig_len:,}→{curr_len:,}文字 ({sign}{diff:,})"
                            )
                        else:
                            st.caption(f"デフォルト | {len(entry.content):,}文字")


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

    # Check if prompt management page is active
    if st.session_state.get("show_prompt_mgmt", False):
        _render_prompt_management()
        return

    _render_step_indicator()

    phase = st.session_state["wizard_phase"]
    if phase == 1:
        _render_phase_1()
    elif phase == 2:
        _render_phase_2()
    elif phase == 3:
        _render_phase_3()
    elif phase == 4:
        _render_phase_4()
    elif phase == 5:
        _render_phase_5()
    elif phase == 6:
        _render_phase_6()
    else:
        st.session_state["wizard_phase"] = 1
        st.rerun()


if __name__ == "__main__":
    main()
