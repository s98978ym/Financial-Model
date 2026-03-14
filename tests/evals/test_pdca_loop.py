from pathlib import Path

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
