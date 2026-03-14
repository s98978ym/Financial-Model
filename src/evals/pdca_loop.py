"""Reference-driven PDCA loop for comparing baseline and candidate profiles."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from .candidate_profiles import fixture_path, fixture_profiles
from .reference_workbook import ReferenceWorkbook, extract_reference_workbook
from .scoring import ScoreResult, score_candidate


@dataclass
class PDCAEvalResult:
    run_id: str
    baseline_score: float | None
    best_candidate_id: str | None
    best_candidate_score: float | None


def run_reference_pdca(
    plan_pdf: Path,
    reference_workbook: Path,
    artifact_root: Path,
    runner: str = "fixture",
) -> PDCAEvalResult:
    reference = extract_reference_workbook(reference_workbook)
    run_id = datetime.utcnow().strftime("run-%Y%m%d-%H%M%S")
    run_root = artifact_root / run_id
    (run_root / "candidates").mkdir(parents=True, exist_ok=True)

    baseline_payload = _load_runner_payload(runner, "baseline_result.json")
    baseline_score = score_candidate(reference, baseline_payload)
    candidates: Dict[str, Dict[str, Any]] = {}
    candidate_scores: Dict[str, ScoreResult] = {}

    for profile in fixture_profiles():
        payload = _load_runner_payload(profile.runner, profile.config["fixture_name"])
        candidates[profile.candidate_id] = payload
        candidate_scores[profile.candidate_id] = score_candidate(reference, payload)

    best_candidate_id = max(candidate_scores, key=lambda candidate_id: candidate_scores[candidate_id].total_score)
    best_candidate_score = candidate_scores[best_candidate_id].total_score

    _write_reference(run_root / "reference.json", reference)
    _write_json(run_root / "baseline.json", baseline_payload)
    for candidate_id, payload in candidates.items():
        _write_json(run_root / "candidates" / f"{candidate_id}.json", payload)
    _write_scores(run_root / "scores.json", baseline_score, candidate_scores)
    _write_summary(
        run_root / "summary.md",
        plan_pdf=plan_pdf,
        reference_workbook=reference_workbook,
        baseline_score=baseline_score,
        candidate_scores=candidate_scores,
        best_candidate_id=best_candidate_id,
    )

    return PDCAEvalResult(
        run_id=run_id,
        baseline_score=baseline_score.total_score,
        best_candidate_id=best_candidate_id,
        best_candidate_score=best_candidate_score,
    )


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_runner_payload(runner: str, fixture_name: str) -> Dict[str, Any]:
    if runner != "fixture":
        raise ValueError(f"Unsupported runner: {runner}")
    return json.loads(fixture_path(_repo_root(), fixture_name).read_text(encoding="utf-8"))


def _write_reference(path: Path, reference: ReferenceWorkbook) -> None:
    path.write_text(json.dumps(asdict(reference), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_scores(path: Path, baseline_score: ScoreResult, candidate_scores: Dict[str, ScoreResult]) -> None:
    payload = {
        "baseline": {
            "total_score": baseline_score.total_score,
            "layer_scores": baseline_score.layer_scores,
        },
        "candidates": {
            candidate_id: {
                "total_score": score.total_score,
                "layer_scores": score.layer_scores,
            }
            for candidate_id, score in candidate_scores.items()
        },
    }
    _write_json(path, payload)


def _write_summary(
    path: Path,
    plan_pdf: Path,
    reference_workbook: Path,
    baseline_score: ScoreResult,
    candidate_scores: Dict[str, ScoreResult],
    best_candidate_id: str,
) -> None:
    lines = [
        "# FAM Reference PDCA Summary",
        "",
        f"- Plan PDF: `{plan_pdf}`",
        f"- Reference workbook: `{reference_workbook}`",
        f"- Baseline score: `{baseline_score.total_score:.4f}`",
        "",
        "## Candidate Scores",
    ]
    for candidate_id, score in candidate_scores.items():
        lines.append(f"- `{candidate_id}`: `{score.total_score:.4f}`")
    lines.extend(
        [
            "",
            "## Recommendation",
            f"- Best candidate: `{best_candidate_id}`",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
