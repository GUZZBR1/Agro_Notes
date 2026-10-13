"""Transient, in-memory voice transcription in Brazilian Portuguese."""

from typing import Any, Protocol

from openai import AsyncOpenAI

from .provider_contracts import TranscriptionResult
from .settings import Settings


class Transcriber(Protocol):
    async def transcribe(self, audio: bytes) -> str | TranscriptionResult: ...


class OpenAITranscriber:
    def __init__(self, settings: Settings, client: Any | None = None) -> None:
        self.client = client or AsyncOpenAI(api_key=settings.openai_api_key, timeout=30.0, max_retries=1)
        self.model = settings.openai_transcription_model

    async def close(self) -> None:
        await self.client.close()

    async def transcribe(self, audio: bytes) -> str:
        result = await self.client.audio.transcriptions.create(
            model=self.model,
            file=("voice.ogg", audio, "audio/ogg"),
            language="pt",
            prompt="Transcreva em português brasileiro, preservando nomes e números.",
        )
        return result.text.strip()
