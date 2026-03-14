"""Constraint helpers for evidence-constrained planning."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.domain.evidence_ledger import AssumptionRecord


@dataclass
class ConstraintViolation:
    code: str
    object_id: str
    message: str
    actual_value: Optional[float] = None
    limit_value: Optional[float] = None


def check_allowed_range(record: AssumptionRecord, proposed_value: float) -> Optional[ConstraintViolation]:
    allowed_range = record.allowed_range
    if allowed_range.min is not None and proposed_value < allowed_range.min:
        return ConstraintViolation(
            code="range_exceeded",
            object_id=record.object_id,
            message=f"{record.metric_name} is below the allowed minimum",
            actual_value=proposed_value,
            limit_value=allowed_range.min,
        )
    if allowed_range.max is not None and proposed_value > allowed_range.max:
        return ConstraintViolation(
            code="range_exceeded",
            object_id=record.object_id,
            message=f"{record.metric_name} is above the allowed maximum",
            actual_value=proposed_value,
            limit_value=allowed_range.max,
        )
    return None


def check_project_capacity(
    object_id: str,
    required_projects: float,
    headcount: float,
    max_projects_per_head: float,
) -> Optional[ConstraintViolation]:
    capacity_limit = headcount * max_projects_per_head
    if required_projects <= capacity_limit:
        return None
    return ConstraintViolation(
        code="capacity_exceeded",
        object_id=object_id,
        message="Required projects exceed modeled staffing capacity",
        actual_value=required_projects,
        limit_value=capacity_limit,
    )
