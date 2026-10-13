"""Provider-neutral AI boundaries; proposals still require domain validation."""

from collections.abc import Mapping
from enum import StrEnum
from typing import Any, Protocol, TypeAlias

from pydantic import Field

from .domain import InterpretationProposal, Model


class ProviderOutcome(StrEnum):
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    TIMEOUT = "TIMEOUT"
    RATE_LIMITED = "RATE_LIMITED"
    INVALID_SCHEMA = "INVALID_SCHEMA"


class ProviderMetadata(Model):
    """Operational evidence without raw responses, audio, or credentials.

    ``schema_valid`` is unknown when a call did not produce structured output,
    including speech transcription. ``request_id`` is an opaque provider or
    application correlation identifier, never a credential or response body.
    """

    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    latency_ms: float = Field(ge=0, allow_inf_nan=False)
    outcome: ProviderOutcome
    schema_valid: bool | None = None
    retry_count: int = Field(default=0, ge=0)
    request_id: str | None = None


class TranscriptionResult(Model):
    text: str
    language: str | None = None
    # Populate only when the provider supplies a calibrated value; never infer
    # confidence from a successful response or from the recognized text.
    confidence: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    metadata: ProviderMetadata


# Preserve the single domain proposal schema across all provider adapters.
ProposedCommand: TypeAlias = InterpretationProposal
InterpretationContext: TypeAlias = Mapping[str, Any]


class InterpretationResult(Model):
    proposal: InterpretationProposal
    metadata: ProviderMetadata


class TranscriptionProvider(Protocol):
    async def transcribe(self, audio: bytes) -> TranscriptionResult: ...


class InterpretationProvider(Protocol):
    def interpret(self, text: str, context: InterpretationContext | None = None) -> InterpretationResult: ...
