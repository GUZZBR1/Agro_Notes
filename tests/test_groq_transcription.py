from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from agro_notes.groq_transcription import GroqTranscriber
from agro_notes.provider_contracts import ProviderOutcome
from agro_notes.settings import Settings


async def test_groq_transcriber_uses_portuguese_ogg_and_returns_neutral_metadata():
    create = AsyncMock(return_value=SimpleNamespace(text="  A vaca 184.  ", language="pt", id="request-1"))
    client = SimpleNamespace(audio=SimpleNamespace(transcriptions=SimpleNamespace(create=create)), close=AsyncMock())
    transcriber = GroqTranscriber(Settings(GROQ_API_KEY="test-key"), client)

    result = await transcriber.transcribe(b"ogg-audio")

    assert result.text == "A vaca 184."
    assert result.language == "pt"
    assert result.confidence is None
    assert result.metadata.provider == "groq"
    assert result.metadata.outcome is ProviderOutcome.SUCCESS
    assert result.metadata.request_id == "request-1"
    create.assert_awaited_once_with(
        model="whisper-large-v3-turbo",
        file=("voice.ogg", b"ogg-audio", "audio/ogg"),
        language="pt",
        prompt="Transcreva em português brasileiro, preservando nomes e números.",
    )


async def test_groq_transcriber_hides_provider_error_details():
    create = AsyncMock(side_effect=TimeoutError("secret body must not escape"))
    client = SimpleNamespace(audio=SimpleNamespace(transcriptions=SimpleNamespace(create=create)), close=AsyncMock())
    transcriber = GroqTranscriber(Settings(GROQ_API_KEY="test-key"), client)

    with pytest.raises(RuntimeError, match="TIMEOUT") as error:
        await transcriber.transcribe(b"ogg-audio")
    assert "secret body" not in str(error.value)
