"""LLM-based parameter extraction from business planning documents."""

from .extractor import ParameterExtractor
from .llm_client import LLMClient
from .normalizer import normalize_value, normalize_japanese_number

try:
    from .llm_client import LLMError
except ImportError:

    class LLMError(Exception):  # type: ignore[no-redef]
        """Raised when the LLM API call fails."""


__all__ = [
    "ParameterExtractor",
    "LLMClient",
    "LLMError",
    "normalize_value",
    "normalize_japanese_number",
]
