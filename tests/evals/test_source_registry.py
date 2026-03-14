import json
from pathlib import Path

from src.evals.source_registry import (
    SOURCE_REGISTRY_PATH,
    analysis_source_refs,
    source_registry_metadata,
    upsert_analysis_source_ref,
)


def test_source_registry_uses_repo_cache_file() -> None:
    assert SOURCE_REGISTRY_PATH.exists()
    assert SOURCE_REGISTRY_PATH.name == "source_cache.json"


def test_source_registry_metadata_exposes_version_and_update_scope() -> None:
    metadata = source_registry_metadata()

    assert metadata["version"]
    assert "sales_efficiency_analysis" in metadata["source_types"]
    assert "partner_strategy_analysis" in metadata["source_types"]
    assert "staged_acceleration_analysis" in metadata["source_types"]


def test_analysis_source_refs_returns_cached_refs_with_urls_and_quotes() -> None:
    refs = analysis_source_refs("sales_efficiency_analysis")

    assert refs
    assert all(ref.get("url", "").startswith("https://") for ref in refs)
    assert all(ref.get("quote") for ref in refs)


def test_analysis_source_refs_returns_defensive_copy() -> None:
    refs = analysis_source_refs("partner_strategy_analysis")
    refs[0]["quote"] = "modified"

    fresh_refs = analysis_source_refs("partner_strategy_analysis")

    assert fresh_refs[0]["quote"] != "modified"


def test_analysis_source_refs_can_enrich_live_sources(monkeypatch, tmp_path: Path) -> None:
    def _fake_enrich(source_type: str, refs: list[dict[str, str]], cache_dir: Path) -> list[dict[str, str]]:
        assert source_type == "staged_acceleration_analysis"
        assert cache_dir == tmp_path
        return [{**ref, "quote": "live-enriched"} for ref in refs]

    monkeypatch.setattr("src.evals.source_registry.enrich_source_refs", _fake_enrich)

    refs = analysis_source_refs(
        "staged_acceleration_analysis",
        enrich_live_sources=True,
        cache_dir=tmp_path,
    )

    assert refs
    assert all(ref["quote"] == "live-enriched" for ref in refs)


def test_upsert_analysis_source_ref_updates_custom_registry_file(tmp_path: Path) -> None:
    registry_path = tmp_path / "source_cache.json"
    registry_path.write_text(
        json.dumps(
            {
                "metadata": {"version": "test", "update_scope": ["sales_efficiency_analysis"]},
                "refs": {
                    "sales_efficiency_analysis": [
                        {
                            "title": "Old title",
                            "url": "https://example.com/old",
                            "publisher": "Example",
                            "quote": "Old quote",
                        }
                    ]
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    updated = upsert_analysis_source_ref(
        "sales_efficiency_analysis",
        title="New title",
        url="https://example.com/new",
        publisher="Example",
        quote="New quote",
        registry_path=registry_path,
    )

    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    refs = payload["refs"]["sales_efficiency_analysis"]

    assert updated["title"] == "New title"
    assert refs[-1]["quote"] == "New quote"


def test_upsert_analysis_source_ref_updates_existing_entry_by_url(tmp_path: Path) -> None:
    registry_path = tmp_path / "source_cache.json"
    registry_path.write_text(
        json.dumps(
            {
                "metadata": {"version": "test", "update_scope": ["partner_strategy_analysis"]},
                "refs": {
                    "partner_strategy_analysis": [
                        {
                            "title": "Partner",
                            "url": "https://example.com/partner",
                            "publisher": "Example",
                            "quote": "Old quote",
                        }
                    ]
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    upsert_analysis_source_ref(
        "partner_strategy_analysis",
        title="Partner updated",
        url="https://example.com/partner",
        publisher="Example 2",
        quote="Updated quote",
        registry_path=registry_path,
    )

    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    refs = payload["refs"]["partner_strategy_analysis"]

    assert len(refs) == 1
    assert refs[0]["title"] == "Partner updated"
    assert refs[0]["quote"] == "Updated quote"
