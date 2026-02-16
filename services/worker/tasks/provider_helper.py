"""Helper to create the correct LLM provider for a worker task.

Reads the project's llm_provider/llm_model settings (or system default)
and returns a ProviderAdapter ready for agent use.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

# Map of provider name → required env var for API key
_PROVIDER_API_KEY_ENV = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "google": "GOOGLE_API_KEY",
}


def get_adapter_for_run(run_id: str):
    """Create a ProviderAdapter using the project's LLM config for the given run.

    Falls back to system default if no project-level override.
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

    # Validate API key is set before attempting to use the provider
    env_var = _PROVIDER_API_KEY_ENV.get(provider_name)
    if env_var and not os.environ.get(env_var):
        raise RuntimeError(
            f"{provider_name}プロバイダーのAPIキー({env_var})が設定されていません。"
            f"Renderダッシュボードの環境変数で{env_var}を設定してください。"
        )

    logger.info(
        "Run %s: using provider=%s model=%s",
        run_id, provider_name, model_id or "(default)",
    )

    provider = get_provider(provider_name, model=model_id)
    return ProviderAdapter(provider)
