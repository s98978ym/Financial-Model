"""Main extraction orchestrator - coordinates document chunks with catalog blocks."""
import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from ..config.models import (
    PhaseAConfig, InputCatalog, CatalogItem, ExtractedParameter,
    Evidence, CellTarget, ExtractionResult
)
from ..ingest.base import DocumentContent
from .llm_client import LLMClient
from .prompts import build_extraction_prompt
from .normalizer import normalize_value, normalize_japanese_number

logger = logging.getLogger(__name__)


class ParameterExtractor:
    """Orchestrates LLM-based parameter extraction from documents."""

    def __init__(
        self,
        config: PhaseAConfig,
        llm_client: Optional[LLMClient] = None,
        prompt_overrides: Optional[Dict[str, str]] = None,
    ):
        self.config = config
        self.llm = llm_client or LLMClient()
        self.prompt_overrides = prompt_overrides or {}

    def extract_parameters(
        self,
        document: DocumentContent,
        catalog: InputCatalog,
    ) -> List[ExtractedParameter]:
        """
        Extract parameters from document, mapping to catalog cells.

        Process:
        1. Split catalog into blocks (by sheet+block)
        2. Split document into chunks
        3. For each block, send relevant chunks + block catalog to LLM
        4. Merge and deduplicate results
        5. Map extracted values to specific cells
        """
        all_parameters = []
        doc_chunks = document.get_chunks(max_chars=6000)

        for block_key, block_items in catalog.blocks.items():
            # Only process writable cells (not formulas)
            writable_items = [item for item in block_items if not item.has_formula]
            if not writable_items:
                continue

            catalog_json = json.dumps(
                [self._catalog_item_to_dict(item) for item in writable_items],
                ensure_ascii=False, indent=2
            )

            block_params = []
            for chunk in doc_chunks:
                messages = build_extraction_prompt(
                    document_chunk=chunk,
                    catalog_block=catalog_json,
                    industry=self.config.industry,
                    business_model=self.config.business_model,
                    strictness=self.config.strictness,
                    cases=self.config.cases,
                    overrides=self.prompt_overrides,
                )

                result = self.llm.extract(messages)
                params = self._parse_extraction_result(result, writable_items, block_key)
                block_params.extend(params)

            # Deduplicate: keep highest confidence for each key
            merged = self._merge_parameters(block_params)
            all_parameters.extend(merged)

        return all_parameters

    def _catalog_item_to_dict(self, item: CatalogItem) -> dict:
        return {
            "sheet": item.sheet,
            "cell": item.cell,
            "current_value": item.current_value,
            "labels": item.label_candidates,
            "units": item.unit_candidates,
            "period": item.year_or_period,
            "block": item.block,
        }

    def _parse_extraction_result(
        self, result: dict, catalog_items: List[CatalogItem], block_key: str
    ) -> List[ExtractedParameter]:
        """Parse LLM extraction result into ExtractedParameter objects."""
        parameters = []
        values = result.get("values", {})
        confidences = result.get("confidence", {})
        evidences = result.get("evidence", {})
        assumptions = result.get("assumptions", {})
        hints = result.get("mapping_hints", {})

        for key, value in values.items():
            confidence = confidences.get(key, 0.5)

            # In strict mode, skip low-confidence inferred values
            if self.config.strictness == "strict" and confidence < 0.7:
                source = "template_default"
            else:
                source = "document" if confidence >= 0.7 else "inferred"

            ev_data = evidences.get(key, {})
            evidence = Evidence(
                quote=ev_data.get("quote", ""),
                page_or_slide=ev_data.get("page_or_slide", ""),
                rationale=ev_data.get("rationale", ""),
            )

            # Try to map to specific catalog cells
            mapped_targets = self._map_to_cells(key, hints.get(key, []), catalog_items)

            # Normalize value
            normalized_value = normalize_value(value)

            param = ExtractedParameter(
                key=key,
                label=key.replace("_", " ").title(),
                value=normalized_value,
                unit=self._infer_unit(key, catalog_items),
                mapped_targets=mapped_targets,
                evidence=evidence,
                confidence=confidence,
                source=source,
            )
            parameters.append(param)

        return parameters

    def _map_to_cells(
        self, key: str, hints: List[str], catalog_items: List[CatalogItem]
    ) -> List[CellTarget]:
        """Map an extracted parameter key to specific cells in the catalog."""
        targets = []
        key_lower = key.lower()

        # First try hints from LLM
        for hint in hints:
            if "::" in hint:
                parts = hint.split("::")
                if len(parts) == 2:
                    targets.append(CellTarget(sheet=parts[0], cell=parts[1]))

        if targets:
            return targets

        # Fall back to label matching
        for item in catalog_items:
            for label in item.label_candidates:
                if key_lower in label.lower() or label.lower() in key_lower:
                    targets.append(CellTarget(sheet=item.sheet, cell=item.cell))
                    break

        return targets

    def _infer_unit(self, key: str, catalog_items: List[CatalogItem]) -> Optional[str]:
        """Infer unit from key name or matching catalog items."""
        key_lower = key.lower()
        if any(w in key_lower for w in ["率", "rate", "ratio", "%"]):
            return "%"
        if any(w in key_lower for w in ["price", "cost", "revenue", "売上", "費", "単価", "金額"]):
            return "円"
        if any(w in key_lower for w in ["人数", "数", "count", "number"]):
            return "人"
        if any(w in key_lower for w in ["月", "month"]):
            return "月"
        return None

    def _merge_parameters(self, params: List[ExtractedParameter]) -> List[ExtractedParameter]:
        """Merge duplicate parameters, keeping highest confidence."""
        by_key: Dict[str, ExtractedParameter] = {}
        for p in params:
            if p.key not in by_key or p.confidence > by_key[p.key].confidence:
                by_key[p.key] = p
        return list(by_key.values())
