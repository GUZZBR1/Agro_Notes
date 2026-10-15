from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock, Mock

import pytest
from aiogram.types import Chat, Message, User

from agro_notes.exports import ExportDocument
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
        answer_document=AsyncMock(),
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


async def test_access_onboarding_keeps_code_out_of_processor():
    proc = processor()
    access = SimpleNamespace(
        is_authorized=AsyncMock(return_value=False),
        start=AsyncMock(return_value="Envie o código"),
        redeem=AsyncMock(return_value="Código inválido ou indisponível."),
        set_waiting=AsyncMock(),
    )
    router = build_router(proc, settings(), access=access)
    msg = message(user_id=99, text="/start")
    msg.from_user.first_name = "User"
    msg.from_user.last_name = ""
    msg.from_user.username = None
    await message_handler(router, "start")(msg)
    msg.text = "0123456789ABCDEF0123456789ABCDEF"
    await message_handler(router, "text")(msg)

    access.start.assert_awaited_once_with(99, "User", "")
    access.redeem.assert_awaited_once_with(99, msg.text, "User", "")
    proc.receive.assert_not_awaited()


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


async def test_export_sends_buffered_document_with_exact_bytes_filename_and_caption():
    proc = processor()
    document = ExportDocument(filename="fazenda.xlsx", content=b"workbook-bytes")
    proc.receive.return_value = BotReply("Aqui está a planilha.", document=document)
    router = build_router(proc, settings(), SimpleNamespace(transcribe=AsyncMock()))
    msg = message(text="/exportar")

    await message_handler(router, "text")(msg)

    proc.receive.assert_awaited_once()
    assert proc.receive.call_args.args == (42, "/exportar")
    msg.answer_document.assert_awaited_once()
    upload = msg.answer_document.call_args.args[0]
    assert upload.filename == "fazenda.xlsx"
    assert upload.data == b"workbook-bytes"
    assert msg.answer_document.call_args.kwargs == {"caption": "Aqui está a planilha."}
    msg.answer.assert_not_awaited()
    proc.bind_confirmation.assert_not_awaited()


async def test_connect_drive_command_sends_link_only_to_authorized_private_user():
    proc = processor()
    drive = SimpleNamespace(
        configured=True,
        is_connected=lambda _user_id: False,
        create_authorization_url=lambda user_id: f"https://accounts.google.test/auth?user={user_id}",
    )
    router = build_router(proc, settings(), google_drive=drive)
    msg = message(text="/conectar_drive")

    await message_handler(router, "connect_drive_command")(msg)

    msg.answer.assert_awaited_once()
    assert "https://accounts.google.test/auth?user=42" in msg.answer.call_args.args[0]
    proc.receive.assert_not_awaited()


async def test_conversational_connect_drive_and_disconnect_drive_are_handled_without_interpretation():
    proc = processor()
    drive = SimpleNamespace(
        configured=True,
        is_connected=lambda _user_id: False,
        create_authorization_url=lambda _user_id: "https://accounts.google.test/auth",
        disconnect=lambda _user_id: True,
    )
    router = build_router(proc, settings(), google_drive=drive)
    msg = message(text="conectar meu Google Drive")

    await message_handler(router, "text")(msg)
    assert "https://accounts.google.test/auth" in msg.answer.call_args.args[0]
    msg.answer.reset_mock()
    msg.text = "desconectar meu Google Drive"
    await message_handler(router, "text")(msg)

    msg.answer.assert_awaited_once()
    assert "desconectado" in msg.answer.call_args.args[0]
    proc.receive.assert_not_awaited()


async def test_connect_drive_command_refuses_group_chat_and_unauthorized_user():
    proc = processor()
    drive = SimpleNamespace(configured=True, create_authorization_url=lambda _user_id: "forbidden")
    router = build_router(proc, settings(), google_drive=drive)
    msg = message(user_id=99, text="/conectar_drive")
    await message_handler(router, "connect_drive_command")(msg)
    msg.answer.assert_awaited_once_with("Acesso não autorizado.")

    msg = message(text="/conectar_drive")
    msg.chat.type = "group"
    await message_handler(router, "connect_drive_command")(msg)
    assert "chat privado" in msg.answer.call_args.args[0]


async def test_drive_confirmation_button_is_bound_to_clicking_telegram_account(monkeypatch):
    proc = processor()
    drive = SimpleNamespace(confirm_connection=Mock(return_value=False))
    router = build_router(proc, settings(), google_drive=drive)
    sent = Message(message_id=20, date=0, chat=Chat(id=100, type="private"))
    monkeypatch.setattr(Message, "edit_reply_markup", AsyncMock())
    monkeypatch.setattr(Message, "answer", AsyncMock())
    query = SimpleNamespace(
        from_user=User(id=43, is_bot=False, first_name="Other authorized user"),
        data="drive_connect:connection-id",
        message=sent,
        answer=AsyncMock(),
    )

    await router.callback_query.handlers[0].callback(query)

    drive.confirm_connection.assert_called_once_with(43, "connection-id")
    query.answer.assert_awaited_once()
    assert "expirou ou foi revogada" in query.answer.call_args.args[0]
    Message.answer.assert_not_awaited()


async def test_voice_export_sends_document_after_transcription():
    proc = processor()
    proc.receive.return_value = BotReply("Planilha", document=ExportDocument("farm.xlsx", b"xlsx-bytes"))
    transcriber = SimpleNamespace(transcribe=AsyncMock(return_value="me manda a planilha"))
    router = build_router(proc, settings(), transcriber)
    msg = message(text=None, voice=SimpleNamespace(file_size=9, file_id="export-voice"))

    async def download(_voice, *, destination):
        destination.write(b"ogg-bytes")

    await message_handler(router, "voice")(msg, SimpleNamespace(download=download))

    assert proc.receive.call_args.args == (42, "me manda a planilha")
    assert proc.receive.call_args.kwargs["source"] == "voice"
    msg.answer_document.assert_awaited_once()
    assert msg.answer_document.call_args.args[0].data == b"xlsx-bytes"
    msg.answer.assert_not_awaited()


@pytest.mark.parametrize("source", ["text", "voice"])
async def test_export_delivery_failure_returns_retry_message_without_success_or_confirmation(source):
    proc = processor()
    proc.receive.return_value = BotReply("Planilha pronta", document=ExportDocument("farm.xlsx", b"xlsx-bytes"))
    transcriber = SimpleNamespace(transcribe=AsyncMock(return_value="/exportar"))
    router = build_router(proc, settings(), transcriber)
    msg = message(text="/exportar", voice=SimpleNamespace(file_size=9, file_id="voice-file"))
    msg.answer_document.side_effect = OSError("private telegram provider details")

    if source == "voice":
        async def download(_voice, *, destination):
            destination.write(b"ogg-bytes")

        await message_handler(router, "voice")(msg, SimpleNamespace(download=download))
    else:
        await message_handler(router, "text")(msg)

    msg.answer_document.assert_awaited_once()
    msg.answer.assert_awaited_once_with("Não foi possível enviar a planilha. Tente novamente.")
    proc.bind_confirmation.assert_not_awaited()


async def test_export_unauthorized_user_never_processes_or_receives_document():
    proc = processor()
    proc.receive.return_value = BotReply("Planilha", document=ExportDocument("farm.xlsx", b"private-data"))
    router = build_router(proc, settings(), SimpleNamespace(transcribe=AsyncMock()))
    msg = message(user_id=99, text="/exportar")

    await message_handler(router, "text")(msg)

    proc.receive.assert_not_awaited()
    msg.answer_document.assert_not_awaited()
    msg.answer.assert_awaited_once_with("Acesso não autorizado.")


async def test_export_group_chat_cannot_process_or_receive_document():
    proc = processor()
    proc.receive.return_value = BotReply("Planilha", document=ExportDocument("farm.xlsx", b"private-data"))
    router = build_router(proc, settings(), SimpleNamespace(transcribe=AsyncMock()))
    msg = message(text="/exportar")
    msg.chat.type = "group"

    await message_handler(router, "text")(msg)

    proc.receive.assert_not_awaited()
    msg.answer_document.assert_not_awaited()
    assert "chat privado" in msg.answer.call_args.args[0]


async def test_export_rechecks_access_before_document_delivery():
    proc = processor()
    proc.receive.return_value = BotReply("Planilha", document=ExportDocument("farm.xlsx", b"private-data"))
    access = SimpleNamespace(is_authorized=AsyncMock(side_effect=[True, True, False]))
    router = build_router(proc, settings(), SimpleNamespace(transcribe=AsyncMock()), access=access)
    msg = message(text="/exportar")

    await message_handler(router, "text")(msg)

    proc.receive.assert_awaited_once()
    assert access.is_authorized.await_count == 3
    assert all(call.args == (42,) for call in access.is_authorized.call_args_list)
    msg.answer_document.assert_not_awaited()
    msg.answer.assert_awaited_once_with("Acesso não autorizado.")
    proc.bind_confirmation.assert_not_awaited()
async def test_authorized_explicit_access_codes_never_reach_processor():
    proc = processor()
    access = SimpleNamespace(is_authorized=AsyncMock(return_value=True), redeem=AsyncMock())
    router = build_router(proc, settings(), access=access)
    handler = message_handler(router, "text")

    await handler(message(text="AGRO-0123456789ABCDEF0123"))
    await handler(message(text="/ACESSO 0123456789ABCDEF0123"))

    proc.receive.assert_not_awaited()
    access.redeem.assert_not_awaited()


async def test_authorized_bare_hex_identifier_reaches_processor():
    proc = processor()
    access = SimpleNamespace(is_authorized=AsyncMock(return_value=True), redeem=AsyncMock())
    router = build_router(proc, settings(), access=access)
    identifier = "0123456789ABCDEF0123"

    await message_handler(router, "text")(message(text=identifier))

    assert proc.receive.await_args.args == (42, identifier)
    access.redeem.assert_not_awaited()
