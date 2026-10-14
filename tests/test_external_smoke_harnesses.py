from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from agro_notes.access_control import AccessService
from agro_notes.settings import Settings
from agro_notes.smoke_google_sheets import _round_trip_smoke
from agro_notes.smoke_telegram import _smoke, smoke


def test_sheets_smoke_uses_and_deletes_a_disposable_tab():
    calls = []

    def batch_update(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            return SimpleNamespace(execute=lambda: {"replies": [{"addSheet": {"properties": {"sheetId": 41}}}]})
        return SimpleNamespace(execute=lambda: {})

    written = []
    values = SimpleNamespace(
        update=lambda **kwargs: SimpleNamespace(execute=lambda: written.append(kwargs["body"]["values"][0][0])),
        get=lambda **kwargs: SimpleNamespace(execute=lambda: {"values": [[written[0], "timestamp"]]}),
    )
    api = SimpleNamespace(batchUpdate=batch_update, values=lambda: values)
    store = SimpleNamespace(service=SimpleNamespace(spreadsheets=lambda: api), spreadsheet_id="sheet-test")

    result = _round_trip_smoke(store)

    assert result == {"status": "PASS", "spreadsheet": "sheet-test", "temporary_tab_deleted": True}
    assert calls[0]["body"]["requests"][0]["addSheet"]["properties"]["title"].startswith("_SMOKE_")
    assert calls[1]["body"]["requests"] == [{"deleteSheet": {"sheetId": 41}}]


def test_sheets_smoke_deletes_tab_after_failed_value_roundtrip():
    calls = []

    def batch_update(**kwargs):
        calls.append(kwargs)
        response = {"replies": [{"addSheet": {"properties": {"sheetId": 42}}}]} if len(calls) == 1 else {}
        return SimpleNamespace(execute=lambda: response)

    values = SimpleNamespace(
        update=lambda **kwargs: SimpleNamespace(execute=lambda: {}),
        get=lambda **kwargs: SimpleNamespace(execute=lambda: {"values": [["unexpected"]]}),
    )
    api = SimpleNamespace(batchUpdate=batch_update, values=lambda: values)
    store = SimpleNamespace(service=SimpleNamespace(spreadsheets=lambda: api), spreadsheet_id="sheet-test")

    with pytest.raises(RuntimeError, match="did not round-trip"):
        _round_trip_smoke(store)

    assert calls[-1]["body"]["requests"] == [{"deleteSheet": {"sheetId": 42}}]


def test_telegram_smoke_confirms_an_authorized_private_inbound_message(monkeypatch):
    settings = Settings(TELEGRAM_BOT_TOKEN="token", TELEGRAM_ALLOWED_USER_IDS="42")
    bot = SimpleNamespace(
        get_me=AsyncMock(return_value=SimpleNamespace(id=9)),
        get_webhook_info=AsyncMock(return_value=SimpleNamespace(url="")),
        get_updates=AsyncMock(),
        send_message=AsyncMock(),
    )

    calls = 0

    async def get_updates(**kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return []
        return [
            SimpleNamespace(
                update_id=100,
                message=SimpleNamespace(
                    text="AGRO-SMOKE-ABCD1234",
                    chat=SimpleNamespace(type="private", id=42),
                    from_user=SimpleNamespace(id=42),
                ),
            )
        ]

    bot.get_updates.side_effect = get_updates
    monkeypatch.setattr("agro_notes.smoke_telegram.secrets.token_hex", lambda _size: "abcd1234")
    import asyncio

    result = asyncio.run(smoke(settings, bot))

    assert result == {"status": "PASS", "bot_id": 9, "inbound_message_verified": True}
    assert bot.send_message.await_args.args[0] == 42
    assert bot.get_updates.await_args_list[-1].kwargs["offset"] == 101
    assert all(
        call.kwargs["allowed_updates"] == ["message", "callback_query"]
        for call in bot.get_updates.await_args_list
    )


def test_telegram_smoke_refuses_to_poll_when_old_updates_are_pending():
    settings = Settings(TELEGRAM_BOT_TOKEN="token", TELEGRAM_ALLOWED_USER_IDS="42")
    bot = SimpleNamespace(
        get_me=AsyncMock(return_value=SimpleNamespace(id=9)),
        get_webhook_info=AsyncMock(return_value=SimpleNamespace(url="")),
        get_updates=AsyncMock(return_value=[SimpleNamespace(update_id=1)]),
        send_message=AsyncMock(),
    )

    import asyncio

    result = asyncio.run(_smoke(bot, settings))

    assert result == {"status": "PENDING_UPDATES", "bot_id": 9}
    bot.send_message.assert_not_awaited()
    assert len(bot.get_updates.await_args_list) == 1


def test_telegram_smoke_detects_callback_updates_without_acknowledging_them():
    settings = Settings(TELEGRAM_BOT_TOKEN="token", TELEGRAM_ALLOWED_USER_IDS="42")
    callback_update = SimpleNamespace(update_id=1, callback_query=SimpleNamespace(id="callback-1"))
    bot = SimpleNamespace(
        get_me=AsyncMock(return_value=SimpleNamespace(id=9)),
        get_webhook_info=AsyncMock(return_value=SimpleNamespace(url="")),
        get_updates=AsyncMock(return_value=[callback_update]),
        send_message=AsyncMock(),
    )

    import asyncio

    result = asyncio.run(_smoke(bot, settings))

    assert result == {"status": "PENDING_UPDATES", "bot_id": 9}
    bot.send_message.assert_not_awaited()
    assert bot.get_updates.await_args_list[0].kwargs == {
        "timeout": 0,
        "limit": 1,
        "allowed_updates": ["message", "callback_query"],
    }


def test_telegram_smoke_refuses_webhook_without_polling():
    settings = Settings(TELEGRAM_BOT_TOKEN="token", TELEGRAM_ALLOWED_USER_IDS="42")
    bot = SimpleNamespace(
        get_me=AsyncMock(return_value=SimpleNamespace(id=9)),
        get_webhook_info=AsyncMock(return_value=SimpleNamespace(url="https://example.test/hook")),
        get_updates=AsyncMock(),
        send_message=AsyncMock(),
    )

    import asyncio

    result = asyncio.run(_smoke(bot, settings))

    assert result == {"status": "BLOCKED_WEBHOOK_CONFIGURED", "bot_id": 9}
    bot.get_updates.assert_not_awaited()


@pytest.mark.parametrize("legacy_ids", ["", "42"])
@pytest.mark.parametrize("state,expected", [("AUTHORIZED", "PASS"), ("REVOKED", "UNEXPECTED_UPDATE_PENDING")])
def test_telegram_smoke_persisted_access_overrides_legacy_ids(monkeypatch, state, expected, legacy_ids):
    import asyncio

    settings = Settings(TELEGRAM_BOT_TOKEN="token", TELEGRAM_ALLOWED_USER_IDS=legacy_ids, GOOGLE_SHEET_ID="sheet")
    rows = [{
        "event_type": "REDEEMED", "telegram_user_id": "42", "property_id": settings.farm_property_id,
        "state": "AUTHORIZED",
    }]
    if state == "REVOKED":
        rows.append({**rows[0], "event_type": "USER_STATE", "state": "REVOKED"})
    store = SimpleNamespace(read_rows=lambda _tab: rows)
    monkeypatch.setattr("agro_notes.smoke_telegram.GoogleSheetsStore.from_credentials", lambda _settings: store)
    monkeypatch.setattr("agro_notes.smoke_telegram.secrets.token_hex", lambda _size: "abcd1234")
    update = SimpleNamespace(
        update_id=100,
        message=SimpleNamespace(
            text="AGRO-SMOKE-ABCD1234", chat=SimpleNamespace(type="private", id=42),
            from_user=SimpleNamespace(id=42),
        ),
    )
    bot = SimpleNamespace(
        get_me=AsyncMock(return_value=SimpleNamespace(id=9)),
        get_webhook_info=AsyncMock(return_value=SimpleNamespace(url="")),
        get_updates=AsyncMock(side_effect=[[], [update], []]),
        send_message=AsyncMock(),
    )

    result = asyncio.run(smoke(settings, bot))

    assert result["status"] == expected
    if state == "AUTHORIZED":
        bot.send_message.assert_awaited_once_with(42, "Smoke do Telegram: recebimento confirmado.")
        assert bot.get_updates.await_args_list[-1].kwargs["offset"] == 101
    else:
        bot.send_message.assert_not_awaited()
        assert all("offset" not in call.kwargs for call in bot.get_updates.await_args_list)


def test_telegram_smoke_keeps_old_updates_with_empty_legacy_ids():
    import asyncio

    settings = Settings(TELEGRAM_BOT_TOKEN="token", TELEGRAM_ALLOWED_USER_IDS="")
    access = AccessService(SimpleNamespace(read_rows=lambda _tab: []), settings)
    bot = SimpleNamespace(
        get_me=AsyncMock(return_value=SimpleNamespace(id=9)),
        get_webhook_info=AsyncMock(return_value=SimpleNamespace(url="")),
        get_updates=AsyncMock(return_value=[SimpleNamespace(update_id=1)]),
        send_message=AsyncMock(),
    )

    result = asyncio.run(_smoke(bot, settings, access=access))

    assert result == {"status": "PENDING_UPDATES", "bot_id": 9}
    bot.send_message.assert_not_awaited()
    assert len(bot.get_updates.await_args_list) == 1
    assert "offset" not in bot.get_updates.await_args.kwargs
