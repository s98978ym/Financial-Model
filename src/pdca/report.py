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
        "# 実験レポート",
        "",
        f"- 実験ID: {manifest.experiment_id}",
        f"- キャンペーンID: {manifest.campaign_id}",
        f"- 対象フェーズ: {manifest.target_phase}",
        f"- 基準出力: {manifest.baseline_source}",
        f"- 判定: {decision}",
        "",
        "## 仮説",
        "",
        manifest.hypothesis,
        "",
        "## 比較指標",
        "",
        "| 指標 | 基準 | 候補 | 差分 |",
        "| --- | --- | --- | --- |",
    ]
    for criterion, values in summary.get("criteria_scores", {}).items():
        lines.append(
            f"| {criterion} | {values['baseline']} | {values['candidate']} | {values['delta']} |"
        )
    lines.extend(
        [
            "",
            "## メモ",
            "",
            "- レビューメモ:",
            "- 次のアクション:",
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
