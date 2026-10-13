import asyncio
from datetime import UTC, datetime, timedelta

from agro_notes.access_control import (
    AUTHORIZED_REPLY,
    BLOCKED_REPLY,
    INVALID_CODE_REPLY,
    AccessService,
    hash_code,
    normalize_code,
)
from agro_notes.settings import Settings
from agro_notes.sheets import TAB_HEADERS


class MemoryStore:
    def __init__(self):
        self.rows = []

    def read_rows(self, tab):
        assert tab == "Telegram_Access"
        return list(self.rows)

    def append_rows(self, tab, rows):
        assert tab == "Telegram_Access"
        self.rows.extend(dict(row) for row in rows)


def fixture(max_uses=1, expires_at=None):
    store = MemoryStore()
    settings = Settings(TELEGRAM_ALLOWED_USER_IDS="", GOOGLE_SHEET_ID="sheet")
    access = AccessService(store, settings)
    code = "0123456789ABCDEF0123456789ABCDEF"
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
    assert normalize_code(" 01234567-89abcdef-01234567-89abcdef ") == code
    assert asyncio.run(access.redeem(7, code)) == AUTHORIZED_REPLY
    assert all(code not in str(row) for row in store.rows)
    assert any(row.get("event_type") == "REDEEMED" for row in store.rows)


def test_unknown_expired_revoked_and_exhausted_codes_have_generic_reply():
    store, access, code = fixture()
    assert asyncio.run(access.redeem(1, "F" * 32)) == INVALID_CODE_REPLY

    expired_store, expired_access, expired_code = fixture(expires_at=datetime.now(UTC) - timedelta(seconds=1))
    assert asyncio.run(expired_access.redeem(2, expired_code)) == INVALID_CODE_REPLY

    revoked_store, revoked_access, revoked_code = fixture()
    revoked_store.rows.append({"event_type": "CODE_REVOKED", "access_code_id": "code-1"})
    assert asyncio.run(revoked_access.redeem(3, revoked_code)) == INVALID_CODE_REPLY

    other_property_store, other_property_access, other_property_code = fixture()
    other_property_store.rows[0]["property_id"] = "another-property"
    assert asyncio.run(other_property_access.redeem(33, other_property_code)) == INVALID_CODE_REPLY

    exhausted_store, exhausted_access, exhausted_code = fixture()
    exhausted_store.rows.append({"event_type": "REDEEMED", "access_code_id": "code-1", "redemption_id": "prior"})
    assert asyncio.run(exhausted_access.redeem(4, exhausted_code)) == INVALID_CODE_REPLY


def test_redemption_is_idempotent_and_existing_authorized_user_consumes_no_second_use():
    store, access, code = fixture(max_uses=1)
    assert asyncio.run(access.redeem(9, code)) == AUTHORIZED_REPLY
    count = sum(row.get("event_type") == "REDEEMED" for row in store.rows)
    assert asyncio.run(access.redeem(9, code)) == AUTHORIZED_REPLY
    assert sum(row.get("event_type") == "REDEEMED" for row in store.rows) == count == 1


def test_redemption_writes_only_columns_in_the_persisted_access_schema():
    store, access, code = fixture()
    original_append = store.append_rows

    def append_rows(tab, rows):
        assert all(set(row).issubset(TAB_HEADERS[tab]) for row in rows)
        original_append(tab, rows)

    store.append_rows = append_rows

    assert asyncio.run(access.redeem(17, code)) == AUTHORIZED_REPLY


def test_single_remaining_use_is_serialized_between_users():
    store, access, code = fixture(max_uses=1)

    async def race():
        return await asyncio.gather(access.redeem(11, code), access.redeem(12, code))

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
    assert asyncio.run(access.redeem(77, "0123456789ABCDEF0123456789ABCDEF")) == BLOCKED_REPLY
    assert any(row.get("state") == "BLOCKED" and row.get("reason") == "FAILED_ATTEMPTS" for row in store.rows)
