import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

from agro_notes.access_control import (
    AUTHORIZED_REPLY,
    BLOCKED_REPLY,
    INVALID_CODE_REPLY,
    AccessService,
    generate_invitation,
    hash_code,
    normalize_code,
)
from agro_notes.settings import Settings
from agro_notes.telegram_bot import BotReply, build_router


class MemoryStore:
    def __init__(self):
        self.rows = []
        self.read_count = 0

    def read_rows(self, tab):
        assert tab == "Telegram_Access"
        self.read_count += 1
        return list(self.rows)

    def append_rows(self, tab, rows):
        assert tab == "Telegram_Access"
        self.rows.extend(dict(row) for row in rows)


def fixture(max_uses=1, expires_at=None):
    store = MemoryStore()
    settings = Settings(TELEGRAM_ALLOWED_USER_IDS="", GOOGLE_SHEET_ID="sheet")
    access = AccessService(store, settings)
    code = "0123456789ABCDEF0123"
    store.rows.append(
        {
            "event_type": "CODE_CREATED",
            "access_code_id": "code-1",
            "code_hash": hash_code(code),
            "property_id": settings.farm_property_id,
            "role": "FARMER",
            "state": "AVAILABLE",
            "created_at": datetime.now(UTC).isoformat(),
            "expires_at": (expires_at or datetime.now(UTC) + timedelta(hours=1)).isoformat(),
            "max_uses": str(max_uses),
        }
    )
    return store, access, code


def test_normalization_and_storage_only_contain_hash():
    store, access, code = fixture()
    assert normalize_code(" AGRO-01234-56789-abcdef01-23 ") == code
    assert asyncio.run(access.redeem(7, code)) == AUTHORIZED_REPLY
    assert all(code not in str(row) for row in store.rows)
    assert any(row.get("event_type") == "REDEEMED" for row in store.rows)


def test_unknown_expired_revoked_and_exhausted_codes_have_generic_reply(caplog):
    store, access, code = fixture()
    invalid_code = "F" * 20
    assert asyncio.run(access.redeem(1, invalid_code)) == INVALID_CODE_REPLY
    assert invalid_code not in caplog.text

    expired_store, expired_access, expired_code = fixture(expires_at=datetime.now(UTC) - timedelta(seconds=1))
    assert asyncio.run(expired_access.redeem(2, expired_code)) == INVALID_CODE_REPLY

    revoked_store, revoked_access, revoked_code = fixture()
    revoked_store.rows.append({"event_type": "CODE_REVOKED", "access_code_id": "code-1"})
    assert asyncio.run(revoked_access.redeem(3, revoked_code)) == INVALID_CODE_REPLY

    malformed_store, malformed_access, malformed_code = fixture()
    malformed_store.rows[0]["max_uses"] = "invalid"
    assert asyncio.run(malformed_access.redeem(34, malformed_code)) == INVALID_CODE_REPLY

    other_property_store, other_property_access, other_property_code = fixture()
    other_property_store.rows[0]["property_id"] = "another-property"
    assert asyncio.run(other_property_access.redeem(33, other_property_code)) == INVALID_CODE_REPLY

    exhausted_store, exhausted_access, exhausted_code = fixture()
    exhausted_store.rows.append({"event_type": "REDEEMED", "access_code_id": "code-1", "redemption_id": "prior"})
    assert asyncio.run(exhausted_access.redeem(4, exhausted_code)) == INVALID_CODE_REPLY


def test_authorization_survives_service_restart_and_revocation():
    store, access, code = fixture()
    assert asyncio.run(access.redeem(55, code)) == AUTHORIZED_REPLY

    restarted = AccessService(store, access.settings)
    assert asyncio.run(restarted.is_authorized(55))
    restarted.revoke_user(55)
    assert not asyncio.run(AccessService(store, access.settings).is_authorized(55))
    assert asyncio.run(AccessService(store, access.settings).redeem(55, code)) == BLOCKED_REPLY


def test_authorized_user_start_skips_code_on_router():
    store, access, code = fixture()
    assert asyncio.run(access.redeem(56, code)) == AUTHORIZED_REPLY
    processor = SimpleNamespace(receive=AsyncMock())
    router = build_router(processor, access.settings, access=access)
    start = next(handler.callback for handler in router.message.handlers if handler.callback.__name__ == "start")
    user = SimpleNamespace(id=56, first_name="Farmer", last_name="", username=None)
    message = SimpleNamespace(
        from_user=user,
        chat=SimpleNamespace(id=100, type="private"),
        text="/start",
        answer=AsyncMock(),
    )

    asyncio.run(start(message))

    assert message.answer.await_args.args[0] == AUTHORIZED_REPLY
    processor.receive.assert_not_awaited()


def test_redemption_is_idempotent_and_existing_authorized_user_consumes_no_second_use():
    store, access, code = fixture(max_uses=1)
    assert asyncio.run(access.redeem(9, code)) == AUTHORIZED_REPLY
    count = sum(row.get("event_type") == "REDEEMED" for row in store.rows)
    assert asyncio.run(access.redeem(9, code)) == AUTHORIZED_REPLY
    assert sum(row.get("event_type") == "REDEEMED" for row in store.rows) == count == 1


def test_single_remaining_use_is_serialized_between_service_instances():
    store, access, code = fixture(max_uses=1)
    second_access = AccessService(store, access.settings)

    async def race():
        return await asyncio.gather(access.redeem(11, code), second_access.redeem(12, code))

    replies = asyncio.run(race())
    assert replies.count(AUTHORIZED_REPLY) == 1
    assert replies.count(INVALID_CODE_REPLY) == 1
    assert sum(row.get("event_type") == "REDEEMED" for row in store.rows) == 1


def test_legacy_migration_only_applies_when_no_persisted_state_exists():
    store = MemoryStore()
    access = AccessService(store, Settings(TELEGRAM_ALLOWED_USER_IDS="42", GOOGLE_SHEET_ID="sheet"))
    assert asyncio.run(access.is_authorized(42))
    store.rows.append(
        {
            "event_type": "USER_STATE",
            "telegram_user_id": "42",
            "state": "REVOKED",
            "property_id": "FARM-001",
            "created_at": datetime.now(UTC).isoformat(),
        }
    )
    assert not asyncio.run(access.is_authorized(42))


def test_cancel_cannot_clear_revoked_or_blocked_user_state():
    store = MemoryStore()
    access = AccessService(store, Settings(TELEGRAM_ALLOWED_USER_IDS="42", GOOGLE_SHEET_ID="sheet"))
    store.rows.append({
        "event_type": "USER_STATE", "telegram_user_id": "42", "state": "REVOKED",
        "property_id": "FARM-001", "created_at": datetime.now(UTC).isoformat(),
    })
    assert asyncio.run(access.set_waiting(42)) == BLOCKED_REPLY
    assert asyncio.run(access.start(42)) == BLOCKED_REPLY
    assert not asyncio.run(access.is_authorized(42))
    assert store.rows[-1]["state"] == "REVOKED"


def test_fifth_invalid_attempt_applies_cooldown():
    store, access, _ = fixture()
    replies = [asyncio.run(access.redeem(77, "invalid")) for _ in range(5)]
    assert replies[-1] == BLOCKED_REPLY
    assert asyncio.run(access.redeem(77, "0123456789ABCDEF0123")) == BLOCKED_REPLY
    assert any(row.get("state") == "BLOCKED" and row.get("reason") == "FAILED_ATTEMPTS" for row in store.rows)


async def test_onboarding_code_never_reaches_agricultural_processor():
    processor = SimpleNamespace(
        receive=AsyncMock(return_value=BotReply("should not run")),
        bind_confirmation=AsyncMock(),
        record_ingress_failure=AsyncMock(),
        confirm=AsyncMock(),
        cancel=AsyncMock(),
    )
    access = SimpleNamespace(
        is_authorized=AsyncMock(return_value=False),
        start=AsyncMock(return_value="Envie o código"),
        redeem=AsyncMock(return_value=INVALID_CODE_REPLY),
        set_waiting=AsyncMock(),
    )
    router = build_router(
        processor,
        Settings(TELEGRAM_ALLOWED_USER_IDS="", GOOGLE_SHEET_ID="sheet"),
        access=access,
    )
    user = SimpleNamespace(id=9, first_name="Usuário", last_name="", username=None)
    start_message = SimpleNamespace(
        from_user=user,
        chat=SimpleNamespace(id=99, type="private"),
        text="/start",
        answer=AsyncMock(),
    )
    text_message = SimpleNamespace(
        from_user=user,
        chat=SimpleNamespace(id=99, type="private"),
        text="0123456789ABCDEF0123",
        answer=AsyncMock(),
    )
    handlers = {handler.callback.__name__: handler.callback for handler in router.message.handlers}
    await handlers["start"](start_message)
    await handlers["text"](text_message)
    access.start.assert_awaited_once_with(9, "Usuário", "")
    access.redeem.assert_awaited_once_with(9, text_message.text, "Usuário", "")
    processor.receive.assert_not_awaited()


def test_blocked_user_spam_does_not_repeat_sheet_reads():
    store, access, _ = fixture()
    for _ in range(5):
        asyncio.run(access.redeem(77, "F" * 20))
    reads_after_block = store.read_count

    assert not asyncio.run(access.is_authorized(77))
    assert asyncio.run(access.redeem(77, "F" * 20)) == BLOCKED_REPLY
    assert asyncio.run(access.start(77)) == BLOCKED_REPLY
    assert asyncio.run(access.set_waiting(77)) == BLOCKED_REPLY
    assert store.read_count == reads_after_block


def test_persisted_cooldown_is_cached_after_service_restart():
    store, access, _ = fixture()
    for _ in range(5):
        asyncio.run(access.redeem(88, "F" * 20))
    restarted_access = AccessService(store, access.settings)
    assert asyncio.run(restarted_access.start(88)) == BLOCKED_REPLY
    reads_after_hydration = store.read_count
    assert asyncio.run(restarted_access.start(88)) == BLOCKED_REPLY
    assert asyncio.run(restarted_access.redeem(88, "F" * 20)) == BLOCKED_REPLY
    assert asyncio.run(restarted_access.set_waiting(88)) == BLOCKED_REPLY
    assert store.read_count == reads_after_hydration


def test_invitation_code_is_short_random_and_only_hash_is_persisted():
    store = MemoryStore()
    settings = Settings(TELEGRAM_ALLOWED_USER_IDS="", GOOGLE_SHEET_ID="sheet")
    code_id, displayed_code = generate_invitation(
        store, settings, expires_at=datetime.now(UTC) + timedelta(hours=2), max_uses=1
    )
    assert displayed_code.startswith("AGRO-")
    assert normalize_code(displayed_code) and len(normalize_code(displayed_code)) == 20
    assert store.rows[0]["access_code_id"] == code_id
    assert store.rows[0]["code_hash"] == hash_code(displayed_code)
    assert displayed_code not in str(store.rows)


def test_authorization_is_scoped_to_configured_property():
    store, access, code = fixture()
    store.rows.append(
        {
            "event_type": "REDEEMED",
            "telegram_user_id": "91",
            "property_id": "another-property",
            "role": "FARMER",
            "state": "AUTHORIZED",
            "access_code_id": "foreign-code",
        }
    )

    assert not asyncio.run(access.is_authorized(91))
    assert asyncio.run(access.redeem(91, code)) == AUTHORIZED_REPLY
    assert asyncio.run(access.is_authorized(91))
    assert access.authorized_property_id(91) == access.settings.farm_property_id
