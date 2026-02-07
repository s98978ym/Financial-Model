"""Prompt Registry -- central management for all agent prompts.

Provides:
  - Default prompts for all agents (system + user)
  - Runtime override via session_state or direct API
  - Reset to defaults
  - Prompt metadata (display name, description, phase)
"""
from __future__ import annotations

import copy
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PromptEntry:
    """A single registered prompt."""
    key: str  # unique ID, e.g. "bm_analyzer_system"
    display_name: str  # shown in UI
    description: str  # what this prompt does
    phase: int  # which wizard phase (2-5)
    prompt_type: str  # "system" or "user"
    default_content: str  # the original prompt text
    current_content: str = ""  # runtime value (empty = use default)

    @property
    def content(self) -> str:
        """Return current content, falling back to default."""
        return self.current_content if self.current_content else self.default_content

    @property
    def is_customized(self) -> bool:
        """Whether the prompt has been modified from default."""
        return bool(self.current_content) and self.current_content != self.default_content

    def reset(self) -> None:
        """Reset to default."""
        self.current_content = ""


class PromptRegistry:
    """Central registry for all agent prompts.

    Usage::

        registry = PromptRegistry()
        # Get prompt content
        system = registry.get("bm_analyzer_system")
        # Override
        registry.set("bm_analyzer_system", "new prompt...")
        # Reset
        registry.reset("bm_analyzer_system")
        # Reset all
        registry.reset_all()
    """

    def __init__(self) -> None:
        self._entries: Dict[str, PromptEntry] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register all default prompts from agent modules."""
        # Lazy imports to avoid circular deps
        from src.agents.business_model_analyzer import (
            BM_ANALYZER_SYSTEM_PROMPT,
            BM_ANALYZER_USER_PROMPT,
        )
        from src.agents.template_mapper import (
            TS_SYSTEM_PROMPT,
            TS_USER_PROMPT,
        )
        from src.agents.model_designer import (
            MD_SYSTEM_PROMPT,
            MD_USER_PROMPT,
        )
        from src.agents.parameter_extractor import (
            PE_SYSTEM_PROMPT,
            PE_USER_PROMPT,
        )
        from src.agents.fm_designer import (
            FM_DESIGNER_SYSTEM_PROMPT,
            FM_DESIGNER_USER_PROMPT,
        )

        entries = [
            # Phase 2: BM Analyzer
            PromptEntry(
                key="bm_analyzer_system",
                display_name="BM分析 - システムプロンプト",
                description="ビジネスモデル分析エージェントの役割・思考プロセスを定義",
                phase=2,
                prompt_type="system",
                default_content=BM_ANALYZER_SYSTEM_PROMPT,
            ),
            PromptEntry(
                key="bm_analyzer_user",
                display_name="BM分析 - ユーザープロンプト",
                description="分析対象の事業計画書と出力形式を指示",
                phase=2,
                prompt_type="user",
                default_content=BM_ANALYZER_USER_PROMPT,
            ),
            # Phase 3: Template Mapper
            PromptEntry(
                key="template_mapper_system",
                display_name="テンプレ構造 - システムプロンプト",
                description="テンプレートのシート構造をビジネスセグメントに対応付ける役割定義",
                phase=3,
                prompt_type="system",
                default_content=TS_SYSTEM_PROMPT,
            ),
            PromptEntry(
                key="template_mapper_user",
                display_name="テンプレ構造 - ユーザープロンプト",
                description="テンプレートシートとセグメントのマッピング指示",
                phase=3,
                prompt_type="user",
                default_content=TS_USER_PROMPT,
            ),
            # Phase 4: Model Designer
            PromptEntry(
                key="model_designer_system",
                display_name="モデル設計 - システムプロンプト",
                description="セルへのビジネス概念マッピングの役割定義",
                phase=4,
                prompt_type="system",
                default_content=MD_SYSTEM_PROMPT,
            ),
            PromptEntry(
                key="model_designer_user",
                display_name="モデル設計 - ユーザープロンプト",
                description="各セルの概念マッピング指示と出力形式",
                phase=4,
                prompt_type="user",
                default_content=MD_USER_PROMPT,
            ),
            # Phase 5: Parameter Extractor
            PromptEntry(
                key="param_extractor_system",
                display_name="パラメーター抽出 - システムプロンプト",
                description="事業計画書から具体的な値を抽出する役割定義",
                phase=5,
                prompt_type="system",
                default_content=PE_SYSTEM_PROMPT,
            ),
            PromptEntry(
                key="param_extractor_user",
                display_name="パラメーター抽出 - ユーザープロンプト",
                description="セルごとの値抽出指示と出力形式",
                phase=5,
                prompt_type="user",
                default_content=PE_USER_PROMPT,
            ),
            # Legacy: FM Designer (Phase 2 legacy)
            PromptEntry(
                key="fm_designer_system",
                display_name="FMデザイナー (レガシー) - システム",
                description="旧パイプラインの直接マッピングエージェント",
                phase=0,
                prompt_type="system",
                default_content=FM_DESIGNER_SYSTEM_PROMPT,
            ),
            PromptEntry(
                key="fm_designer_user",
                display_name="FMデザイナー (レガシー) - ユーザー",
                description="旧パイプラインの直接マッピング指示",
                phase=0,
                prompt_type="user",
                default_content=FM_DESIGNER_USER_PROMPT,
            ),
        ]

        for entry in entries:
            self._entries[entry.key] = entry

    def get(self, key: str) -> str:
        """Get the current prompt content (custom or default)."""
        entry = self._entries.get(key)
        if not entry:
            raise KeyError(f"Unknown prompt key: {key}")
        return entry.content

    def get_entry(self, key: str) -> PromptEntry:
        """Get the full PromptEntry."""
        entry = self._entries.get(key)
        if not entry:
            raise KeyError(f"Unknown prompt key: {key}")
        return entry

    def set(self, key: str, content: str) -> None:
        """Override a prompt with custom content."""
        entry = self._entries.get(key)
        if not entry:
            raise KeyError(f"Unknown prompt key: {key}")
        entry.current_content = content
        logger.info("Prompt '%s' customized (%d chars)", key, len(content))

    def reset(self, key: str) -> None:
        """Reset a prompt to its default."""
        entry = self._entries.get(key)
        if not entry:
            raise KeyError(f"Unknown prompt key: {key}")
        entry.reset()
        logger.info("Prompt '%s' reset to default", key)

    def reset_all(self) -> None:
        """Reset all prompts to defaults."""
        for entry in self._entries.values():
            entry.reset()
        logger.info("All prompts reset to defaults")

    def list_entries(self, phase: Optional[int] = None) -> List[PromptEntry]:
        """List all entries, optionally filtered by phase."""
        entries = list(self._entries.values())
        if phase is not None:
            entries = [e for e in entries if e.phase == phase]
        entries.sort(key=lambda e: (e.phase, e.prompt_type))
        return entries

    def get_customized_keys(self) -> List[str]:
        """Get keys of all customized prompts."""
        return [k for k, e in self._entries.items() if e.is_customized]

    def to_session_state(self) -> Dict[str, str]:
        """Export customizations to a dict (for session_state persistence)."""
        return {k: e.current_content for k, e in self._entries.items() if e.is_customized}

    def from_session_state(self, state: Dict[str, str]) -> None:
        """Import customizations from a dict."""
        for key, content in state.items():
            if key in self._entries and content:
                self._entries[key].current_content = content
