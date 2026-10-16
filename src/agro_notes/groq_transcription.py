"""Groq speech-to-text adapter using the OpenAI-compatible audio endpoint."""

from __future__ import annotations

import email.utils
import math
import re
import time
from time import perf_counter
from typing import Any

from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI, RateLimitError

from .provider_contracts import (
    ProviderMetadata,
    ProviderOutcome,
    TranscriptionErrorClass,
    TranscriptionResult,
)
from .settings import Settings


class GroqTranscriptionError(RuntimeError):
    def __init__(self, metadata: ProviderMetadata) -> None:
        self.metadata = metadata
        super().__init__(f"Groq transcription failed ({metadata.outcome.value}).")


def _duration_seconds(value: str | None) -> float | None:
    if not value:
        return None
    try:
        numeric = float(value)
    except ValueError:
        numeric = math.nan
    if math.isfinite(numeric) and numeric >= 0:
        return numeric
    parts = re.findall(r"(\d+(?:\.\d+)?)([hms])", value.casefold())
    if not parts or "".join(number + unit for number, unit in parts) != value.casefold().replace(" ", ""):
        return None
    scales = {"h": 3600, "m": 60, "s": 1}
    seconds = sum(float(number) * scales[unit] for number, unit in parts)
    return seconds if math.isfinite(seconds) and seconds >= 0 else None


def _retry_after_seconds(headers: Any) -> float | None:
    value = headers.get("retry-after") if headers else None
    if not value:
        return None
    seconds = _duration_seconds(str(value))
    if seconds is not None:
        return seconds
    try:
        retry_at = email.utils.parsedate_to_datetime(str(value))
        return max(0.0, retry_at.timestamp() - time.time())
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def _explicit_daily_body(body: Any) -> bool:
    if not isinstance(body, dict):
        return False
    error = body.get("error")
    if not isinstance(error, dict):
        return False
    code = str(error.get("code") or "").casefold().replace("-", "_")
    message = str(error.get("message") or "").casefold()
    return code in {"daily_quota_exceeded", "requests_per_day_exceeded", "rpd_exceeded"} or any(
        marker in message for marker in ("requests per day", "daily quota", "daily limit", "rpd limit")
    )


def _classify_exception(exc: Exception) -> tuple[TranscriptionErrorClass, int | None, float | None, float | None]:
    if isinstance(exc, APITimeoutError) or isinstance(exc, (TimeoutError,)):
        return TranscriptionErrorClass.TRANSIENT_NETWORK_ERROR, None, None, None
    if isinstance(exc, APIConnectionError):
        return TranscriptionErrorClass.TRANSIENT_NETWORK_ERROR, None, None, None
    if not isinstance(exc, APIStatusError):
        return TranscriptionErrorClass.PROVIDER_ERROR, None, None, None

    status = exc.status_code
    headers = exc.response.headers
    retry_after = _retry_after_seconds(headers)
    reset_requests = _duration_seconds(headers.get("x-ratelimit-reset-requests"))
    if status == 429 or isinstance(exc, RateLimitError):
        limit_requests = _duration_seconds(headers.get("x-ratelimit-limit-requests"))
        remaining_requests = _duration_seconds(headers.get("x-ratelimit-remaining-requests"))
        remaining_tokens = _duration_seconds(headers.get("x-ratelimit-remaining-tokens"))
        has_daily_headers = (
            limit_requests is not None
            and limit_requests > 0
            and remaining_requests is not None
            and remaining_requests <= 0
            and reset_requests is not None
            and reset_requests > 0
        )
        if has_daily_headers or _explicit_daily_body(exc.body):
            kind = TranscriptionErrorClass.DAILY_QUOTA_EXHAUSTED
        elif remaining_tokens is not None and remaining_tokens <= 0:
            kind = TranscriptionErrorClass.TEMPORARY_RATE_LIMIT
        else:
            kind = TranscriptionErrorClass.UNKNOWN_RATE_LIMIT
        return kind, status, retry_after, reset_requests
    if status in {401, 403}:
        kind = TranscriptionErrorClass.AUTHENTICATION_ERROR
    elif status in {400, 404, 413, 422}:
        kind = TranscriptionErrorClass.INVALID_REQUEST
    else:
        kind = TranscriptionErrorClass.PROVIDER_ERROR
    return kind, status, retry_after, reset_requests


class GroqTranscriber:
    def __init__(self, settings: Settings, client: Any | None = None) -> None:
        self.model = settings.groq_transcription_model
        self.client = client or AsyncOpenAI(
            api_key=settings.groq_api_key,
            base_url=settings.groq_base_url,
            timeout=30.0,
            max_retries=0,
        )

    async def close(self) -> None:
        await self.client.close()

    async def transcribe(self, audio: bytes, *, retry_count: int = 0) -> TranscriptionResult:
        started = perf_counter()
        try:
            response = await self.client.audio.transcriptions.create(
                model=self.model,
                file=("voice.ogg", audio, "audio/ogg"),
                language="pt",
                prompt="Transcreva em português brasileiro, preservando nomes e números.",
            )
        except Exception as exc:
            error_class, status_code, retry_after, reset_requests = _classify_exception(exc)
            rate_limited = error_class in {
                TranscriptionErrorClass.TEMPORARY_RATE_LIMIT,
                TranscriptionErrorClass.DAILY_QUOTA_EXHAUSTED,
                TranscriptionErrorClass.UNKNOWN_RATE_LIMIT,
            }
            outcome = (
                ProviderOutcome.RATE_LIMITED
                if rate_limited
                else ProviderOutcome.TIMEOUT
                if error_class is TranscriptionErrorClass.TRANSIENT_NETWORK_ERROR
                else ProviderOutcome.ERROR
            )
            metadata = ProviderMetadata(
                provider="groq",
                model=self.model,
                latency_ms=max(0.0, (perf_counter() - started) * 1000),
                outcome=outcome,
                error_class=error_class,
                status_code=status_code,
                retry_after_seconds=retry_after,
                reset_requests_seconds=reset_requests,
                retry_count=retry_count,
                request_id=getattr(exc, "request_id", None),
            )
            metadata.emit_log(operation="transcribe", failed=True)
            raise GroqTranscriptionError(metadata) from None
        request_id = getattr(response, "_request_id", None) or getattr(response, "id", None)
        metadata = ProviderMetadata(
            provider="groq",
            model=self.model,
            latency_ms=max(0.0, (perf_counter() - started) * 1000),
            outcome=ProviderOutcome.SUCCESS,
            retry_count=retry_count,
            request_id=str(request_id) if request_id else None,
            audio_seconds=getattr(response, "duration", None),
        )
        metadata.emit_log(operation="transcribe")
        return TranscriptionResult(
            text=response.text.strip(),
            language=getattr(response, "language", None) or "pt",
            confidence=None,
            metadata=metadata,
        )
