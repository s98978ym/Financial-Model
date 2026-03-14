"""Reference-driven PDCA loop for comparing baseline and candidate profiles."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from src.ingest.reader import read_document

from .candidate_profiles import fixture_path, fixture_profiles, live_profiles
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
    document_text = read_document(str(plan_pdf)).full_text if runner == "live" else None

    baseline_payload = _baseline_payload(plan_pdf, reference, runner, document_text=document_text)
    baseline_score = score_candidate(reference, baseline_payload)
    candidates: Dict[str, Dict[str, Any]] = {}
    candidate_scores: Dict[str, ScoreResult] = {}

    for profile in _profiles_for_runner(runner):
        payload = _candidate_payload(
            plan_pdf,
            reference,
            profile.runner,
            profile.config,
            document_text=document_text,
        )
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
        runner=runner,
    )

    return PDCAEvalResult(
        run_id=run_id,
        baseline_score=baseline_score.total_score,
        best_candidate_id=best_candidate_id,
        best_candidate_score=best_candidate_score,
    )


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _profiles_for_runner(runner: str):
    if runner == "fixture":
        return fixture_profiles()
    if runner == "live":
        return live_profiles()
    raise ValueError(f"Unsupported runner: {runner}")


def _baseline_payload(
    plan_pdf: Path,
    reference: ReferenceWorkbook,
    runner: str,
    document_text: str | None = None,
) -> Dict[str, Any]:
    if runner == "fixture":
        return _load_fixture_payload("baseline_result.json")
    if runner == "live":
        return _build_live_payload(plan_pdf, reference, mode="baseline", document_text=document_text)
    raise ValueError(f"Unsupported runner: {runner}")


def _candidate_payload(
    plan_pdf: Path,
    reference: ReferenceWorkbook,
    runner: str,
    config: Dict[str, Any],
    document_text: str | None = None,
) -> Dict[str, Any]:
    if runner == "fixture":
        return _load_fixture_payload(config["fixture_name"])
    if runner == "live":
        return _build_live_payload(plan_pdf, reference, mode=config["mode"], document_text=document_text)
    raise ValueError(f"Unsupported runner: {runner}")


def _load_fixture_payload(fixture_name: str) -> Dict[str, Any]:
    return json.loads(fixture_path(_repo_root(), fixture_name).read_text(encoding="utf-8"))


def _build_live_payload(
    plan_pdf: Path,
    reference: ReferenceWorkbook,
    mode: str,
    document_text: str | None = None,
) -> Dict[str, Any]:
    text = document_text or read_document(str(plan_pdf)).full_text
    detected_segments = _detect_segments(text)

    if mode == "baseline":
        return {
            "segments": [{"name": name, "engine_type": "custom_formula"} for name in detected_segments],
            "model_sheets": {},
            "pl_lines": {},
            "assumptions": _document_assumptions(detected_segments, approved=False),
        }

    if mode == "structure_seeded":
        return {
            "segments": [{"name": name, "engine_type": _expected_engine(name)} for name in detected_segments],
            "model_sheets": {
                name: {metric_name: [] for metric_name in reference.model_sheets.get(name, {})}
                for name in detected_segments
            },
            "pl_lines": {},
            "assumptions": _document_assumptions(detected_segments, approved=False),
        }

    if mode == "reference_seeded":
        return {
            "segments": [{"name": name, "engine_type": _expected_engine(name)} for name in detected_segments],
            "model_sheets": {name: reference.model_sheets.get(name, {}) for name in detected_segments},
            "pl_lines": reference.pl_lines,
            "assumptions": _document_assumptions(detected_segments, approved=True) + _benchmark_assumptions(reference),
        }

    raise ValueError(f"Unsupported live payload mode: {mode}")


def _detect_segments(text: str) -> list[str]:
    detected: list[str] = []
    patterns = {
        "アカデミー": [r"アカデミー", r"B級", r"A級", r"S級"],
        "コンサル": [r"コンサル", r"OJT", r"セミナー"],
        "ミール": [r"ミール", r"食事", r"栄養管理食"],
    }
    for segment_name, segment_patterns in patterns.items():
        if any(re.search(pattern, text) for pattern in segment_patterns):
            detected.append(segment_name)
    return detected


def _expected_engine(segment_name: str) -> str:
    if segment_name == "ミール":
        return "unit_economics"
    if segment_name == "アカデミー":
        return "progression"
    if segment_name == "コンサル":
        return "project_capacity"
    return "custom_formula"


def _document_assumptions(segment_names: list[str], approved: bool) -> list[dict[str, Any]]:
    return [
        {
            "source_type": "document",
            "evidence_refs": [{"source_id": f"segment:{segment_name}"}],
            "review_status": "approved" if approved else "needs_review",
        }
        for segment_name in segment_names
    ]


def _benchmark_assumptions(reference: ReferenceWorkbook) -> list[dict[str, Any]]:
    return [
        {
            "source_type": "benchmark",
            "evidence_refs": [{"source_id": f"reference:{segment_name}"}],
            "review_status": "approved",
        }
        for segment_name in reference.segment_names
    ]


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
    runner: str,
) -> None:
    lines = [
        "# FAM Reference PDCA Summary",
        "",
        f"- Plan PDF: `{plan_pdf}`",
        f"- Reference workbook: `{reference_workbook}`",
        f"- Baseline score: `{baseline_score.total_score:.4f}`",
        "",
        "## Baseline Layer Scores",
    ]
    for layer_name, layer_score in baseline_score.layer_scores.items():
        lines.append(f"- `{layer_name}`: `{layer_score:.4f}`")
    lines.extend(
        [
            "",
        "## Candidate Scores",
        ]
    )
    for candidate_id, score in candidate_scores.items():
        lines.append(f"- `{candidate_id}`: `{score.total_score:.4f}`")
        for layer_name, layer_score in score.layer_scores.items():
            lines.append(f"  - `{layer_name}`: `{layer_score:.4f}`")
    lines.extend(
        [
            "",
            "## Recommendation",
            f"- Best candidate: `{best_candidate_id}`",
        ]
    )
    if runner == "live" and best_candidate_id == "candidate-reference-seeded":
        lines.extend(
            [
                "",
                "## Note",
                "- `candidate-reference-seeded` は参照 workbook の構造と数値を seed として使う bootstrap 候補です。",
                "- これは現時点の上限比較であり、純粋に PDF だけから再現した結果ではありません。",
                "- 次の改善では、PDF 由来の抽出だけで model_sheets と PL をどこまで再現できるかを強めます。",
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
