"""Tests for PDCA artifact storage."""

from pathlib import Path

from src.pdca.models import (
    Campaign,
    ExperimentManifest,
    InputDocumentRef,
    LLMConfigSnapshot,
    PromptPairInfo,
)
from src.pdca.storage import create_campaign, create_experiment, list_experiments


def _build_manifest(experiment_id: str, status: str = "draft") -> ExperimentManifest:
    return ExperimentManifest(
        experiment_id=experiment_id,
        campaign_id="camp-20260314-001",
        target_phase=5,
        hypothesis="evidence wording improves extraction quality",
        status=status,
        llm_config=LLMConfigSnapshot(
            provider="anthropic",
            model="claude-sonnet-4-5-20250929",
            temperature=0.1,
            max_tokens=32768,
        ),
        prompt_pair=PromptPairInfo(
            system_key="param_extractor_system",
            user_key="param_extractor_user",
            changed="system",
        ),
        input_document=InputDocumentRef(
            project_id="project-1",
            document_hash="sha256:abc123",
            filename="sample.pdf",
        ),
    )


def test_create_campaign_writes_campaign_json(tmp_path: Path):
    artifact_root = tmp_path / "artifacts" / "llm-pdca"
    campaign = Campaign(
        campaign_id="camp-20260314-001",
        name="Phase 5 accuracy",
        target_phase=5,
        goal="Improve extraction quality",
    )

    campaign_dir = create_campaign(artifact_root, campaign)

    assert (campaign_dir / "campaign.json").exists()


def test_create_experiment_writes_manifest_and_hypothesis(tmp_path: Path):
    artifact_root = tmp_path / "artifacts" / "llm-pdca"
    manifest = _build_manifest("exp-20260314-001")

    experiment_dir = create_experiment(
        artifact_root,
        manifest,
        hypothesis_markdown="# Hypothesis\n\nTest change.",
    )

    assert (experiment_dir / "manifest.json").exists()
    assert (experiment_dir / "hypothesis.md").exists()
    assert (experiment_dir / "inputs").is_dir()
    assert (experiment_dir / "outputs").is_dir()
    assert (experiment_dir / "compare").is_dir()


def test_list_experiments_filters_by_status(tmp_path: Path):
    artifact_root = tmp_path / "artifacts" / "llm-pdca"
    create_experiment(artifact_root, _build_manifest("exp-20260314-001", status="draft"))
    create_experiment(artifact_root, _build_manifest("exp-20260314-002", status="completed"))

    listed = list_experiments(artifact_root, status="completed")

    assert [item.experiment_id for item in listed] == ["exp-20260314-002"]
