from pathlib import Path

import subprocess
import sys

from src.evals.pdca_loop import run_reference_pdca


def test_run_reference_pdca_selects_highest_scoring_candidate(tmp_path) -> None:
    result = run_reference_pdca(
        plan_pdf=Path("/tmp/fake.pdf"),
        reference_workbook=Path("tests/fixtures/evals/reference_workbook_minimal.xlsx"),
        artifact_root=tmp_path,
        runner="fixture",
    )

    assert result.best_candidate_id == "candidate-better"
    assert (tmp_path / result.run_id / "summary.md").exists()


def test_run_reference_pdca_writes_scores_and_summary(tmp_path) -> None:
    result = run_reference_pdca(
        plan_pdf=Path("/tmp/fake.pdf"),
        reference_workbook=Path("tests/fixtures/evals/reference_workbook_minimal.xlsx"),
        artifact_root=tmp_path,
        runner="fixture",
    )

    assert (tmp_path / result.run_id / "scores.json").exists()
    assert result.baseline_score is not None


def test_fam_reference_cli_writes_artifacts(tmp_path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.cli.main",
            "eval",
            "fam-reference",
            "--plan-pdf",
            "/tmp/fake.pdf",
            "--reference-workbook",
            "tests/fixtures/evals/reference_workbook_minimal.xlsx",
            "--artifact-root",
            str(tmp_path),
            "--runner",
            "fixture",
        ],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "best_candidate_id" in result.stdout
