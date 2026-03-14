"""Pydantic models for LLM improvement PDCA artifacts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


PromptChange = Literal["system", "user", "both"]
CampaignStatus = Literal["active", "paused", "completed"]
ExperimentStatus = Literal["draft", "ready", "imported", "compared", "reported", "completed"]
DecisionStatus = Literal["adopted", "rejected", "hold"]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class PDCADataModel(BaseModel):
    """Base model with strict field validation for PDCA artifacts."""

    model_config = ConfigDict(extra="forbid")


class LLMConfigSnapshot(PDCADataModel):
    provider: str
    model: str
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


class PromptPairInfo(PDCADataModel):
    system_key: str
    user_key: str
    changed: PromptChange


class InputDocumentRef(PDCADataModel):
    project_id: Optional[str] = None
    document_hash: Optional[str] = None
    filename: str = ""
    source_path: str = ""


class PromptSnapshot(PDCADataModel):
    system_prompt: str
    user_prompt: str
    prompt_key: str = ""
    source: str = ""


class ImportedOutputMeta(PDCADataModel):
    provider: str = ""
    model: str = ""
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    latency_ms: Optional[int] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    notes: str = ""


class Campaign(PDCADataModel):
    campaign_id: str
    name: str
    target_phase: int
    goal: str = ""
    status: CampaignStatus = "active"
    created_at: str = Field(default_factory=_utc_now)


class ExperimentManifest(PDCADataModel):
    experiment_id: str
    campaign_id: str
    parent_experiment_id: Optional[str] = None
    baseline_source: str = "default"
    target_phase: int
    hypothesis: str
    status: ExperimentStatus = "draft"
    decision: Optional[DecisionStatus] = None
    decision_reason: Optional[str] = None
    llm_config: LLMConfigSnapshot
    prompt_pair: PromptPairInfo
    input_document: InputDocumentRef
    created_at: str = Field(default_factory=_utc_now)
    completed_at: Optional[str] = None
