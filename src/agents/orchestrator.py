"""Agent Orchestrator -- coordinates the multi-phase extraction pipeline.

Pipeline (6 phases):
    Phase 1: Upload + Template Scan (no LLM)
    Phase 2: Business Model Analysis        (Agent 1) -> feedback -> confirm
    Phase 3: Template Structure Mapping      (Agent 2) -> feedback -> confirm
    Phase 4: Model Design (cell assignments) (Agent 3) -> feedback -> confirm
    Phase 5: Parameter Extraction            (Agent 4) -> feedback -> confirm
    Phase 6: Final Review + Excel Generation

Each phase can be run independently with optional user feedback.
The Streamlit UI controls the flow between phases.

Legacy two-agent pipeline (``run()``) is preserved for backward
compatibility and tests.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .business_model_analyzer import BusinessModelAnalyzer, BusinessModelAnalysis
from .fm_designer import FMDesigner, FMDesignResult, CellExtraction
from .template_mapper import TemplateMapper, TemplateStructureResult
from .model_designer import ModelDesigner, ModelDesignResult
from .parameter_extractor import ParameterExtractorAgent, ParameterExtractionResult

logger = logging.getLogger(__name__)


@dataclass
class AgentStep:
    """Record of one agent execution step."""
    agent_name: str
    status: str = "pending"  # pending / running / success / error
    started_at: float = 0.0
    finished_at: float = 0.0
    error_message: str = ""
    summary: str = ""

    @property
    def elapsed_seconds(self) -> float:
        if self.finished_at and self.started_at:
            return self.finished_at - self.started_at
        return 0.0


@dataclass
class OrchestrationResult:
    """Complete result from the two-agent pipeline (legacy)."""
    analysis: Optional[BusinessModelAnalysis] = None
    design: Optional[FMDesignResult] = None
    steps: List[AgentStep] = field(default_factory=list)
    total_elapsed: float = 0.0
    document_chars: int = 0
    document_preview: str = ""

    @property
    def is_success(self) -> bool:
        return all(s.status == "success" for s in self.steps)

    @property
    def extractions(self) -> List[CellExtraction]:
        if self.design:
            return self.design.extractions
        return []

    @property
    def warnings(self) -> List[str]:
        warnings = []
        if self.design:
            warnings.extend(self.design.warnings)
        for step in self.steps:
            if step.status == "error":
                warnings.append(f"{step.agent_name}: {step.error_message}")
        return warnings


class AgentOrchestrator:
    """Coordinates the multi-phase extraction pipeline.

    Phased usage (new)::

        orch = AgentOrchestrator(llm_client)

        # Phase 2
        bm = orch.run_bm_analysis(document_text)
        # ... user feedback ...
        bm = orch.run_bm_analysis(document_text, feedback="add segment X")

        # Phase 3
        ts = orch.run_template_mapping(bm.raw_json, catalog_items)

        # Phase 4
        md = orch.run_model_design(bm.raw_json, ts.raw_json, catalog_items)

        # Phase 5
        pe = orch.run_parameter_extraction(md.raw_json, document_text)

    Legacy usage (preserved for backward compat)::

        result = orch.run(document_text, catalog_items)
    """

    def __init__(
        self,
        llm_client: Any,
        prompt_overrides: Optional[Dict[str, str]] = None,
    ) -> None:
        self.llm = llm_client
        po = prompt_overrides or {}
        self.agent1 = BusinessModelAnalyzer(
            llm_client,
            system_prompt=po.get("bm_analyzer_system"),
            user_prompt=po.get("bm_analyzer_user"),
        )
        self.agent2 = FMDesigner(llm_client)
        self.template_mapper = TemplateMapper(
            llm_client,
            system_prompt=po.get("template_mapper_system"),
            user_prompt=po.get("template_mapper_user"),
        )
        self.model_designer = ModelDesigner(
            llm_client,
            system_prompt=po.get("model_designer_system"),
            user_prompt=po.get("model_designer_user"),
        )
        self.param_extractor = ParameterExtractorAgent(
            llm_client,
            system_prompt=po.get("param_extractor_system"),
            user_prompt=po.get("param_extractor_user"),
        )

    # ------------------------------------------------------------------
    # Phased execution (new)
    # ------------------------------------------------------------------

    def run_bm_analysis(
        self,
        document_text: str,
        feedback: str = "",
    ) -> BusinessModelAnalysis:
        """Phase 2: Run Business Model Analyzer."""
        return self.agent1.analyze(document_text, feedback=feedback)

    def run_template_mapping(
        self,
        analysis_json: Dict[str, Any],
        catalog_items: List[Dict[str, Any]],
        feedback: str = "",
    ) -> TemplateStructureResult:
        """Phase 3: Run Template Structure Mapper."""
        return self.template_mapper.map_structure(
            analysis_json, catalog_items, feedback=feedback,
        )

    def run_model_design(
        self,
        analysis_json: Dict[str, Any],
        template_structure_json: Dict[str, Any],
        catalog_items: List[Dict[str, Any]],
        feedback: str = "",
    ) -> ModelDesignResult:
        """Phase 4: Run Model Designer."""
        return self.model_designer.design(
            analysis_json, template_structure_json, catalog_items,
            feedback=feedback,
        )

    def run_parameter_extraction(
        self,
        model_design_json: Dict[str, Any],
        document_text: str,
        feedback: str = "",
    ) -> ParameterExtractionResult:
        """Phase 5: Run Parameter Extractor."""
        return self.param_extractor.extract_values(
            model_design_json, document_text, feedback=feedback,
        )

    # ------------------------------------------------------------------
    # Legacy two-agent pipeline (backward compat)
    # ------------------------------------------------------------------

    def run(
        self,
        document_text: str,
        catalog_items: List[Dict[str, Any]],
        *,
        on_step: Any = None,
    ) -> OrchestrationResult:
        """Run the full two-agent pipeline (legacy).

        Parameters
        ----------
        document_text : str
            Full text of the business plan.
        catalog_items : list[dict]
            Writable template cells as dicts with keys:
            sheet, cell, labels, units, period, block, current_value.
        on_step : callable, optional
            Callback ``(step: AgentStep) -> None`` for progress updates.
        """
        result = OrchestrationResult()
        result.document_chars = len(document_text) if document_text else 0
        result.document_preview = (document_text[:300] if document_text else "")
        t_start = time.time()

        # ---- Step 1: Business Model Analysis ----
        step1 = AgentStep(agent_name="Business Model Analyzer")
        result.steps.append(step1)
        step1.status = "running"
        step1.started_at = time.time()
        if on_step:
            on_step(step1)

        try:
            analysis = self.agent1.analyze(document_text)
            result.analysis = analysis
            step1.status = "success"
            step1.summary = (
                f"業種: {analysis.industry} | "
                f"セグメント: {len(analysis.segments)}件 | "
                f"モデル: {analysis.business_model_type}"
            )
            logger.info("Step 1 complete: %s", step1.summary)
        except Exception as e:
            step1.status = "error"
            step1.error_message = str(e)
            logger.error("Step 1 failed: %s", e)
        finally:
            step1.finished_at = time.time()
            if on_step:
                on_step(step1)

        # ---- Step 2: FM Design ----
        step2 = AgentStep(agent_name="FM Designer")
        result.steps.append(step2)
        step2.status = "running"
        step2.started_at = time.time()
        if on_step:
            on_step(step2)

        analysis_for_step2 = result.analysis or BusinessModelAnalysis()

        if not result.analysis or not result.analysis.segments:
            step2.summary = "Agent 1 未完了のため、直接抽出モードで実行"
            logger.info("Step 2: running in direct extraction mode")

        try:
            design = self.agent2.design(
                analysis=analysis_for_step2,
                catalog_items=catalog_items,
                document_text=document_text,
            )
            result.design = design
            step2.status = "success"
            n_ext = len(design.extractions)
            n_unmap = len(design.unmapped_cells)
            step2.summary = f"抽出: {n_ext}件 | 未マッピング: {n_unmap}件 | 警告: {len(design.warnings)}件"
            logger.info("Step 2 complete: %s", step2.summary)
        except Exception as e:
            step2.status = "error"
            step2.error_message = str(e)
            logger.error("Step 2 failed: %s", e)
        finally:
            step2.finished_at = time.time()
            if on_step:
                on_step(step2)

        result.total_elapsed = time.time() - t_start
        return result
