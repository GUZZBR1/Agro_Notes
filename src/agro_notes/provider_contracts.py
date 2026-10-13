"""Provider-neutral AI boundaries; proposals still require domain validation."""

import logging
from collections.abc import Mapping
from enum import StrEnum
from typing import Any, Protocol, TypeAlias

from pydantic import Field

from .domain import InterpretationProposal, Model

logger = logging.getLogger("agro_notes.providers")


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
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    audio_seconds: float | None = Field(default=None, ge=0, allow_inf_nan=False)

    def log_fields(self, *, operation: str) -> dict[str, Any]:
        """Return safe structured log fields; never includes prompts or credentials."""
        return {
            "provider_operation": operation,
            "provider_name": self.provider,
            "provider_model": self.model,
            "provider_latency_ms": self.latency_ms,
            "provider_outcome": self.outcome.value,
            "provider_schema_valid": self.schema_valid,
            "provider_retry_count": self.retry_count,
            "provider_request_id": self.request_id,
            "provider_input_tokens": self.input_tokens,
            "provider_output_tokens": self.output_tokens,
            "provider_audio_seconds": self.audio_seconds,
        }

    def emit_log(self, *, operation: str, failed: bool = False) -> None:
        logger.log(
            logging.WARNING if failed else logging.INFO,
            "provider_request_failed" if failed else "provider_request_completed",
            extra=self.log_fields(operation=operation),
        )


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
