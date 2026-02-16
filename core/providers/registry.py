"""LLM provider factory and model catalog.

Central registry of available LLM providers, models, and a factory
function to instantiate the correct provider for a given selection.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base import LLMProvider

# ---------------------------------------------------------------------------
# Model catalog — authoritative list of supported provider/model combos
# ---------------------------------------------------------------------------

MODEL_CATALOG: List[Dict[str, Any]] = [
    # --- Anthropic Claude ---
    {
        "provider": "anthropic",
        "provider_label": "Claude",
        "model_id": "claude-sonnet-4-5-20250929",
        "label": "Claude Sonnet 4.5",
        "tier": "standard",
        "description": "バランス型。速度とコストの最適解",
    },
    {
        "provider": "anthropic",
        "provider_label": "Claude",
        "model_id": "claude-opus-4-6",
        "label": "Claude Opus 4.6",
        "tier": "premium",
        "description": "最高精度。複雑な分析向け",
    },
    {
        "provider": "anthropic",
        "provider_label": "Claude",
        "model_id": "claude-haiku-4-5-20251001",
        "label": "Claude Haiku 4.5",
        "tier": "fast",
        "description": "高速・低コスト。シンプルな分析向け",
    },
    # --- OpenAI GPT ---
    {
        "provider": "openai",
        "provider_label": "ChatGPT",
        "model_id": "gpt-4o",
        "label": "GPT-4o",
        "tier": "standard",
        "description": "マルチモーダル対応の汎用モデル",
    },
    {
        "provider": "openai",
        "provider_label": "ChatGPT",
        "model_id": "gpt-4o-mini",
        "label": "GPT-4o mini",
        "tier": "fast",
        "description": "高速・低コスト版",
    },
    {
        "provider": "openai",
        "provider_label": "ChatGPT",
        "model_id": "gpt-4-turbo",
        "label": "GPT-4 Turbo",
        "tier": "standard",
        "description": "高性能。128Kコンテキスト",
    },
    {
        "provider": "openai",
        "provider_label": "ChatGPT",
        "model_id": "o1",
        "label": "o1",
        "tier": "premium",
        "description": "推論特化モデル。深い分析向け",
    },
    {
        "provider": "openai",
        "provider_label": "ChatGPT",
        "model_id": "o3-mini",
        "label": "o3-mini",
        "tier": "fast",
        "description": "推論特化の軽量版",
    },
    # --- Google Gemini ---
    {
        "provider": "google",
        "provider_label": "Gemini",
        "model_id": "gemini-2.0-flash",
        "label": "Gemini 2.0 Flash",
        "tier": "fast",
        "description": "高速。コスト効率重視",
    },
    {
        "provider": "google",
        "provider_label": "Gemini",
        "model_id": "gemini-1.5-pro",
        "label": "Gemini 1.5 Pro",
        "tier": "standard",
        "description": "汎用プロモデル。長文対応",
    },
    {
        "provider": "google",
        "provider_label": "Gemini",
        "model_id": "gemini-2.5-pro",
        "label": "Gemini 2.5 Pro",
        "tier": "premium",
        "description": "最新世代。高精度分析",
    },
]


def get_model_catalog() -> List[Dict[str, Any]]:
    """Return the full model catalog for API/frontend consumption."""
    return MODEL_CATALOG


def get_providers() -> List[Dict[str, str]]:
    """Return unique provider list with labels."""
    seen = {}
    for m in MODEL_CATALOG:
        if m["provider"] not in seen:
            seen[m["provider"]] = m["provider_label"]
    return [{"id": k, "label": v} for k, v in seen.items()]


def get_models_for_provider(provider: str) -> List[Dict[str, Any]]:
    """Return models available for a given provider."""
    return [m for m in MODEL_CATALOG if m["provider"] == provider]


def get_default_model_for_provider(provider: str) -> Optional[str]:
    """Return the default (standard tier) model_id for a provider."""
    for m in MODEL_CATALOG:
        if m["provider"] == provider and m["tier"] == "standard":
            return m["model_id"]
    # Fallback to first model
    for m in MODEL_CATALOG:
        if m["provider"] == provider:
            return m["model_id"]
    return None


def validate_provider_model(provider: str, model_id: str) -> bool:
    """Check if a provider/model combination is valid."""
    return any(
        m["provider"] == provider and m["model_id"] == model_id
        for m in MODEL_CATALOG
    )


# ---------------------------------------------------------------------------
# Provider factory
# ---------------------------------------------------------------------------

def get_provider(provider_name: str, model: Optional[str] = None) -> LLMProvider:
    """Create and return an LLMProvider instance for the given provider/model.

    Parameters
    ----------
    provider_name :
        One of "anthropic", "openai", "google".
    model :
        Optional model ID override. Passed as default_model to the provider.

    Returns
    -------
    LLMProvider
        Ready-to-use provider instance.

    Raises
    ------
    ValueError
        If the provider_name is not recognized.
    """
    kwargs: Dict[str, Any] = {}
    if model:
        kwargs["default_model"] = model

    if provider_name == "anthropic":
        from .anthropic_provider import AnthropicProvider
        return AnthropicProvider(**kwargs)
    elif provider_name == "openai":
        from .openai_provider import OpenAIProvider
        return OpenAIProvider(**kwargs)
    elif provider_name == "google":
        from .google_provider import GoogleProvider
        return GoogleProvider(**kwargs)
    else:
        raise ValueError(
            f"Unknown LLM provider: {provider_name!r}. "
            f"Supported: anthropic, openai, google"
        )
