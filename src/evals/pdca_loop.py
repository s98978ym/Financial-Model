"""Reference-driven PDCA loop for comparing baseline and candidate profiles."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable

from src.ingest.reader import read_document

from .candidate_profiles import CandidateProfile, fixture_path, fixture_profiles, live_profiles
from .reference_workbook import ReferenceWorkbook, extract_reference_workbook
from .scoring import ScoreResult, score_candidate


@dataclass
class PDCAEvalResult:
    run_id: str
    baseline_score: float | None
    best_candidate_id: str | None
    best_candidate_score: float | None


LAYER_DEFINITIONS = {
    "structure": {
        "label": "事業構造の再現度",
        "description": "ミール・アカデミー・コンサルのような事業の柱を正しく分解できているか、各柱に合う engine_type を選べているかを見る項目です。",
    },
    "model_sheets": {
        "label": "モデルシートの再現度",
        "description": "各モデルシートの主要ドライバーを、参照 workbook の数値系列にどこまで近づけられているかを見る項目です。",
    },
    "pl": {
        "label": "PL の再現度",
        "description": "PL 設計シートの主要行について、FY26-FY30 の数値系列が参照 workbook にどこまで近いかを見る項目です。",
    },
    "explainability": {
        "label": "説明責任の充足度",
        "description": "重要前提に source_type・evidence_refs・review_status が入り、役員や投資家に説明できる状態になっているかを見る項目です。",
    },
}


def run_reference_pdca(
    plan_pdf: Path,
    reference_workbook: Path,
    artifact_root: Path,
    runner: str = "fixture",
) -> PDCAEvalResult:
    reference = extract_reference_workbook(reference_workbook)
    profiles = list(_profiles_for_runner(runner))
    run_id = datetime.utcnow().strftime("run-%Y%m%d-%H%M%S")
    run_root = artifact_root / run_id
    (run_root / "candidates").mkdir(parents=True, exist_ok=True)
    document_text = read_document(str(plan_pdf)).full_text if runner == "live" else None

    baseline_payload = _baseline_payload(plan_pdf, reference, runner, document_text=document_text)
    baseline_score = score_candidate(reference, baseline_payload)
    candidates: Dict[str, Dict[str, Any]] = {}
    candidate_scores: Dict[str, ScoreResult] = {}

    for profile in profiles:
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
        profiles=profiles,
    )

    return PDCAEvalResult(
        run_id=run_id,
        baseline_score=baseline_score.total_score,
        best_candidate_id=best_candidate_id,
        best_candidate_score=best_candidate_score,
    )


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _profiles_for_runner(runner: str) -> Iterable[CandidateProfile]:
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
        "layer_definitions": LAYER_DEFINITIONS,
        "baseline": {
            "total_score": baseline_score.total_score,
            "layer_scores": baseline_score.layer_scores,
        },
        "candidates": {
            candidate_id: {
                "total_score": score.total_score,
                "delta_vs_baseline": round(score.total_score - baseline_score.total_score, 4),
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
    profiles: Iterable[CandidateProfile],
) -> None:
    profile_map = {profile.candidate_id: profile for profile in profiles}
    practical_best_id, practical_best_score = _select_practical_best(candidate_scores)
    practical_delta = None
    if practical_best_id and practical_best_score is not None:
        practical_delta = round(practical_best_score.total_score - baseline_score.total_score, 4)

    lines = [
        "# FAM 参照 PDCA サマリー",
        "",
        f"- Plan PDF: `{plan_pdf}`",
        f"- Reference workbook: `{reference_workbook}`",
        "",
        "## 評価項目の説明",
    ]
    for layer_name, metadata in LAYER_DEFINITIONS.items():
        lines.append(f"- `{layer_name}` ({metadata['label']}): {metadata['description']}")

    lines.extend(
        [
            "",
            "## 総合評価",
            f"- Baseline: `{baseline_score.total_score:.4f}`",
            f"  - 解釈: {_overall_interpretation(baseline_score.total_score, 'baseline')}",
        ]
    )
    if practical_best_id and practical_best_score is not None and practical_delta is not None:
        lines.extend(
            [
                f"- 実務上の改善候補: `{practical_best_id}` = `{practical_best_score.total_score:.4f}` (`{practical_delta:+.4f}` vs baseline)",
                f"  - 解釈: {_overall_interpretation(practical_best_score.total_score, practical_best_id)}",
            ]
        )
    best_delta = round(candidate_scores[best_candidate_id].total_score - baseline_score.total_score, 4)
    lines.extend(
        [
            f"- 最高スコア候補: `{best_candidate_id}` = `{candidate_scores[best_candidate_id].total_score:.4f}` (`{best_delta:+.4f}` vs baseline)",
            f"  - 解釈: {_overall_interpretation(candidate_scores[best_candidate_id].total_score, best_candidate_id)}",
        ]
    )
    if _is_upper_bound_candidate(best_candidate_id):
        lines.append(
            "  - 注記: この候補は参照 workbook を seed とした上限比較なので、純粋に PDF だけから再現した結果ではありません。"
        )

    lines.extend(
        [
            "",
            "## 個別評価",
            "### baseline",
            f"- 総合スコア: `{baseline_score.total_score:.4f}`",
            f"- 解釈: {_overall_interpretation(baseline_score.total_score, 'baseline')}",
        ]
    )
    lines.extend(_layer_detail_lines(baseline_score))

    for candidate_id, score in candidate_scores.items():
        delta = round(score.total_score - baseline_score.total_score, 4)
        lines.extend(
            [
                "",
                f"### {candidate_id}",
                f"- 総合スコア: `{score.total_score:.4f}` (`{delta:+.4f}` vs baseline)",
                f"- 解釈: {_overall_interpretation(score.total_score, candidate_id)}",
            ]
        )
        if candidate_id in profile_map:
            lines.append(f"- 候補の意味: {profile_map[candidate_id].label}")
        if _is_upper_bound_candidate(candidate_id):
            lines.append("- 注記: 参照 workbook を seed とした上限比較です。")
        lines.extend(_layer_detail_lines(score))

    lines.extend(
        [
            "",
            "## 検証した仮説",
            f"- baseline: {_baseline_hypothesis(runner)}",
        ]
    )
    for profile in profiles:
        lines.append(f"- {profile.candidate_id}: {_candidate_hypothesis(profile, runner)}")

    lines.extend(
        [
            "",
            "## 結果",
            f"- baseline: {_overall_interpretation(baseline_score.total_score, 'baseline')}",
        ]
    )
    for candidate_id, score in candidate_scores.items():
        lines.append(
            f"- {candidate_id}: {_candidate_result(candidate_id, score, baseline_score)}"
        )

    lines.extend(
        [
            "",
            "## 課題",
        ]
    )
    lines.extend(f"- {issue}" for issue in _issues(candidate_scores, baseline_score))

    lines.extend(
        [
            "",
            "## 改善内容",
        ]
    )
    lines.extend(f"- {improvement}" for improvement in _improvements(profiles, runner))

    lines.extend(
        [
            "",
            "## 次の方針",
        ]
    )
    lines.extend(f"- {direction}" for direction in _next_directions(candidate_scores, runner))

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _layer_detail_lines(score: ScoreResult) -> list[str]:
    lines: list[str] = []
    for layer_name, layer_score in score.layer_scores.items():
        metadata = LAYER_DEFINITIONS[layer_name]
        lines.extend(
            [
                f"- `{layer_name}`: `{layer_score:.4f}`",
                f"  - 説明: {metadata['description']}",
                f"  - 解釈: {_layer_interpretation(layer_name, layer_score)}",
            ]
        )
    return lines


def _layer_interpretation(layer_name: str, layer_score: float) -> str:
    if layer_name == "structure":
        if layer_score >= 0.8:
            return "事業の柱と engine_type の解釈はかなり参照に近いです。"
        if layer_score >= 0.4:
            return "事業の柱はかなり掴めていますが、engine の解釈や抜け漏れがまだ残っています。"
        return "事業の柱や engine_type の解釈がまだ参照から大きく外れています。"
    if layer_name == "model_sheets":
        if layer_score >= 0.8:
            return "モデルシートの主要ドライバーをかなり再現できています。"
        if layer_score >= 0.4:
            return "一部のモデルシート指標は近づいていますが、まだズレが大きいです。"
        return "モデルシートの主要ドライバーはまだほとんど再現できていません。"
    if layer_name == "pl":
        if layer_score >= 0.8:
            return "PL の主要行はかなり参照に近いです。"
        if layer_score >= 0.4:
            return "PL の方向感は出ていますが、主要行の数値はまだ粗いです。"
        return "PL の主要行はまだ参照に近づいていません。"
    if layer_name == "explainability":
        if layer_score >= 0.8:
            return "重要前提の根拠と承認状態がかなり整理されていて、説明責任に強い状態です。"
        if layer_score >= 0.4:
            return "根拠の型はありますが、承認済み前提や evidence の厚みがまだ足りません。"
        return "根拠や承認状態の記録が不足していて、説明責任はまだ弱いです。"
    return "この項目の解釈は未定義です。"


def _overall_interpretation(total_score: float, candidate_id: str) -> str:
    if _is_upper_bound_candidate(candidate_id):
        return "参照 workbook を seed にした理想上限としては満点で、現行評価器は正解セットを識別できています。"
    if total_score >= 0.8:
        return "参照 workbook にかなり近く、モデルシートと PL の両方で高い再現度が出ています。"
    if total_score >= 0.5:
        return "方向性はかなり合っていますが、モデルシートか PL のどちらかにまだ目立つ差があります。"
    if total_score >= 0.3:
        return "構造理解には前進がありますが、モデルシートや PL の再現はまだ弱い段階です。"
    return "現状は PDF からの再現力が低く、事業構造の理解と数値生成の両方に改善余地があります。"


def _is_upper_bound_candidate(candidate_id: str) -> bool:
    return candidate_id == "candidate-reference-seeded"


def _baseline_hypothesis(runner: str) -> str:
    if runner == "live":
        return "PDF だけから事業構造・モデルシート・PL をどこまで再現できるかを確認する。"
    return "fixture の基準データだけで、評価器と比較ロジックが期待通りに動くかを確認する。"


def _candidate_hypothesis(profile: CandidateProfile, runner: str) -> str:
    if runner == "live":
        if profile.candidate_id == "candidate-structure-seeded":
            return "ミール・アカデミー・コンサルの segment と engine_type を先に与えると、構造再現が改善するはず。"
        if profile.candidate_id == "candidate-reference-seeded":
            return "参照 workbook のモデルシートと PL を seed にすると、現時点の上限再現度を測れるはず。"
    return f"{profile.label} が baseline より高いスコアを取れるかを確認する。"


def _candidate_result(candidate_id: str, score: ScoreResult, baseline_score: ScoreResult) -> str:
    delta = round(score.total_score - baseline_score.total_score, 4)
    delta_text = f"{delta:+.4f}"
    if _is_upper_bound_candidate(candidate_id):
        return (
            f"総合スコアは `{score.total_score:.4f}` ({delta_text} vs baseline)。"
            " 参照 workbook を seed にすると満点まで到達できるので、評価器の上限比較としては有効です。"
        )
    return (
        f"総合スコアは `{score.total_score:.4f}` ({delta_text} vs baseline)。"
        f" 主な解釈は「{_overall_interpretation(score.total_score, candidate_id)}」です。"
    )


def _select_practical_best(candidate_scores: Dict[str, ScoreResult]) -> tuple[str | None, ScoreResult | None]:
    practical_scores = {
        candidate_id: score
        for candidate_id, score in candidate_scores.items()
        if not _is_upper_bound_candidate(candidate_id)
    }
    if not practical_scores:
        return None, None
    candidate_id = max(practical_scores, key=lambda item: practical_scores[item].total_score)
    return candidate_id, practical_scores[candidate_id]


def _issues(candidate_scores: Dict[str, ScoreResult], baseline_score: ScoreResult) -> list[str]:
    practical_best_id, practical_best_score = _select_practical_best(candidate_scores)
    focus_score = practical_best_score or baseline_score
    issues: list[str] = []
    if focus_score.layer_scores.get("model_sheets", 0.0) < 0.2:
        issues.append("PDF 由来の情報だけでは、モデルシートの主要ドライバーをまだほとんど再現できていません。")
    if focus_score.layer_scores.get("pl", 0.0) < 0.2:
        issues.append("PL の主要行はまだ参照 workbook に近づいておらず、構造理解が数値生成につながっていません。")
    if focus_score.layer_scores.get("explainability", 0.0) < 0.8:
        issues.append("前提の根拠と承認状態は型としてはありますが、board-ready と言えるほど十分には埋まっていません。")
    if practical_best_id and practical_best_score and practical_best_score.layer_scores.get("structure", 0.0) >= 0.8:
        issues.append("構造理解の改善がモデルシート再現と PL 再現にまだ波及していないため、構造と数値生成の橋渡しが必要です。")
    return issues or ["現時点で目立つ課題は検出されませんでした。"]


def _improvements(profiles: Iterable[CandidateProfile], runner: str) -> list[str]:
    improvements: list[str] = []
    if runner == "live":
        improvements.append("baseline では PDF だけを使い、現状の再現力をそのまま測りました。")
        for profile in profiles:
            if profile.candidate_id == "candidate-structure-seeded":
                improvements.append("事業の柱と engine_type を seed して、構造理解だけを先に押し上げる候補を追加しました。")
            elif profile.candidate_id == "candidate-reference-seeded":
                improvements.append("参照 workbook の model_sheets と PL を seed して、現時点の理論上限を測る候補を追加しました。")
        return improvements

    improvements.append("fixture データで baseline と candidate の差を比較し、評価器と summary 生成の整合性を確認しました。")
    return improvements


def _next_directions(candidate_scores: Dict[str, ScoreResult], runner: str) -> list[str]:
    directions: list[str] = []
    if runner == "live":
        directions.append("次は PDF からモデルシートの driver 候補を直接抽出し、`model_sheets` スコアを先に引き上げます。")
        directions.append("その driver を canonical model と engine 計算に通して、`pl` スコアが上がるかを確認します。")
        directions.append("重要前提ごとに evidence と review_status を増やして、`explainability` を board-ready 寄りに改善します。")
        if any(_is_upper_bound_candidate(candidate_id) for candidate_id in candidate_scores):
            directions.append("`candidate-reference-seeded` は上限比較として維持しつつ、採用判断は PDF 由来候補だけで行うようにします。")
        return directions

    directions.append("live runner で同じ summary 形式を維持しながら、FAM 実データで仮説の改善量を追えるようにします。")
    return directions
