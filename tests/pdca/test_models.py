"""Tests for PDCA experiment data models."""

import pytest
from pydantic import ValidationError

from src.pdca.models import (
    ExperimentManifest,
    ImportedOutputMeta,
    InputDocumentRef,
    LLMConfigSnapshot,
    PromptPairInfo,
    PromptSnapshot,
)


def test_experiment_manifest_requires_core_fields():
    with pytest.raises(ValidationError):
        ExperimentManifest()


def test_experiment_manifest_defaults_baseline_source_and_status():
    manifest = ExperimentManifest(
        experiment_id="exp-20260314-001",
        campaign_id="camp-20260314-001",
        target_phase=5,
        hypothesis="evidence guidance improves extraction quality",
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

    assert manifest.baseline_source == "default"
    assert manifest.status == "draft"


def test_prompt_snapshot_accepts_prompt_provenance():
    snapshot = PromptSnapshot(
        system_prompt="system text",
        user_prompt="user text",
        prompt_key="param_extractor",
        source="code_default",
    )

    assert snapshot.system_prompt == "system text"
    assert snapshot.user_prompt == "user text"
    assert snapshot.source == "code_default"


def test_imported_output_meta_allows_optional_usage_fields():
    meta = ImportedOutputMeta(
        provider="anthropic",
        model="claude-sonnet-4-5-20250929",
        notes="manual import from Claude Code",
    )

    dumped = meta.model_dump()

    assert dumped["provider"] == "anthropic"
    assert dumped["input_tokens"] is None
    assert dumped["notes"] == "manual import from Claude Code"
