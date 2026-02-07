"""Tests for the new multi-phase agents (Phase 3-5)."""
from __future__ import annotations

import json
import pytest
from unittest.mock import MagicMock

from src.agents.template_mapper import (
    TemplateMapper,
    TemplateStructureResult,
    SheetMapping,
)
from src.agents.model_designer import (
    ModelDesigner,
    ModelDesignResult,
    CellAssignment,
)
from src.agents.parameter_extractor import (
    ParameterExtractorAgent,
    ParameterExtractionResult,
    ExtractedValue,
)
from src.agents.orchestrator import AgentOrchestrator


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------

def _make_mock_llm(responses: list) -> MagicMock:
    mock = MagicMock()
    mock.extract = MagicMock(side_effect=responses)
    return mock


# ---------------------------------------------------------------------------
# Mock data
# ---------------------------------------------------------------------------

MOCK_BM_JSON = {
    "company_name": "テスト株式会社",
    "industry": "SaaS",
    "business_model_type": "B2B",
    "executive_summary": "法人向けSaaSプロダクト",
    "segments": [
        {
            "name": "SaaS",
            "model_type": "subscription",
            "revenue_formula": "顧客数 × ARPU × 12",
            "revenue_drivers": [
                {"name": "顧客数", "unit": "社", "estimated_value": "100", "evidence": "", "description": ""},
            ],
            "key_assumptions": [],
        },
    ],
    "shared_costs": [],
    "growth_trajectory": "",
    "risk_factors": [],
}

MOCK_TS_RESPONSE = {
    "overall_structure": "SaaS向け収益モデルテンプレート",
    "sheet_mappings": [
        {
            "sheet_name": "SaaSモデル",
            "mapped_segment": "SaaS",
            "sheet_purpose": "revenue_model",
            "confidence": 0.9,
            "reasoning": "シート名がSaaSモデル",
        },
        {
            "sheet_name": "費用リスト",
            "mapped_segment": "共通",
            "sheet_purpose": "cost_detail",
            "confidence": 0.8,
            "reasoning": "コスト一覧シート",
        },
    ],
    "suggestions": ["合計シートの追加を検討"],
}

MOCK_MD_RESPONSE = {
    "cell_assignments": [
        {
            "sheet": "SaaSモデル",
            "cell": "C5",
            "label": "顧客数",
            "assigned_concept": "月間アクティブ顧客数",
            "segment": "SaaS",
            "period": "FY1",
            "unit": "社",
            "derivation": "direct",
            "confidence": 0.95,
            "reasoning": "ラベルが顧客数と一致",
        },
        {
            "sheet": "SaaSモデル",
            "cell": "C6",
            "label": "ARPU",
            "assigned_concept": "顧客あたり月額売上",
            "segment": "SaaS",
            "period": "FY1",
            "unit": "円/月",
            "derivation": "direct",
            "confidence": 0.9,
            "reasoning": "ARPUラベルと一致",
        },
    ],
    "unmapped_cells": [
        {"sheet": "SaaSモデル", "cell": "C10", "label": "解約率", "reason": "対応概念なし"},
    ],
    "warnings": ["解約率の概念マッピングが必要"],
}

MOCK_PE_RESPONSE = {
    "extractions": [
        {
            "sheet": "SaaSモデル",
            "cell": "C5",
            "label": "顧客数",
            "concept": "月間アクティブ顧客数",
            "value": 100,
            "unit": "社",
            "source": "document",
            "confidence": 0.95,
            "evidence": "顧客数は100社を目標",
            "segment": "SaaS",
            "period": "FY1",
        },
        {
            "sheet": "SaaSモデル",
            "cell": "C6",
            "label": "ARPU",
            "concept": "顧客あたり月額売上",
            "value": 50000,
            "unit": "円/月",
            "source": "document",
            "confidence": 0.9,
            "evidence": "月額5万円プラン",
            "segment": "SaaS",
            "period": "FY1",
        },
    ],
    "unmapped_cells": [
        {"sheet": "SaaSモデル", "cell": "C10", "label": "解約率", "reason": "文書に記載なし"},
    ],
    "warnings": [],
}

SAMPLE_CATALOG = [
    {"sheet": "SaaSモデル", "cell": "C5", "labels": ["顧客数"], "units": ["社"], "period": "FY1", "block": "収益", "current_value": None},
    {"sheet": "SaaSモデル", "cell": "C6", "labels": ["ARPU"], "units": ["円/月"], "period": "FY1", "block": "収益", "current_value": None},
    {"sheet": "SaaSモデル", "cell": "C10", "labels": ["解約率"], "units": ["%"], "period": "FY1", "block": "収益", "current_value": None},
    {"sheet": "費用リスト", "cell": "B3", "labels": ["人件費"], "units": ["円"], "period": "", "block": "固定費", "current_value": None},
]


# ---------------------------------------------------------------------------
# Phase 3: Template Mapper
# ---------------------------------------------------------------------------

class TestTemplateMapper:
    def test_map_structure_returns_result(self) -> None:
        llm = _make_mock_llm([MOCK_TS_RESPONSE])
        mapper = TemplateMapper(llm)
        result = mapper.map_structure(MOCK_BM_JSON, SAMPLE_CATALOG)

        assert isinstance(result, TemplateStructureResult)
        assert len(result.sheet_mappings) == 2
        assert result.sheet_mappings[0].sheet_name == "SaaSモデル"
        assert result.sheet_mappings[0].mapped_segment == "SaaS"
        assert result.sheet_mappings[0].sheet_purpose == "revenue_model"

    def test_map_structure_preserves_overall_structure(self) -> None:
        llm = _make_mock_llm([MOCK_TS_RESPONSE])
        result = TemplateMapper(llm).map_structure(MOCK_BM_JSON, SAMPLE_CATALOG)
        assert "SaaS" in result.overall_structure

    def test_map_structure_preserves_suggestions(self) -> None:
        llm = _make_mock_llm([MOCK_TS_RESPONSE])
        result = TemplateMapper(llm).map_structure(MOCK_BM_JSON, SAMPLE_CATALOG)
        assert len(result.suggestions) == 1
        assert "合計" in result.suggestions[0]

    def test_map_structure_with_feedback(self) -> None:
        llm = _make_mock_llm([MOCK_TS_RESPONSE])
        TemplateMapper(llm).map_structure(
            MOCK_BM_JSON, SAMPLE_CATALOG, feedback="費用リストは人件費専用",
        )
        call_args = llm.extract.call_args[0][0]
        user_msg = call_args[1]["content"]
        assert "費用リストは人件費専用" in user_msg
        assert "ユーザーフィードバック" in user_msg

    def test_map_structure_stores_raw_json(self) -> None:
        llm = _make_mock_llm([MOCK_TS_RESPONSE])
        result = TemplateMapper(llm).map_structure(MOCK_BM_JSON, SAMPLE_CATALOG)
        assert result.raw_json == MOCK_TS_RESPONSE


# ---------------------------------------------------------------------------
# Phase 4: Model Designer
# ---------------------------------------------------------------------------

class TestModelDesigner:
    def test_design_returns_assignments(self) -> None:
        llm = _make_mock_llm([MOCK_MD_RESPONSE])
        designer = ModelDesigner(llm)
        result = designer.design(MOCK_BM_JSON, MOCK_TS_RESPONSE, SAMPLE_CATALOG)

        assert isinstance(result, ModelDesignResult)
        assert len(result.cell_assignments) == 2
        assert result.cell_assignments[0].cell == "C5"
        assert result.cell_assignments[0].assigned_concept == "月間アクティブ顧客数"

    def test_design_reports_unmapped(self) -> None:
        llm = _make_mock_llm([MOCK_MD_RESPONSE])
        result = ModelDesigner(llm).design(MOCK_BM_JSON, MOCK_TS_RESPONSE, SAMPLE_CATALOG)
        assert len(result.unmapped_cells) == 1
        assert result.unmapped_cells[0]["cell"] == "C10"

    def test_design_reports_warnings(self) -> None:
        llm = _make_mock_llm([MOCK_MD_RESPONSE])
        result = ModelDesigner(llm).design(MOCK_BM_JSON, MOCK_TS_RESPONSE, SAMPLE_CATALOG)
        assert len(result.warnings) == 1
        assert "解約率" in result.warnings[0]

    def test_design_with_feedback(self) -> None:
        llm = _make_mock_llm([MOCK_MD_RESPONSE])
        ModelDesigner(llm).design(
            MOCK_BM_JSON, MOCK_TS_RESPONSE, SAMPLE_CATALOG,
            feedback="C10は解約率ではなく成長率",
        )
        call_args = llm.extract.call_args[0][0]
        user_msg = call_args[1]["content"]
        assert "C10は解約率ではなく成長率" in user_msg


# ---------------------------------------------------------------------------
# Phase 5: Parameter Extractor
# ---------------------------------------------------------------------------

class TestParameterExtractor:
    def test_extract_returns_values(self) -> None:
        llm = _make_mock_llm([MOCK_PE_RESPONSE])
        extractor = ParameterExtractorAgent(llm)
        result = extractor.extract_values(MOCK_MD_RESPONSE, "事業計画書テキスト")

        assert isinstance(result, ParameterExtractionResult)
        assert len(result.extractions) == 2
        assert result.extractions[0].cell == "C5"
        assert result.extractions[0].value == 100

    def test_extract_reports_unmapped(self) -> None:
        llm = _make_mock_llm([MOCK_PE_RESPONSE])
        result = ParameterExtractorAgent(llm).extract_values(MOCK_MD_RESPONSE, "text")
        assert len(result.unmapped_cells) == 1

    def test_extract_preserves_evidence(self) -> None:
        llm = _make_mock_llm([MOCK_PE_RESPONSE])
        result = ParameterExtractorAgent(llm).extract_values(MOCK_MD_RESPONSE, "text")
        assert result.extractions[0].evidence == "顧客数は100社を目標"

    def test_extract_preserves_source_and_confidence(self) -> None:
        llm = _make_mock_llm([MOCK_PE_RESPONSE])
        result = ParameterExtractorAgent(llm).extract_values(MOCK_MD_RESPONSE, "text")
        assert result.extractions[0].source == "document"
        assert result.extractions[0].confidence == 0.95

    def test_extract_with_feedback(self) -> None:
        llm = _make_mock_llm([MOCK_PE_RESPONSE])
        ParameterExtractorAgent(llm).extract_values(
            MOCK_MD_RESPONSE, "text", feedback="顧客数は200です",
        )
        call_args = llm.extract.call_args[0][0]
        user_msg = call_args[1]["content"]
        assert "顧客数は200です" in user_msg

    def test_extract_truncates_long_documents(self) -> None:
        llm = _make_mock_llm([MOCK_PE_RESPONSE])
        long_doc = "x" * 20000
        ParameterExtractorAgent(llm).extract_values(MOCK_MD_RESPONSE, long_doc)
        call_args = llm.extract.call_args[0][0]
        user_msg = call_args[1]["content"]
        assert "先頭 10,000 文字を表示" in user_msg


# ---------------------------------------------------------------------------
# Orchestrator phased methods
# ---------------------------------------------------------------------------

class TestOrchestratorPhased:
    def test_run_bm_analysis(self) -> None:
        mock_bm_response = {
            "company_name": "テスト",
            "industry": "SaaS",
            "business_model_type": "B2B",
            "executive_summary": "",
            "segments": [
                {
                    "name": "SaaS",
                    "model_type": "subscription",
                    "revenue_formula": "N × ARPU",
                    "revenue_drivers": [],
                    "key_assumptions": [],
                },
            ],
            "shared_costs": [],
            "growth_trajectory": "",
            "risk_factors": [],
        }
        llm = _make_mock_llm([mock_bm_response])
        orch = AgentOrchestrator(llm)
        bm = orch.run_bm_analysis("document text")
        assert bm.company_name == "テスト"
        assert len(bm.segments) == 1

    def test_run_template_mapping(self) -> None:
        llm = _make_mock_llm([MOCK_TS_RESPONSE])
        orch = AgentOrchestrator(llm)
        ts = orch.run_template_mapping(MOCK_BM_JSON, SAMPLE_CATALOG)
        assert len(ts.sheet_mappings) == 2

    def test_run_model_design(self) -> None:
        llm = _make_mock_llm([MOCK_MD_RESPONSE])
        orch = AgentOrchestrator(llm)
        md = orch.run_model_design(MOCK_BM_JSON, MOCK_TS_RESPONSE, SAMPLE_CATALOG)
        assert len(md.cell_assignments) == 2

    def test_run_parameter_extraction(self) -> None:
        llm = _make_mock_llm([MOCK_PE_RESPONSE])
        orch = AgentOrchestrator(llm)
        pe = orch.run_parameter_extraction(MOCK_MD_RESPONSE, "document text")
        assert len(pe.extractions) == 2
        assert pe.extractions[0].value == 100

    def test_orchestrator_with_prompt_overrides(self) -> None:
        """Orchestrator should pass custom prompts to agents."""
        mock_bm = {
            "company_name": "Test",
            "industry": "IT",
            "business_model_type": "B2B",
            "segments": [{"name": "IT", "model_type": "subscription",
                          "revenue_formula": "N×P", "revenue_drivers": [], "key_assumptions": []}],
            "shared_costs": [], "risk_factors": [],
        }
        llm = _make_mock_llm([mock_bm])
        overrides = {"bm_analyzer_system": "Custom system prompt"}
        orch = AgentOrchestrator(llm, prompt_overrides=overrides)
        assert orch.agent1._system_prompt == "Custom system prompt"
        # Others should have defaults
        from src.agents.template_mapper import TS_SYSTEM_PROMPT
        assert orch.template_mapper._system_prompt == TS_SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# Prompt Registry
# ---------------------------------------------------------------------------

class TestPromptRegistry:
    def test_registry_initializes_all_prompts(self) -> None:
        from src.agents.prompt_registry import PromptRegistry
        registry = PromptRegistry()
        entries = registry.list_entries()
        assert len(entries) == 10  # 5 agents × 2 (system + user)

    def test_get_default_content(self) -> None:
        from src.agents.prompt_registry import PromptRegistry
        from src.agents.business_model_analyzer import BM_ANALYZER_SYSTEM_PROMPT
        registry = PromptRegistry()
        content = registry.get("bm_analyzer_system")
        assert content == BM_ANALYZER_SYSTEM_PROMPT

    def test_set_and_get_custom(self) -> None:
        from src.agents.prompt_registry import PromptRegistry
        registry = PromptRegistry()
        registry.set("bm_analyzer_system", "Custom prompt")
        assert registry.get("bm_analyzer_system") == "Custom prompt"
        assert registry.get_entry("bm_analyzer_system").is_customized

    def test_reset_to_default(self) -> None:
        from src.agents.prompt_registry import PromptRegistry
        from src.agents.business_model_analyzer import BM_ANALYZER_SYSTEM_PROMPT
        registry = PromptRegistry()
        registry.set("bm_analyzer_system", "Custom prompt")
        registry.reset("bm_analyzer_system")
        assert registry.get("bm_analyzer_system") == BM_ANALYZER_SYSTEM_PROMPT
        assert not registry.get_entry("bm_analyzer_system").is_customized

    def test_reset_all(self) -> None:
        from src.agents.prompt_registry import PromptRegistry
        registry = PromptRegistry()
        registry.set("bm_analyzer_system", "Custom 1")
        registry.set("template_mapper_system", "Custom 2")
        assert len(registry.get_customized_keys()) == 2
        registry.reset_all()
        assert len(registry.get_customized_keys()) == 0

    def test_list_by_phase(self) -> None:
        from src.agents.prompt_registry import PromptRegistry
        registry = PromptRegistry()
        phase2 = registry.list_entries(phase=2)
        assert len(phase2) == 2  # system + user for BM analyzer
        assert all(e.phase == 2 for e in phase2)

    def test_unknown_key_raises(self) -> None:
        from src.agents.prompt_registry import PromptRegistry
        registry = PromptRegistry()
        with pytest.raises(KeyError):
            registry.get("nonexistent_key")
