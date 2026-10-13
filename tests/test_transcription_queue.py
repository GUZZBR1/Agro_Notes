import asyncio
import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from agro_notes.groq_transcription import GroqTranscriptionError
from agro_notes.provider_contracts import ProviderMetadata, ProviderOutcome, TranscriptionErrorClass
from agro_notes.settings import Settings
from agro_notes.telegram_bot import BotReply, DurableTranscriptionQueue


class QueueProcessor:
    def __init__(self):
        self.rows = []
        self.receive = AsyncMock(return_value=BotReply("Evento registrado."))
        self.deliveries = []

    async def persist_transcription_state(self, user_id, **values):
        self.rows.append(
            {
                "message_id": f"{values['message_id']}:{values['state']}",
                "raw_text_ref": values["message_id"],
                "user_id": str(user_id),
                "command_id": f"tg:{user_id}:{values['message_id']}",
                "audio_ref": values["source_reference"],
                "captured_at": values["captured_at"],
                "received_at": values["received_at"],
                "state": values["state"],
                "transcript": values.get("transcript", ""),
                "response": values.get("response", ""),
                "pending_command_json": json.dumps(values["queue_metadata"]),
            }
        )

    async def transcription_job(self, message_id):
        return next((row for row in reversed(self.rows) if row["raw_text_ref"] == message_id), None)

    async def transcription_jobs(self):
        latest = {}
        for row in self.rows:
            latest[row["raw_text_ref"]] = row
        active = DurableTranscriptionQueue._active_states
        return [row for row in latest.values() if row["state"] in active]

    async def mark_transcription_delivered(self, message_id, **values):
        self.deliveries.append((message_id, values))
        job = await self.transcription_job(message_id)
        job["state"] = "TRANSCRIPTION_DELIVERED"
        job["response"] = values["response"]

    async def bind_confirmation(self, *args, **kwargs):
        return None


def make_error(error_class, *, retry_after=None, reset=None):
    return GroqTranscriptionError(
        ProviderMetadata(
            provider="groq",
            model="whisper-large-v3-turbo",
            latency_ms=1,
            outcome=(
                ProviderOutcome.RATE_LIMITED
                if "RATE_LIMIT" in error_class.value or "QUOTA" in error_class.value
                else ProviderOutcome.TIMEOUT
            ),
            error_class=error_class,
            status_code=429 if error_class in {
                TranscriptionErrorClass.TEMPORARY_RATE_LIMIT,
                TranscriptionErrorClass.DAILY_QUOTA_EXHAUSTED,
                TranscriptionErrorClass.UNKNOWN_RATE_LIMIT,
            } else None,
            retry_after_seconds=retry_after,
            reset_requests_seconds=reset,
        )
    )


def voice_message(user_id=42, chat_id=100, message_id=10, file_id="telegram-file"):
    return SimpleNamespace(
        from_user=SimpleNamespace(id=user_id),
        chat=SimpleNamespace(id=chat_id, type="private"),
        message_id=message_id,
        date=datetime(2026, 10, 13, tzinfo=UTC),
        voice=SimpleNamespace(file_id=file_id),
    )


def bot_stub():
    async def download_file(_path, *, destination):
        destination.write(b"ogg-audio")

    sent = SimpleNamespace(
        chat=SimpleNamespace(id=100),
        message_id=101,
        edit_reply_markup=AsyncMock(),
    )
    return SimpleNamespace(
        get_file=AsyncMock(return_value=SimpleNamespace(file_path="voice.ogg")),
        download_file=download_file,
        send_message=AsyncMock(return_value=sent),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "first_error",
    [
        make_error(TranscriptionErrorClass.TEMPORARY_RATE_LIMIT, retry_after=3),
        TimeoutError("network details must not reach the user"),
    ],
)
async def test_temporary_rate_limit_and_timeout_retry_after_restart(first_error):
    processor = QueueProcessor()
    transcriber = SimpleNamespace(
        transcribe=AsyncMock(side_effect=[first_error, SimpleNamespace(text="relato da fazenda")])
    )
    settings = Settings(TELEGRAM_ALLOWED_USER_IDS="42", GROQ_RETRY_BASE_SECONDS=5, GROQ_MAX_RETRIES=2)
    queue = DurableTranscriptionQueue(processor, settings, transcriber)
    bot = bot_stub()

    response = await queue.submit(voice_message(), bot, 42)
    assert response and "vou tentar de novo automaticamente" in response.text
    pending = await processor.transcription_job("100:10")
    assert pending["state"] == "RETRY_WAIT"
    assert pending["audio_ref"] == "telegram-file"
    assert pending["command_id"] == "tg:42:100:10"
    assert json.loads(pending["pending_command_json"])["retry_count"] == 1

    metadata = json.loads(pending["pending_command_json"])
    metadata["next_attempt_at"] = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
    pending["pending_command_json"] = json.dumps(metadata)
    processor.rows[-1]["pending_command_json"] = pending["pending_command_json"]
    restarted_queue = DurableTranscriptionQueue(processor, settings, transcriber)
    await restarted_queue._process(pending, bot)

    transcriber.transcribe.assert_awaited_with(b"ogg-audio", retry_count=1)
    processor.receive.assert_awaited_once()
    assert processor.deliveries[0][0] == "100:10"
    assert bot.send_message.await_args.args[1].startswith("Pronto — consegui processar seu áudio.")


@pytest.mark.asyncio
async def test_retry_after_receive_failure_reuses_saved_transcript():
    processor = QueueProcessor()
    processor.receive = AsyncMock(side_effect=[RuntimeError("temporary sheets outage"), BotReply("Evento registrado.")])
    transcriber = SimpleNamespace(transcribe=AsyncMock(return_value=SimpleNamespace(text="relato já transcrito")))
    settings = Settings(TELEGRAM_ALLOWED_USER_IDS="42", GROQ_RETRY_BASE_SECONDS=5)
    queue = DurableTranscriptionQueue(processor, settings, transcriber)
    bot = bot_stub()

    await queue.submit(voice_message(), bot, 42)
    pending = await processor.transcription_job("100:10")
    assert pending["state"] == "RETRY_WAIT"
    assert pending["transcript"] == "relato já transcrito"
    metadata = json.loads(pending["pending_command_json"])
    metadata["next_attempt_at"] = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
    pending["pending_command_json"] = json.dumps(metadata)
    processor.rows[-1]["pending_command_json"] = pending["pending_command_json"]

    await DurableTranscriptionQueue(processor, settings, transcriber)._process(pending, bot)

    transcriber.transcribe.assert_awaited_once()
    assert processor.receive.await_count == 2
    assert processor.deliveries[0][1]["transcript"] == "relato já transcrito"


@pytest.mark.asyncio
async def test_daily_quota_blocks_audio_without_a_short_retry_loop():
    processor = QueueProcessor()
    transcriber = SimpleNamespace(
        transcribe=AsyncMock(
            side_effect=make_error(TranscriptionErrorClass.DAILY_QUOTA_EXHAUSTED, reset=3600)
        )
    )
    queue = DurableTranscriptionQueue(processor, Settings(TELEGRAM_ALLOWED_USER_IDS="42"), transcriber)
    response = await queue.submit(voice_message(), bot_stub(), 42)

    assert response and "cota diária" in response.text
    blocked = await processor.transcription_job("100:10")
    assert blocked["state"] == "DAILY_QUOTA_BLOCKED"
    assert blocked["audio_ref"] == "telegram-file"
    assert transcriber.transcribe.await_count == 1
    assert len(await processor.transcription_jobs()) == 1
    assert not queue._is_due(blocked)


def test_invalid_daily_reset_uses_safe_fallback_delay():
    queue = DurableTranscriptionQueue(
        QueueProcessor(), Settings(TELEGRAM_ALLOWED_USER_IDS="42", GROQ_DAILY_QUOTA_RETRY_SECONDS=7200),
        SimpleNamespace(),
    )
    assert queue._daily_delay(make_error(TranscriptionErrorClass.DAILY_QUOTA_EXHAUSTED, reset=0)) == 7200


def test_retry_after_is_honored_above_exponential_backoff():
    queue = DurableTranscriptionQueue(
        QueueProcessor(), Settings(TELEGRAM_ALLOWED_USER_IDS="42"), SimpleNamespace()
    )
    assert queue._retry_delay(1, 120) == 120


@pytest.mark.asyncio
async def test_retry_limit_fails_without_an_infinite_loop():
    processor = QueueProcessor()
    repeated = make_error(TranscriptionErrorClass.UNKNOWN_RATE_LIMIT)
    transcriber = SimpleNamespace(transcribe=AsyncMock(side_effect=[repeated, repeated]))
    queue = DurableTranscriptionQueue(
        processor,
        Settings(TELEGRAM_ALLOWED_USER_IDS="42", GROQ_MAX_RETRIES=1),
        transcriber,
    )
    await queue.submit(voice_message(), bot_stub(), 42)
    pending = await processor.transcription_job("100:10")
    metadata = json.loads(pending["pending_command_json"])
    metadata["next_attempt_at"] = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
    pending["pending_command_json"] = json.dumps(metadata)
    processor.rows[-1]["pending_command_json"] = pending["pending_command_json"]

    await DurableTranscriptionQueue(processor, queue.settings, transcriber)._process(pending, bot_stub())

    failed = await processor.transcription_job("100:10")
    assert failed["state"] == "FAILED"
    assert transcriber.transcribe.await_count == 2
    assert await processor.transcription_jobs() == []


@pytest.mark.asyncio
async def test_two_users_keep_independent_transcription_jobs():
    processor = QueueProcessor()
    transcriber = SimpleNamespace(transcribe=AsyncMock(return_value=SimpleNamespace(text="relato")))
    queue = DurableTranscriptionQueue(processor, Settings(TELEGRAM_ALLOWED_USER_IDS="42,43"), transcriber)
    bot = bot_stub()

    await asyncio.gather(
        queue.submit(voice_message(user_id=42, message_id=10, file_id="file-a"), bot, 42),
        queue.submit(voice_message(user_id=43, message_id=11, file_id="file-b"), bot, 43),
    )

    assert transcriber.transcribe.await_count == 2
    assert {row["command_id"] for row in processor.rows if row["state"] == "TRANSCRIPTION_DELIVERED"} == {
        "tg:42:100:10",
        "tg:43:100:11",
    }


@pytest.mark.asyncio
async def test_duplicate_delivery_does_not_create_another_transcription_job():
    processor = QueueProcessor()
    transcriber = SimpleNamespace(transcribe=AsyncMock(return_value=SimpleNamespace(text="relato")))
    queue = DurableTranscriptionQueue(processor, Settings(TELEGRAM_ALLOWED_USER_IDS="42"), transcriber)
    await processor.persist_transcription_state(
        42,
        message_id="100:10",
        captured_at=datetime.now(UTC).isoformat(),
        received_at=datetime.now(UTC).isoformat(),
        source_reference="telegram-file",
        state="RETRY_WAIT",
        queue_metadata={"retry_count": 1, "next_attempt_at": "2099-01-01T00:00:00+00:00"},
    )

    response = await queue.submit(voice_message(), bot_stub(), 42)

    assert response is None
    transcriber.transcribe.assert_not_awaited()
    assert len(processor.rows) == 1


@pytest.mark.asyncio
async def test_startup_recovers_interrupted_processing_state():
    processor = QueueProcessor()
    await processor.persist_transcription_state(
        42,
        message_id="100:10",
        captured_at=datetime.now(UTC).isoformat(),
        received_at=datetime.now(UTC).isoformat(),
        source_reference="telegram-file",
        state="PROCESSING_TRANSCRIPTION",
        queue_metadata={"retry_count": 1},
    )
    processed = asyncio.Event()

    async def transcribe(_audio, *, retry_count=0):
        processed.set()
        return SimpleNamespace(text="recuperado após reinício")

    queue = DurableTranscriptionQueue(
        processor,
        Settings(TELEGRAM_ALLOWED_USER_IDS="42"),
        SimpleNamespace(transcribe=transcribe),
    )
    bot = bot_stub()
    await queue.start(bot)
    await asyncio.wait_for(processed.wait(), timeout=2)
    await queue.close()

    assert processor.receive.await_count == 1
    assert processor.deliveries[0][1]["transcript"] == "recuperado após reinício"
