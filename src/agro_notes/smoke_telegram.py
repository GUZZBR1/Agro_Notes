"""Verify Telegram authentication and one authorized inbound message safely."""

from __future__ import annotations

import asyncio
import json
import secrets
from typing import Any

from aiogram import Bot

from .settings import Settings, get_settings

SMOKE_UPDATE_TYPES = ["message", "callback_query"]


async def _smoke(bot: Any, settings: Settings, *, wait_seconds: int = 30) -> dict[str, object]:
    if not settings.telegram_bot_token.strip():
        return {"status": "WAITING_FOR_EXTERNAL_CREDENTIALS", "required": "TELEGRAM_BOT_TOKEN"}
    if not settings.allowed_user_ids:
        return {"status": "WAITING_FOR_EXTERNAL_CREDENTIALS", "required": "TELEGRAM_ALLOWED_USER_IDS"}

    identity = await bot.get_me()
    webhook = await bot.get_webhook_info()
    if webhook.url:
        return {"status": "BLOCKED_WEBHOOK_CONFIGURED", "bot_id": identity.id}

    # Refuse to poll when older updates are queued: getUpdates is destructive
    # once an offset acknowledges them, and the smoke must not consume app data.
    pending = await bot.get_updates(timeout=0, limit=1, allowed_updates=SMOKE_UPDATE_TYPES)
    if pending:
        return {"status": "PENDING_UPDATES", "bot_id": identity.id}

    challenge = f"AGRO-SMOKE-{secrets.token_hex(4).upper()}"
    print(json.dumps({"telegram_smoke_challenge": challenge, "send_from_authorized_private_chat": True}))
    updates = await bot.get_updates(
        timeout=wait_seconds,
        limit=1,
        allowed_updates=SMOKE_UPDATE_TYPES,
        request_timeout=wait_seconds + 5,
    )
    if not updates:
        return {"status": "WAITING_FOR_OPERATOR_MESSAGE", "bot_id": identity.id}

    update = updates[0]
    message = update.message
    user = message.from_user if message else None
    if (
        message is None
        or message.text != challenge
        or message.chat.type != "private"
        or user is None
        or user.id not in settings.allowed_user_ids
    ):
        # Do not set an offset: an unrelated update remains available to the
        # application when the operator starts it after this smoke check.
        return {"status": "UNEXPECTED_UPDATE_PENDING", "bot_id": identity.id}

    await bot.send_message(message.chat.id, "Smoke do Telegram: recebimento confirmado.")
    # Acknowledge only the one verified challenge update. limit=1 and the empty
    # preflight ensure this offset cannot skip older updates.
    await bot.get_updates(
        offset=update.update_id + 1,
        timeout=0,
        limit=1,
        allowed_updates=SMOKE_UPDATE_TYPES,
    )
    return {"status": "PASS", "bot_id": identity.id, "inbound_message_verified": True}


async def smoke(settings: Settings | None = None, bot: Any | None = None) -> dict[str, object]:
    settings = settings or get_settings()
    if not settings.telegram_bot_token.strip():
        return {"status": "WAITING_FOR_EXTERNAL_CREDENTIALS", "required": "TELEGRAM_BOT_TOKEN"}
    if not settings.allowed_user_ids:
        return {"status": "WAITING_FOR_EXTERNAL_CREDENTIALS", "required": "TELEGRAM_ALLOWED_USER_IDS"}
    owns_bot = bot is None
    bot = bot or Bot(settings.telegram_bot_token)
    try:
        return await _smoke(bot, settings)
    except Exception as exc:
        return {"status": "EXTERNAL_PROVIDER_BLOCKED", "reason": type(exc).__name__}
    finally:
        if owns_bot:
            await bot.session.close()


def main() -> None:
    result = asyncio.run(smoke())
    print(json.dumps(result, ensure_ascii=False))
    if result["status"] != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
