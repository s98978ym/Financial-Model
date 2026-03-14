"""CLI smoke tests for PDCA command handlers."""

import json
from pathlib import Path

from src.cli.main import (
    pdca_campaign_create,
    pdca_import_output_command,
    pdca_init,
)


def test_pdca_init_creates_experiment_artifacts(tmp_path: Path):
    artifact_root = tmp_path / "artifacts" / "llm-pdca"

    campaign = pdca_campaign_create(
        artifact_root=str(artifact_root),
        campaign_id="camp-20260314-001",
        name="Phase 5 quality",
        phase=5,
    )
    assert campaign.endswith("campaign.json")

    result = pdca_init(
        artifact_root=str(artifact_root),
        experiment_id="exp-20260314-001",
        campaign_id="camp-20260314-001",
        phase=5,
        hypothesis="evidence guidance improves extraction quality",
    )

    assert result.endswith("manifest.json")
    manifest = artifact_root / "experiments" / "exp-20260314-001" / "manifest.json"
    assert manifest.exists()


def test_pdca_import_output_writes_candidate_files(tmp_path: Path):
    artifact_root = tmp_path / "artifacts" / "llm-pdca"
    payload_path = tmp_path / "candidate.json"
    payload_path.write_text(json.dumps({"extractions": [], "warnings": []}), encoding="utf-8")

    pdca_campaign_create(
        artifact_root=str(artifact_root),
        campaign_id="camp-20260314-001",
        name="Phase 5 quality",
        phase=5,
    )
    pdca_init(
        artifact_root=str(artifact_root),
        experiment_id="exp-20260314-001",
        campaign_id="camp-20260314-001",
        phase=5,
        hypothesis="evidence guidance improves extraction quality",
    )

    result = pdca_import_output_command(
        artifact_root=str(artifact_root),
        experiment_id="exp-20260314-001",
        role="candidate",
        payload_file=str(payload_path),
    )

    assert result.endswith("candidate_output.json")
    output_path = artifact_root / "experiments" / "exp-20260314-001" / "outputs" / "candidate_output.json"
    assert output_path.exists()
