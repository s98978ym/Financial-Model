"""Admin prompt management endpoints.

Provides CRUD for LLM prompt customizations with version history.
All endpoints are under /v1/admin/prompts.
"""
from __future__ import annotations

import logging
import secrets
import sys
import os
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException

from .. import db

logger = logging.getLogger(__name__)
router = APIRouter()

# -------------------------------------------------------------------
# Admin authentication
# -------------------------------------------------------------------
_valid_tokens: set = set()


def _require_admin(authorization: Optional[str] = Header(default=None)):
    """Verify admin Bearer token on protected endpoints."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="管理者認証が必要です")
    token = authorization[7:]
    if token not in _valid_tokens:
        raise HTTPException(status_code=401, detail="認証トークンが無効または期限切れです")


@router.post("/admin/auth")
async def admin_auth(body: dict):
    """Authenticate admin user with ID and password."""
    admin_id = body.get("admin_id", "")
    password = body.get("password", "")

    if not admin_id or not password:
        raise HTTPException(status_code=422, detail="IDとパスワードは必須です")

    expected_id = os.environ.get("ADMIN_ID", "admin")
    expected_pw = os.environ.get("ADMIN_PASSWORD", "plgen2024")

    if admin_id == expected_id and password == expected_pw:
        token = secrets.token_hex(32)
        _valid_tokens.add(token)
        logger.info("Admin authenticated (token count: %d)", len(_valid_tokens))
        return {"authenticated": True, "token": token}

    raise HTTPException(status_code=401, detail="IDまたはパスワードが正しくありません")


@router.get("/admin/auth/verify", dependencies=[Depends(_require_admin)])
async def verify_admin_token():
    """Verify if admin token is still valid."""
    return {"authenticated": True}


def _get_registry():
    """Lazy-load the PromptRegistry to get default prompts."""
    # Ensure src/ is importable
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from src.agents.prompt_registry import PromptRegistry
    return PromptRegistry()


# Cache registry instance (defaults don't change at runtime)
_registry_cache = None


def _registry():
    global _registry_cache
    if _registry_cache is None:
        try:
            _registry_cache = _get_registry()
        except Exception as e:
            logger.warning("Failed to load PromptRegistry: %s", e)
            return None
    return _registry_cache


# -------------------------------------------------------------------
# Phase metadata for pipeline visualization
# -------------------------------------------------------------------

PHASE_META = [
    {
        "phase": 2,
        "label": "BM分析",
        "description": "ビジネスモデル分析 — 事業計画書を読み解き、3-5個の収益構造提案を生成",
        "icon": "search",
        "prompts": ["bm_analyzer_system", "bm_analyzer_user"],
        "model": "claude-sonnet-4-5-20250929",
        "temperature": 0.1,
        "max_tokens": 32768,
    },
    {
        "phase": 3,
        "label": "テンプレマップ",
        "description": "テンプレート構造マッピング — シートとビジネスセグメントの対応関係を決定",
        "icon": "map",
        "prompts": ["template_mapper_system", "template_mapper_user"],
        "model": "claude-sonnet-4-5-20250929",
        "temperature": 0.1,
        "max_tokens": 32768,
    },
    {
        "phase": 4,
        "label": "モデル設計",
        "description": "モデル設計 — 各セルにビジネスコンセプトを割り当て、PLの骨格を構築",
        "icon": "cube",
        "prompts": ["model_designer_system", "model_designer_user"],
        "model": "claude-sonnet-4-5-20250929",
        "temperature": 0.1,
        "max_tokens": 32768,
    },
    {
        "phase": 5,
        "label": "パラメータ抽出",
        "description": "パラメータ抽出 — 事業計画書から具体的な数値・テキストを抽出",
        "icon": "download",
        "prompts": ["param_extractor_system", "param_extractor_user"],
        "model": "claude-sonnet-4-5-20250929",
        "temperature": 0.1,
        "max_tokens": 32768,
    },
]


@router.get("/admin/prompts/phases", dependencies=[Depends(_require_admin)])
async def list_phases():
    """Pipeline phase metadata for visualization."""
    return PHASE_META


@router.get("/admin/prompts", dependencies=[Depends(_require_admin)])
async def list_prompts(project_id: Optional[str] = None):
    """List all registered prompts with metadata and customization status."""
    reg = _registry()
    if not reg:
        raise HTTPException(status_code=500, detail="PromptRegistry not available")

    entries = reg.list_entries()
    result = []
    for entry in entries:
        if entry.phase == 0:
            continue  # skip legacy

        active = db.get_active_prompt(entry.key, project_id)
        result.append({
            "key": entry.key,
            "display_name": entry.display_name,
            "description": entry.description,
            "phase": entry.phase,
            "prompt_type": entry.prompt_type,
            "default_content": entry.default_content,
            "current_content": active["content"] if active else entry.default_content,
            "is_customized": active is not None,
            "active_version_id": active["id"] if active else None,
            "scope": "project" if (active and active.get("project_id")) else "global" if active else "default",
        })
    return result


@router.get("/admin/prompts/{prompt_key}", dependencies=[Depends(_require_admin)])
async def get_prompt(prompt_key: str, project_id: Optional[str] = None):
    """Get full detail for a single prompt including version history."""
    reg = _registry()
    if not reg:
        raise HTTPException(status_code=500, detail="PromptRegistry not available")

    try:
        entry = reg.get_entry(prompt_key)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown prompt key: {prompt_key}")

    active = db.get_active_prompt(prompt_key, project_id)
    versions = db.get_prompt_versions(prompt_key, project_id)

    return {
        "key": entry.key,
        "display_name": entry.display_name,
        "description": entry.description,
        "phase": entry.phase,
        "prompt_type": entry.prompt_type,
        "default_content": entry.default_content,
        "current_content": active["content"] if active else entry.default_content,
        "is_customized": active is not None,
        "active_version_id": active["id"] if active else None,
        "versions": versions,
    }


@router.put("/admin/prompts/{prompt_key}", dependencies=[Depends(_require_admin)])
async def update_prompt(prompt_key: str, body: dict):
    """Save a new version of a prompt.

    Body:
      content: str — new prompt text
      project_id: str | null — null for global, UUID for project-specific
      label: str — optional version label (e.g. "v2 more detailed")
    """
    reg = _registry()
    if not reg:
        raise HTTPException(status_code=500, detail="PromptRegistry not available")

    try:
        reg.get_entry(prompt_key)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown prompt key: {prompt_key}")

    content = body.get("content", "").strip()
    if not content:
        raise HTTPException(status_code=422, detail="content is required")

    project_id = body.get("project_id")
    label = body.get("label", "")

    version = db.save_prompt_version(
        prompt_key=prompt_key,
        content=content,
        project_id=project_id,
        label=label,
        is_active=True,
    )
    return version


@router.post("/admin/prompts/{prompt_key}/reset", dependencies=[Depends(_require_admin)])
async def reset_prompt(prompt_key: str, body: dict = None):
    """Reset prompt to default (deactivate all custom versions for this key+scope).

    Body:
      project_id: str | null — scope to reset
    """
    body = body or {}
    project_id = body.get("project_id")

    reg = _registry()
    if not reg:
        raise HTTPException(status_code=500, detail="PromptRegistry not available")

    try:
        entry = reg.get_entry(prompt_key)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown prompt key: {prompt_key}")

    # Deactivate all versions for this key+scope
    versions = db.get_prompt_versions(prompt_key, project_id)
    for v in versions:
        if v["is_active"]:
            db.activate_prompt_version("__none__", prompt_key, project_id)
            break

    return {"status": "reset", "prompt_key": prompt_key, "default_content": entry.default_content}


@router.put("/admin/prompts/{prompt_key}/versions/{version_id}", dependencies=[Depends(_require_admin)])
async def activate_version(prompt_key: str, version_id: str, body: dict = None):
    """Activate a specific historical version."""
    body = body or {}
    project_id = body.get("project_id")

    result = db.activate_prompt_version(version_id, prompt_key, project_id)
    if not result:
        raise HTTPException(status_code=404, detail="Version not found")
    return result
