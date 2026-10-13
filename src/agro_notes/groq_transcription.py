"""Groq speech-to-text adapter using the OpenAI-compatible audio endpoint."""

from __future__ import annotations

from time import perf_counter
from typing import Any

from openai import AsyncOpenAI

from .provider_contracts import ProviderMetadata, ProviderOutcome, TranscriptionResult
from .settings import Settings


class GroqTranscriber:
    def __init__(self, settings: Settings, client: Any | None = None) -> None:
        self.model = settings.groq_transcription_model
        self.client = client or AsyncOpenAI(
            api_key=settings.groq_api_key,
            base_url=settings.groq_base_url,
            timeout=30.0,
            max_retries=1,
        )

    async def close(self) -> None:
        await self.client.close()

    async def transcribe(self, audio: bytes) -> TranscriptionResult:
        started = perf_counter()
        try:
            response = await self.client.audio.transcriptions.create(
                model=self.model,
                file=("voice.ogg", audio, "audio/ogg"),
                language="pt",
                prompt="Transcreva em português brasileiro, preservando nomes e números.",
            )
        except Exception as exc:
            name = type(exc).__name__
            outcome = (
                ProviderOutcome.TIMEOUT if "timeout" in name.casefold()
                else ProviderOutcome.RATE_LIMITED if "rate" in name.casefold()
                else ProviderOutcome.ERROR
            )
            raise RuntimeError(f"Groq transcription failed ({outcome.value}).") from None
        request_id = getattr(response, "_request_id", None) or getattr(response, "id", None)
        return TranscriptionResult(
            text=response.text.strip(),
            language=getattr(response, "language", None) or "pt",
            confidence=None,
            metadata=ProviderMetadata(
                provider="groq",
                model=self.model,
                latency_ms=max(0.0, (perf_counter() - started) * 1000),
                outcome=ProviderOutcome.SUCCESS,
                request_id=str(request_id) if request_id else None,
            ),
        )
