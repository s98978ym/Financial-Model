"""
PL Generator - Configuration and Data Models
=============================================

Defines ALL Pydantic v2 models used across the PL Generator pipeline:

  Phase A  : PhaseAConfig, ColorConfig
  Catalog  : CatalogItem, InputCatalog
  Phase B  : ExtractedParameter, ExtractionResult, AnalysisReport, KPIDefinition
  Phase C  : CustomizationInstruction, ProposedChange
  Generate : GenerationConfig
  Simulate : SimulationConfig
  Validate : ValidationResult

Convention
----------
- Japanese comments clarify domain-specific semantics.
- ``model_config = ConfigDict(arbitrary_types_allowed=True)`` is set on
  models that may hold opaque / numpy-like values coming from Excel or
  simulation layers.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Literal, Optional, Tuple

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


# ============================================================
# Colour helpers
# ============================================================

_HEX_CHARS = set("0123456789abcdefABCDEF")


def _validate_hex_color(value: str) -> str:
    """Accept ``AARRGGBB`` or ``#RRGGBB`` / ``RRGGBB`` hex colour strings.

    Returns the canonical ``AARRGGBB`` form (8 hex digits, no ``#``).
    """
    raw = value.lstrip("#")
    if not all(c in _HEX_CHARS for c in raw):
        raise ValueError(f"Invalid hex colour: {value!r}")
    if len(raw) == 6:
        raw = "FF" + raw  # assume fully opaque
    if len(raw) != 8:
        raise ValueError(
            f"Hex colour must be 6 (RRGGBB) or 8 (AARRGGBB) digits, got {value!r}"
        )
    return raw.upper()


# ============================================================
# 1 / 2.  ColorConfig  &  PhaseAConfig  (Phase A - user prefs)
# ============================================================


class ColorConfig(BaseModel):
    """Excel cell-colour preferences.

    Colours are stored in ``AARRGGBB`` hex (openpyxl-compatible).

    Attributes:
        input_color:         背景色 for user-input cells (薄黄色 by default).
        formula_color:       フォント色 for formula cells  (青文字 by default).
        total_color:         背景色 for total / subtotal rows (薄グレー).
        apply_formula_color: Whether to actually paint formula-font colour.
        apply_total_color:   Whether to actually paint total-row background.
    """

    input_color: str = Field(
        default="FFFFF2CC",
        description="Background fill for input cells (AARRGGBB hex). Default: 薄黄色",
    )
    formula_color: str = Field(
        default="FF0000FF",
        description="Font colour for formula cells (AARRGGBB hex). Default: 青文字",
    )
    total_color: str = Field(
        default="FFD9D9D9",
        description="Background fill for total rows (AARRGGBB hex). Default: 薄グレー",
    )
    apply_formula_color: bool = Field(
        default=False,
        description="If True, apply formula_color to formula cells in output.",
    )
    apply_total_color: bool = Field(
        default=False,
        description="If True, apply total_color to total/subtotal rows in output.",
    )

    # -- validators ----------------------------------------------------------

    @field_validator("input_color", "formula_color", "total_color", mode="before")
    @classmethod
    def _normalise_hex(cls, v: str) -> str:
        return _validate_hex_color(v)

    # -- helpers -------------------------------------------------------------

    def as_openpyxl_dict(self) -> Dict[str, str]:
        """Return a mapping usable by ``openpyxl.styles.PatternFill`` etc."""
        return {
            "input_color": self.input_color,
            "formula_color": self.formula_color,
            "total_color": self.total_color,
        }


class PhaseAConfig(BaseModel):
    """User-customisation settings collected during Phase A.

    Attributes:
        industry:       業種.  One of the preset labels or free-text.
        business_model: ビジネスモデル類型.
        strictness:     厳密 (strict) = エビデンスが無い項目は空欄のまま,
                        ノーマル (normal) = LLM推定で補完.
        cases:          生成するケース一覧 (best / base / worst).
        simulation:     Monte-Carlo simulation を実行するか.
        colors:         Excel セル色設定.
    """

    industry: str = Field(
        default="その他",
        description=(
            "業種.  Preset values: SaaS, 教育, 人材, EC, 小売, 飲食, "
            "メーカー, ヘルスケア, その他.  Free-text is also accepted."
        ),
    )
    business_model: Literal["B2B", "B2C", "B2B2C", "MIX", "Other"] = Field(
        default="B2B",
        description="ビジネスモデル類型.",
    )
    strictness: Literal["strict", "normal"] = Field(
        default="normal",
        description=(
            "厳密 (strict): evidence-only; "
            "ノーマル (normal): allow LLM inference."
        ),
    )
    cases: List[Literal["best", "base", "worst"]] = Field(
        default_factory=lambda: ["base", "worst"],
        description="生成するシナリオケース一覧.",
    )
    simulation: bool = Field(
        default=False,
        description="Monte-Carlo simulation を Phase E で実行するか.",
    )
    colors: ColorConfig = Field(
        default_factory=ColorConfig,
        description="Excel output colour settings.",
    )

    # -- validators ----------------------------------------------------------

    @field_validator("cases", mode="before")
    @classmethod
    def _deduplicate_cases(cls, v: Any) -> List[str]:
        """Deduplicate the case list while preserving order."""
        if isinstance(v, str):
            v = [v]
        seen: set[str] = set()
        out: list[str] = []
        for c in v:
            if c not in seen:
                seen.add(c)
                out.append(c)
        return out

    @model_validator(mode="after")
    def _ensure_at_least_one_case(self) -> "PhaseAConfig":
        if not self.cases:
            raise ValueError("At least one case must be specified.")
        return self

    # -- helpers -------------------------------------------------------------

    PRESET_INDUSTRIES: list[str] = [
        "SaaS",
        "教育",
        "人材",
        "EC",
        "小売",
        "飲食",
        "メーカー",
        "ヘルスケア",
        "その他",
    ]

    def is_strict(self) -> bool:
        """Convenience: True when strictness == 'strict'."""
        return self.strictness == "strict"

    def is_preset_industry(self) -> bool:
        """Return True if the industry matches a built-in preset."""
        return self.industry in self.PRESET_INDUSTRIES


# ============================================================
# 3 / 4.  CatalogItem  &  InputCatalog  (template scan)
# ============================================================


class CatalogItem(BaseModel):
    """A single input-cell discovered during template catalogue scanning.

    Attributes:
        sheet:            Sheet name where the cell lives.
        cell:             Cell address (e.g. ``"B5"``).
        current_value:    The value already present in the template cell.
        fill_color:       Background fill colour of the cell (AARRGGBB hex).
        has_formula:      Whether the cell contains an Excel formula.
        label_candidates: Possible label strings harvested from nearby cells.
        unit_candidates:  Possible unit strings (円, %, 人, 月, …).
        year_or_period:   Period annotation (e.g. ``"FY2025"``).
        block:            Logical grouping / block name within the sheet.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    sheet: str
    cell: str = Field(
        ..., pattern=r"^[A-Z]{1,3}[0-9]+$", description="Cell address, e.g. 'B5'."
    )
    current_value: Any = None
    fill_color: str = Field(default="FFFFFFFF", description="Cell background (AARRGGBB).")
    has_formula: bool = False
    label_candidates: List[str] = Field(default_factory=list)
    unit_candidates: List[str] = Field(default_factory=list)
    year_or_period: Optional[str] = None
    block: Optional[str] = None

    # -- helpers -------------------------------------------------------------

    @property
    def address(self) -> str:
        """Return ``'SheetName!B5'``-style full address."""
        return f"{self.sheet}!{self.cell}"

    def primary_label(self) -> str:
        """Return the first label candidate, or the cell address as fallback."""
        return self.label_candidates[0] if self.label_candidates else self.address

    def to_prompt_fragment(self) -> str:
        """Produce a short text fragment suitable for inclusion in an LLM prompt."""
        label = self.primary_label()
        unit = self.unit_candidates[0] if self.unit_candidates else ""
        period = self.year_or_period or ""
        parts = [f"[{self.address}]", label]
        if unit:
            parts.append(f"({unit})")
        if period:
            parts.append(f"[{period}]")
        if self.current_value is not None:
            parts.append(f"= {self.current_value}")
        return " ".join(parts)


class InputCatalog(BaseModel):
    """Aggregated collection of :class:`CatalogItem` instances.

    Provides grouping by ``sheet + block`` for block-level LLM extraction.
    """

    items: List[CatalogItem] = Field(default_factory=list)
    blocks: Dict[str, List[CatalogItem]] = Field(
        default_factory=dict,
        description=(
            "Items grouped by 'sheet::block' key.  "
            "Populated by :meth:`rebuild_blocks`."
        ),
    )

    # -- helpers -------------------------------------------------------------

    def rebuild_blocks(self) -> None:
        """Re-compute :attr:`blocks` from the current :attr:`items` list."""
        self.blocks.clear()
        for item in self.items:
            key = self._block_key(item)
            self.blocks.setdefault(key, []).append(item)

    @staticmethod
    def _block_key(item: CatalogItem) -> str:
        block = item.block or "__default__"
        return f"{item.sheet}::{block}"

    def add(self, item: CatalogItem) -> None:
        """Append an item and update the block index."""
        self.items.append(item)
        key = self._block_key(item)
        self.blocks.setdefault(key, []).append(item)

    def get_block(self, sheet: str, block: Optional[str] = None) -> List[CatalogItem]:
        """Retrieve all items for a given sheet/block combination."""
        key = f"{sheet}::{block or '__default__'}"
        return self.blocks.get(key, [])

    def sheets(self) -> List[str]:
        """Return a deduplicated, order-preserved list of sheet names."""
        seen: set[str] = set()
        out: list[str] = []
        for item in self.items:
            if item.sheet not in seen:
                seen.add(item.sheet)
                out.append(item.sheet)
        return out

    def to_prompt_text(self) -> str:
        """Serialise the whole catalogue into a text block for LLM prompts."""
        lines: list[str] = []
        for block_key, block_items in self.blocks.items():
            lines.append(f"--- {block_key} ---")
            for item in block_items:
                lines.append(f"  {item.to_prompt_fragment()}")
        return "\n".join(lines)

    def __len__(self) -> int:
        return len(self.items)


# ============================================================
# 5 / 6 / 7.  CellTarget, Evidence, ExtractedParameter
# ============================================================


class CellTarget(BaseModel):
    """A reference to a specific sheet + cell in the Excel workbook."""

    sheet: str
    cell: str = Field(
        ..., pattern=r"^[A-Z]{1,3}[0-9]+$", description="Cell address, e.g. 'C12'."
    )

    @property
    def address(self) -> str:
        """Return ``'Sheet!Cell'`` style address."""
        return f"{self.sheet}!{self.cell}"

    def __hash__(self) -> int:
        return hash((self.sheet, self.cell))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CellTarget):
            return NotImplemented
        return self.sheet == other.sheet and self.cell == other.cell


class Evidence(BaseModel):
    """Supporting evidence for an extracted parameter value.

    Attributes:
        quote:         Verbatim text from the source document.
        page_or_slide: Page / slide number reference.
        rationale:     LLM explanation of why this value was chosen.
    """

    quote: str = Field(default="", description="Verbatim quote from the source document.")
    page_or_slide: str = Field(default="", description="Page or slide reference (e.g. 'p.3').")
    rationale: str = Field(default="", description="LLM reasoning for the extracted value.")

    def is_empty(self) -> bool:
        """True when no evidence fields have been populated."""
        return not (self.quote or self.page_or_slide or self.rationale)

    def to_display_text(self) -> str:
        """Human-readable summary suitable for UI display."""
        parts: list[str] = []
        if self.page_or_slide:
            parts.append(f"[{self.page_or_slide}]")
        if self.quote:
            parts.append(f'"{self.quote}"')
        if self.rationale:
            parts.append(f"({self.rationale})")
        return " ".join(parts) if parts else "(no evidence)"


class ExtractedParameter(BaseModel):
    """A single parameter value extracted by the LLM during Phase B.

    Holds both the extracted value and metadata that enables Phase C editing
    and Phase D Excel writing.

    Attributes:
        key:             Normalised parameter key (English snake_case).
        label:           Human-readable display name (Japanese or English).
        value:           The normalised numeric / string value.
        unit:            Unit of measurement (円, %, 人, 月 …).
        mapped_targets:  Where in the workbook to write this value.
        evidence:        Source evidence.
        confidence:      LLM self-assessed confidence [0.0 - 1.0].
        source:          Origin of the value.
        selected:        User toggle for Phase C (include / exclude).
        adjusted_value:  Optional user-adjusted value from Phase C.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    key: str = Field(..., description="Normalised parameter key (snake_case).")
    label: str = Field(..., description="Display name for the parameter.")
    value: Any = Field(..., description="Extracted value (numeric or string).")
    unit: Optional[str] = Field(
        default=None, description="Unit: 円, %, 人, 月 etc."
    )
    mapped_targets: List[CellTarget] = Field(
        default_factory=list,
        description="Target cells in the Excel workbook.",
    )
    evidence: Evidence = Field(
        default_factory=Evidence,
        description="Supporting evidence from the source document.",
    )
    confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Confidence score [0.0 - 1.0]."
    )
    source: Literal["document", "inferred", "template_default"] = Field(
        default="document",
        description="Origin of the parameter value.",
    )
    selected: bool = Field(
        default=True,
        description="User selection toggle for Phase C (include / exclude).",
    )
    adjusted_value: Optional[Any] = Field(
        default=None,
        description="User-adjusted value from Phase C (overrides *value* when set).",
    )

    # -- helpers -------------------------------------------------------------

    @property
    def effective_value(self) -> Any:
        """Return *adjusted_value* if set, otherwise *value*."""
        return self.adjusted_value if self.adjusted_value is not None else self.value

    def is_high_confidence(self, threshold: float = 0.8) -> bool:
        """Check whether confidence exceeds the given threshold."""
        return self.confidence >= threshold

    def target_addresses(self) -> List[str]:
        """Return list of ``'Sheet!Cell'`` address strings."""
        return [t.address for t in self.mapped_targets]

    def to_summary_dict(self) -> Dict[str, Any]:
        """Compact dictionary representation for logging / display."""
        return {
            "key": self.key,
            "label": self.label,
            "value": self.effective_value,
            "unit": self.unit,
            "confidence": self.confidence,
            "source": self.source,
            "targets": self.target_addresses(),
            "selected": self.selected,
        }


# ============================================================
# 8.  ExtractionResult  (per-block LLM output)
# ============================================================


class ExtractionResult(BaseModel):
    """Raw extraction output from the LLM for one catalogue block.

    This intermediate representation is transformed into a list of
    :class:`ExtractedParameter` during the mapping phase.

    Attributes:
        values:         key -> extracted value.
        confidence:     key -> confidence float.
        evidence:       key -> Evidence instance.
        assumptions:    key -> assumption text when value was inferred.
        mapping_hints:  key -> list of candidate cell addresses.
    """

    values: Dict[str, Any] = Field(default_factory=dict)
    confidence: Dict[str, float] = Field(default_factory=dict)
    evidence: Dict[str, Evidence] = Field(default_factory=dict)
    assumptions: Dict[str, str] = Field(default_factory=dict)
    mapping_hints: Dict[str, List[str]] = Field(default_factory=dict)

    # -- helpers -------------------------------------------------------------

    def keys(self) -> List[str]:
        """Return the list of extracted parameter keys."""
        return list(self.values.keys())

    def get_confidence(self, key: str, default: float = 0.0) -> float:
        """Return the confidence for *key*, or *default* if missing."""
        return self.confidence.get(key, default)

    def get_evidence(self, key: str) -> Evidence:
        """Return Evidence for *key*, or an empty Evidence if absent."""
        return self.evidence.get(key, Evidence())

    def high_confidence_keys(self, threshold: float = 0.8) -> List[str]:
        """Return keys whose confidence >= *threshold*."""
        return [k for k, c in self.confidence.items() if c >= threshold]

    def merge(self, other: "ExtractionResult") -> "ExtractionResult":
        """Return a **new** ExtractionResult merging *self* and *other*.

        On key collisions, *other* wins.
        """
        return ExtractionResult(
            values={**self.values, **other.values},
            confidence={**self.confidence, **other.confidence},
            evidence={**self.evidence, **other.evidence},
            assumptions={**self.assumptions, **other.assumptions},
            mapping_hints={**self.mapping_hints, **other.mapping_hints},
        )


# ============================================================
# 8b.  FormulaInfo  &  DependencyNode  (model-map internals)
# ============================================================


class FormulaInfo(BaseModel):
    """Parsed information about a single formula cell in the template."""

    sheet: str
    cell: str = Field(default="", description="Cell address, e.g. 'C12'.")
    raw_formula: str = Field(default="", description="Raw Excel formula string.")
    referenced_cells: List[str] = Field(default_factory=list)
    human_readable: str = Field(default="", description="Human-readable formula translation.")
    label: str = Field(default="", description="Row/column label for this cell.")


class DependencyNode(BaseModel):
    """A node in the formula dependency tree."""

    address: str = Field(default="", description="'Sheet!Cell' style address.")
    label: str = ""
    is_input: bool = False
    is_kpi: bool = False
    children: List["DependencyNode"] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "address": self.address,
            "label": self.label,
            "is_input": self.is_input,
            "is_kpi": self.is_kpi,
            "children": [c.to_dict() for c in self.children],
        }


# Allow self-referencing model
DependencyNode.model_rebuild()


# ============================================================
# 9 / 10.  KPIDefinition  &  AnalysisReport  (Phase B output)
# ============================================================


class KPIDefinition(BaseModel):
    """Definition of a Key Performance Indicator discovered in the template.

    Attributes:
        name:          KPI name (e.g. ``"売上高"``, ``"EBITDA"``).
        excel_formula: Raw Excel formula string (e.g. ``"=SUM(B5:B16)"``).
        human_formula: Human-readable description of the formula.
        sheet:         Sheet where the KPI lives.
        cell:          Cell address of the KPI.
        dependencies:  List of parameter keys this KPI depends on.
    """

    name: str
    excel_formula: str = Field(default="", description="Raw Excel formula string.")
    human_formula: str = Field(default="", description="Human-readable formula description.")
    raw_formula: str = Field(default="", description="Alias: raw Excel formula string.")
    human_readable_formula: str = Field(default="", description="Alias: human-readable formula.")
    sheet: str = ""
    cell: str = ""
    dependencies: List[str] = Field(default_factory=list)

    @property
    def address(self) -> str:
        """Return ``'Sheet!Cell'`` address or empty string if incomplete."""
        if self.sheet and self.cell:
            return f"{self.sheet}!{self.cell}"
        return self.cell or ""


class AnalysisReport(BaseModel):
    """Complete output of Phase B (template analysis + document extraction).

    Supports both the analyzer-facing fields (formulas, kpis, label_map, summary)
    and the UI-facing fields (model_summary, kpi_definitions, etc.).
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Analyzer-facing fields
    template_path: str = ""
    formulas: List[FormulaInfo] = Field(default_factory=list)
    kpis: List[KPIDefinition] = Field(default_factory=list)
    label_map: Dict[str, str] = Field(default_factory=dict)
    summary: str = ""

    # UI-facing fields
    model_summary: str = Field(
        default="",
        description="High-level text summary of the financial model.",
    )
    sheet_descriptions: Dict[str, str] = Field(
        default_factory=dict,
        description="Sheet name -> human-readable purpose description.",
    )
    kpi_definitions: List[KPIDefinition] = Field(
        default_factory=list,
        description="KPIs discovered during template analysis.",
    )
    dependency_tree: Dict[str, Any] = Field(
        default_factory=dict,
        description="KPI address -> DependencyNode tree.",
    )
    parameters: List[ExtractedParameter] = Field(
        default_factory=list,
        description="All extracted parameters.",
    )
    case_structure: Dict[str, str] = Field(
        default_factory=dict,
        description="Case name -> description (e.g. 'best': '楽観ケース').",
    )

    # -- helpers -------------------------------------------------------------

    def selected_parameters(self) -> List[ExtractedParameter]:
        """Return only the parameters toggled *on* by the user (Phase C)."""
        return [p for p in self.parameters if p.selected]

    def high_confidence_parameters(
        self, threshold: float = 0.8,
    ) -> List[ExtractedParameter]:
        """Return parameters whose confidence >= *threshold*."""
        return [p for p in self.parameters if p.confidence >= threshold]

    def parameter_by_key(self, key: str) -> Optional[ExtractedParameter]:
        """Look up a parameter by its normalised key."""
        for p in self.parameters:
            if p.key == key:
                return p
        return None

    def kpi_by_name(self, name: str) -> Optional[KPIDefinition]:
        """Look up a KPI by name (case-insensitive)."""
        name_lower = name.lower()
        for k in self.kpi_definitions:
            if k.name.lower() == name_lower:
                return k
        return None

    def to_summary_json(self) -> str:
        """Compact JSON summary suitable for LLM context injection."""
        return json.dumps(
            {
                "model_summary": self.model_summary,
                "sheets": list(self.sheet_descriptions.keys()),
                "kpi_count": len(self.kpi_definitions),
                "parameter_count": len(self.parameters),
                "cases": list(self.case_structure.keys()),
            },
            ensure_ascii=False,
            indent=2,
        )


# ============================================================
# 11 / 12.  ProposedChange  &  CustomizationInstruction  (Phase C)
# ============================================================


class ProposedChange(BaseModel):
    """A single value change proposed during Phase C customisation.

    Created either from free-text instructions or from UI slider adjustments.

    Attributes:
        parameter_key:              Key of the target parameter.
        original_value:             Value before change.
        proposed_value:             New value proposed.
        reason:                     Human-readable reason for the change.
        affected_cases:             Which scenario cases are affected.
        evidence_from_instruction:  Verbatim text from the user instruction.
        accepted:                   Whether the user has approved this change.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    parameter_key: str
    original_value: Any = None
    proposed_value: Any = None
    reason: str = ""
    affected_cases: List[str] = Field(default_factory=list)
    evidence_from_instruction: str = Field(
        default="",
        description="Verbatim text from the user instruction that motivated this change.",
    )
    accepted: bool = Field(
        default=False,
        description="Set to True when the user confirms this change.",
    )

    # -- helpers -------------------------------------------------------------

    def accept(self) -> None:
        """Mark the change as accepted."""
        self.accepted = True

    def reject(self) -> None:
        """Mark the change as rejected."""
        self.accepted = False

    def delta_description(self) -> str:
        """Return a concise ``old -> new`` description string."""
        return f"{self.parameter_key}: {self.original_value} -> {self.proposed_value}"


class CustomizationInstruction(BaseModel):
    """Free-text customisation instruction from the user (Phase C).

    The raw text is parsed by the LLM into a list of :class:`ProposedChange`.

    Attributes:
        raw_text:        The original user instruction.
        parsed_changes:  Structured changes derived from *raw_text*.
    """

    raw_text: str = Field(
        ..., min_length=1, description="User's free-text customisation instruction."
    )
    parsed_changes: List[ProposedChange] = Field(
        default_factory=list,
        description="Structured changes parsed from raw_text.",
    )

    # -- helpers -------------------------------------------------------------

    def accepted_changes(self) -> List[ProposedChange]:
        """Return only the changes the user has accepted."""
        return [c for c in self.parsed_changes if c.accepted]

    def pending_changes(self) -> List[ProposedChange]:
        """Return changes not yet accepted."""
        return [c for c in self.parsed_changes if not c.accepted]

    def accept_all(self) -> None:
        """Mark every parsed change as accepted."""
        for c in self.parsed_changes:
            c.accept()


# ============================================================
# 13.  GenerationConfig  (Phase D input)
# ============================================================


class GenerationConfig(BaseModel):
    """Final aggregated configuration consumed by the Excel generation phase.

    Attributes:
        phase_a:          User preferences from Phase A.
        parameters:       Finalised parameters (after Phase C adjustments).
        proposed_changes: Accepted changes from Phase C.
        template_path:    Path to the source Excel template.
        output_dir:       Directory for generated output files.
    """

    phase_a: PhaseAConfig = Field(default_factory=PhaseAConfig)
    parameters: List[ExtractedParameter] = Field(default_factory=list)
    proposed_changes: List[ProposedChange] = Field(default_factory=list)
    template_path: str = Field(
        ..., min_length=1, description="Absolute path to the Excel template."
    )
    output_dir: str = Field(
        ..., min_length=1, description="Directory for output files."
    )

    # -- helpers -------------------------------------------------------------

    def active_parameters(self) -> List[ExtractedParameter]:
        """Return selected parameters with effective values resolved."""
        return [p for p in self.parameters if p.selected]

    def accepted_changes(self) -> List[ProposedChange]:
        """Return only accepted proposed changes."""
        return [c for c in self.proposed_changes if c.accepted]

    def output_filename(self, case: str, ext: str = ".xlsx") -> str:
        """Generate a conventional output filename for a given case."""
        industry = self.phase_a.industry.replace("/", "_")
        return f"PL_{industry}_{case}{ext}"

    def to_serialisable_dict(self) -> Dict[str, Any]:
        """Return a JSON-safe dictionary (useful for audit logs)."""
        return json.loads(self.model_dump_json())


# ============================================================
# 14.  SimulationConfig  (Phase E)
# ============================================================


class SimulationConfig(BaseModel):
    """Configuration for Monte-Carlo simulation (Phase E).

    Attributes:
        enabled:           Whether simulation is turned on.
        method:            Execution method (xlwings for live Excel recalc,
                           fallback for pure-Python approximation).
        iterations:        Number of Monte-Carlo iterations.
        kpi_targets:       KPI keys to track during simulation.
        parameter_ranges:  key -> (min, max) bounds for stochastic sampling.
    """

    enabled: bool = Field(default=False)
    method: Literal["xlwings", "fallback"] = Field(
        default="fallback",
        description="'xlwings' = live Excel recalc; 'fallback' = Python approximation.",
    )
    iterations: int = Field(
        default=1000, ge=1, le=100_000, description="Monte-Carlo iteration count."
    )
    kpi_targets: List[str] = Field(
        default_factory=lambda: [
            "revenue",
            "gross_profit",
            "operating_profit",
            "ebitda",
        ],
        description="KPI keys to record during simulation runs.",
    )
    parameter_ranges: Dict[str, Tuple[float, float]] = Field(
        default_factory=dict,
        description="Parameter key -> (min, max) sampling bounds.",
    )

    # -- validators ----------------------------------------------------------

    @field_validator("parameter_ranges", mode="before")
    @classmethod
    def _coerce_ranges(cls, v: Any) -> Dict[str, Tuple[float, float]]:
        """Accept list-style ``[min, max]`` and convert to tuples."""
        if isinstance(v, dict):
            coerced: Dict[str, Tuple[float, float]] = {}
            for key, rng in v.items():
                if isinstance(rng, (list, tuple)) and len(rng) == 2:
                    coerced[key] = (float(rng[0]), float(rng[1]))
                else:
                    raise ValueError(
                        f"Range for {key!r} must be [min, max], got {rng!r}"
                    )
            return coerced
        return v

    # -- helpers -------------------------------------------------------------

    def get_range(
        self, key: str, default: Tuple[float, float] = (0.8, 1.2),
    ) -> Tuple[float, float]:
        """Return the sampling range for *key*, with a sensible default."""
        return self.parameter_ranges.get(key, default)

    def summary(self) -> str:
        """One-line summary for logging."""
        return (
            f"SimulationConfig(enabled={self.enabled}, method={self.method}, "
            f"iterations={self.iterations}, params={len(self.parameter_ranges)})"
        )


# ============================================================
# 15.  ValidationResult  (post-generation checks)
# ============================================================


class ValidationResult(BaseModel):
    """Result of post-generation validation checks.

    Attributes:
        passed:             Overall pass / fail.
        formula_preserved:  All original formulas are intact.
        no_new_errors:      No new ``#REF!``, ``#VALUE!`` etc. introduced.
        full_calc_on_load:  Workbook recalculates cleanly on open.
        changed_cells:      Cells that were modified during generation.
        errors_found:       Descriptive error messages.
        warnings:           Non-blocking warning messages.
    """

    passed: bool = Field(
        default=True, description="True if all validation checks passed."
    )
    formula_preserved: bool = Field(
        default=True, description="True if no formula cells were overwritten."
    )
    no_new_errors: bool = Field(
        default=True, description="True if no new Excel errors were introduced."
    )
    full_calc_on_load: bool = Field(
        default=True,
        description="True if the workbook recalculates without issues on open.",
    )
    changed_cells: List[CellTarget] = Field(
        default_factory=list,
        description="Cells modified during generation.",
    )
    errors_found: List[str] = Field(
        default_factory=list, description="Error messages from validation."
    )
    warnings: List[str] = Field(
        default_factory=list, description="Non-blocking warning messages."
    )

    # -- helpers -------------------------------------------------------------

    def add_error(self, message: str) -> None:
        """Record an error and set *passed* to False."""
        self.errors_found.append(message)
        self.passed = False

    def add_warning(self, message: str) -> None:
        """Record a warning (does not fail validation)."""
        self.warnings.append(message)

    def mark_formula_overwritten(self, target: CellTarget) -> None:
        """Record that a formula cell was overwritten (auto-fails)."""
        self.formula_preserved = False
        self.add_error(f"Formula overwritten at {target.address}")

    def mark_excel_error(self, target: CellTarget, error_type: str) -> None:
        """Record a new Excel error (``#REF!``, ``#VALUE!`` etc.)."""
        self.no_new_errors = False
        self.add_error(f"{error_type} at {target.address}")

    @property
    def error_count(self) -> int:
        """Total number of errors found."""
        return len(self.errors_found)

    @property
    def warning_count(self) -> int:
        """Total number of warnings found."""
        return len(self.warnings)

    def to_report_text(self) -> str:
        """Multi-line human-readable validation report."""
        status = "PASSED" if self.passed else "FAILED"
        lines = [
            f"=== Validation Report: {status} ===",
            f"  Formula preserved : {self.formula_preserved}",
            f"  No new errors     : {self.no_new_errors}",
            f"  Full calc on load : {self.full_calc_on_load}",
            f"  Changed cells     : {len(self.changed_cells)}",
            f"  Errors            : {self.error_count}",
            f"  Warnings          : {self.warning_count}",
        ]
        if self.errors_found:
            lines.append("  --- Errors ---")
            for e in self.errors_found:
                lines.append(f"    - {e}")
        if self.warnings:
            lines.append("  --- Warnings ---")
            for w in self.warnings:
                lines.append(f"    - {w}")
        return "\n".join(lines)
