"""Comparison helpers for imported experiment outputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .criteria.phase5_extraction import phase5_metrics
from .storage import experiment_dir


def _criteria_summary(baseline_metrics: dict[str, Any], candidate_metrics: dict[str, Any]) -> dict[str, dict[str, Any]]:
    summary: dict[str, dict[str, Any]] = {}
    for key in baseline_metrics:
        base_value = baseline_metrics[key]
        cand_value = candidate_metrics[key]
        delta = None
        if isinstance(base_value, (int, float)) and isinstance(cand_value, (int, float)):
            delta = round(cand_value - base_value, 4)
        summary[key] = {
            "baseline": base_value,
            "candidate": cand_value,
            "delta": delta,
        }
    return summary


def compare_phase5_payloads(baseline_payload: Any, candidate_payload: Any) -> dict[str, Any]:
    baseline_metrics = phase5_metrics(baseline_payload)
    candidate_metrics = phase5_metrics(candidate_payload)
    return {
        "phase": 5,
        "criteria_scores": _criteria_summary(baseline_metrics, candidate_metrics),
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _render_diff(summary: dict[str, Any]) -> str:
    lines = [
        "# Comparison Diff",
        "",
        "| Criterion | Baseline | Candidate | Delta |",
        "| --- | --- | --- | --- |",
    ]
    for criterion, values in summary["criteria_scores"].items():
        lines.append(
            f"| {criterion} | {values['baseline']} | {values['candidate']} | {values['delta']} |"
        )
    lines.append("")
    return "\n".join(lines)


def compare_experiment(artifact_root: Path, experiment_id: str, *, phase: int) -> dict[str, Any]:
    if phase != 5:
        raise ValueError(f"Unsupported phase for compare: {phase}")

    root = experiment_dir(artifact_root, experiment_id)
    outputs_dir = root / "outputs"
    compare_dir = root / "compare"
    baseline_payload = _read_json(outputs_dir / "baseline_output.json")
    candidate_payload = _read_json(outputs_dir / "candidate_output.json")
    summary = compare_phase5_payloads(baseline_payload, candidate_payload)
    compare_dir.mkdir(parents=True, exist_ok=True)
    _write_json(compare_dir / "summary.json", summary)
    (compare_dir / "diff.md").write_text(_render_diff(summary), encoding="utf-8")
    return summary
