"""Tests for evidence and assumption ledger models."""

from __future__ import annotations

from src.domain.evidence_ledger import AssumptionLedger, AssumptionRecord, EvidenceRef, ValueRange


def test_evidence_ref_supports_document_quote_metadata() -> None:
    evidence = EvidenceRef(
        ref_type="document_quote",
        source_id="pdf:fam",
        location="page:11",
        quote="リリース3年目:5億円",
        rationale="事業計画に明記",
    )

    assert evidence.ref_type == "document_quote"
    assert evidence.location == "page:11"


def test_assumption_record_tracks_provenance_review_and_board_ready() -> None:
    record = AssumptionRecord(
        record_id="assump_academy_completion",
        object_type="driver",
        object_id="academy_completion_rate",
        metric_name="修了率",
        value=0.9,
        unit="%",
        source_type="internal_case",
        confidence=0.7,
        evidence_refs=[
            EvidenceRef(
                ref_type="internal_case",
                source_id="case:academy-2025",
                location="sheet:summary",
                quote="平均修了率90%",
            )
        ],
        allowed_range=ValueRange(min=0.8, base=0.9, max=0.95),
        owner="finance",
        review_status="approved",
        board_ready=True,
        explanation="類似案件実績から採用",
    )

    assert record.allowed_range.base == 0.9
    assert record.review_status == "approved"
    assert record.board_ready is True


def test_assumption_ledger_groups_records() -> None:
    ledger = AssumptionLedger(
        records=[
            AssumptionRecord(
                record_id="assump_revenue_target",
                object_type="target",
                object_id="target_fy5_revenue",
                metric_name="FY5売上",
                value=1_000_000_000,
                unit="JPY",
                source_type="management_decision",
            )
        ]
    )

    assert len(ledger.records) == 1
    assert ledger.records[0].metric_name == "FY5売上"
