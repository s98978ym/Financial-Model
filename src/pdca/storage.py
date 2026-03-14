"""Storage helpers for LLM PDCA artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Optional

from .models import Campaign, ExperimentManifest, ExperimentStatus


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def campaigns_root(artifact_root: Path) -> Path:
    return Path(artifact_root) / "campaigns"


def experiments_root(artifact_root: Path) -> Path:
    return Path(artifact_root) / "experiments"


def campaign_dir(artifact_root: Path, campaign_id: str) -> Path:
    return campaigns_root(artifact_root) / campaign_id


def experiment_dir(artifact_root: Path, experiment_id: str) -> Path:
    return experiments_root(artifact_root) / experiment_id


def create_campaign(artifact_root: Path, campaign: Campaign) -> Path:
    target = campaign_dir(artifact_root, campaign.campaign_id)
    target.mkdir(parents=True, exist_ok=True)
    _write_json(target / "campaign.json", campaign.model_dump())
    return target


def load_campaign(artifact_root: Path, campaign_id: str) -> Campaign:
    path = campaign_dir(artifact_root, campaign_id) / "campaign.json"
    return Campaign.model_validate_json(path.read_text(encoding="utf-8"))


def list_campaigns(artifact_root: Path) -> list[Campaign]:
    results: list[Campaign] = []
    root = campaigns_root(artifact_root)
    if not root.exists():
        return results
    for campaign_path in sorted(root.glob("*/campaign.json")):
        results.append(Campaign.model_validate_json(campaign_path.read_text(encoding="utf-8")))
    return results


def create_experiment(
    artifact_root: Path,
    manifest: ExperimentManifest,
    *,
    hypothesis_markdown: str = "",
) -> Path:
    target = experiment_dir(artifact_root, manifest.experiment_id)
    for relpath in ("inputs", "outputs", "compare"):
        (target / relpath).mkdir(parents=True, exist_ok=True)
    _write_json(target / "manifest.json", manifest.model_dump())
    (target / "hypothesis.md").write_text(hypothesis_markdown, encoding="utf-8")
    return target


def load_experiment_manifest(artifact_root: Path, experiment_id: str) -> ExperimentManifest:
    path = experiment_dir(artifact_root, experiment_id) / "manifest.json"
    return ExperimentManifest.model_validate_json(path.read_text(encoding="utf-8"))


def save_experiment_manifest(
    artifact_root: Path,
    manifest: ExperimentManifest,
) -> Path:
    path = experiment_dir(artifact_root, manifest.experiment_id) / "manifest.json"
    _write_json(path, manifest.model_dump())
    return path


def list_experiments(
    artifact_root: Path,
    *,
    status: Optional[ExperimentStatus] = None,
    campaign_id: Optional[str] = None,
) -> list[ExperimentManifest]:
    results: list[ExperimentManifest] = []
    root = experiments_root(artifact_root)
    if not root.exists():
        return results
    for manifest_path in sorted(root.glob("*/manifest.json")):
        manifest = ExperimentManifest.model_validate_json(
            manifest_path.read_text(encoding="utf-8")
        )
        if status and manifest.status != status:
            continue
        if campaign_id and manifest.campaign_id != campaign_id:
            continue
        results.append(manifest)
    return results
