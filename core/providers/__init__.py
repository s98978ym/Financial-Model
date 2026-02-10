"""LLM Provider abstraction layer.

Supports multiple LLM backends (Anthropic Claude, OpenAI, Google Gemini)
with a unified interface, audit logging, and output guards.
"""

from .base import LLMProvider, LLMResponse, LLMConfig
from .anthropic_provider import AnthropicProvider
from .adapter import ProviderAdapter
from .guards import JSONOutputGuard, EvidenceGuard, ConfidencePenalty, ExtractionCompleteness
from .audit import AuditLogger, AuditRecord

__all__ = [
    "LLMProvider",
    "LLMResponse",
    "LLMConfig",
    "AnthropicProvider",
    "ProviderAdapter",
    "JSONOutputGuard",
    "EvidenceGuard",
    "ConfidencePenalty",
    "ExtractionCompleteness",
    "AuditLogger",
    "AuditRecord",
]
