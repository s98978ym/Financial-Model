"""Helper to create the correct LLM provider for a worker task.

Reads the project's llm_provider/llm_model settings (or system default)
and returns a ProviderAdapter ready for agent use.

When the selected provider is unavailable (missing package or API key),
automatically falls back to Anthropic with a warning.
"""
from __future__ import annotations

import importlib
import logging
import os

logger = logging.getLogger(__name__)

# Map of provider name → (required env var, import check module)
_PROVIDER_REQUIREMENTS = {
    "anthropic": ("ANTHROPIC_API_KEY", "anthropic"),
    "openai":    ("OPENAI_API_KEY",    "openai"),
    "google":    ("GOOGLE_API_KEY",    "google.generativeai"),
}

_FALLBACK_PROVIDER = "anthropic"


def _check_provider_available(provider_name: str) -> str | None:
    """Return None if provider is ready, or an error message string."""
    reqs = _PROVIDER_REQUIREMENTS.get(provider_name)
    if not reqs:
        return f"Unknown provider: {provider_name}"

    env_var, import_module = reqs

    # Check package is installed
    try:
        importlib.import_module(import_module)
    except ImportError:
        return f"{import_module} パッケージが未インストール"

    # Check API key is set
    if not os.environ.get(env_var):
        return f"環境変数 {env_var} が未設定"

    return None


def get_adapter_for_run(run_id: str):
    """Create a ProviderAdapter using the project's LLM config for the given run.

    Falls back to system default if no project-level override.
    If the selected provider is unavailable, falls back to Anthropic.
    """
    from core.providers.adapter import ProviderAdapter
    from core.providers.registry import get_provider
    from services.api.app import db

    # Get project_id from run
    project_id = None
    if db._use_pg():
        with db.get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT project_id FROM runs WHERE id = %s", (run_id,))
            row = cur.fetchone()
            if row:
                project_id = str(row[0])
    else:
        run = db._mem_runs.get(run_id)
        if run:
            project_id = run.get("project_id")

    if project_id:
        llm_config = db.get_project_llm_config(project_id)
    else:
        llm_config = db.get_llm_default()

    provider_name = llm_config.get("provider", "anthropic")
    model_id = llm_config.get("model")

    # Validate selected provider is available; fall back to Anthropic if not
    error = _check_provider_available(provider_name)
    if error and provider_name != _FALLBACK_PROVIDER:
        logger.warning(
            "Run %s: provider '%s' unavailable (%s) — falling back to anthropic",
            run_id, provider_name, error,
        )
        fallback_error = _check_provider_available(_FALLBACK_PROVIDER)
        if fallback_error:
            raise RuntimeError(
                f"{provider_name}プロバイダーが使用不可({error})、"
                f"フォールバック先のanthropicも使用不可({fallback_error})。"
                f"Renderダッシュボードで環境変数を設定してください。"
            )
        provider_name = _FALLBACK_PROVIDER
        model_id = None  # Use Anthropic's default model
    elif error:
        # Anthropic itself is unavailable and no fallback possible
        raise RuntimeError(
            f"anthropicプロバイダーが使用不可({error})。"
            f"RenderダッシュボードでANTHROPIC_API_KEYを設定してください。"
        )

    logger.info(
        "Run %s: using provider=%s model=%s",
        run_id, provider_name, model_id or "(default)",
    )

    provider = get_provider(provider_name, model=model_id)
    return ProviderAdapter(provider)
