from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock

import pytest
from aiogram.types import Chat, Message, User

from agro_notes.settings import Settings
from agro_notes.telegram_bot import (
    BotReply,
    BoundedAudioBuffer,
    VoiceTooLarge,
    build_router,
    download_voice,
    is_allowed,
)
from agro_notes.transcription import OpenAITranscriber


def settings(**kwargs):
    return Settings(TELEGRAM_ALLOWED_USER_IDS="42,43", **kwargs)


def message(user_id=42, text="nasceram dois bezerros", voice=None):
    return SimpleNamespace(
        from_user=SimpleNamespace(id=user_id),
        chat=SimpleNamespace(id=100, type="private"),
        message_id=10,
        date=datetime(2026, 10, 12, tzinfo=UTC),
        text=text,
        voice=voice,
        answer=AsyncMock(return_value=SimpleNamespace(chat=SimpleNamespace(id=100), message_id=20)),
    )


def processor():
    return SimpleNamespace(
        receive=AsyncMock(return_value=BotReply("Confira", "pending-1")),
        bind_confirmation=AsyncMock(),
        confirm=AsyncMock(return_value=BotReply("Registrado")),
        cancel=AsyncMock(return_value=BotReply("Cancelado")),
    )


def message_handler(router, name):
    return next(handler.callback for handler in router.message.handlers if handler.callback.__name__ == name)


def test_whitelist_and_actual_download_cap():
    assert is_allowed(42, settings())
    assert not is_allowed(99, settings())
    assert not is_allowed(None, settings())
    with BoundedAudioBuffer(3) as buf:
        buf.write(b"ab")
        with pytest.raises(VoiceTooLarge):
            buf.write(b"cd")
        assert buf.getvalue() == b"ab"


async def test_declared_size_rejected_before_download():
    bot = SimpleNamespace(download=AsyncMock())
    with pytest.raises(VoiceTooLarge):
        await download_voice(bot, message(voice=SimpleNamespace(file_size=4)), 3)
    bot.download.assert_not_awaited()


async def test_download_undeclared_size_is_still_capped():
    async def download(_voice, *, destination):
        destination.write(b"abcd")

    with pytest.raises(VoiceTooLarge):
        await download_voice(SimpleNamespace(download=download), message(voice=SimpleNamespace(file_size=None)), 3)


async def test_unauthorized_text_audio_callbacks_never_process():
    proc = processor()
    transcriber = SimpleNamespace(transcribe=AsyncMock())
    router = build_router(proc, settings(), transcriber)
    msg = message(user_id=99)
    await message_handler(router, "start")(msg)
    await message_handler(router, "voice")(msg, SimpleNamespace(download=AsyncMock()))
    await message_handler(router, "text")(msg)
    query = SimpleNamespace(from_user=SimpleNamespace(id=99), answer=AsyncMock())
    await router.callback_query.handlers[0].callback(query)
    proc.receive.assert_not_awaited()
    proc.confirm.assert_not_awaited()
    transcriber.transcribe.assert_not_awaited()


async def test_voice_transcription_forwarded_with_message_key():
    proc = processor()
    transcriber = SimpleNamespace(transcribe=AsyncMock(return_value="nasceram dois bezerros"))
    router = build_router(proc, settings(), transcriber)

    async def download(_voice, *, destination):
        destination.write(b"ogg-bytes")

    await message_handler(router, "voice")(
        message(voice=SimpleNamespace(file_size=9, file_id="file-1")),
        SimpleNamespace(download=download),
    )
    transcriber.transcribe.assert_awaited_once_with(b"ogg-bytes")
    proc.receive.assert_awaited_once_with(
        42,
        "nasceram dois bezerros",
        source="voice",
        message_id="100:10",
        captured_at="2026-10-12T00:00:00+00:00",
        device_timezone=None,
        source_reference="file-1",
        received_at=ANY,
    )


@pytest.mark.parametrize("action,button_index", [("confirm", 0), ("cancel", 1)])
async def test_callbacks_use_persisted_command_id_and_bind_reply_message(monkeypatch, action, button_index):
    proc = processor()
    router = build_router(proc, settings(), SimpleNamespace(transcribe=AsyncMock()))
    msg = message()
    await message_handler(router, "text")(msg)
    data = msg.answer.call_args.kwargs["reply_markup"].inline_keyboard[0][button_index].callback_data
    assert data == f"{action}:pending-1"
    proc.bind_confirmation.assert_awaited_once_with(42, "pending-1", chat_id=100, message_id=20)

    sent = Message(message_id=20, date=0, chat=Chat(id=100, type="private"))
    monkeypatch.setattr(Message, "edit_reply_markup", AsyncMock())
    monkeypatch.setattr(Message, "answer", AsyncMock())
    query = SimpleNamespace(
        from_user=User(id=99, is_bot=False, first_name="Other"),
        data=data,
        message=sent,
        answer=AsyncMock(),
    )
    await router.callback_query.handlers[0].callback(query)
    getattr(proc, action).assert_not_awaited()

    query.from_user = User(id=42, is_bot=False, first_name="Owner")
    getattr(proc, action).return_value = BotReply("OK", remove_keyboard=True)
    await router.callback_query.handlers[0].callback(query)
    getattr(proc, action).assert_awaited_once_with(42, "pending-1", source_chat_id=100, source_message_id=20)


async def test_authorized_non_owner_does_not_remove_preview_keyboard(monkeypatch):
    proc = processor()
    proc.confirm.return_value = BotReply("Esta confirmação não pertence a você.")
    router = build_router(proc, settings(), SimpleNamespace(transcribe=AsyncMock()))
    sent = Message(message_id=20, date=0, chat=Chat(id=100, type="private"))
    edit = AsyncMock()
    monkeypatch.setattr(Message, "edit_reply_markup", edit)
    monkeypatch.setattr(Message, "answer", AsyncMock())
    query = SimpleNamespace(
        from_user=User(id=43, is_bot=False, first_name="Other authorized user"),
        data="confirm:pending-1", message=sent, answer=AsyncMock(),
    )
    await router.callback_query.handlers[0].callback(query)
    proc.confirm.assert_awaited_once_with(43, "pending-1", source_chat_id=100, source_message_id=20)
    edit.assert_not_awaited()


async def test_group_chat_is_rejected_before_processing():
    proc = processor()
    router = build_router(proc, settings(), SimpleNamespace(transcribe=AsyncMock()))
    msg = message()
    msg.chat.type = "group"
    await message_handler(router, "text")(msg)

    proc.receive.assert_not_awaited()
    msg.answer.assert_awaited_once()


async def test_pending_callback_data_survives_router_recreation(monkeypatch):
    proc = processor()
    first_router = build_router(proc, settings(), SimpleNamespace(transcribe=AsyncMock()))
    msg = message()
    await message_handler(first_router, "text")(msg)
    data = msg.answer.call_args.kwargs["reply_markup"].inline_keyboard[0][0].callback_data

    second_router = build_router(proc, settings(), SimpleNamespace(transcribe=AsyncMock()))
    sent = Message(message_id=20, date=0, chat=Chat(id=100, type="private"))
    monkeypatch.setattr(Message, "edit_reply_markup", AsyncMock())
    monkeypatch.setattr(Message, "answer", AsyncMock())
    query = SimpleNamespace(
        from_user=User(id=42, is_bot=False, first_name="Owner"),
        data=data,
        message=sent,
        answer=AsyncMock(),
    )
    await second_router.callback_query.handlers[0].callback(query)
    proc.confirm.assert_awaited_once_with(42, "pending-1", source_chat_id=100, source_message_id=20)


async def test_openai_transcription_uses_memory_and_portuguese():
    create = AsyncMock(return_value=SimpleNamespace(text="  dois bezerros  "))
    client = SimpleNamespace(audio=SimpleNamespace(transcriptions=SimpleNamespace(create=create)))
    result = await OpenAITranscriber(settings(), client).transcribe(b"ogg")
    assert result.text == "dois bezerros"
    assert result.metadata.provider == "openai"
    assert result.metadata.outcome.value == "SUCCESS"
    assert create.call_args.kwargs["file"] == ("voice.ogg", b"ogg", "audio/ogg")
    assert create.call_args.kwargs["language"] == "pt"


async def test_authorized_code_replays_never_reach_processor():
    proc = processor()
    access = SimpleNamespace(is_authorized=AsyncMock(return_value=True), redeem=AsyncMock())
    router = build_router(proc, settings(), access=access)
    handler = message_handler(router, "text")

    await handler(message(text="0123456789ABCDEF0123"))
    await handler(message(text="/ACESSO 0123456789ABCDEF0123"))

    proc.receive.assert_not_awaited()
    access.redeem.assert_not_awaited()
