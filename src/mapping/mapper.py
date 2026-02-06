"""Parameter-to-cell mapping engine."""
import re
import logging
from typing import List, Dict, Optional, Tuple
from difflib import SequenceMatcher

from ..config.models import (
    CatalogItem, InputCatalog, ExtractedParameter, CellTarget
)
from ..config.industry import INDUSTRY_SYNONYMS

logger = logging.getLogger(__name__)


class ParameterMapper:
    """Maps extracted parameters to template input cells."""

    def __init__(self, catalog: InputCatalog, industry: str = ""):
        self.catalog = catalog
        self.industry = industry
        self.synonyms = INDUSTRY_SYNONYMS.get(industry, {})
        # Build lookup structures
        self._label_index = self._build_label_index()

    def _build_label_index(self) -> Dict[str, List[CatalogItem]]:
        """Build an index from normalized labels to catalog items."""
        index = {}
        for item in self.catalog.items:
            if item.has_formula:
                continue
            for label in item.label_candidates:
                normalized = self._normalize_label(label)
                if normalized not in index:
                    index[normalized] = []
                index[normalized].append(item)
        return index

    def _normalize_label(self, label: str) -> str:
        """Normalize a label for matching."""
        label = label.strip().lower()
        label = re.sub(r'[\s\u3000]+', ' ', label)  # Normalize whitespace
        label = re.sub(r'[（）()【】\[\]「」『』]', '', label)  # Remove brackets
        return label

    def map_parameter(self, param: ExtractedParameter) -> List[CellTarget]:
        """Map a single parameter to target cells."""
        targets = []

        # 1. Try exact key match against labels
        exact = self._exact_match(param.key)
        if exact:
            targets.extend(exact)
            return targets

        # 2. Try synonym expansion
        synonym = self._synonym_match(param.key)
        if synonym:
            targets.extend(synonym)
            return targets

        # 3. Try fuzzy matching
        fuzzy = self._fuzzy_match(param.key, param.label, threshold=0.6)
        if fuzzy:
            targets.extend(fuzzy)
            return targets

        # 4. Try LLM mapping hints if available
        if param.mapped_targets:
            return param.mapped_targets

        logger.warning(f"No mapping found for parameter '{param.key}'")
        return targets

    def map_all(self, parameters: List[ExtractedParameter]) -> List[ExtractedParameter]:
        """Map all parameters to cells, updating their mapped_targets."""
        for param in parameters:
            if not param.mapped_targets:
                param.mapped_targets = self.map_parameter(param)
            elif len(param.mapped_targets) == 0:
                param.mapped_targets = self.map_parameter(param)
        return parameters

    def _exact_match(self, key: str) -> List[CellTarget]:
        """Try exact label matching."""
        normalized = self._normalize_label(key)
        if normalized in self._label_index:
            items = self._label_index[normalized]
            return [CellTarget(sheet=item.sheet, cell=item.cell) for item in items]
        return []

    def _synonym_match(self, key: str) -> List[CellTarget]:
        """Try matching via industry synonyms."""
        key_lower = key.lower()

        for canonical, synonyms in self.synonyms.items():
            if key_lower == canonical.lower() or key_lower in [s.lower() for s in synonyms]:
                # Found a synonym match, now find cells with any of these labels
                all_names = [canonical] + synonyms
                for name in all_names:
                    result = self._exact_match(name)
                    if result:
                        return result
        return []

    def _fuzzy_match(
        self, key: str, label: str, threshold: float = 0.6
    ) -> List[CellTarget]:
        """Try fuzzy string matching against catalog labels."""
        best_score = 0.0
        best_items = []

        search_terms = [key.lower(), label.lower()]

        for norm_label, items in self._label_index.items():
            for term in search_terms:
                score = SequenceMatcher(None, term, norm_label).ratio()
                if score > best_score and score >= threshold:
                    best_score = score
                    best_items = items

        if best_items:
            return [CellTarget(sheet=item.sheet, cell=item.cell) for item in best_items]
        return []

    def get_mapping_report(self, parameters: List[ExtractedParameter]) -> str:
        """Generate a report of parameter-to-cell mappings."""
        lines = ["# Parameter Mapping Report\n"]

        mapped = [p for p in parameters if p.mapped_targets]
        unmapped = [p for p in parameters if not p.mapped_targets]

        lines.append(f"## Summary")
        lines.append(f"- Total parameters: {len(parameters)}")
        lines.append(f"- Mapped: {len(mapped)}")
        lines.append(f"- Unmapped: {len(unmapped)}\n")

        if mapped:
            lines.append("## Mapped Parameters")
            lines.append("| Key | Value | Target Cells |")
            lines.append("|-----|-------|-------------|")
            for p in mapped:
                cells = ", ".join(f"{t.sheet}!{t.cell}" for t in p.mapped_targets)
                lines.append(f"| {p.key} | {p.value} | {cells} |")

        if unmapped:
            lines.append("\n## Unmapped Parameters (Needs Review)")
            lines.append("| Key | Value | Confidence | Source |")
            lines.append("|-----|-------|-----------|--------|")
            for p in unmapped:
                lines.append(f"| {p.key} | {p.value} | {p.confidence:.2f} | {p.source} |")

        return "\n".join(lines)
