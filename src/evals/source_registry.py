"""Stable source registry backed by a repo cache file."""

from __future__ import annotations

import json
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any

from .source_intel import enrich_source_refs


SOURCE_REGISTRY_PATH = Path(__file__).with_name("data").joinpath("source_cache.json")
DEFAULT_SOURCE_CACHE_DIR = Path("artifacts/fam-eval/source-cache")


def _resolve_registry_path(registry_path: Path | None = None) -> Path:
    return Path(registry_path) if registry_path is not None else SOURCE_REGISTRY_PATH


@lru_cache(maxsize=1)
def _source_registry_payload(registry_path_str: str) -> dict[str, Any]:
    return json.loads(Path(registry_path_str).read_text(encoding="utf-8"))


def source_registry_metadata(registry_path: Path | None = None) -> dict[str, Any]:
    resolved_path = _resolve_registry_path(registry_path)
    payload = _source_registry_payload(str(resolved_path))
    metadata = deepcopy(payload.get("metadata", {}))
    metadata["source_types"] = sorted(payload.get("refs", {}).keys())
    metadata["registry_path"] = str(resolved_path)
    return metadata


def analysis_source_refs(
    source_type: str,
    enrich_live_sources: bool = False,
    cache_dir: Path | None = None,
    registry_path: Path | None = None,
) -> list[dict[str, str]]:
    resolved_path = _resolve_registry_path(registry_path)
    payload = _source_registry_payload(str(resolved_path))
    refs = deepcopy(payload.get("refs", {}).get(source_type, []))
    if enrich_live_sources and refs:
        return enrich_source_refs(source_type, refs, cache_dir or DEFAULT_SOURCE_CACHE_DIR)
    return refs


def upsert_analysis_source_ref(
    source_type: str,
    *,
    title: str,
    url: str,
    publisher: str,
    quote: str,
    registry_path: Path | None = None,
) -> dict[str, str]:
    resolved_path = _resolve_registry_path(registry_path)
    payload = _source_registry_payload(str(resolved_path))
    writable_payload = deepcopy(payload)

    metadata = writable_payload.setdefault("metadata", {})
    update_scope = metadata.setdefault("update_scope", [])
    if source_type not in update_scope:
        update_scope.append(source_type)

    refs_by_source = writable_payload.setdefault("refs", {})
    refs = refs_by_source.setdefault(source_type, [])
    new_ref = {
        "title": title,
        "url": url,
        "publisher": publisher,
        "quote": quote,
    }

    existing_index = next(
        (
            index
            for index, ref in enumerate(refs)
            if ref.get("url") == url or ref.get("title") == title
        ),
        None,
    )
    if existing_index is None:
        refs.append(new_ref)
    else:
        refs[existing_index] = new_ref

    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_path.write_text(
        json.dumps(writable_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _source_registry_payload.cache_clear()
    return new_ref
