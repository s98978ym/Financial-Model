"""Centralized compatibility layer for Streamlit app imports.

When Streamlit Cloud deploys from ``main`` but the feature branch has new
exports, individual imports break.  This module provides a SINGLE place
to define fallbacks so that ``streamlit_app.py`` never has scattered
try/except blocks.

Adding a new import:
1. Add the import to the ``try`` block below.
2. Add a fallback in the ``except`` block.
3. Export it via ``__all__``.
4. In ``streamlit_app.py``, do ``from src.app.compat import X``.
"""
from __future__ import annotations

# ------------------------------------------------------------------
# LLM client
# ------------------------------------------------------------------
from src.extract.llm_client import LLMClient

try:
    from src.extract.llm_client import LLMError
except ImportError:

    class LLMError(Exception):  # type: ignore[no-redef]
        """Raised when the LLM API call fails."""


# ------------------------------------------------------------------
# Prompt constants
# ------------------------------------------------------------------
try:
    from src.extract.prompts import SYSTEM_PROMPT_NORMAL
except ImportError:
    SYSTEM_PROMPT_NORMAL = (
        "You are a financial model specialist. Extract parameters from "
        "business plan documents and map them to P&L template cells."
    )

try:
    from src.extract.prompts import SYSTEM_PROMPT_STRICT
except ImportError:
    SYSTEM_PROMPT_STRICT = (
        SYSTEM_PROMPT_NORMAL
        + "\nSTRICT MODE: Only include values explicitly stated in the document."
    )

try:
    from src.extract.prompts import INDUSTRY_PROMPTS
except ImportError:
    INDUSTRY_PROMPTS: dict = {}  # type: ignore[no-redef]

try:
    from src.extract.prompts import BUSINESS_MODEL_PROMPTS
except ImportError:
    BUSINESS_MODEL_PROMPTS: dict = {}  # type: ignore[no-redef]

try:
    from src.extract.prompts import USER_PROMPT_TEMPLATE
except ImportError:
    USER_PROMPT_TEMPLATE = (
        "以下の事業計画書から、PLテンプレートの各入力セルに対応する"
        "パラメータを抽出してください。\n\n"
        "■ 生成ケース: {cases}\n\n"
        "■ テンプレート入力セル一覧:\n{catalog_block}\n\n"
        "■ 事業計画書:\n{document_chunk}\n"
    )

# ------------------------------------------------------------------
# Exports
# ------------------------------------------------------------------
__all__ = [
    "LLMClient",
    "LLMError",
    "SYSTEM_PROMPT_NORMAL",
    "SYSTEM_PROMPT_STRICT",
    "INDUSTRY_PROMPTS",
    "BUSINESS_MODEL_PROMPTS",
    "USER_PROMPT_TEMPLATE",
]
