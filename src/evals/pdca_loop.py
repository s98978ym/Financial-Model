"""Reference-driven PDCA loop for comparing baseline and candidate profiles."""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable

from src.ingest.reader import read_document

from .candidate_profiles import CandidateProfile, fixture_path, fixture_profiles, live_profiles
from .diagnosis import build_candidate_diagnosis
from .external_analysis import build_external_analysis_candidate
from .pdf_signals import extract_academy_signals, extract_meal_signals, extract_pl_signals
from .reference_workbook import ReferenceWorkbook, extract_reference_workbook
from .scoring import ScoreResult, score_candidate
from .workbook_export import export_candidate_workbook


@dataclass
class PDCAEvalResult:
    run_id: str
    baseline_score: float | None
    best_candidate_id: str | None
    best_candidate_score: float | None
    best_practical_candidate_id: str | None


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
    profiles: Iterable[CandidateProfile] | None = None,
    baseline_mode: str | None = None,
) -> PDCAEvalResult:
    reference = extract_reference_workbook(reference_workbook)
    profiles = list(profiles) if profiles is not None else list(_profiles_for_runner(runner))
    run_id = datetime.utcnow().strftime("run-%Y%m%d-%H%M%S")
    run_root = artifact_root / run_id
    (run_root / "candidates").mkdir(parents=True, exist_ok=True)
    document_text = read_document(str(plan_pdf)).full_text if runner == "live" else None

    baseline_payload = _baseline_payload(
        plan_pdf,
        reference,
        runner,
        document_text=document_text,
        baseline_mode=baseline_mode,
    )
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
    diagnoses = _candidate_diagnoses(
        baseline_score=baseline_score,
        candidate_scores=candidate_scores,
        profiles=profiles,
        candidates=candidates,
    )

    _write_reference(run_root / "reference.json", reference)
    _write_json(run_root / "baseline.json", baseline_payload)
    for candidate_id, payload in candidates.items():
        _write_json(run_root / "candidates" / f"{candidate_id}.json", payload)
    _write_scores(run_root / "scores.json", baseline_score, candidate_scores)
    _write_diagnosis(
        run_root / "diagnosis.json",
        baseline_score=baseline_score,
        diagnoses=diagnoses,
    )
    export_paths = _write_workbook_exports(
        run_root=run_root,
        baseline_payload=baseline_payload,
        baseline_score=baseline_score,
        candidate_scores=candidate_scores,
        candidates=candidates,
        diagnoses=diagnoses,
        best_candidate_id=best_candidate_id,
    )
    _write_summary(
        run_root / "summary.md",
        plan_pdf=plan_pdf,
        reference_workbook=reference_workbook,
        baseline_score=baseline_score,
        candidate_scores=candidate_scores,
        best_candidate_id=best_candidate_id,
        runner=runner,
        profiles=profiles,
        candidates=candidates,
        diagnoses=diagnoses,
        export_paths=export_paths,
    )

    return PDCAEvalResult(
        run_id=run_id,
        baseline_score=baseline_score.total_score,
        best_candidate_id=best_candidate_id,
        best_candidate_score=best_candidate_score,
        best_practical_candidate_id=export_paths["best_practical_candidate_id"],
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
    baseline_mode: str | None = None,
) -> Dict[str, Any]:
    if runner == "fixture":
        fixture_name = baseline_mode or "baseline_result.json"
        return _load_fixture_payload(fixture_name)
    if runner == "live":
        return _build_live_payload(plan_pdf, reference, mode=baseline_mode or "baseline", document_text=document_text)
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

    if mode == "structure_pl_extracted":
        pl_lines = extract_pl_signals(text)
        return {
            "segments": [{"name": name, "engine_type": _expected_engine(name)} for name in detected_segments],
            "model_sheets": {
                name: {metric_name: [] for metric_name in reference.model_sheets.get(name, {})}
                for name in detected_segments
            },
            "pl_lines": pl_lines,
            "assumptions": _document_assumptions(detected_segments, approved=False)
            + _line_item_assumptions(pl_lines),
        }

    if mode == "structure_model_pl_extracted":
        pl_lines = extract_pl_signals(text)
        academy_signals = extract_academy_signals(text)
        return {
            "segments": [{"name": name, "engine_type": _expected_engine(name)} for name in detected_segments],
            "model_sheets": {
                "アカデミー": academy_signals,
                **{
                    name: {metric_name: [] for metric_name in reference.model_sheets.get(name, {})}
                    for name in detected_segments
                    if name != "アカデミー"
                },
            },
            "pl_lines": pl_lines,
            "assumptions": _document_assumptions(detected_segments, approved=False)
            + _line_item_assumptions(pl_lines)
            + _model_signal_assumptions("アカデミー", academy_signals),
        }

    if mode == "integrated_derived":
        pl_lines = extract_pl_signals(text)
        academy_signals = extract_academy_signals(text)
        meal_signals = extract_meal_signals(text)
        consulting_signals = _consulting_benchmark_signals(pl_lines)
        return {
            "segments": [{"name": name, "engine_type": _expected_engine(name)} for name in detected_segments],
            "model_sheets": {
                "アカデミー": academy_signals,
                "ミール": meal_signals,
                "コンサル": consulting_signals,
            },
            "pl_lines": pl_lines,
            "assumptions": _document_assumptions(detected_segments, approved=False)
            + _line_item_assumptions(pl_lines)
            + _model_signal_assumptions("アカデミー", academy_signals)
            + _model_signal_assumptions("ミール", meal_signals)
            + _benchmark_model_assumptions("コンサル", consulting_signals),
        }

    if mode in {
        "industry_analysis",
        "competitor_analysis",
        "trend_analysis",
        "public_market_analysis",
        "industry_price_portion",
        "industry_meal_frequency",
        "industry_retention",
        "combined_industry_public_market",
        "combined_industry_trend",
        "combined_industry_trend_public_market",
        "workforce_development_cost_analysis",
        "marketing_cost_analysis",
        "operating_model_analysis",
        "workforce_internal_unit_cost",
        "workforce_external_unit_cost",
        "workforce_effort_mix",
        "combined_cost_workforce_marketing",
        "combined_cost_workforce_operating",
        "combined_cost_operating_model",
        "branding_lift_analysis",
        "marketing_efficiency_analysis",
        "sales_efficiency_analysis",
        "partner_strategy_analysis",
        "staged_acceleration_analysis",
        "validation_period_analysis",
        "acceleration_period_analysis",
        "gated_acceleration_analysis",
        "combined_staged_sales",
        "combined_staged_partner",
        "combined_staged_branding",
    }:
        base_mode = "integrated_derived"
        if mode in {
            "workforce_development_cost_analysis",
            "marketing_cost_analysis",
            "operating_model_analysis",
            "workforce_internal_unit_cost",
            "workforce_external_unit_cost",
            "workforce_effort_mix",
            "combined_cost_workforce_marketing",
            "combined_cost_workforce_operating",
            "combined_cost_operating_model",
        }:
            base_mode = "combined_industry_trend_public_market"
        if mode in {
            "branding_lift_analysis",
            "marketing_efficiency_analysis",
            "sales_efficiency_analysis",
            "partner_strategy_analysis",
            "staged_acceleration_analysis",
            "validation_period_analysis",
            "acceleration_period_analysis",
            "gated_acceleration_analysis",
            "combined_staged_sales",
            "combined_staged_partner",
            "combined_staged_branding",
        }:
            base_mode = "combined_cost_operating_model"
        analysis_payload = _build_live_payload(plan_pdf, reference, mode=base_mode, document_text=text)
        return build_external_analysis_candidate(
            analysis_id=mode,
            base_candidate=analysis_payload,
            reference=reference,
            enrich_live_sources=_live_source_fetch_enabled(),
        )

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


def _live_source_fetch_enabled() -> bool:
    return os.getenv("FAM_FETCH_LIVE_SOURCES", "").lower() in {"1", "true", "yes"}


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


def _line_item_assumptions(pl_lines: Dict[str, list[float]]) -> list[dict[str, Any]]:
    return [
        {
            "source_type": "document",
            "evidence_refs": [{"source_id": f"pl:{label}"}],
            "review_status": "approved",
        }
        for label, series in pl_lines.items()
        if series
    ]


def _model_signal_assumptions(segment_name: str, model_signals: Dict[str, list[float]]) -> list[dict[str, Any]]:
    return [
        {
            "source_type": "document",
            "evidence_refs": [{"source_id": f"model:{segment_name}:{metric_name}"}],
            "review_status": "approved",
        }
        for metric_name, series in model_signals.items()
        if series
    ]


def _benchmark_model_assumptions(segment_name: str, model_signals: Dict[str, list[float]]) -> list[dict[str, Any]]:
    return [
        {
            "source_type": "benchmark",
            "evidence_refs": [{"source_id": f"benchmark:{segment_name}:{metric_name}"}],
            "review_status": "approved",
        }
        for metric_name, series in model_signals.items()
        if series
    ]


def _consulting_benchmark_signals(pl_lines: Dict[str, list[float]]) -> Dict[str, list[float]]:
    first_revenue = pl_lines.get("売上", [0.0])[0] if pl_lines.get("売上") else 0.0
    per_team_price = round(first_revenue / 3, 4) if first_revenue else 15_000_000.0
    return {
        "sku_unit_price": [per_team_price],
        "sku_retention": [0.6],
    }


def _write_reference(path: Path, reference: ReferenceWorkbook) -> None:
    path.write_text(json.dumps(asdict(reference), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_scores(path: Path, baseline_score: ScoreResult, candidate_scores: Dict[str, ScoreResult]) -> None:
    ranked_candidate_ids = _ranked_candidate_ids(candidate_scores)
    payload = {
        "layer_definitions": LAYER_DEFINITIONS,
        "baseline": {
            "total_score": baseline_score.total_score,
            "layer_scores": baseline_score.layer_scores,
            "layer_deltas": {
                layer_name: 0.0 for layer_name in baseline_score.layer_scores
            },
            "rank": 0,
            "is_upper_bound": False,
            "is_practical_candidate": False,
        },
        "candidates": {
            candidate_id: {
                "total_score": score.total_score,
                "delta_vs_baseline": round(score.total_score - baseline_score.total_score, 4),
                "layer_scores": score.layer_scores,
                "layer_deltas": _layer_deltas(score, baseline_score),
                "rank": ranked_candidate_ids.index(candidate_id) + 1,
                "is_upper_bound": _is_upper_bound_candidate(candidate_id),
                "is_practical_candidate": not _is_upper_bound_candidate(candidate_id),
            }
            for candidate_id, score in candidate_scores.items()
        },
    }
    _write_json(path, payload)


def _write_diagnosis(
    path: Path,
    *,
    baseline_score: ScoreResult,
    diagnoses: Dict[str, Dict[str, Any]],
) -> None:
    payload = {
        "baseline": {
            "total_score": baseline_score.total_score,
            "layer_scores": baseline_score.layer_scores,
        },
        "candidates": diagnoses,
    }
    _write_json(path, payload)


def _candidate_diagnoses(
    *,
    baseline_score: ScoreResult,
    candidate_scores: Dict[str, ScoreResult],
    profiles: Iterable[CandidateProfile],
    candidates: Dict[str, Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    profile_map = {profile.candidate_id: profile for profile in profiles}
    diagnoses: Dict[str, Dict[str, Any]] = {}
    for candidate_id, score in candidate_scores.items():
        profile = profile_map.get(candidate_id)
        if profile is None:
            continue
        diagnoses[candidate_id] = build_candidate_diagnosis(
            profile,
            score,
            baseline_score,
            evidence_summary=_evidence_summary(candidates.get(candidate_id, {})),
        )
    return diagnoses


def _write_summary(
    path: Path,
    plan_pdf: Path,
    reference_workbook: Path,
    baseline_score: ScoreResult,
    candidate_scores: Dict[str, ScoreResult],
    best_candidate_id: str,
    runner: str,
    profiles: Iterable[CandidateProfile],
    candidates: Dict[str, Dict[str, Any]],
    diagnoses: Dict[str, Dict[str, Any]],
    export_paths: Dict[str, Path],
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
        "## Workbook Artifacts",
        f"- baseline workbook: `{export_paths['baseline']}`",
        f"- best practical workbook: `{export_paths['best_practical']}`",
        "",
        "## 評価項目の説明",
    ]
    for layer_name, metadata in LAYER_DEFINITIONS.items():
        lines.append(f"- `{layer_name}` ({metadata['label']}): {metadata['description']}")

    lines.extend(
        [
            "",
            "## スコア推移グラフ",
            "```text",
        ]
    )
    lines.extend(_score_graph_lines(baseline_score, candidate_scores, profiles))
    lines.extend(["```"])

    lines.extend(
        [
            "",
            "## 施策・効果・課題",
            "| 候補 | 施策 | 効果 | 残課題 |",
            "|---|---|---|---|",
        ]
    )
    lines.extend(_initiative_table_lines(baseline_score, candidate_scores, profiles))

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
            "## 仮説内容",
            f"- baseline: {_baseline_hypothesis(runner)}",
        ]
    )
    for profile in profiles:
        lines.extend(
            [
                f"### {profile.candidate_id}",
                f"- タイトル: {profile.hypothesis_title or profile.label}",
                f"- 仮説: {profile.hypothesis_detail or _candidate_hypothesis(profile, runner)}",
                f"- ON: {', '.join(profile.toggles_on) if profile.toggles_on else '-'}",
                f"- OFF: {', '.join(profile.toggles_off) if profile.toggles_off else '-'}",
                f"- 期待効果: {_format_expected_impacts(profile.expected_impacts)}",
            ]
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
            "## 仮説検証結果",
        ]
    )
    for candidate_id, diagnosis in diagnoses.items():
        lines.extend(
            [
                f"### {candidate_id}",
                f"- 判定: {_verdict_label(diagnosis['verdict']['status'])}",
                f"- 理由: {diagnosis['verdict']['reason']}",
                f"- 差分: {_format_layer_deltas(diagnosis['score']['layers'])}",
            ]
        )

    lines.extend(
        [
            "",
            "## ロジック",
        ]
    )
    for candidate_id, diagnosis in diagnoses.items():
        lines.append(f"### {candidate_id}")
        if diagnosis["logic"]["steps"]:
            lines.extend(f"- {step}" for step in diagnosis["logic"]["steps"])
        else:
            lines.append("- ロジックの追加説明はありません。")

    lines.extend(
        [
            "",
            "## 根拠ファクトとデータ",
        ]
    )
    for candidate_id, diagnosis in diagnoses.items():
        evidence = diagnosis["evidence"]
        lines.extend(
            [
                f"### {candidate_id}",
                f"- source_types: {', '.join(evidence.get('source_types', [])) or '-'}",
                f"- PDF facts: {_format_evidence_list(evidence.get('pdf_facts', []))}",
                f"- External: {_format_external_sources(evidence.get('external_sources', []))}",
                f"- Benchmark fills: {_format_evidence_list(evidence.get('benchmark_fills', []))}",
                f"- Seed notes: {_format_evidence_list(evidence.get('seed_notes', []))}",
            ]
        )

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
            "## 次の改善施策",
        ]
    )
    for candidate_id, diagnosis in diagnoses.items():
        lines.append(f"### {candidate_id}")
        if diagnosis.get("next_actions"):
            lines.extend(f"- {action}" for action in diagnosis["next_actions"])
        else:
            lines.append("- 次の改善施策はまだ定義されていません。")

    lines.extend(
        [
            "",
            "## 次の方針",
        ]
    )
    lines.extend(f"- {direction}" for direction in _next_directions(candidate_scores, runner))

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_workbook_exports(
    *,
    run_root: Path,
    baseline_payload: Dict[str, Any],
    baseline_score: ScoreResult,
    candidate_scores: Dict[str, ScoreResult],
    candidates: Dict[str, Dict[str, Any]],
    diagnoses: Dict[str, Dict[str, Any]],
    best_candidate_id: str,
) -> Dict[str, Any]:
    exports_dir = run_root / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)

    baseline_path = exports_dir / "baseline.xlsx"
    best_practical_id, _ = _select_practical_best(candidate_scores)
    best_practical_id = best_practical_id or best_candidate_id
    best_practical_path = exports_dir / "best-practical.xlsx"
    best_practical_labeled_path = exports_dir / f"best-practical-{best_practical_id}.xlsx"

    export_candidate_workbook(
        output_path=baseline_path,
        candidate_id="baseline",
        candidate_payload=baseline_payload,
        diagnosis=_baseline_diagnosis(baseline_score),
        baseline_total=baseline_score.total_score,
        run_root=run_root,
        iteration_summaries=_iteration_summaries(
            baseline_score=baseline_score,
            candidate_scores=candidate_scores,
            diagnoses=diagnoses,
            candidate_order=list(candidate_scores.keys()),
        ),
    )
    export_candidate_workbook(
        output_path=best_practical_path,
        candidate_id=best_practical_id,
        candidate_payload=candidates[best_practical_id],
        diagnosis=diagnoses[best_practical_id],
        baseline_total=baseline_score.total_score,
        run_root=run_root,
        iteration_summaries=_iteration_summaries(
            baseline_score=baseline_score,
            candidate_scores=candidate_scores,
            diagnoses=diagnoses,
            candidate_order=list(candidate_scores.keys()),
        ),
    )
    export_candidate_workbook(
        output_path=best_practical_labeled_path,
        candidate_id=best_practical_id,
        candidate_payload=candidates[best_practical_id],
        diagnosis=diagnoses[best_practical_id],
        baseline_total=baseline_score.total_score,
        run_root=run_root,
        iteration_summaries=_iteration_summaries(
            baseline_score=baseline_score,
            candidate_scores=candidate_scores,
            diagnoses=diagnoses,
            candidate_order=list(candidate_scores.keys()),
        ),
    )

    return {
        "baseline": baseline_path,
        "best_practical": best_practical_path,
        "best_practical_labeled": best_practical_labeled_path,
        "best_practical_candidate_id": best_practical_id,
    }


def _baseline_diagnosis(baseline_score: ScoreResult) -> Dict[str, Any]:
    return {
        "candidate_id": "baseline",
        "label": "baseline",
        "hypothesis": {
            "title": "baseline",
            "detail": "改善前の基準候補です。",
        },
        "logic": {
            "toggles_on": [],
            "toggles_off": [],
            "steps": ["改善前の基準候補として採点した結果です。"],
        },
        "evidence": {
            "source_types": [],
            "pdf_facts": [],
            "external_sources": [],
            "benchmark_fills": [],
            "seed_notes": [],
        },
        "score": {
            "total": baseline_score.total_score,
            "delta_vs_baseline": 0.0,
            "layers": {
                layer_name: {
                    "value": layer_value,
                    "delta": 0.0,
                }
                for layer_name, layer_value in baseline_score.layer_scores.items()
            },
        },
        "verdict": {
            "status": "baseline",
            "reason": "比較の基準となる候補です。",
        },
        "next_actions": [],
    }


def _iteration_summaries(
    *,
    baseline_score: ScoreResult,
    candidate_scores: Dict[str, ScoreResult],
    diagnoses: Dict[str, Dict[str, Any]],
    candidate_order: list[str],
) -> list[Dict[str, Any]]:
    items: list[Dict[str, Any]] = [
        {
            "iteration": 0,
            "candidate_id": "baseline",
            "hypothesis": "baseline",
            "changed_levers": "-",
            "improved_points": "-",
            "worsened_points": "-",
            "structure_delta": 0.0,
            "model_sheets_delta": 0.0,
            "pl_delta": 0.0,
            "explainability_delta": 0.0,
            "artifact_impact": "比較基準",
            "verdict": "baseline",
            "next_action": "以降の候補を比較する",
        }
    ]
    for idx, candidate_id in enumerate(candidate_order, start=1):
        score = candidate_scores[candidate_id]
        diagnosis = diagnoses.get(candidate_id, {})
        verdict = diagnosis.get("verdict", {}).get("status", "")
        layers = diagnosis.get("score", {}).get("layers", {})
        structure_delta = layers.get("structure", {}).get("delta", 0.0)
        model_sheets_delta = layers.get("model_sheets", {}).get("delta", 0.0)
        pl_delta = layers.get("pl", {}).get("delta", 0.0)
        explainability_delta = layers.get("explainability", {}).get("delta", 0.0)
        title = diagnosis.get("hypothesis", {}).get("title", candidate_id)
        next_action = (diagnosis.get("next_actions") or [""])[0]
        items.append(
            {
                "iteration": idx,
                "candidate_id": candidate_id,
                "hypothesis": title,
                "changed_levers": _changed_levers(diagnosis),
                "improved_points": _layer_change_summary(layers, positive=True),
                "worsened_points": _layer_change_summary(layers, positive=False),
                "structure_delta": structure_delta,
                "model_sheets_delta": model_sheets_delta,
                "pl_delta": pl_delta,
                "explainability_delta": explainability_delta,
                "artifact_impact": _artifact_impact_summary(
                    structure_delta=structure_delta,
                    model_sheets_delta=model_sheets_delta,
                    pl_delta=pl_delta,
                    explainability_delta=explainability_delta,
                ),
                "verdict": verdict,
                "next_action": next_action,
            }
        )
    return items


def _changed_levers(diagnosis: Dict[str, Any]) -> str:
    logic = diagnosis.get("logic", {})
    on = logic.get("toggles_on", []) or []
    off = logic.get("toggles_off", []) or []
    parts = []
    if on:
        parts.append("ON: " + ", ".join(on))
    if off:
        parts.append("OFF: " + ", ".join(off))
    return " / ".join(parts) or "-"


def _layer_change_summary(layers: Dict[str, Dict[str, float]], *, positive: bool) -> str:
    labels = []
    for layer_name in ("structure", "model_sheets", "pl", "explainability"):
        delta = layers.get(layer_name, {}).get("delta", 0.0)
        if positive and delta > 0:
            labels.append(f"{layer_name} {delta:+.4f}")
        if not positive and delta < 0:
            labels.append(f"{layer_name} {delta:+.4f}")
    return " / ".join(labels) if labels else "-"


def _artifact_impact_summary(
    *,
    structure_delta: float,
    model_sheets_delta: float,
    pl_delta: float,
    explainability_delta: float,
) -> str:
    impacts: list[str] = []
    if model_sheets_delta > 0:
        impacts.append("モデル改善")
    if pl_delta > 0:
        impacts.append("PL改善")
    if explainability_delta > 0:
        impacts.append("説明強化")
    if structure_delta < 0 or model_sheets_delta < 0 or pl_delta < 0:
        impacts.append("一部悪化")
    return " / ".join(impacts) if impacts else "横ばい"


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


def _layer_deltas(score: ScoreResult, baseline_score: ScoreResult) -> Dict[str, float]:
    return {
        layer_name: round(
            score.layer_scores.get(layer_name, 0.0) - baseline_score.layer_scores.get(layer_name, 0.0),
            4,
        )
        for layer_name in score.layer_scores
    }


def _ranked_candidate_ids(candidate_scores: Dict[str, ScoreResult]) -> list[str]:
    return sorted(
        candidate_scores,
        key=lambda candidate_id: candidate_scores[candidate_id].total_score,
        reverse=True,
    )


def _evidence_summary(candidate_payload: Dict[str, Any]) -> Dict[str, Any]:
    assumptions = candidate_payload.get("assumptions", [])
    pdf_facts: list[str] = []
    benchmark_fills: list[str] = []
    external_sources: list[Dict[str, Any]] = []
    seed_notes: list[str] = []

    for assumption in assumptions:
        source_type = assumption.get("source_type", "")
        explanation = assumption.get("explanation") or assumption.get("metric_name") or assumption.get("name") or ""
        if source_type == "document" and explanation:
            pdf_facts.append(explanation)
        elif "benchmark" in source_type and explanation:
            benchmark_fills.append(explanation)
        elif source_type in {"external", "public_market", "industry", "competitor", "trend"}:
            for ref in assumption.get("evidence_refs", []):
                external_sources.append(
                    {
                        "title": ref.get("title") or ref.get("source_id") or "",
                        "url": ref.get("url") or "",
                        "quote": ref.get("quote") or "",
                    }
                )
        elif "seed" in source_type and explanation:
            seed_notes.append(explanation)

    return {
        "pdf_facts": _unique_nonempty(pdf_facts),
        "external_sources": _dedupe_external_sources(external_sources),
        "benchmark_fills": _unique_nonempty(benchmark_fills),
        "seed_notes": _unique_nonempty(seed_notes),
    }


def _unique_nonempty(items: Iterable[str]) -> list[str]:
    seen: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.append(item)
    return seen


def _dedupe_external_sources(items: Iterable[Dict[str, Any]]) -> list[Dict[str, Any]]:
    deduped: list[Dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for item in items:
        key = (item.get("title", ""), item.get("url", ""), item.get("quote", ""))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _format_expected_impacts(expected_impacts: Dict[str, float]) -> str:
    if not expected_impacts:
        return "-"
    return ", ".join(f"{layer_name} {delta:+.4f}" for layer_name, delta in expected_impacts.items())


def _verdict_label(status: str) -> str:
    return {
        "hit": "当たり",
        "partial_hit": "一部当たり",
        "miss": "外れ",
    }.get(status, status)


def _format_layer_deltas(layer_details: Dict[str, Dict[str, float]]) -> str:
    return ", ".join(
        f"{layer_name} {detail.get('delta', 0.0):+.4f}"
        for layer_name, detail in layer_details.items()
    )


def _format_evidence_list(items: Iterable[str]) -> str:
    values = [item for item in items if item]
    return "; ".join(values) if values else "-"


def _format_external_sources(items: Iterable[Dict[str, Any]]) -> str:
    formatted: list[str] = []
    for item in items:
        title = item.get("title") or "source"
        url = item.get("url") or ""
        quote = item.get("quote") or ""
        if url and quote:
            formatted.append(f"{title} ({url}) - {quote}")
        elif url:
            formatted.append(f"{title} ({url})")
        elif quote:
            formatted.append(f"{title} - {quote}")
        else:
            formatted.append(title)
    return "; ".join(formatted) if formatted else "-"


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
        if profile.candidate_id == "candidate-structure-pl-extracted":
            return "事業構造に加えて PDF から PL 系列を直接抜ければ、`pl` と `explainability` が改善するはず。"
        if profile.candidate_id == "candidate-structure-model-pl-extracted":
            return "PDF からアカデミーの単価・人数・売上系列も抜ければ、`model_sheets` が改善して総合スコアがさらに上がるはず。"
        if profile.candidate_id == "candidate-integrated-derived":
            return "PDF で拾える meal/academy の断片と、欠損が大きい consulting の benchmark 補完を組み合わせると、`model_sheets` がさらに改善するはず。"
        if profile.candidate_id == "candidate-reference-seeded":
            return "参照 workbook のモデルシートと PL を seed にすると、現時点の上限再現度を測れるはず。"
        if profile.candidate_id == "candidate-analysis-industry":
            return "業界分析で meal の運用前提を補うと、model_sheets の改善幅が大きいはず。"
        if profile.candidate_id == "candidate-analysis-competitor":
            return "競合分析で consulting の価格と継続前提を補うと、model_sheets が部分的に改善するはず。"
        if profile.candidate_id == "candidate-analysis-trend":
            return "トレンド分析で academy の成長系列を補うと、model_sheets と explainability が改善するはず。"
        if profile.candidate_id == "candidate-analysis-public-market":
            return "公開企業/株式市場分析で PL 比率を補うと、pl の改善幅が見えるはず。"
        if profile.candidate_id == "candidate-industry-price-portion":
            return "industry 分析の中では、meal の価格/構成要素だけでも大きな lift を作るはず。"
        if profile.candidate_id == "candidate-industry-meal-frequency":
            return "industry 分析の中では、meal の食事頻度が model_sheets 改善の主要因になっているはず。"
        if profile.candidate_id == "candidate-industry-retention":
            return "industry 分析の中では、継続率だけでも一定の lift を作るはず。"
        if profile.candidate_id == "candidate-combined-industry-public-market":
            return "meal 前提の industry 分析に公開企業/株式市場の PL 比率を重ねると、model_sheets と pl の両方が改善するはず。"
        if profile.candidate_id == "candidate-combined-industry-trend":
            return "industry で meal を固めた上で trend で academy 成長を補うと、model_sheets の改善がさらに伸びるはず。"
        if profile.candidate_id == "candidate-combined-industry-trend-public-market":
            return "industry + trend + public-market を同時投入すると、model_sheets と pl をまとめて押し上げられるはず。"
        if profile.candidate_id == "candidate-cost-workforce-development":
            return "人件費・開発費を内部/外部の単価と工数で分解すると、OPEX の再現度がもっと上がるはず。"
        if profile.candidate_id == "candidate-cost-marketing":
            return "マーケ費を人件費とメディア/インセンティブに分けると、OPEX の説明力が上がるはず。"
        if profile.candidate_id == "candidate-cost-operating-purpose":
            return "業務内容と目的まで費用にひも付けると、OPEX の説明責任がさらに上がるはず。"
        if profile.candidate_id == "candidate-cost-internal-unit":
            return "人件費・開発費の中では、内部人材の単価が最も大きく効くはず。"
        if profile.candidate_id == "candidate-cost-external-unit":
            return "人件費・開発費の中では、外部人材の単価が大きく効くはず。"
        if profile.candidate_id == "candidate-cost-effort-mix":
            return "人件費・開発費の中では、工数配分が最も大きく効くはず。"
        if profile.candidate_id == "candidate-cost-workforce-marketing":
            return "人件費・開発費とマーケ費を重ねると、OPEX の再現度が一段上がるはず。"
        if profile.candidate_id == "candidate-cost-workforce-operating":
            return "人件費・開発費と業務内容/目的の紐付けを重ねると、説明責任が一段上がるはず。"
        if profile.candidate_id == "candidate-cost-combined":
            return "人件費・開発費・マーケ費・業務内容/目的をまとめて入れると、費用面の PL 再現が最も改善するはず。"
        if profile.candidate_id == "candidate-revenue-branding-lift":
            return "ブランディングの間接効果で直販施策の効率が上がると、PL の売上・粗利系列が改善するはず。"
        if profile.candidate_id == "candidate-revenue-marketing-efficiency":
            return "マーケの CAC と ROAS を明示すると、売上成長の PL 再現が改善するはず。"
        if profile.candidate_id == "candidate-revenue-sales-efficiency":
            return "営業の CAC と生産性を明示すると、consulting の driver と売上系列が改善するはず。"
        if profile.candidate_id == "candidate-revenue-partner-strategy":
            return "パートナー戦略の寄与を織り込むと、consulting の継続と売上系列が改善するはず。"
        if profile.candidate_id == "candidate-revenue-staged-acceleration":
            return "3年間の検証期間の後に投資アクセルを踏む構造を入れると、計画全体の売上系列が最も参照に近づくはず。"
        if profile.candidate_id == "candidate-revenue-validation-period":
            return "検証期間の設計だけでも、前半3年の売上・粗利系列がかなり改善するはず。"
        if profile.candidate_id == "candidate-revenue-acceleration-period":
            return "検証後の営業・マーケ投資アクセルだけでも、後半の売上系列に大きく効くはず。"
        if profile.candidate_id == "candidate-revenue-gated-acceleration":
            return "検証後に条件付きで投資を開放する gate を入れると、無理な前倒しを避けつつ売上系列が改善するはず。"
        if profile.candidate_id == "candidate-revenue-staged-sales":
            return "検証後アクセルに営業効率の改善を重ねると、売上と model_sheets がさらに伸びるはず。"
        if profile.candidate_id == "candidate-revenue-staged-partner":
            return "検証後アクセルにパートナー戦略を重ねると、売上系列と継続性がさらに改善するはず。"
        if profile.candidate_id == "candidate-revenue-staged-branding":
            return "検証後アクセルにブランド波及を重ねると、直接施策の効率がさらに上がるはず。"
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
            elif profile.candidate_id == "candidate-structure-pl-extracted":
                improvements.append("PDF 本文から売上・粗利・OPEX の系列を直接抽出し、PL 再現と説明責任を改善する候補を追加しました。")
            elif profile.candidate_id == "candidate-structure-model-pl-extracted":
                improvements.append("PDF 本文からアカデミーの単価・人数・売上系列も直接抽出し、model_sheets の改善候補を追加しました。")
            elif profile.candidate_id == "candidate-integrated-derived":
                improvements.append("meal の unit economics を PDF 断片から導出し、consulting は benchmark で欠損を補完する統合候補を追加しました。")
            elif profile.candidate_id == "candidate-reference-seeded":
                improvements.append("参照 workbook の model_sheets と PL を seed して、現時点の理論上限を測る候補を追加しました。")
            elif profile.candidate_id == "candidate-analysis-industry":
                improvements.append("業界分析レイヤーをオンにして、meal のドライバー前提を外部知識で補う候補を追加しました。")
            elif profile.candidate_id == "candidate-analysis-competitor":
                improvements.append("競合分析レイヤーをオンにして、consulting の価格・継続・工数前提を競合比較で補う候補を追加しました。")
            elif profile.candidate_id == "candidate-analysis-trend":
                improvements.append("トレンド分析レイヤーをオンにして、academy の人数・認証・売上の成長系列を補う候補を追加しました。")
            elif profile.candidate_id == "candidate-analysis-public-market":
                improvements.append("公開企業/株式市場レイヤーをオンにして、PL 比率の補完がどこまで効くかを見る候補を追加しました。")
            elif profile.candidate_id == "candidate-industry-price-portion":
                improvements.append("industry 分析を価格/構成要素だけに分解し、meal の単価・品数がどこまで効くかを見る候補を追加しました。")
            elif profile.candidate_id == "candidate-industry-meal-frequency":
                improvements.append("industry 分析を食事頻度だけに分解し、meal の利用頻度がどこまで効くかを見る候補を追加しました。")
            elif profile.candidate_id == "candidate-industry-retention":
                improvements.append("industry 分析を継続率だけに分解し、retention 単独の効き方を見る候補を追加しました。")
            elif profile.candidate_id == "candidate-combined-industry-public-market":
                improvements.append("industry の meal 前提と public-market の PL 比率を重ねた複合候補を追加しました。")
            elif profile.candidate_id == "candidate-combined-industry-trend":
                improvements.append("industry の meal 前提と trend の academy 成長系列を重ねた複合候補を追加しました。")
            elif profile.candidate_id == "candidate-combined-industry-trend-public-market":
                improvements.append("industry・trend・public-market をまとめてオンにした総合候補を追加しました。")
            elif profile.candidate_id == "candidate-cost-workforce-development":
                improvements.append("人件費・開発費を内部/外部の単価と工数に分解して、OPEX の改善候補を追加しました。")
            elif profile.candidate_id == "candidate-cost-marketing":
                improvements.append("マーケ費を人件費・メディア費・インセンティブ費に分解して、OPEX の改善候補を追加しました。")
            elif profile.candidate_id == "candidate-cost-operating-purpose":
                improvements.append("費用を業務内容と目的に紐付けて、説明責任を強める候補を追加しました。")
            elif profile.candidate_id == "candidate-cost-internal-unit":
                improvements.append("人件費・開発費のうち内部人材単価だけを動かす候補を追加しました。")
            elif profile.candidate_id == "candidate-cost-external-unit":
                improvements.append("人件費・開発費のうち外部人材単価だけを動かす候補を追加しました。")
            elif profile.candidate_id == "candidate-cost-effort-mix":
                improvements.append("人件費・開発費のうち工数配分だけを動かす候補を追加しました。")
            elif profile.candidate_id == "candidate-cost-workforce-marketing":
                improvements.append("人件費・開発費とマーケ費を組み合わせた費用候補を追加しました。")
            elif profile.candidate_id == "candidate-cost-workforce-operating":
                improvements.append("人件費・開発費と業務内容/目的の整理を組み合わせた費用候補を追加しました。")
            elif profile.candidate_id == "candidate-cost-combined":
                improvements.append("人件費・開発費・マーケ費・業務内容/目的を全部乗せした費用候補を追加しました。")
            elif profile.candidate_id == "candidate-revenue-branding-lift":
                improvements.append("ブランド施策の間接効果で direct 施策効率が上がる前提を、売上系列に重ねた候補を追加しました。")
            elif profile.candidate_id == "candidate-revenue-marketing-efficiency":
                improvements.append("マーケの CAC・ROAS 改善が売上系列にどう効くかを見る候補を追加しました。")
            elif profile.candidate_id == "candidate-revenue-sales-efficiency":
                improvements.append("営業の CAC・成約効率・担当生産性を consulting driver に反映する候補を追加しました。")
            elif profile.candidate_id == "candidate-revenue-partner-strategy":
                improvements.append("パートナー経由の獲得・継続寄与を consulting と売上系列に反映する候補を追加しました。")
            elif profile.candidate_id == "candidate-revenue-staged-acceleration":
                improvements.append("3年間の検証期間の後に営業/マーケ投資を加速させる段階投資候補を追加しました。")
            elif profile.candidate_id == "candidate-revenue-validation-period":
                improvements.append("前半のユニットエコノミクス検証期間だけを切り出した候補を追加しました。")
            elif profile.candidate_id == "candidate-revenue-acceleration-period":
                improvements.append("検証後の営業/マーケ投資アクセル期間だけを切り出した候補を追加しました。")
            elif profile.candidate_id == "candidate-revenue-gated-acceleration":
                improvements.append("検証 KPI を満たしたときだけ投資を解放する gate 付き候補を追加しました。")
            elif profile.candidate_id == "candidate-revenue-staged-sales":
                improvements.append("段階投資に営業効率の改善を重ねた複合候補を追加しました。")
            elif profile.candidate_id == "candidate-revenue-staged-partner":
                improvements.append("段階投資にパートナー戦略を重ねた複合候補を追加しました。")
            elif profile.candidate_id == "candidate-revenue-staged-branding":
                improvements.append("段階投資にブランド波及を重ねた複合候補を追加しました。")
        return improvements

    improvements.append("fixture データで baseline と candidate の差を比較し、評価器と summary 生成の整合性を確認しました。")
    return improvements


def _next_directions(candidate_scores: Dict[str, ScoreResult], runner: str) -> list[str]:
    directions: list[str] = []
    if runner == "live":
        revenue_candidates = [candidate_id for candidate_id in candidate_scores if candidate_id.startswith("candidate-revenue-")]
        if revenue_candidates:
            directions.append("次はブランド・マーケ・営業・パートナーの仮説を、実際の外部ソース取込に置き換えて再評価します。")
            directions.append("特に `staged acceleration` で効いた後半の売上跳ねを、営業投資・マーケ投資・パートナー寄与に分解して PL へ接続します。")
            directions.append("consulting の driver を revenue line に結び付ける中間ロジックを足して、`pl` をさらに押し上げます。")
            if any(_is_upper_bound_candidate(candidate_id) for candidate_id in candidate_scores):
                directions.append("`candidate-reference-seeded` は上限比較のまま維持し、採用判断は revenue overlay 候補だけで続けます。")
            return directions
        directions.append("次は PDF からモデルシートの driver 候補を直接抽出し、`model_sheets` スコアを先に引き上げます。")
        directions.append("その driver を canonical model と engine 計算に通して、`pl` スコアが上がるかを確認します。")
        directions.append("重要前提ごとに evidence と review_status を増やして、`explainability` を board-ready 寄りに改善します。")
        if any(_is_upper_bound_candidate(candidate_id) for candidate_id in candidate_scores):
            directions.append("`candidate-reference-seeded` は上限比較として維持しつつ、採用判断は PDF 由来候補だけで行うようにします。")
        return directions

    directions.append("live runner で同じ summary 形式を維持しながら、FAM 実データで仮説の改善量を追えるようにします。")
    return directions


def _score_graph_lines(
    baseline_score: ScoreResult,
    candidate_scores: Dict[str, ScoreResult],
    profiles: Iterable[CandidateProfile],
) -> list[str]:
    lines = [_bar_line("Baseline", baseline_score.total_score)]
    for profile in profiles:
        score = candidate_scores.get(profile.candidate_id)
        if score is None or _is_upper_bound_candidate(profile.candidate_id):
            continue
        lines.append(_bar_line(profile.candidate_id, score.total_score))
    if any(_is_upper_bound_candidate(profile.candidate_id) for profile in profiles):
        upper_bound_score = candidate_scores.get("candidate-reference-seeded")
        if upper_bound_score is not None:
            lines.append(_bar_line("UpperBound", upper_bound_score.total_score))
    return lines


def _bar_line(label: str, score: float) -> str:
    width = max(1, round(score * 20))
    return f"{label:<32} {score:>6.4f}  {'█' * width}"


def _initiative_table_lines(
    baseline_score: ScoreResult,
    candidate_scores: Dict[str, ScoreResult],
    profiles: Iterable[CandidateProfile],
) -> list[str]:
    lines = [
        "| baseline | PDF のみで現状再現力を測る | 総合 `"
        + f"{baseline_score.total_score:.4f}"
        + "` | 構造は半分見えるが model_sheets / pl が未再現 |"
    ]
    for profile in profiles:
        score = candidate_scores.get(profile.candidate_id)
        if score is None:
            continue
        delta = round(score.total_score - baseline_score.total_score, 4)
        effect = f"総合 `{score.total_score:.4f}` (`{delta:+.4f}`)"
        issue = _short_issue(score)
        if _is_upper_bound_candidate(profile.candidate_id):
            issue = "参照 workbook を seed にした上限比較"
        lines.append(
            f"| {profile.candidate_id} | {_short_measure(profile)} | {effect} | {issue} |"
        )
    return lines


def _short_measure(profile: CandidateProfile) -> str:
    mapping = {
        "candidate-structure-seeded": "segment と engine_type を seed",
        "candidate-structure-pl-extracted": "PDF から PL 系列を直接抽出",
        "candidate-structure-model-pl-extracted": "PDF から academy モデル系列も抽出",
        "candidate-integrated-derived": "meal 抽出 + consulting 補完を統合",
        "candidate-analysis-industry": "業界分析で meal 前提を補完",
        "candidate-analysis-competitor": "競合分析で consulting 前提を補完",
        "candidate-analysis-trend": "トレンド分析で academy 成長系列を補完",
        "candidate-analysis-public-market": "公開企業分析で PL 比率を補完",
        "candidate-industry-price-portion": "industry を価格/構成だけに分解",
        "candidate-industry-meal-frequency": "industry を食事頻度だけに分解",
        "candidate-industry-retention": "industry を継続率だけに分解",
        "candidate-combined-industry-public-market": "industry + public-market を重ねる",
        "candidate-combined-industry-trend": "industry + trend を重ねる",
        "candidate-combined-industry-trend-public-market": "industry + trend + public-market を重ねる",
        "candidate-cost-workforce-development": "人件費/開発費を単価×工数で分解",
        "candidate-cost-marketing": "マーケ費を人件費+実費に分解",
        "candidate-cost-operating-purpose": "費用を業務内容/目的に紐付け",
        "candidate-cost-internal-unit": "内部人材単価だけを調整",
        "candidate-cost-external-unit": "外部人材単価だけを調整",
        "candidate-cost-effort-mix": "工数配分だけを調整",
        "candidate-cost-workforce-marketing": "人件費/開発費 + マーケ費",
        "candidate-cost-workforce-operating": "人件費/開発費 + 業務内容/目的",
        "candidate-cost-combined": "費用3要素を全部統合",
        "candidate-revenue-branding-lift": "ブランド波及で direct 効率を補正",
        "candidate-revenue-marketing-efficiency": "マーケ CAC/ROAS を補正",
        "candidate-revenue-sales-efficiency": "営業 CAC/生産性を補正",
        "candidate-revenue-partner-strategy": "パートナー戦略効果を補正",
        "candidate-revenue-staged-acceleration": "検証後アクセルの段階投資を反映",
        "candidate-revenue-validation-period": "前半の検証期間だけを反映",
        "candidate-revenue-acceleration-period": "後半の投資アクセルだけを反映",
        "candidate-revenue-gated-acceleration": "条件付きアクセル gate を反映",
        "candidate-revenue-staged-sales": "段階投資 + 営業効率を重ねる",
        "candidate-revenue-staged-partner": "段階投資 + パートナー戦略を重ねる",
        "candidate-revenue-staged-branding": "段階投資 + ブランド波及を重ねる",
        "candidate-reference-seeded": "参照 workbook の model/pl を seed",
    }
    return mapping.get(profile.candidate_id, profile.label)


def _short_issue(score: ScoreResult) -> str:
    if score.layer_scores.get("model_sheets", 0.0) < 0.1:
        return "model_sheets がまだ弱い"
    if score.layer_scores.get("pl", 0.0) < 0.2:
        return "PL 再現がまだ弱い"
    if score.layer_scores.get("explainability", 0.0) < 0.9:
        return "説明責任は改善中だが未完成"
    return "大きな課題は縮小"
