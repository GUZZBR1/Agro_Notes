"""Telegram transport. Domain decisions and persistence belong to the processor."""

import asyncio
import io
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

from aiogram import Bot, Dispatcher, F, Router
from aiogram.exceptions import TelegramNetworkError, TelegramRetryAfter, TelegramServerError
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from openai import APIConnectionError, APIStatusError, RateLimitError

from .provider_contracts import TranscriptionErrorClass
from .provider_factory import build_transcriber
from .settings import Settings
from .transcription import Transcriber

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BotReply:
    text: str
    pending_id: str | None = None
    remove_keyboard: bool = False


class Processor(Protocol):
    async def receive(
        self,
        user_id: int,
        text: str,
        *,
        source: str,
        message_id: str,
        captured_at: str,
        device_timezone: str | None,
        source_reference: str | None,
        received_at: str | None = None,
    ) -> BotReply: ...

    async def record_ingress_failure(
        self,
        user_id: int,
        *,
        message_id: str,
        captured_at: str,
        received_at: str,
        source_reference: str | None,
        failure_code: str,
        response: str,
    ) -> None: ...

    async def persist_transcription_state(
        self, user_id: int, *, message_id: str, captured_at: str, received_at: str,
        source_reference: str, state: str, queue_metadata: dict, response: str = "", transcript: str = "",
    ) -> None: ...

    async def transcription_job(self, message_id: str) -> dict | None: ...

    async def transcription_jobs(self) -> list[dict]: ...

    async def mark_transcription_delivered(
        self, message_id: str, *, queue_metadata: dict, transcript: str, response: str
    ) -> None: ...

    async def bind_confirmation(self, user_id: int, pending_id: str, *, chat_id: int, message_id: int) -> None: ...

    async def confirm(
        self, user_id: int, pending_id: str, *, source_chat_id: int | None = None, source_message_id: int | None = None
    ) -> BotReply: ...

    async def cancel(
        self, user_id: int, pending_id: str, *, source_chat_id: int | None = None, source_message_id: int | None = None
    ) -> BotReply: ...


class DurableTranscriptionQueue:
    """Recoverable Telegram voice jobs backed by the existing conversation journal."""

    _active_states = {
        "PENDING_TRANSCRIPTION", "PROCESSING_TRANSCRIPTION", "RETRY_WAIT",
        "DAILY_QUOTA_BLOCKED", "TRANSCRIBED",
    }
    _poll_seconds = 5

    def __init__(self, processor: Processor, settings: Settings, transcriber: Transcriber) -> None:
        self.processor = processor
        self.settings = settings
        self.transcriber = transcriber
        self._locks: dict[int, asyncio.Lock] = {}
        self._semaphore = asyncio.Semaphore(2)
        self._task: asyncio.Task | None = None
        self._stopping = asyncio.Event()

    def _lock_for(self, user_id: int) -> asyncio.Lock:
        return self._locks.setdefault(user_id, asyncio.Lock())

    async def start(self, bot: Bot) -> None:
        for job in await self.processor.transcription_jobs():
            if job.get("state") == "PROCESSING_TRANSCRIPTION":
                metadata = self._metadata(job)
                await self._save(job, "RETRY_WAIT", metadata, next_attempt_at=datetime.now(UTC).isoformat())
        self._stopping.clear()
        self._task = asyncio.create_task(self._run(bot), name="groq-transcription-recovery")

    async def close(self) -> None:
        self._stopping.set()
        if self._task:
            await self._task

    async def submit(self, message: Message, bot: Bot, user_id: int) -> BotReply | None:
        voice = message.voice
        if voice is None:
            return None
        message_id = f"{message.chat.id}:{message.message_id}"
        async with self._semaphore:
            async with self._lock_for(user_id):
                prior = await self.processor.transcription_job(message_id)
                if prior:
                    if prior.get("state") in self._active_states:
                        return None
                    return BotReply(str(prior.get("response") or "Este áudio já foi processado."))
                received_at = datetime.now(UTC).isoformat()
                metadata = {
                    "retry_count": 0,
                    "notification_sent": False,
                    "provider": self.settings.transcription_provider,
                    "model": self.settings.transcription_model,
                }
                await self.processor.persist_transcription_state(
                    user_id,
                    message_id=message_id,
                    captured_at=message.date.astimezone(UTC).isoformat(),
                    received_at=received_at,
                    source_reference=voice.file_id,
                    state="PENDING_TRANSCRIPTION",
                    queue_metadata=metadata,
                )
                job = await self.processor.transcription_job(message_id)
                if not job:
                    return BotReply("Não consegui salvar seu áudio para processamento. Tente novamente.")
                return await self._process_locked(job, bot, user_id)

    async def _run(self, bot: Bot) -> None:
        while not self._stopping.is_set():
            try:
                jobs = await self.processor.transcription_jobs()
            except Exception as exc:
                logger.error("Transcription recovery scan failed (%s)", type(exc).__name__)
                jobs = []
            due = [job for job in jobs if self._is_due(job)]
            if due:
                await asyncio.gather(*(self._process(job, bot) for job in due), return_exceptions=True)
            try:
                await asyncio.wait_for(self._stopping.wait(), timeout=self._poll_seconds)
            except TimeoutError:
                pass

    async def _process(self, job: dict, bot: Bot) -> None:
        try:
            user_id = int(job["user_id"])
        except (KeyError, ValueError, TypeError):
            return
        async with self._semaphore, self._lock_for(user_id):
            try:
                latest = await self.processor.transcription_job(str(job.get("raw_text_ref", "")))
                if latest and self._is_due(latest):
                    result = await self._process_locked(latest, bot, user_id, resumed=True)
                    if result:
                        if latest.get("state") == "TRANSCRIBED" and self._metadata(latest).get("awaiting_delivery"):
                            await self._send_background_reply(bot, latest, user_id, result)
                        else:
                            await send_bot_reply(
                                bot, self.processor,
                                int(str(latest["raw_text_ref"]).split(":", 1)[0]), user_id, result,
                            )
            except Exception as exc:
                logger.error(
                    "Transcription job failed command=%s (%s)",
                    job.get("command_id", ""),
                    type(exc).__name__,
                )

    async def _process_locked(self, job: dict, bot: Bot, user_id: int, *, resumed: bool = False) -> BotReply | None:
        message_id = str(job.get("raw_text_ref") or "")
        source_reference = str(job.get("audio_ref") or "")
        captured_at = str(job.get("captured_at") or "")
        received_at = str(job.get("received_at") or datetime.now(UTC).isoformat())
        state = str(job.get("state") or "PENDING_TRANSCRIPTION")
        metadata = self._metadata(job)
        notification_already_sent = bool(metadata.get("notification_sent"))
        if state == "TRANSCRIBED" and metadata.get("awaiting_delivery"):
            pending_id = metadata.get("pending_id")
            return BotReply(str(job.get("response") or ""), str(pending_id) if pending_id else None)
        if state in {"PROCESSING_TRANSCRIPTION", "TRANSCRIBED", "RETRY_WAIT"}:
            # A restart after provider success safely reuses the saved transcript.
            transcript = str(job.get("transcript") or "") if state == "TRANSCRIBED" else ""
            if state == "RETRY_WAIT":
                transcript = str(job.get("transcript") or "")
        else:
            transcript = ""
        try:
            if not transcript:
                metadata.pop("next_attempt_at", None)
                await self._save(job, "PROCESSING_TRANSCRIPTION", metadata, transcript=transcript)
                audio = await self._download_file(bot, source_reference)
                result = await self.transcriber.transcribe(audio, retry_count=int(metadata.get("retry_count", 0)))
                transcript = result.text if hasattr(result, "text") else str(result)
                transcript = transcript.strip()
                if not transcript:
                    raise ValueError("empty transcript")
                await self._save(job, "TRANSCRIBED", metadata, transcript=transcript)
            result = await self.processor.receive(
                user_id,
                transcript,
                source="voice",
                message_id=message_id,
                captured_at=captured_at,
                device_timezone=None,
                source_reference=source_reference,
                received_at=received_at,
            )
            if result.text.startswith("Não consegui concluir o registro."):
                await self._save(job, "FAILED", metadata, transcript=transcript, response=result.text)
                return BotReply(result.text, result.pending_id)
            if resumed:
                result = BotReply("Pronto — consegui processar seu áudio.\n\n" + result.text, result.pending_id)
            if result.pending_id:
                metadata["pending_id"] = result.pending_id
            metadata["awaiting_delivery"] = True
            await self._save(
                job, "TRANSCRIBED", metadata, transcript=transcript, response=result.text
            )
            return result
        except Exception as exc:
            error_class = self._error_class(exc)
            retry_count = int(metadata.get("retry_count", 0))
            if error_class is TranscriptionErrorClass.DAILY_QUOTA_EXHAUSTED:
                delay = self._daily_delay(exc)
                metadata.update(
                    retry_count=retry_count,
                    next_attempt_at=(datetime.now(UTC) + timedelta(seconds=delay)).isoformat(),
                    notification_sent=True,
                    error_class=error_class.value,
                    retry_after_seconds=getattr(getattr(exc, "metadata", None), "retry_after_seconds", None),
                    reset_requests_seconds=getattr(getattr(exc, "metadata", None), "reset_requests_seconds", None),
                    status_code=getattr(getattr(exc, "metadata", None), "status_code", None),
                )
                response = (
                    "Sua cota diária de transcrição foi atingida. Seu áudio ficou salvo e será processado "
                    "quando a cota estiver disponível novamente."
                )
                await self._save(job, "DAILY_QUOTA_BLOCKED", metadata, transcript=transcript, response=response)
                return BotReply(response) if not notification_already_sent else None

            retryable = isinstance(
                exc, (TelegramNetworkError, TelegramServerError, TelegramRetryAfter)
            ) or error_class in {
                TranscriptionErrorClass.TEMPORARY_RATE_LIMIT,
                TranscriptionErrorClass.UNKNOWN_RATE_LIMIT,
                TranscriptionErrorClass.TRANSIENT_NETWORK_ERROR,
            } or (
                error_class is TranscriptionErrorClass.PROVIDER_ERROR
                and (
                    getattr(getattr(exc, "metadata", None), "status_code", 0) >= 500
                    or bool(transcript)
                )
            )
            if retryable and retry_count < self.settings.groq_max_retries:
                retry_count += 1
                retry_after = getattr(getattr(exc, "metadata", None), "retry_after_seconds", None)
                delay = self._retry_delay(retry_count, retry_after)
                metadata.update(
                    retry_count=retry_count,
                    next_attempt_at=(datetime.now(UTC) + timedelta(seconds=delay)).isoformat(),
                    notification_sent=True,
                    error_class=error_class.value,
                    retry_after_seconds=retry_after,
                    status_code=getattr(getattr(exc, "metadata", None), "status_code", None),
                    reset_requests_seconds=getattr(getattr(exc, "metadata", None), "reset_requests_seconds", None),
                )
                response = (
                    "O serviço está temporariamente ocupado. Espere alguns segundos que vou tentar de novo "
                    "automaticamente."
                )
                await self._save(job, "RETRY_WAIT", metadata, transcript=transcript, response=response)
                return BotReply(response) if not notification_already_sent else None

            response = (
                "O áudio é grande demais para processar. Envie um áudio menor, por favor."
                if isinstance(exc, VoiceTooLarge)
                else "Não consegui recuperar o áudio salvo. Envie o áudio novamente, por favor."
            )
            metadata.update(error_class=error_class.value)
            await self._save(job, "FAILED", metadata, transcript=transcript, response=response)
            return BotReply(response)

    async def _download_file(self, bot: Bot, file_id: str) -> bytes:
        remote = await bot.get_file(file_id)
        with BoundedAudioBuffer(self.settings.voice_max_bytes) as buffer:
            await bot.download_file(remote.file_path, destination=buffer)
            return buffer.getvalue()

    async def _save(
        self, job: dict, state: str, metadata: dict, *, transcript: str = "", response: str = "",
        next_attempt_at: str | None = None,
    ) -> None:
        if next_attempt_at:
            metadata["next_attempt_at"] = next_attempt_at
        logger.info(
            "transcription_status_transition",
            extra={
                "provider": self.settings.transcription_provider,
                "model": self.settings.transcription_model,
                "error_class": metadata.get("error_class"),
                "retry_count": int(metadata.get("retry_count", 0)),
                "retry_after_seconds": metadata.get("retry_after_seconds"),
                "transcription_status_from": job.get("state", "UNKNOWN"),
                "transcription_status_to": state,
                "command_id": job.get("command_id", ""),
            },
        )
        await self.processor.persist_transcription_state(
            int(job["user_id"]),
            message_id=str(job["raw_text_ref"]),
            captured_at=str(job.get("captured_at") or ""),
            received_at=str(job.get("received_at") or datetime.now(UTC).isoformat()),
            source_reference=str(job.get("audio_ref") or ""),
            state=state,
            queue_metadata=metadata,
            transcript=transcript,
            response=response,
        )
        job.update(
            state=state,
            transcript=transcript,
            response=response,
            pending_command_json=json.dumps(metadata, ensure_ascii=False, sort_keys=True),
        )

    @staticmethod
    def _metadata(job: dict) -> dict:
        value = job.get("pending_command_json") or "{}"
        if isinstance(value, dict):
            return dict(value)
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except (TypeError, json.JSONDecodeError):
            return {}

    @staticmethod
    def _error_class(exc: Exception) -> TranscriptionErrorClass:
        metadata = getattr(exc, "metadata", None)
        kind = getattr(metadata, "error_class", None)
        if kind:
            try:
                return TranscriptionErrorClass(kind)
            except ValueError:
                pass
        if isinstance(exc, (TimeoutError, ConnectionError)):
            return TranscriptionErrorClass.TRANSIENT_NETWORK_ERROR
        if isinstance(exc, APIConnectionError):
            return TranscriptionErrorClass.TRANSIENT_NETWORK_ERROR
        if isinstance(exc, RateLimitError) or (isinstance(exc, APIStatusError) and exc.status_code == 429):
            return TranscriptionErrorClass.UNKNOWN_RATE_LIMIT
        return TranscriptionErrorClass.PROVIDER_ERROR

    def _retry_delay(self, retry_count: int, retry_after: float | None) -> float:
        fallback = min(
            self.settings.groq_retry_base_seconds * (2 ** max(0, retry_count - 1)),
            self.settings.groq_retry_max_seconds,
        )
        if retry_after is None or retry_after < 0:
            return fallback
        return min(retry_after, self.settings.groq_retry_after_max_seconds)

    def _daily_delay(self, exc: Exception) -> float:
        metadata = getattr(exc, "metadata", None)
        reset = getattr(metadata, "reset_requests_seconds", None)
        if reset is None or reset <= 0:
            return self.settings.groq_daily_quota_retry_seconds
        return max(60.0, min(reset, 86400.0))

    @staticmethod
    def _is_due(job: dict) -> bool:
        state = job.get("state")
        metadata = DurableTranscriptionQueue._metadata(job)
        if state == "TRANSCRIBED" and metadata.get("awaiting_delivery"):
            value = metadata.get("next_attempt_at")
            if not value:
                return True
            try:
                when = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
                return when <= datetime.now(UTC)
            except (TypeError, ValueError):
                return False
        if job.get("state") in {
            "PENDING_TRANSCRIPTION", "PROCESSING_TRANSCRIPTION", "TRANSCRIBED"
        }:
            return True
        value = DurableTranscriptionQueue._metadata(job).get("next_attempt_at")
        if not value:
            return False
        try:
            when = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            return when <= datetime.now(UTC)
        except (TypeError, ValueError):
            return False

    async def _send_background_reply(self, bot: Bot, job: dict, user_id: int, result: BotReply) -> None:
        try:
            chat_id = int(str(job["raw_text_ref"]).split(":", 1)[0])
            await send_bot_reply(bot, self.processor, chat_id, user_id, result)
            await self._mark_delivered(job, result)
        except Exception as exc:
            logger.error("Could not send transcription result command=%s", job.get("command_id", ""))
            metadata = self._metadata(job)
            attempts = int(metadata.get("delivery_retry_count", 0)) + 1
            metadata.update(
                delivery_retry_count=attempts,
                next_attempt_at=(datetime.now(UTC) + timedelta(seconds=min(5 * (2 ** (attempts - 1)), 60))).isoformat(),
                delivery_error=type(exc).__name__,
            )
            await self._save(
                job, "TRANSCRIBED", metadata,
                transcript=str(job.get("transcript") or ""), response=result.text,
            )

    async def _mark_delivered(self, job: dict, result: BotReply) -> None:
        await self.processor.mark_transcription_delivered(
            str(job.get("raw_text_ref") or ""),
            queue_metadata=self._metadata(job),
            transcript=str(job.get("transcript") or ""),
            response=result.text,
        )

def is_allowed(user_id: int | None, settings: Settings) -> bool:
    return user_id is not None and user_id in settings.allowed_user_ids


class VoiceTooLarge(ValueError):
    pass


class BoundedAudioBuffer(io.BytesIO):
    """Enforce the byte cap even when Telegram's declared size is inaccurate."""

    def __init__(self, max_bytes: int) -> None:
        super().__init__()
        self.max_bytes = max_bytes

    def write(self, data: bytes) -> int:
        if self.tell() + len(data) > self.max_bytes:
            raise VoiceTooLarge("Audio exceeds configured limit")
        return super().write(data)


async def download_voice(bot: Bot, message: Message, max_bytes: int) -> bytes:
    voice = message.voice
    if voice is None:
        raise ValueError("Message has no voice")
    if voice.file_size is not None and voice.file_size > max_bytes:
        raise VoiceTooLarge("Audio exceeds configured limit")
    with BoundedAudioBuffer(max_bytes) as buffer:
        await bot.download(voice, destination=buffer)
        return buffer.getvalue()


async def send_bot_reply(bot: Bot, processor: Processor, chat_id: int, user_id: int, result: BotReply) -> None:
    markup = None
    if result.pending_id:
        if len(f"confirm:{result.pending_id}") > 64:
            result = BotReply("Não consegui vincular a confirmação. Envie o comando novamente.")
        else:
            markup = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(text="Confirmar", callback_data=f"confirm:{result.pending_id}"),
                        InlineKeyboardButton(text="Cancelar", callback_data=f"cancel:{result.pending_id}"),
                    ]
                ]
            )
    sent = await bot.send_message(chat_id, result.text, reply_markup=markup)
    if result.pending_id:
        try:
            await processor.bind_confirmation(
                user_id, result.pending_id, chat_id=sent.chat.id, message_id=sent.message_id
            )
        except Exception:
            await sent.edit_reply_markup(reply_markup=None)
            await bot.send_message(chat_id, "Não consegui vincular a confirmação. Envie o comando novamente.")


def build_router(
    processor: Processor,
    settings: Settings,
    transcriber: Transcriber | None = None,
    transcription_queue: DurableTranscriptionQueue | None = None,
) -> Router:
    router = Router(name="agro_notes")
    owns_transcriber = transcriber is None
    locks: dict[int, asyncio.Lock] = {}

    def lock_for(user_id: int) -> asyncio.Lock:
        return locks.setdefault(user_id, asyncio.Lock())

    @router.shutdown()
    async def close_transcriber() -> None:
        if owns_transcriber and transcriber is not None:
            close = getattr(transcriber, "close", None)
            if close:
                await close()

    async def reply(message: Message, user_id: int, result: BotReply) -> None:
        markup = None
        if result.pending_id:
            markup = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(text="Confirmar", callback_data=f"confirm:{result.pending_id}"),
                        InlineKeyboardButton(text="Cancelar", callback_data=f"cancel:{result.pending_id}"),
                    ]
                ]
            )
        if result.pending_id and len(f"confirm:{result.pending_id}") > 64:
            result = BotReply("Não consegui vincular a confirmação. Envie o comando novamente.")
            markup = None
        sent = await message.answer(result.text, reply_markup=markup)
        if result.pending_id:
            try:
                await processor.bind_confirmation(
                    user_id, result.pending_id, chat_id=sent.chat.id, message_id=sent.message_id
                )
            except Exception:
                await sent.edit_reply_markup(reply_markup=None)
                await message.answer("Não consegui vincular a confirmação. Envie o comando novamente.")

    async def authorize(message: Message) -> bool:
        if message.chat.type != "private":
            await message.answer("Por segurança, use o chat privado do bot para acessar dados da fazenda.")
            return False
        if not is_allowed(message.from_user.id if message.from_user else None, settings):
            await message.answer("Acesso não autorizado.")
            return False
        return True

    async def audit_voice_failure(
        message: Message, user_id: int, received_at: str, failure_code: str, response: str
    ) -> None:
        try:
            await processor.record_ingress_failure(
                user_id,
                message_id=f"{message.chat.id}:{message.message_id}",
                captured_at=message.date.astimezone(UTC).isoformat(),
                received_at=received_at,
                source_reference=message.voice.file_id if message.voice else None,
                failure_code=failure_code,
                response=response,
            )
        except Exception:
            logger.error("Could not audit failed voice message %s:%s", message.chat.id, message.message_id)

    @router.message(CommandStart())
    async def start(message: Message) -> None:
        if await authorize(message):
            await message.answer(
                "Envie um texto ou áudio com a movimentação da fazenda. "
                "Vou pedir esclarecimentos quando faltarem dados; alguns registros são gravados após validação "
                "e outros exigem sua confirmação."
            )

    @router.message(F.voice)
    async def voice(message: Message, bot: Bot) -> None:
        nonlocal transcriber
        if not await authorize(message):
            return
        assert message.from_user is not None
        user_id = message.from_user.id
        received_at = datetime.now(UTC).isoformat()
        async with lock_for(user_id):
            failure_code = "AUDIO_DOWNLOAD_FAILED"
            try:
                if transcription_queue is not None:
                    result = await transcription_queue.submit(message, bot, user_id)
                    if result is not None:
                        try:
                            await reply(message, user_id, result)
                            job = await processor.transcription_job(f"{message.chat.id}:{message.message_id}")
                            if (
                                job
                                and job.get("state") == "TRANSCRIBED"
                                and transcription_queue._metadata(job).get("awaiting_delivery")
                            ):
                                await transcription_queue._mark_delivered(job, result)
                        except Exception as exc:
                            logger.error(
                                "Could not deliver transcription result command=tg:%s:%s (%s)",
                                user_id, message.chat.id, type(exc).__name__,
                            )
                    return
                audio = await download_voice(bot, message, settings.voice_max_bytes)
                failure_code = "TRANSCRIPTION_FAILED"
                if transcriber is None:
                    transcriber = build_transcriber(settings)
                transcription = await transcriber.transcribe(audio)
                text = transcription.text if hasattr(transcription, "text") else transcription
                del audio
                if not text.strip():
                    response_text = "Não consegui entender o áudio. Envie novamente ou escreva a mensagem."
                    await audit_voice_failure(message, user_id, received_at, "EMPTY_TRANSCRIPT", response_text)
                    await message.answer(response_text)
                    return
                failure_code = "PROCESSING_FAILED"
                result = await processor.receive(
                    user_id,
                    text,
                    source="voice",
                    message_id=f"{message.chat.id}:{message.message_id}",
                    captured_at=message.date.astimezone(UTC).isoformat(),
                    device_timezone=None,
                    source_reference=message.voice.file_id if message.voice else None,
                    received_at=received_at,
                )
                await reply(message, user_id, result)
            except VoiceTooLarge:
                response_text = "Áudio muito grande. Envie um áudio menor."
                await audit_voice_failure(message, user_id, received_at, "VOICE_TOO_LARGE", response_text)
                await message.answer(response_text)
            except Exception as exc:
                logger.error(
                    "Voice processing failed message=%s:%s (%s)",
                    message.chat.id,
                    message.message_id,
                    type(exc).__name__,
                )
                response_text = "Não foi possível processar o áudio. Tente novamente ou envie um texto."
                await audit_voice_failure(message, user_id, received_at, failure_code, response_text)
                await message.answer(response_text)

    @router.message(F.text)
    async def text(message: Message) -> None:
        if not await authorize(message):
            return
        assert message.from_user is not None and message.text is not None
        user_id = message.from_user.id
        received_at = datetime.now(UTC).isoformat()
        async with lock_for(user_id):
            try:
                result = await processor.receive(
                    user_id,
                    message.text,
                    source="text",
                    message_id=f"{message.chat.id}:{message.message_id}",
                    captured_at=message.date.astimezone(UTC).isoformat(),
                    device_timezone=None,
                    source_reference=None,
                    received_at=received_at,
                )
                await reply(message, user_id, result)
            except Exception as exc:
                logger.error(
                    "Text processing failed message=%s:%s (%s)",
                    message.chat.id,
                    message.message_id,
                    type(exc).__name__,
                )
                await message.answer("Não foi possível processar a mensagem. Tente novamente.")

    @router.callback_query()
    async def callback(query: CallbackQuery) -> None:
        user_id = query.from_user.id
        if not is_allowed(user_id, settings):
            await query.answer("Acesso não autorizado.", show_alert=True)
            return
        if not isinstance(query.message, Message) or query.message.chat.type != "private":
            await query.answer("Use o chat privado do bot para acessar dados da fazenda.", show_alert=True)
            return
        action, _, pending_id = (query.data or "").partition(":")
        async with lock_for(user_id):
            if action not in {"confirm", "cancel"} or not pending_id or not isinstance(query.message, Message):
                await query.answer("Esta confirmação expirou ou não pertence a você.", show_alert=True)
                return
            try:
                method = processor.confirm if action == "confirm" else processor.cancel
                result = await method(
                    user_id,
                    pending_id,
                    source_chat_id=query.message.chat.id,
                    source_message_id=query.message.message_id,
                )
            except Exception as exc:
                logger.error("Callback processing failed command=%s (%s)", pending_id, type(exc).__name__)
                await query.answer("Não foi possível concluir. Tente novamente.", show_alert=True)
                return
            await query.answer()
            if result.remove_keyboard:
                await query.message.edit_reply_markup(reply_markup=None)
            await reply(query.message, user_id, result)

    return router


async def run_polling(processor: Processor, settings: Settings, transcriber: Transcriber | None = None) -> None:
    dispatcher = Dispatcher()
    dispatcher.include_router(build_router(processor, settings, transcriber))
    async with Bot(settings.telegram_bot_token) as bot:
        await dispatcher.start_polling(bot)
