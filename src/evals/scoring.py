"""Multi-layer scoring for reference-driven evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from .reference_workbook import ReferenceWorkbook


EXPECTED_ENGINES = {
    "ミール": "unit_economics",
    "アカデミー": "progression",
    "コンサル": "project_capacity",
}


@dataclass
class ScoreResult:
    layer_scores: Dict[str, float] = field(default_factory=dict)
    total_score: float = 0.0


def score_candidate(reference: ReferenceWorkbook, candidate: Dict[str, Any]) -> ScoreResult:
    layer_scores = {
        "structure": _score_structure(reference, candidate),
        "model_sheets": _score_model_sheets(reference, candidate),
        "pl": _score_pl(reference, candidate),
        "explainability": _score_explainability(candidate),
    }
    total_score = round(sum(layer_scores.values()) / len(layer_scores), 4)
    return ScoreResult(layer_scores=layer_scores, total_score=total_score)


def _score_structure(reference: ReferenceWorkbook, candidate: Dict[str, Any]) -> float:
    candidate_segments = candidate.get("segments", [])
    candidate_names = {segment.get("name") for segment in candidate_segments}
    expected_names = set(reference.segment_names)

    if not expected_names:
        return 0.0

    overlap = len(candidate_names & expected_names) / len(expected_names)

    engine_hits = 0
    for segment in candidate_segments:
        name = segment.get("name")
        if name in EXPECTED_ENGINES and segment.get("engine_type") == EXPECTED_ENGINES[name]:
            engine_hits += 1
    engine_score = engine_hits / len(expected_names)

    return round((overlap + engine_score) / 2, 4)


def _score_model_sheets(reference: ReferenceWorkbook, candidate: Dict[str, Any]) -> float:
    candidate_sheets = candidate.get("model_sheets", {})
    scores: List[float] = []

    for segment_name, reference_metrics in reference.model_sheets.items():
        candidate_metrics = candidate_sheets.get(segment_name, {})
        for metric_name, reference_series in reference_metrics.items():
            scores.append(_score_series(reference_series, candidate_metrics.get(metric_name, [])))

    return round(sum(scores) / len(scores), 4) if scores else 0.0


def _score_pl(reference: ReferenceWorkbook, candidate: Dict[str, Any]) -> float:
    candidate_pl = candidate.get("pl_lines", {})
    scores = [
        _score_series(reference_series, candidate_pl.get(label, []))
        for label, reference_series in reference.pl_lines.items()
    ]
    return round(sum(scores) / len(scores), 4) if scores else 0.0


def _score_explainability(candidate: Dict[str, Any]) -> float:
    assumptions = candidate.get("assumptions", [])
    if not assumptions:
        return 0.0

    scored = 0.0
    for assumption in assumptions:
        if assumption.get("source_type"):
            scored += 1 / 3
        if assumption.get("evidence_refs"):
            scored += 1 / 3
        if assumption.get("review_status") == "approved":
            scored += 1 / 3

    return round(scored / len(assumptions), 4)


def _score_series(reference_series: List[float], candidate_series: List[float]) -> float:
    if not reference_series:
        return 0.0
    if not candidate_series:
        return 0.0

    pairs = zip(reference_series, candidate_series)
    errors: List[float] = []
    for reference_value, candidate_value in pairs:
        denom = max(abs(float(reference_value)), 1.0)
        error = min(abs(float(candidate_value) - float(reference_value)) / denom, 1.0)
        errors.append(error)

    if not errors:
        return 0.0
    return round(1.0 - (sum(errors) / len(errors)), 4)
