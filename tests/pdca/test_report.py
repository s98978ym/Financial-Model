"""Tests for PDCA markdown report generation."""

from pathlib import Path

from src.pdca.compare import compare_experiment
from src.pdca.importer import import_output
from src.pdca.report import render_report, write_report
from src.pdca.storage import create_experiment, load_experiment_manifest
from tests.pdca.test_compare import _payload
from tests.pdca.test_storage import _build_manifest


def test_report_includes_hypothesis_and_decision_placeholders(tmp_path: Path):
    artifact_root = tmp_path / "artifacts" / "llm-pdca"
    create_experiment(artifact_root, _build_manifest("exp-20260314-001"))
    manifest = load_experiment_manifest(artifact_root, "exp-20260314-001")
    summary = {
        "phase": 5,
        "criteria_scores": {
            "extraction_count": {"baseline": 1, "candidate": 2, "delta": 1},
        },
    }

    report = render_report(manifest, summary)

    assert manifest.hypothesis in report
    assert "# 実験レポート" in report
    assert "判定: pending" in report


def test_report_includes_criteria_scores(tmp_path: Path):
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
    compare_experiment(artifact_root, "exp-20260314-001", phase=5)

    report_path = write_report(artifact_root, "exp-20260314-001")
    report = report_path.read_text(encoding="utf-8")

    assert "avg_confidence" in report
    assert "比較指標" in report
    assert "基準出力" in report
