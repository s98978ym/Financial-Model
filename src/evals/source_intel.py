"""Fetch and summarize external source evidence for revenue overlays."""

from __future__ import annotations

import hashlib
import html
import re
import tempfile
from pathlib import Path
from typing import Iterable
from urllib.request import Request, urlopen

from src.ingest.reader import read_document


USER_AGENT = "Mozilla/5.0 (compatible; CodexEvalBot/1.0)"


KEYWORDS_BY_SOURCE_TYPE = {
    "branding_lift_analysis": ["brand", "growth engine", "mix modelling", "measurement"],
    "marketing_efficiency_analysis": ["cac", "cpl", "benchmark", "channel"],
    "sales_efficiency_analysis": ["win rate", "sales cycle", "pipeline", "conversion", "benchmark"],
    "partner_strategy_analysis": ["partner", "enablement", "revenue", "channel"],
    "staged_acceleration_analysis": ["measurement", "growth", "investment", "cac"],
    "validation_period_analysis": ["measurement", "incremental", "validation"],
    "acceleration_period_analysis": ["growth", "mix modelling", "cac", "investment"],
    "gated_acceleration_analysis": ["measurement", "payback", "cac", "guardrail"],
}


def extract_keyword_excerpt(text: str, keywords: Iterable[str], window: int = 260) -> str:
    collapsed = " ".join(text.split())
    lowered = collapsed.lower()
    for keyword in keywords:
        needle = keyword.lower()
        index = lowered.find(needle)
        if index >= 0:
            start = max(0, index - window // 2)
            end = min(len(collapsed), index + len(keyword) + window // 2)
            return collapsed[start:end].strip()
    return collapsed[:window].strip()


def enrich_source_refs(source_type: str, refs: list[dict[str, str]], cache_dir: Path) -> list[dict[str, str]]:
    enriched: list[dict[str, str]] = []
    for ref in refs:
        if not ref.get("url"):
            enriched.append(ref)
            continue
        quote = fetch_source_quote(ref["url"], KEYWORDS_BY_SOURCE_TYPE.get(source_type, []), cache_dir)
        enriched.append({**ref, "quote": quote})
    return enriched


def fetch_source_quote(url: str, keywords: Iterable[str], cache_dir: Path) -> str:
    cache_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    suffix = ".pdf" if url.lower().endswith(".pdf") else ".html"
    cached_path = cache_dir / f"{digest}{suffix}"

    if not cached_path.exists():
        req = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(req, timeout=20) as response:
            body = response.read()
            cached_path.write_bytes(body)

    if cached_path.suffix.lower() == ".pdf":
        text = read_document(str(cached_path)).full_text
    else:
        raw = cached_path.read_text(encoding="utf-8", errors="ignore")
        text = _html_to_text(raw)
    return extract_keyword_excerpt(text, keywords)


def _html_to_text(raw_html: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?>.*?</\\1>", " ", raw_html)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = html.unescape(text)
    return " ".join(text.split())
