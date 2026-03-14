"""Tests for PDCA input and output importing."""

import json
from pathlib import Path

from src.pdca.importer import import_output, save_prompt_snapshots
from src.pdca.models import ImportedOutputMeta, PromptSnapshot
from src.pdca.storage import create_experiment
from tests.pdca.test_storage import _build_manifest


def test_save_prompt_snapshot_writes_json_and_markdown(tmp_path: Path):
    artifact_root = tmp_path / "artifacts" / "llm-pdca"
    create_experiment(artifact_root, _build_manifest("exp-20260314-001"))

    save_prompt_snapshots(
        artifact_root,
        "exp-20260314-001",
        baseline=PromptSnapshot(
            system_prompt="baseline system",
            user_prompt="baseline user",
            prompt_key="param_extractor",
            source="default",
        ),
        candidate=PromptSnapshot(
            system_prompt="candidate system",
            user_prompt="candidate user",
            prompt_key="param_extractor",
            source="edited",
        ),
        context={"project_id": "project-1"},
    )

    inputs_dir = artifact_root / "experiments" / "exp-20260314-001" / "inputs"
    assert (inputs_dir / "baseline_prompt_snapshot.json").exists()
    assert (inputs_dir / "candidate_prompt_snapshot.json").exists()
    assert (inputs_dir / "system_prompt.md").read_text(encoding="utf-8") == "candidate system"
    assert (inputs_dir / "user_prompt.md").read_text(encoding="utf-8") == "candidate user"


def test_import_output_writes_role_specific_files(tmp_path: Path):
    artifact_root = tmp_path / "artifacts" / "llm-pdca"
    create_experiment(artifact_root, _build_manifest("exp-20260314-001"))

    import_output(
        artifact_root,
        "exp-20260314-001",
        role="candidate",
        payload={"stats": {"avg_confidence": 0.8}},
        meta=ImportedOutputMeta(provider="anthropic", model="claude-sonnet-4-5-20250929"),
    )

    outputs_dir = artifact_root / "experiments" / "exp-20260314-001" / "outputs"
    assert json.loads((outputs_dir / "candidate_output.json").read_text(encoding="utf-8"))["stats"]["avg_confidence"] == 0.8
    assert json.loads((outputs_dir / "candidate_meta.json").read_text(encoding="utf-8"))["provider"] == "anthropic"


def test_import_meta_is_optional(tmp_path: Path):
    artifact_root = tmp_path / "artifacts" / "llm-pdca"
    create_experiment(artifact_root, _build_manifest("exp-20260314-001"))

    import_output(
        artifact_root,
        "exp-20260314-001",
        role="baseline",
        payload={"stats": {"avg_confidence": 0.5}},
    )

    outputs_dir = artifact_root / "experiments" / "exp-20260314-001" / "outputs"
    assert (outputs_dir / "baseline_output.json").exists()
    assert not (outputs_dir / "baseline_meta.json").exists()
