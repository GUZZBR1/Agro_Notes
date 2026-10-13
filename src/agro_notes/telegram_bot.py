"""Telegram transport. Domain decisions and persistence belong to the processor."""

import asyncio
import io
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from .access_control import AccessService
from .exports import ExportDocument
from .google_drive import DriveConfigurationError, match_drive_connection_intent
from .provider_factory import build_transcriber
from .settings import Settings
from .transcription import Transcriber

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BotReply:
    text: str
    pending_id: str | None = None
    remove_keyboard: bool = False
    document: ExportDocument | None = None


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

    async def bind_confirmation(self, user_id: int, pending_id: str, *, chat_id: int, message_id: int) -> None: ...

    async def confirm(
        self, user_id: int, pending_id: str, *, source_chat_id: int | None = None, source_message_id: int | None = None
    ) -> BotReply: ...

    async def cancel(
        self, user_id: int, pending_id: str, *, source_chat_id: int | None = None, source_message_id: int | None = None
    ) -> BotReply: ...


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


def build_router(
    processor: Processor,
    settings: Settings,
    transcriber: Transcriber | None = None,
    access: AccessService | None = None,
    google_drive: Any | None = None,
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
        if result.document is not None:
            if not await authorize(message):
                return
            try:
                await message.answer_document(
                    BufferedInputFile(result.document.content, filename=result.document.filename),
                    caption=result.text,
                )
            except Exception as exc:
                logger.error("Telegram export delivery failed (%s)", type(exc).__name__)
                await message.answer("Não foi possível enviar a planilha. Tente novamente.")
            return
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
        user_id = message.from_user.id if message.from_user else None
        allowed = (
            await access.is_authorized(user_id) if access and user_id is not None else is_allowed(user_id, settings)
        )
        if not allowed:
            await message.answer("Acesso não autorizado.")
            return False
        return True

    async def connect_drive(message: Message, user_id: int) -> None:
        if not google_drive or not google_drive.configured:
            await message.answer("O Google Drive ainda não está configurado pelo administrador.")
            return
        try:
            already_connected = await asyncio.to_thread(google_drive.is_connected, user_id)
            if already_connected:
                await message.answer("Seu Google Drive já está conectado.")
                return
            url = await asyncio.to_thread(google_drive.create_authorization_url, user_id)
        except ValueError as exc:
            if str(exc) == "Google Drive is already connected":
                await message.answer("Seu Google Drive já está conectado.")
                return
            await message.answer("Não foi possível iniciar a conexão. Tente novamente.")
            return
        except DriveConfigurationError:
            await message.answer("O Google Drive ainda não está configurado pelo administrador.")
            return
        await message.answer(f"Para conectar seu Google Drive, abra este link e autorize o Agro Notes.\n{url}")

    async def disconnect_drive(message: Message, user_id: int) -> None:
        if not google_drive:
            await message.answer("Não há uma conexão Google Drive ativa.")
            return
        try:
            disconnected = await asyncio.to_thread(google_drive.disconnect, user_id)
        except Exception as exc:
            logger.error("Google Drive disconnect failed (%s)", type(exc).__name__)
            await message.answer("Não foi possível desconectar o Google Drive. Tente novamente.")
            return
        if disconnected:
            await message.answer("Google Drive desconectado. A conexão não poderá mais ser usada pelo Agro Notes.")
        else:
            await message.answer("Não há uma conexão Google Drive ativa.")

    def user_display(message: Message) -> tuple[str, str]:
        user = message.from_user
        if user is None:
            return "", ""
        return (" ".join(part for part in (user.first_name, user.last_name) if part), user.username or "")

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
        if message.chat.type != "private":
            await message.answer("Por segurança, inicie o bot em uma conversa privada.")
            return
        if access and message.from_user:
            display, username = user_display(message)
            text = await access.start(message.from_user.id, display, username)
            await message.answer(text)
        elif await authorize(message):
            await message.answer(
                "Envie um texto ou áudio com a movimentação da fazenda. "
                "Vou pedir esclarecimentos quando faltarem dados; alguns registros são gravados após validação "
                "e outros exigem sua confirmação."
            )

    @router.message(Command("acesso"))
    async def access_code(message: Message) -> None:
        if message.chat.type != "private":
            await message.answer("Envie o código somente em conversa privada com o bot.")
            return
        if not access or not message.from_user:
            await message.answer("O cadastro por código não está disponível.")
            return
        pieces = (message.text or "").split(maxsplit=1)
        if len(pieces) != 2:
            await message.answer("Uso: /acesso SEU_CODIGO (somente nesta conversa privada).")
            return
        display, username = user_display(message)
        await message.answer(await access.redeem(message.from_user.id, pieces[1], display, username))

    @router.message(Command("conectar_drive"))
    async def connect_drive_command(message: Message) -> None:
        if not await authorize(message):
            return
        assert message.from_user is not None
        await connect_drive(message, message.from_user.id)

    @router.message(Command("desconectar_drive"))
    async def disconnect_drive_command(message: Message) -> None:
        if not await authorize(message):
            return
        assert message.from_user is not None
        await disconnect_drive(message, message.from_user.id)

    @router.message(F.voice)
    async def voice(message: Message, bot: Bot) -> None:
        nonlocal transcriber
        if message.chat.type != "private":
            await message.answer("Por segurança, use o chat privado do bot para acessar dados da fazenda.")
            return
        if access and message.from_user and not await access.is_authorized(message.from_user.id):
            await message.answer("Para liberar o acesso, envie /start e depois /acesso SEU_CODIGO por texto.")
            return
        if not await authorize(message):
            return
        assert message.from_user is not None
        user_id = message.from_user.id
        received_at = datetime.now(UTC).isoformat()
        async with lock_for(user_id):
            failure_code = "AUDIO_DOWNLOAD_FAILED"
            try:
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
        if message.chat.type != "private":
            await message.answer("Por segurança, use o chat privado do bot para acessar dados da fazenda.")
            return
        if access and message.from_user and not await access.is_authorized(message.from_user.id):
            raw = message.text or ""
            if raw.strip().lower() == "/cancel":
                await message.answer(await access.set_waiting(message.from_user.id))
            else:
                display, username = user_display(message)
                await message.answer(await access.redeem(message.from_user.id, raw, display, username))
            return
        if not await authorize(message):
            return
        assert message.from_user is not None and message.text is not None
        user_id = message.from_user.id
        drive_action = match_drive_connection_intent(message.text)
        if drive_action == "connect":
            await connect_drive(message, user_id)
            return
        if drive_action == "disconnect":
            await disconnect_drive(message, user_id)
            return
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
        allowed = await access.is_authorized(user_id) if access else is_allowed(user_id, settings)
        if not allowed:
            await query.answer("Acesso não autorizado.", show_alert=True)
            return
        if not isinstance(query.message, Message) or query.message.chat.type != "private":
            await query.answer("Use o chat privado do bot para acessar dados da fazenda.", show_alert=True)
            return
        action, _, pending_id = (query.data or "").partition(":")
        if action == "drive_connect":
            if not google_drive:
                await query.answer("Esta conexão expirou. Solicite um novo link.", show_alert=True)
                return
            try:
                connected = await asyncio.to_thread(google_drive.confirm_connection, user_id, pending_id)
            except Exception as exc:
                logger.error("Google Drive confirmation failed (%s)", type(exc).__name__)
                connected = False
            if not connected:
                await query.answer("Esta conexão expirou ou foi revogada. Solicite um novo link.", show_alert=True)
                await query.message.edit_reply_markup(reply_markup=None)
                return
            await query.answer("Google Drive conectado.")
            await query.message.edit_reply_markup(reply_markup=None)
            await query.message.answer("Google Drive conectado com sucesso.")
            return
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
