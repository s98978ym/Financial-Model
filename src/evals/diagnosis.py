"""Structured diagnosis helpers for FAM reference evaluation."""

from __future__ import annotations

from typing import Any, Dict

from .candidate_profiles import CandidateProfile
from .scoring import ScoreResult


def build_candidate_diagnosis(
    profile: CandidateProfile,
    score: ScoreResult,
    baseline_score: ScoreResult,
    evidence_summary: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    layer_deltas = _layer_deltas(score, baseline_score)
    verdict = _verdict(profile, score, baseline_score, layer_deltas)

    return {
        "candidate_id": profile.candidate_id,
        "label": profile.label,
        "hypothesis": {
            "title": profile.hypothesis_title,
            "detail": profile.hypothesis_detail,
        },
        "logic": {
            "toggles_on": profile.toggles_on,
            "toggles_off": profile.toggles_off,
            "steps": profile.logic_steps,
        },
        "evidence": {
            "source_types": profile.evidence_source_types,
            **(evidence_summary or {}),
        },
        "score": {
            "total": score.total_score,
            "delta_vs_baseline": round(score.total_score - baseline_score.total_score, 4),
            "layers": {
                layer_name: {
                    "value": layer_value,
                    "delta": layer_deltas[layer_name],
                }
                for layer_name, layer_value in score.layer_scores.items()
            },
        },
        "verdict": verdict,
        "next_actions": profile.next_if_success if verdict["status"] == "hit" else profile.next_if_fail,
    }


def _layer_deltas(score: ScoreResult, baseline_score: ScoreResult) -> Dict[str, float]:
    return {
        layer_name: round(score.layer_scores.get(layer_name, 0.0) - baseline_score.layer_scores.get(layer_name, 0.0), 4)
        for layer_name in score.layer_scores
    }


def _verdict(
    profile: CandidateProfile,
    score: ScoreResult,
    baseline_score: ScoreResult,
    layer_deltas: Dict[str, float],
) -> Dict[str, str]:
    if score.total_score < baseline_score.total_score:
        return {
            "status": "miss",
            "reason": "総合スコアが baseline を下回りました。",
        }

    expected_impacts = profile.expected_impacts or {}
    if expected_impacts:
        primary_layer, expected_threshold = max(expected_impacts.items(), key=lambda item: item[1])
        if primary_layer == "total":
            actual_delta = round(score.total_score - baseline_score.total_score, 4)
        else:
            actual_delta = layer_deltas.get(primary_layer, 0.0)
        if actual_delta >= expected_threshold:
            return {
                "status": "hit",
                "reason": f"主目的の `{primary_layer}` が `{actual_delta:+.4f}` 改善し、期待値 `{expected_threshold:+.4f}` を満たしました。",
            }
        if actual_delta > 0:
            return {
                "status": "partial_hit",
                "reason": f"主目的の `{primary_layer}` は `{actual_delta:+.4f}` 改善しましたが、期待値 `{expected_threshold:+.4f}` には届きませんでした。",
            }
        return {
            "status": "miss",
            "reason": f"主目的の `{primary_layer}` が改善しませんでした。",
        }

    if score.total_score > baseline_score.total_score:
        return {
            "status": "hit",
            "reason": "総合スコアが baseline を上回りました。",
        }

    return {
        "status": "partial_hit",
        "reason": "総合スコアは横ばいで、大きな改善は見られませんでした。",
    }
