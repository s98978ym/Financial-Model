"""Phase 5 comparison metrics."""

from __future__ import annotations

from typing import Any


def phase5_metrics(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "json_validity": False,
            "extraction_count": 0,
            "avg_confidence": 0.0,
            "mapped_target_rate": 0.0,
            "missing_required_fields": 0,
        }

    extractions = payload.get("extractions", [])
    if not isinstance(extractions, list):
        extractions = []
        json_validity = False
    else:
        json_validity = True

    count = len(extractions)
    if count:
        avg_conf = round(
            sum(float(item.get("confidence", 0.0)) for item in extractions) / count,
            4,
        )
        mapped_count = sum(
            1
            for item in extractions
            if item.get("sheet") and item.get("cell")
        )
    else:
        avg_conf = 0.0
        mapped_count = 0

    missing_fields = 0
    for item in extractions:
        for field in ("sheet", "cell", "label", "concept", "period"):
            if not item.get(field):
                missing_fields += 1

    return {
        "json_validity": json_validity,
        "extraction_count": count,
        "avg_confidence": avg_conf,
        "mapped_target_rate": round(mapped_count / count, 4) if count else 0.0,
        "missing_required_fields": missing_fields,
    }

