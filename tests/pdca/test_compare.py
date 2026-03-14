"""Tests for Phase 5 comparison logic."""

import json
from pathlib import Path

from src.pdca.compare import compare_experiment, compare_phase5_payloads
from src.pdca.importer import import_output
from src.pdca.storage import create_experiment
from tests.pdca.test_storage import _build_manifest


def _payload(extractions):
    return {
        "extractions": extractions,
        "warnings": [],
    }


def test_phase5_compare_computes_expected_criteria_scores():
    baseline = _payload(
        [
            {
                "sheet": "PL",
                "cell": "C5",
                "label": "月間顧客数",
                "concept": "月間顧客数",
                "value": 100,
                "confidence": 0.4,
                "period": "FY1",
            }
        ]
    )
    candidate = _payload(
        [
            {
                "sheet": "PL",
                "cell": "C5",
                "label": "月間顧客数",
                "concept": "月間顧客数",
                "value": 100,
                "confidence": 0.8,
                "period": "FY1",
            },
            {
                "sheet": "PL",
                "cell": "D5",
                "label": "月間顧客数",
                "concept": "月間顧客数",
                "value": 180,
                "confidence": 0.7,
                "period": "FY2",
            },
        ]
    )

    summary = compare_phase5_payloads(baseline, candidate)

    assert summary["criteria_scores"]["extraction_count"]["baseline"] == 1
    assert summary["criteria_scores"]["extraction_count"]["candidate"] == 2
    assert summary["criteria_scores"]["avg_confidence"]["candidate"] == 0.75
    assert summary["criteria_scores"]["mapped_target_rate"]["candidate"] == 1.0


def test_compare_flags_invalid_json():
    summary = compare_phase5_payloads([], {"extractions": []})

    assert summary["criteria_scores"]["json_validity"]["baseline"] is False
    assert summary["criteria_scores"]["json_validity"]["candidate"] is True


def test_compare_writes_summary_payload(tmp_path: Path):
    artifact_root = tmp_path / "artifacts" / "llm-pdca"
    create_experiment(artifact_root, _build_manifest("exp-20260314-001"))
    import_output(
        artifact_root,
        "exp-20260314-001",
        role="baseline",
        payload=_payload(
            [
                {
                    "sheet": "PL",
                    "cell": "C5",
                    "label": "月間顧客数",
                    "concept": "月間顧客数",
                    "value": 100,
                    "confidence": 0.4,
                    "period": "FY1",
                }
            ]
        ),
    )
    import_output(
        artifact_root,
        "exp-20260314-001",
        role="candidate",
        payload=_payload(
            [
                {
                    "sheet": "PL",
                    "cell": "C5",
                    "label": "月間顧客数",
                    "concept": "月間顧客数",
                    "value": 100,
                    "confidence": 0.8,
                    "period": "FY1",
                }
            ]
        ),
    )

    summary = compare_experiment(artifact_root, "exp-20260314-001", phase=5)
    compare_dir = artifact_root / "experiments" / "exp-20260314-001" / "compare"

    assert (compare_dir / "summary.json").exists()
    assert (compare_dir / "diff.md").exists()
    assert summary["phase"] == 5
    assert json.loads((compare_dir / "summary.json").read_text(encoding="utf-8"))["phase"] == 5
