"""Candidate profiles for reference-driven PDCA runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class CandidateProfile:
    candidate_id: str
    label: str
    runner: str = "fixture"
    config: Dict[str, Any] = field(default_factory=dict)


def fixture_profiles() -> List[CandidateProfile]:
    return [
        CandidateProfile(
            candidate_id="candidate-better",
            label="Fixture better candidate",
            runner="fixture",
            config={"fixture_name": "candidate_result.json"},
        ),
        CandidateProfile(
            candidate_id="candidate-baseline-like",
            label="Fixture baseline-like candidate",
            runner="fixture",
            config={"fixture_name": "baseline_result.json"},
        ),
    ]


def fixture_path(root: Path, fixture_name: str) -> Path:
    return root / "tests" / "fixtures" / "evals" / fixture_name


def live_profiles() -> List[CandidateProfile]:
    return [
        CandidateProfile(
            candidate_id="candidate-structure-seeded",
            label="PDF structure-seeded candidate",
            runner="live",
            config={"mode": "structure_seeded"},
        ),
        CandidateProfile(
            candidate_id="candidate-structure-pl-extracted",
            label="PDF structure + PL extracted candidate",
            runner="live",
            config={"mode": "structure_pl_extracted"},
        ),
        CandidateProfile(
            candidate_id="candidate-structure-model-pl-extracted",
            label="PDF structure + academy model + PL extracted candidate",
            runner="live",
            config={"mode": "structure_model_pl_extracted"},
        ),
        CandidateProfile(
            candidate_id="candidate-integrated-derived",
            label="PDF structure + model extraction + benchmark completion candidate",
            runner="live",
            config={"mode": "integrated_derived"},
        ),
        CandidateProfile(
            candidate_id="candidate-reference-seeded",
            label="PDF reference-seeded candidate",
            runner="live",
            config={"mode": "reference_seeded"},
        ),
    ]
