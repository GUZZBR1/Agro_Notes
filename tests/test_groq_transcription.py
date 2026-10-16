from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from openai import RateLimitError

from agro_notes.groq_transcription import GroqTranscriber
from agro_notes.provider_contracts import ProviderOutcome, TranscriptionErrorClass
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
    assert error.value.metadata.error_class is TranscriptionErrorClass.TRANSIENT_NETWORK_ERROR


@pytest.mark.parametrize(
    ("headers", "body", "expected"),
    [
        (
            {
                "x-ratelimit-limit-requests": "1000",
                "x-ratelimit-remaining-requests": "0",
                "x-ratelimit-reset-requests": "5h",
            },
            {},
            TranscriptionErrorClass.DAILY_QUOTA_EXHAUSTED,
        ),
        (
            {"x-ratelimit-remaining-tokens": "0", "x-ratelimit-reset-tokens": "12s", "retry-after": "12"},
            {},
            TranscriptionErrorClass.TEMPORARY_RATE_LIMIT,
        ),
        ({"retry-after": "3"}, {}, TranscriptionErrorClass.UNKNOWN_RATE_LIMIT),
        (
            {},
            {"error": {"code": "requests_per_day_exceeded", "message": "private provider text"}},
            TranscriptionErrorClass.DAILY_QUOTA_EXHAUSTED,
        ),
    ],
)
async def test_groq_rate_limit_classification_uses_evidence(headers, body, expected):
    response = httpx.Response(429, headers=headers, request=httpx.Request("POST", "https://api.groq.com"))
    exc = RateLimitError("safe test error", response=response, body=body)
    create = AsyncMock(side_effect=exc)
    client = SimpleNamespace(audio=SimpleNamespace(transcriptions=SimpleNamespace(create=create)), close=AsyncMock())
    transcriber = GroqTranscriber(Settings(GROQ_API_KEY="test-key"), client)

    with pytest.raises(RuntimeError) as raised:
        await transcriber.transcribe(b"ogg-audio")

    assert raised.value.metadata.error_class is expected
    assert raised.value.metadata.status_code == 429
    assert "private provider text" not in str(raised.value)
    if headers.get("retry-after"):
        assert raised.value.metadata.retry_after_seconds == float(headers["retry-after"])
