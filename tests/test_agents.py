"""Tests for the two-agent extraction pipeline."""
from __future__ import annotations

import json
import pytest
from unittest.mock import MagicMock, patch

from src.agents.business_model_analyzer import (
    BusinessModelAnalyzer,
    BusinessModelAnalysis,
    BusinessSegment,
    RevenueDriver,
    CostItem,
)
from src.agents.fm_designer import (
    FMDesigner,
    FMDesignResult,
    CellExtraction,
    TemplateSheetMapping,
)
from src.agents.orchestrator import AgentOrchestrator, OrchestrationResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MOCK_BM_RESPONSE = {
    "company_name": "テスト株式会社",
    "industry": "SaaS",
    "business_model_type": "B2B",
    "executive_summary": "法人向けSaaSプロダクトを提供するスタートアップ",
    "segments": [
        {
            "name": "SaaSサブスクリプション",
            "model_type": "subscription",
            "revenue_formula": "顧客数 × ARPU × 12ヶ月",
            "revenue_drivers": [
                {"name": "顧客数", "unit": "社", "estimated_value": "100", "evidence": "顧客数は100社を目標", "description": ""},
                {"name": "ARPU", "unit": "円/月", "estimated_value": "50000", "evidence": "月額5万円のプラン", "description": ""},
            ],
            "key_assumptions": ["年間解約率10%", "新規獲得月5社"],
        },
    ],
    "shared_costs": [
        {"name": "人件費", "category": "fixed", "estimated_value": "30000000", "evidence": "社員10名×年収300万", "description": ""},
        {"name": "サーバー費", "category": "variable", "estimated_value": "1000000", "evidence": "月額約8万円", "description": ""},
    ],
    "growth_trajectory": "3年で顧客数300社を目指す",
    "risk_factors": ["解約率の上振れ", "競合参入"],
    "time_horizon": "5年間 (FY1-FY5)",
    "currency": "JPY",
}

MOCK_FM_RESPONSE = {
    "sheet_mappings": [
        {
            "sheet_name": "SaaSモデル",
            "mapped_segment": "SaaSサブスクリプション",
            "sheet_purpose": "revenue_model",
            "confidence": 0.9,
        },
        {
            "sheet_name": "費用リスト",
            "mapped_segment": "共通",
            "sheet_purpose": "cost_detail",
            "confidence": 0.85,
        },
    ],
    "extractions": [
        {
            "sheet": "SaaSモデル",
            "cell": "C5",
            "label": "顧客数",
            "value": 100,
            "unit": "社",
            "source": "document",
            "confidence": 0.95,
            "evidence": "顧客数は100社を目標",
            "segment": "SaaSサブスクリプション",
            "period": "FY1",
        },
        {
            "sheet": "SaaSモデル",
            "cell": "C6",
            "label": "ARPU",
            "value": 50000,
            "unit": "円/月",
            "source": "document",
            "confidence": 0.9,
            "evidence": "月額5万円のプラン",
            "segment": "SaaSサブスクリプション",
            "period": "FY1",
        },
    ],
    "unmapped_cells": [
        {"sheet": "SaaSモデル", "cell": "C10", "label": "解約率", "reason": "文書に具体値なし"},
    ],
    "warnings": ["成長率が年50%と高め -- 持続可能性の確認が必要"],
}

SAMPLE_CATALOG = [
    {"sheet": "SaaSモデル", "cell": "C5", "labels": ["顧客数"], "units": ["社"], "period": "FY1", "block": "収益モデル", "current_value": None},
    {"sheet": "SaaSモデル", "cell": "C6", "labels": ["ARPU"], "units": ["円/月"], "period": "FY1", "block": "収益モデル", "current_value": None},
    {"sheet": "SaaSモデル", "cell": "C10", "labels": ["解約率"], "units": ["%"], "period": "FY1", "block": "収益モデル", "current_value": None},
    {"sheet": "費用リスト", "cell": "B3", "labels": ["人件費"], "units": ["円"], "period": "", "block": "固定費", "current_value": None},
]


def _make_mock_llm(responses: list) -> MagicMock:
    """Create a mock LLM client that returns responses in sequence."""
    mock = MagicMock()
    mock.extract = MagicMock(side_effect=responses)
    return mock


# ---------------------------------------------------------------------------
# Agent 1: Business Model Analyzer
# ---------------------------------------------------------------------------

class TestBusinessModelAnalyzer:
    def test_analyze_returns_structured_result(self) -> None:
        llm = _make_mock_llm([MOCK_BM_RESPONSE])
        agent = BusinessModelAnalyzer(llm)
        result = agent.analyze("テスト事業計画書の内容")

        assert isinstance(result, BusinessModelAnalysis)
        assert result.company_name == "テスト株式会社"
        assert result.industry == "SaaS"
        assert len(result.segments) == 1
        assert result.segments[0].name == "SaaSサブスクリプション"
        assert result.segments[0].model_type == "subscription"
        assert len(result.segments[0].revenue_drivers) == 2

    def test_analyze_handles_multi_segment(self) -> None:
        multi_seg = dict(MOCK_BM_RESPONSE)
        multi_seg["segments"] = [
            MOCK_BM_RESPONSE["segments"][0],
            {
                "name": "コンサルティング",
                "model_type": "project",
                "revenue_formula": "案件数 × 単価",
                "revenue_drivers": [],
                "key_assumptions": [],
            },
        ]
        llm = _make_mock_llm([multi_seg])
        result = BusinessModelAnalyzer(llm).analyze("multi-segment doc")
        assert len(result.segments) == 2
        assert result.segments[1].name == "コンサルティング"

    def test_analyze_preserves_costs(self) -> None:
        llm = _make_mock_llm([MOCK_BM_RESPONSE])
        result = BusinessModelAnalyzer(llm).analyze("doc")
        assert len(result.shared_costs) == 2
        assert result.shared_costs[0].category == "fixed"
        assert result.shared_costs[1].category == "variable"

    def test_analyze_truncates_long_documents(self) -> None:
        llm = _make_mock_llm([MOCK_BM_RESPONSE])
        long_doc = "x" * 20000
        BusinessModelAnalyzer(llm).analyze(long_doc)
        call_args = llm.extract.call_args[0][0]
        user_msg = call_args[1]["content"]
        assert "先頭 12,000 文字を分析" in user_msg


# ---------------------------------------------------------------------------
# Agent 2: FM Designer
# ---------------------------------------------------------------------------

class TestFMDesigner:
    def test_design_returns_mappings_and_extractions(self) -> None:
        llm = _make_mock_llm([MOCK_FM_RESPONSE])
        agent = FMDesigner(llm)
        analysis = BusinessModelAnalyzer(_make_mock_llm([MOCK_BM_RESPONSE])).analyze("doc")

        result = agent.design(analysis, SAMPLE_CATALOG, "document text")

        assert isinstance(result, FMDesignResult)
        assert len(result.sheet_mappings) == 2
        assert result.sheet_mappings[0].sheet_name == "SaaSモデル"
        assert result.sheet_mappings[0].mapped_segment == "SaaSサブスクリプション"

    def test_design_extracts_cell_values(self) -> None:
        llm = _make_mock_llm([MOCK_FM_RESPONSE])
        analysis = BusinessModelAnalyzer(_make_mock_llm([MOCK_BM_RESPONSE])).analyze("doc")
        result = FMDesigner(llm).design(analysis, SAMPLE_CATALOG, "text")

        assert len(result.extractions) == 2
        assert result.extractions[0].cell == "C5"
        assert result.extractions[0].value == 100
        assert result.extractions[0].segment == "SaaSサブスクリプション"

    def test_design_reports_unmapped_cells(self) -> None:
        llm = _make_mock_llm([MOCK_FM_RESPONSE])
        analysis = BusinessModelAnalyzer(_make_mock_llm([MOCK_BM_RESPONSE])).analyze("doc")
        result = FMDesigner(llm).design(analysis, SAMPLE_CATALOG, "text")

        assert len(result.unmapped_cells) == 1
        assert result.unmapped_cells[0]["cell"] == "C10"

    def test_design_reports_warnings(self) -> None:
        llm = _make_mock_llm([MOCK_FM_RESPONSE])
        analysis = BusinessModelAnalyzer(_make_mock_llm([MOCK_BM_RESPONSE])).analyze("doc")
        result = FMDesigner(llm).design(analysis, SAMPLE_CATALOG, "text")

        assert len(result.warnings) == 1
        assert "成長率" in result.warnings[0]


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class TestAgentOrchestrator:
    def test_full_pipeline_success(self) -> None:
        llm = _make_mock_llm([MOCK_BM_RESPONSE, MOCK_FM_RESPONSE])
        orch = AgentOrchestrator(llm)
        result = orch.run("事業計画書", SAMPLE_CATALOG)

        assert isinstance(result, OrchestrationResult)
        assert result.is_success
        assert len(result.steps) == 2
        assert result.steps[0].status == "success"
        assert result.steps[1].status == "success"
        assert len(result.extractions) == 2
        assert result.analysis.industry == "SaaS"

    def test_pipeline_handles_agent1_failure(self) -> None:
        llm = MagicMock()
        llm.extract = MagicMock(side_effect=Exception("API error"))
        orch = AgentOrchestrator(llm)
        result = orch.run("doc", SAMPLE_CATALOG)

        assert not result.is_success
        assert result.steps[0].status == "error"
        assert "API error" in result.steps[0].error_message
        assert result.steps[1].status == "error"  # skipped

    def test_pipeline_calls_progress_callback(self) -> None:
        llm = _make_mock_llm([MOCK_BM_RESPONSE, MOCK_FM_RESPONSE])
        orch = AgentOrchestrator(llm)
        steps_seen = []
        result = orch.run("doc", SAMPLE_CATALOG, on_step=lambda s: steps_seen.append(s.status))

        # running + success for each agent = 4 callbacks
        assert len(steps_seen) == 4
        assert "running" in steps_seen
        assert "success" in steps_seen

    def test_extractions_have_sheet_and_cell(self) -> None:
        llm = _make_mock_llm([MOCK_BM_RESPONSE, MOCK_FM_RESPONSE])
        result = AgentOrchestrator(llm).run("doc", SAMPLE_CATALOG)

        for ext in result.extractions:
            assert ext.sheet, f"Extraction missing sheet: {ext}"
            assert ext.cell, f"Extraction missing cell: {ext}"

    def test_orchestrator_elapsed_time_tracked(self) -> None:
        llm = _make_mock_llm([MOCK_BM_RESPONSE, MOCK_FM_RESPONSE])
        result = AgentOrchestrator(llm).run("doc", SAMPLE_CATALOG)
        assert result.total_elapsed > 0
        for step in result.steps:
            assert step.elapsed_seconds >= 0
