"""Helpers for saving prompt snapshots and imported outputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal, Optional

from .models import ImportedOutputMeta, PromptSnapshot
from .storage import experiment_dir

ImportRole = Literal["baseline", "candidate"]


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def save_prompt_snapshots(
    artifact_root: Path,
    experiment_id: str,
    *,
    baseline: PromptSnapshot,
    candidate: PromptSnapshot,
    context: Optional[dict[str, Any]] = None,
) -> Path:
    inputs_dir = experiment_dir(artifact_root, experiment_id) / "inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    _write_json(inputs_dir / "baseline_prompt_snapshot.json", baseline.model_dump())
    _write_json(inputs_dir / "candidate_prompt_snapshot.json", candidate.model_dump())
    (inputs_dir / "system_prompt.md").write_text(candidate.system_prompt, encoding="utf-8")
    (inputs_dir / "user_prompt.md").write_text(candidate.user_prompt, encoding="utf-8")
    if context is not None:
        _write_json(inputs_dir / "context.json", context)
    return inputs_dir


def import_output(
    artifact_root: Path,
    experiment_id: str,
    *,
    role: ImportRole,
    payload: dict[str, Any],
    meta: Optional[ImportedOutputMeta] = None,
) -> Path:
    outputs_dir = experiment_dir(artifact_root, experiment_id) / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    _write_json(outputs_dir / f"{role}_output.json", payload)
    if meta is not None:
        _write_json(outputs_dir / f"{role}_meta.json", meta.model_dump())
    return outputs_dir
