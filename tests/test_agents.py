"""Tests for the two-agent extraction pipeline."""
from __future__ import annotations

import json
import pytest
from unittest.mock import MagicMock, patch

from src.agents.business_model_analyzer import (
    BusinessModelAnalyzer,
    BusinessModelAnalysis,
    BusinessModelProposal,
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

    def test_analyze_smart_truncates_long_documents(self) -> None:
        llm = _make_mock_llm([MOCK_BM_RESPONSE])
        long_doc = "A" * 15000 + "B" * 15000 + "C" * 15000  # 45K chars
        BusinessModelAnalyzer(llm).analyze(long_doc)
        call_args = llm.extract.call_args[0][0]
        user_msg = call_args[1]["content"]
        # Smart truncation preserves start + end
        assert "中間部分" in user_msg
        assert "先頭" in user_msg
        assert "末尾" in user_msg
        # Start and end of document preserved
        assert "A" in user_msg  # head
        assert "C" in user_msg  # tail

    def test_analyze_legacy_format_wrapped_as_proposal(self) -> None:
        """Old-format LLM response (segments at top level) should be wrapped."""
        llm = _make_mock_llm([MOCK_BM_RESPONSE])
        result = BusinessModelAnalyzer(llm).analyze("doc")
        # Should have proposals (wrapped from legacy)
        assert len(result.proposals) == 1
        assert result.proposals[0].industry == "SaaS"
        assert len(result.proposals[0].segments) == 1

    def test_analyze_with_feedback(self) -> None:
        llm = _make_mock_llm([MOCK_BM_RESPONSE])
        BusinessModelAnalyzer(llm).analyze("doc", feedback="セグメント追加して")
        call_args = llm.extract.call_args[0][0]
        user_msg = call_args[1]["content"]
        assert "ユーザーフィードバック" in user_msg
        assert "セグメント追加して" in user_msg


# Mock for new proposals-format LLM response
MOCK_BM_PROPOSALS_RESPONSE = {
    "company_name": "テスト株式会社",
    "document_narrative": "テスト株式会社は法人向けクラウドサービスを提供する企業である。主にSaaS型のサブスクリプションモデルで収益を得ている。",
    "key_facts": ["月額5万円のプラン", "顧客数100社", "年間解約率10%"],
    "proposals": [
        {
            "label": "パターンA: SaaS単一モデル",
            "industry": "SaaS",
            "business_model_type": "B2B",
            "executive_summary": "純粋なSaaS型で単一セグメント",
            "segments": [
                {
                    "name": "SaaSサブスクリプション",
                    "model_type": "subscription",
                    "revenue_formula": "顧客数 × ARPU × 12",
                    "revenue_drivers": [
                        {"name": "顧客数", "unit": "社", "estimated_value": "100", "evidence": "「顧客数100社」", "description": "", "is_from_document": True},
                    ],
                    "key_assumptions": ["解約率10%"],
                },
            ],
            "shared_costs": [
                {"name": "人件費", "category": "fixed", "estimated_value": "30000000", "evidence": "推定", "description": ""},
            ],
            "growth_trajectory": "3年で300社",
            "risk_factors": ["解約率上振れ"],
            "time_horizon": "5年間",
            "confidence": 0.85,
            "reasoning": "資料の記述がサブスクリプション型に合致",
        },
        {
            "label": "パターンB: SaaS+コンサル複合",
            "industry": "IT",
            "business_model_type": "B2B",
            "executive_summary": "SaaS+導入コンサルティングの複合モデル",
            "segments": [
                {
                    "name": "SaaSサブスクリプション",
                    "model_type": "subscription",
                    "revenue_formula": "顧客数 × ARPU × 12",
                    "revenue_drivers": [],
                    "key_assumptions": [],
                },
                {
                    "name": "導入コンサルティング",
                    "model_type": "project",
                    "revenue_formula": "案件数 × 単価",
                    "revenue_drivers": [],
                    "key_assumptions": [],
                },
            ],
            "shared_costs": [],
            "growth_trajectory": "SaaS拡大+コンサル安定",
            "risk_factors": ["人材確保"],
            "time_horizon": "5年間",
            "confidence": 0.65,
            "reasoning": "IT企業は導入支援を併設することが多い",
        },
        {
            "label": "パターンC: プラットフォーム型",
            "industry": "IT",
            "business_model_type": "B2B2C",
            "executive_summary": "将来的にプラットフォーム型に進化する可能性",
            "segments": [
                {
                    "name": "プラットフォーム",
                    "model_type": "marketplace",
                    "revenue_formula": "取引額 × 手数料率",
                    "revenue_drivers": [],
                    "key_assumptions": [],
                },
            ],
            "shared_costs": [],
            "growth_trajectory": "ネットワーク効果で加速",
            "risk_factors": ["鶏と卵問題"],
            "time_horizon": "5年間",
            "confidence": 0.35,
            "reasoning": "プラットフォーム化の兆候あり",
        },
    ],
    "currency": "JPY",
}


class TestBusinessModelAnalyzerProposals:
    """Tests for the new proposals-based BM analysis."""

    def test_analyze_returns_proposals(self) -> None:
        llm = _make_mock_llm([MOCK_BM_PROPOSALS_RESPONSE])
        result = BusinessModelAnalyzer(llm).analyze("doc text")
        assert isinstance(result, BusinessModelAnalysis)
        assert len(result.proposals) == 3
        assert result.document_narrative != ""
        assert len(result.key_facts) == 3

    def test_proposals_sorted_by_confidence(self) -> None:
        llm = _make_mock_llm([MOCK_BM_PROPOSALS_RESPONSE])
        result = BusinessModelAnalyzer(llm).analyze("doc")
        confidences = [p.confidence for p in result.proposals]
        assert confidences == sorted(confidences, reverse=True)

    def test_first_proposal_auto_selected(self) -> None:
        llm = _make_mock_llm([MOCK_BM_PROPOSALS_RESPONSE])
        result = BusinessModelAnalyzer(llm).analyze("doc")
        assert result.selected_index == 0
        # Main fields should match first (highest-confidence) proposal
        assert result.industry == result.proposals[0].industry
        assert result.segments == result.proposals[0].segments

    def test_select_proposal_updates_fields(self) -> None:
        llm = _make_mock_llm([MOCK_BM_PROPOSALS_RESPONSE])
        result = BusinessModelAnalyzer(llm).analyze("doc")
        # Select pattern B (index 1)
        result2 = result.select_proposal(1)
        assert result2.selected_index == 1
        assert result2.industry == "IT"
        assert len(result2.segments) == 2
        assert result2.segments[1].name == "導入コンサルティング"
        # Narrative preserved
        assert result2.document_narrative == result.document_narrative

    def test_select_proposal_raw_json_compat(self) -> None:
        """raw_json should have old-format keys for downstream phases."""
        llm = _make_mock_llm([MOCK_BM_PROPOSALS_RESPONSE])
        result = BusinessModelAnalyzer(llm).analyze("doc")
        result2 = result.select_proposal(0)
        raw = result2.raw_json
        assert "segments" in raw
        assert "shared_costs" in raw
        assert "industry" in raw
        assert raw["company_name"] == "テスト株式会社"

    def test_select_proposal_out_of_range(self) -> None:
        llm = _make_mock_llm([MOCK_BM_PROPOSALS_RESPONSE])
        result = BusinessModelAnalyzer(llm).analyze("doc")
        # Out of range should return self unchanged
        result2 = result.select_proposal(99)
        assert result2.selected_index == result.selected_index

    def test_proposal_model_fields(self) -> None:
        llm = _make_mock_llm([MOCK_BM_PROPOSALS_RESPONSE])
        result = BusinessModelAnalyzer(llm).analyze("doc")
        p = result.proposals[0]
        assert isinstance(p, BusinessModelProposal)
        assert p.label != ""
        assert p.reasoning != ""
        assert 0.0 <= p.confidence <= 1.0


class TestGroundingValidation:
    """Tests for the anti-hallucination grounding validation."""

    def test_grounding_score_calculated(self) -> None:
        """Evidence matching document text should yield high grounding score."""
        llm = _make_mock_llm([MOCK_BM_PROPOSALS_RESPONSE])
        # Document contains the quoted evidence text
        doc = "この会社の顧客数100社を誇る法人向けクラウドサービスです"
        result = BusinessModelAnalyzer(llm).analyze(doc)
        # First proposal has evidence "「顧客数100社」" which IS in the doc
        p = result.proposals[0]
        assert hasattr(p, "grounding_score")
        assert p.grounding_score > 0

    def test_grounding_penalizes_ungrounded_confidence(self) -> None:
        """If evidence is not found in document, confidence should be penalized."""
        # Create a response with evidence that won't match the doc
        fake_response = {
            "company_name": "捏造会社",
            "document_narrative": "テスト",
            "key_facts": [],
            "proposals": [{
                "label": "パターンA: 捏造モデル",
                "industry": "IT",
                "business_model_type": "B2B",
                "executive_summary": "テスト",
                "segments": [{
                    "name": "セグメント1",
                    "model_type": "subscription",
                    "revenue_formula": "A × B",
                    "revenue_drivers": [
                        {
                            "name": "顧客数",
                            "unit": "社",
                            "estimated_value": "999",
                            "evidence": "「この文書には存在しないテキスト」",
                            "description": "",
                            "is_from_document": True,
                        },
                        {
                            "name": "単価",
                            "unit": "円",
                            "estimated_value": "50000",
                            "evidence": "「これも存在しないテキスト」",
                            "description": "",
                            "is_from_document": True,
                        },
                    ],
                    "key_assumptions": [],
                }],
                "shared_costs": [],
                "growth_trajectory": "",
                "risk_factors": [],
                "time_horizon": "",
                "confidence": 0.9,
                "reasoning": "テスト",
            }],
            "currency": "JPY",
        }
        llm = _make_mock_llm([fake_response])
        result = BusinessModelAnalyzer(llm).analyze("全く異なる内容の文書テキスト")
        p = result.proposals[0]
        # Grounding should be 0 (no evidence matches)
        assert p.grounding_score == 0.0
        # Confidence should be penalized (was 0.9, should be much lower)
        assert p.confidence < 0.9

    def test_smart_truncation_preserves_start_and_end(self) -> None:
        """Smart truncation should keep both the start and end of the document."""
        start_marker = "START_OF_DOCUMENT_MARKER"
        end_marker = "END_OF_DOCUMENT_MARKER"
        text = start_marker + ("x" * 40000) + end_marker
        result = BusinessModelAnalyzer._smart_truncate(text, max_chars=30000)
        assert start_marker in result
        assert end_marker in result
        assert "中間部分" in result
        assert len(result) <= 35000  # some overhead for separator

    def test_smart_truncation_no_change_for_short_docs(self) -> None:
        """Short documents should pass through unchanged."""
        text = "short document"
        result = BusinessModelAnalyzer._smart_truncate(text, max_chars=30000)
        assert result == text

    def test_is_from_document_field_populated(self) -> None:
        """is_from_document should be set on revenue drivers after grounding check."""
        llm = _make_mock_llm([MOCK_BM_PROPOSALS_RESPONSE])
        doc = "法人向けサービスで顧客数100社"
        result = BusinessModelAnalyzer(llm).analyze(doc)
        p = result.proposals[0]
        for seg in p.segments:
            for d in seg.revenue_drivers:
                assert hasattr(d, "is_from_document")
                assert isinstance(d.is_from_document, bool)


# ---------------------------------------------------------------------------
# R&D Themes Extraction
# ---------------------------------------------------------------------------

MOCK_BM_WITH_RD_THEMES = {
    **MOCK_BM_PROPOSALS_RESPONSE,
    "rd_themes": [
        {"name": "アカデミーサービス", "items": ["栄養士DX化", "コンテンツ高度化"]},
        {"name": "ミールサービス", "items": ["ロジスティクス効率化"]},
        {"name": "共通", "items": ["CSシステム構築"]},
    ],
}


class TestRDThemesExtraction:
    def test_rd_themes_parsed_from_llm_response(self) -> None:
        """rd_themes should be parsed from LLM response."""
        llm = _make_mock_llm([MOCK_BM_WITH_RD_THEMES])
        result = BusinessModelAnalyzer(llm).analyze("事業計画書テキスト")
        assert len(result.rd_themes) == 3
        assert result.rd_themes[0].name == "アカデミーサービス"
        assert result.rd_themes[0].items == ["栄養士DX化", "コンテンツ高度化"]
        assert result.rd_themes[1].name == "ミールサービス"
        assert result.rd_themes[1].items == ["ロジスティクス効率化"]
        assert result.rd_themes[2].name == "共通"
        assert result.rd_themes[2].items == ["CSシステム構築"]

    def test_rd_themes_empty_when_not_in_response(self) -> None:
        """rd_themes should be empty list when LLM doesn't return it."""
        llm = _make_mock_llm([MOCK_BM_PROPOSALS_RESPONSE])
        result = BusinessModelAnalyzer(llm).analyze("事業計画書テキスト")
        assert result.rd_themes == []

    def test_rd_themes_in_raw_json_after_select(self) -> None:
        """rd_themes should appear in raw_json after select_proposal."""
        llm = _make_mock_llm([MOCK_BM_WITH_RD_THEMES])
        result = BusinessModelAnalyzer(llm).analyze("事業計画書テキスト")
        selected = result.select_proposal(0)
        assert "rd_themes" in selected.raw_json
        assert len(selected.raw_json["rd_themes"]) == 3

    def test_rd_themes_in_model_dump(self) -> None:
        """rd_themes should be serializable via model_dump()."""
        llm = _make_mock_llm([MOCK_BM_WITH_RD_THEMES])
        result = BusinessModelAnalyzer(llm).analyze("事業計画書テキスト")
        dumped = result.model_dump()
        assert "rd_themes" in dumped
        assert len(dumped["rd_themes"]) == 3
        assert dumped["rd_themes"][0]["name"] == "アカデミーサービス"

    def test_rd_themes_skips_invalid_entries(self) -> None:
        """Invalid rd_themes entries (no name, not dict) should be skipped."""
        response = {
            **MOCK_BM_PROPOSALS_RESPONSE,
            "rd_themes": [
                {"name": "有効カテゴリ", "items": ["テーマA"]},
                {"name": "", "items": ["テーマB"]},      # empty name → skip
                "invalid_string",                         # not dict → skip
                {"name": "空アイテム", "items": []},      # empty items → skip
            ],
        }
        llm = _make_mock_llm([response])
        result = BusinessModelAnalyzer(llm).analyze("事業計画書テキスト")
        assert len(result.rd_themes) == 1
        assert result.rd_themes[0].name == "有効カテゴリ"


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

    def test_pipeline_handles_agent1_failure_and_still_runs_agent2(self) -> None:
        # Agent 1 raises, Agent 2 should still try (direct extraction mode)
        llm = MagicMock()
        llm.extract = MagicMock(side_effect=[
            Exception("API error"),  # Agent 1 fails
            MOCK_FM_RESPONSE,        # Agent 2 gets response
        ])
        orch = AgentOrchestrator(llm)
        result = orch.run("doc", SAMPLE_CATALOG)

        assert result.steps[0].status == "error"
        assert "API error" in result.steps[0].error_message
        # Agent 2 still ran
        assert result.steps[1].status == "success"
        assert len(result.extractions) == 2

    def test_agent1_raises_on_empty_llm_response(self) -> None:
        """Agent 1 should raise RuntimeError when LLM returns empty/useless response."""
        llm = _make_mock_llm([{}])  # empty response
        agent = BusinessModelAnalyzer(llm)
        with pytest.raises(RuntimeError, match="LLMがビジネスモデル分析を返しませんでした"):
            agent.analyze("some document text")

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
