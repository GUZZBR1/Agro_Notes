"""Transient, in-memory voice transcription in Brazilian Portuguese."""

from time import perf_counter
from typing import Any, Protocol

from openai import AsyncOpenAI

from .provider_contracts import ProviderMetadata, ProviderOutcome, TranscriptionResult
from .settings import Settings


class Transcriber(Protocol):
    async def transcribe(self, audio: bytes, *, retry_count: int = 0) -> TranscriptionResult: ...


class OpenAITranscriber:
    def __init__(self, settings: Settings, client: Any | None = None) -> None:
        self.client = client or AsyncOpenAI(api_key=settings.openai_api_key, timeout=30.0, max_retries=0)
        self.model = settings.openai_transcription_model

    async def close(self) -> None:
        await self.client.close()

    async def transcribe(self, audio: bytes, *, retry_count: int = 0) -> TranscriptionResult:
        started = perf_counter()
        try:
            result = await self.client.audio.transcriptions.create(
                model=self.model,
                file=("voice.ogg", audio, "audio/ogg"),
                language="pt",
                prompt="Transcreva em português brasileiro, preservando nomes e números.",
            )
        except Exception as exc:
            name = type(exc).__name__.casefold()
            outcome = (
                ProviderOutcome.TIMEOUT if "timeout" in name
                else ProviderOutcome.RATE_LIMITED if "rate" in name
                else ProviderOutcome.ERROR
            )
            ProviderMetadata(
                provider="openai", model=self.model,
                latency_ms=max(0.0, (perf_counter() - started) * 1000), outcome=outcome, retry_count=retry_count,
            ).emit_log(operation="transcribe", failed=True)
            raise RuntimeError(f"OpenAI transcription failed ({outcome.value}).") from None
        request_id = getattr(result, "_request_id", None) or getattr(result, "id", None)
        metadata = ProviderMetadata(
            provider="openai",
            model=self.model,
            latency_ms=max(0.0, (perf_counter() - started) * 1000),
            outcome=ProviderOutcome.SUCCESS,
            retry_count=retry_count,
            request_id=str(request_id) if request_id else None,
            audio_seconds=getattr(result, "duration", None),
        )
        metadata.emit_log(operation="transcribe")
        return TranscriptionResult(
            text=result.text.strip(),
            language=getattr(result, "language", None) or "pt",
            confidence=None,
            metadata=metadata,
        )
