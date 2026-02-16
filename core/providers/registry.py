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
        "model_id": "claude-opus-4-6",
        "label": "Claude Opus 4.6",
        "tier": "premium",
        "description": "最高精度。128K出力。複雑な分析・推論向け",
    },
    {
        "provider": "anthropic",
        "provider_label": "Claude",
        "model_id": "claude-opus-4-5-20251101",
        "label": "Claude Opus 4.5",
        "tier": "premium",
        "description": "前世代Opus。拡張思考対応。安定性重視",
    },
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
        "model_id": "claude-sonnet-4-20250514",
        "label": "Claude Sonnet 4.0",
        "tier": "standard",
        "description": "安定版Sonnet。1Mコンテキスト(beta)",
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
        "model_id": "gpt-5.2",
        "label": "GPT-5.2",
        "tier": "premium",
        "description": "最新フラッグシップ。400Kコンテキスト。推論レベル調整可能",
    },
    {
        "provider": "openai",
        "provider_label": "ChatGPT",
        "model_id": "gpt-5",
        "label": "GPT-5",
        "tier": "standard",
        "description": "GPT-5基本版。高精度な汎用モデル",
    },
    {
        "provider": "openai",
        "provider_label": "ChatGPT",
        "model_id": "gpt-5-mini",
        "label": "GPT-5 mini",
        "tier": "fast",
        "description": "コスト効率の良い推論モデル",
    },
    {
        "provider": "openai",
        "provider_label": "ChatGPT",
        "model_id": "gpt-5-nano",
        "label": "GPT-5 nano",
        "tier": "fast",
        "description": "最速・最安。分類・要約向け",
    },
    {
        "provider": "openai",
        "provider_label": "ChatGPT",
        "model_id": "gpt-4.1",
        "label": "GPT-4.1",
        "tier": "standard",
        "description": "コーディング特化。1Mコンテキスト",
    },
    {
        "provider": "openai",
        "provider_label": "ChatGPT",
        "model_id": "gpt-4.1-mini",
        "label": "GPT-4.1 mini",
        "tier": "fast",
        "description": "手頃な中間層。1Mコンテキスト",
    },
    {
        "provider": "openai",
        "provider_label": "ChatGPT",
        "model_id": "gpt-4.1-nano",
        "label": "GPT-4.1 nano",
        "tier": "fast",
        "description": "最小・最速。シンプルなタスク向け",
    },
    {
        "provider": "openai",
        "provider_label": "ChatGPT",
        "model_id": "o3",
        "label": "o3",
        "tier": "premium",
        "description": "深層推論特化。複雑な多段階分析向け",
    },
    # --- Google Gemini ---
    {
        "provider": "google",
        "provider_label": "Gemini",
        "model_id": "gemini-3-pro-preview",
        "label": "Gemini 3 Pro",
        "tier": "premium",
        "description": "最新世代プレビュー。マルチモーダル推論。1Mコンテキスト",
    },
    {
        "provider": "google",
        "provider_label": "Gemini",
        "model_id": "gemini-3-flash-preview",
        "label": "Gemini 3 Flash",
        "tier": "fast",
        "description": "最新世代プレビュー。Pro級の速度重視版",
    },
    {
        "provider": "google",
        "provider_label": "Gemini",
        "model_id": "gemini-2.5-pro",
        "label": "Gemini 2.5 Pro",
        "tier": "standard",
        "description": "高精度推論。1Mコンテキスト。安定版",
    },
    {
        "provider": "google",
        "provider_label": "Gemini",
        "model_id": "gemini-2.5-flash",
        "label": "Gemini 2.5 Flash",
        "tier": "fast",
        "description": "最高コスパ。1Mコンテキスト",
    },
    {
        "provider": "google",
        "provider_label": "Gemini",
        "model_id": "gemini-2.5-flash-lite",
        "label": "Gemini 2.5 Flash Lite",
        "tier": "fast",
        "description": "最安。大量バッチ処理向け",
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
