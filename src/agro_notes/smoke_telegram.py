"""Verify Telegram bot authentication without sending a message."""

from __future__ import annotations

import asyncio
import json

from aiogram import Bot

from .settings import get_settings


async def smoke() -> dict[str, object]:
    settings = get_settings()
    if not settings.telegram_bot_token.strip():
        return {"status": "WAITING_FOR_EXTERNAL_CREDENTIALS", "required": "TELEGRAM_BOT_TOKEN"}
    bot = Bot(settings.telegram_bot_token)
    try:
        identity = await bot.get_me()
        return {"status": "PASS", "bot_id": identity.id, "bot_username": identity.username}
    finally:
        await bot.session.close()


def main() -> None:
    result = asyncio.run(smoke())
    print(json.dumps(result, ensure_ascii=False))
    if result["status"] != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
