"""Agent Orchestrator -- coordinates the two-agent extraction pipeline.

Pipeline:
    Document + Template
        │
        ├─ Step 1: BusinessModelAnalyzer  (Agent 1)
        │   → What kind of business is this?
        │
        ├─ Step 2: FMDesigner  (Agent 2)
        │   → How does this business map to the template?
        │
        └─ Output: cell-level extractions with full context

This replaces the old single-pass ParameterExtractor with a
two-agent pipeline that first understands the business, then
maps it intelligently to the template.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .business_model_analyzer import BusinessModelAnalyzer, BusinessModelAnalysis
from .fm_designer import FMDesigner, FMDesignResult, CellExtraction

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
    """Complete result from the two-agent pipeline."""
    analysis: Optional[BusinessModelAnalysis] = None
    design: Optional[FMDesignResult] = None
    steps: List[AgentStep] = field(default_factory=list)
    total_elapsed: float = 0.0

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
    """Coordinates the two-agent extraction pipeline.

    Usage::

        from src.extract.llm_client import LLMClient
        from src.agents.orchestrator import AgentOrchestrator

        llm = LLMClient()
        orch = AgentOrchestrator(llm)
        result = orch.run(document_text, catalog_items)

        # Business model analysis
        print(result.analysis.executive_summary)
        print(result.analysis.segments)

        # Cell extractions
        for ext in result.extractions:
            print(f"{ext.sheet}!{ext.cell} = {ext.value} ({ext.confidence})")
    """

    def __init__(self, llm_client: Any) -> None:
        self.llm = llm_client
        self.agent1 = BusinessModelAnalyzer(llm_client)
        self.agent2 = FMDesigner(llm_client)

    def run(
        self,
        document_text: str,
        catalog_items: List[Dict[str, Any]],
        *,
        on_step: Any = None,
    ) -> OrchestrationResult:
        """Run the full two-agent pipeline.

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

        # ---- Step 2: FM Design (only if Step 1 succeeded) ----
        step2 = AgentStep(agent_name="FM Designer")
        result.steps.append(step2)

        if result.analysis and result.analysis.segments:
            step2.status = "running"
            step2.started_at = time.time()
            if on_step:
                on_step(step2)

            try:
                design = self.agent2.design(
                    analysis=result.analysis,
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
        else:
            step2.status = "error"
            step2.error_message = "Step 1 (Business Model Analysis) が失敗したため、スキップされました"
            if on_step:
                on_step(step2)

        result.total_elapsed = time.time() - t_start
        return result
