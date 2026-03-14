"""Markdown report helpers for PDCA experiments."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import ExperimentManifest
from .storage import experiment_dir, load_experiment_manifest


def render_report(manifest: ExperimentManifest, summary: dict[str, Any]) -> str:
    decision = manifest.decision or "pending"
    lines = [
        "# Experiment Report",
        "",
        f"- experiment_id: {manifest.experiment_id}",
        f"- campaign_id: {manifest.campaign_id}",
        f"- target_phase: {manifest.target_phase}",
        f"- baseline_source: {manifest.baseline_source}",
        f"- Decision: {decision}",
        "",
        "## Hypothesis",
        "",
        manifest.hypothesis,
        "",
        "## Criteria Scores",
        "",
        "| Criterion | Baseline | Candidate | Delta |",
        "| --- | --- | --- | --- |",
    ]
    for criterion, values in summary.get("criteria_scores", {}).items():
        lines.append(
            f"| {criterion} | {values['baseline']} | {values['candidate']} | {values['delta']} |"
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- reviewer_notes:",
            "- follow_up:",
            "",
        ]
    )
    return "\n".join(lines)


def write_report(artifact_root: Path, experiment_id: str) -> Path:
    root = experiment_dir(artifact_root, experiment_id)
    manifest = load_experiment_manifest(artifact_root, experiment_id)
    summary = json.loads((root / "compare" / "summary.json").read_text(encoding="utf-8"))
    report_path = root / "compare" / "report.md"
    report_path.write_text(render_report(manifest, summary), encoding="utf-8")
    return report_path
