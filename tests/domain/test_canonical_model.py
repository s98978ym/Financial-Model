"""Tests for canonical business model schema."""

from __future__ import annotations

import json
from pathlib import Path

from src.domain.canonical_model import CanonicalBusinessModel, Driver


FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "canonical"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def test_fam_fixture_validates_as_canonical_business_model() -> None:
    model = CanonicalBusinessModel.model_validate(_load_fixture("fam_expected.json"))

    assert model.metadata.project_name == "FAM"
    assert len(model.segments) == 3
    assert {segment.segment_id for segment in model.segments} == {
        "meal",
        "academy",
        "consulting",
    }
    assert model.segments[0].engines[0].engine_type == "unit_economics"


def test_saas_fixture_validates_as_canonical_business_model() -> None:
    model = CanonicalBusinessModel.model_validate(_load_fixture("saas_expected.json"))

    assert model.metadata.project_name == "SaaS Demo"
    assert len(model.segments) == 1
    assert model.segments[0].engines[0].engine_type == "subscription"
    assert model.segments[0].engines[0].drivers[0].source == "document"


def test_driver_supports_provenance_and_planning_fields() -> None:
    driver = Driver(
        driver_id="academy_students",
        name="受講人数",
        unit="人",
        category="volume",
        source="benchmark",
        confidence=0.72,
        mode="solve_for",
        decision_required=True,
        tags=["academy"],
    )

    assert driver.source == "benchmark"
    assert driver.mode == "solve_for"
    assert driver.decision_required is True
