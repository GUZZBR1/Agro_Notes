"""Single-process application entry point; do not run multiple workers."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from fastapi import FastAPI, HTTPException

from .application import MVPProcessor
from .provider_factory import build_interpreter, build_transcriber
from .settings import get_settings
from .sheets import GoogleSheetsStore
from .telegram_bot import build_router

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate_runtime()
    store = GoogleSheetsStore.from_credentials(settings)
    await asyncio.to_thread(store.bootstrap)
    transcriber = None
    interpreter = None
    bot = None
    dispatcher = None
    polling = None
    try:
        interpreter = build_interpreter(settings)
        processor = MVPProcessor(settings, store, interpreter)
        transcriber = build_transcriber(settings)
        dispatcher = Dispatcher()
        dispatcher.include_router(build_router(processor, settings, transcriber))
        bot = Bot(settings.telegram_bot_token)
        polling = asyncio.create_task(dispatcher.start_polling(bot))
        app.state.store = store
        app.state.processor = processor
        app.state.ai_provider = settings.ai_provider
        app.state.transcription_provider = settings.transcription_provider
        app.state.polling_task = polling
        yield
    finally:
        if dispatcher and polling and not polling.done():
            try:
                await dispatcher.stop_polling()
            except Exception as exc:
                logger.error("Telegram polling stop failed (%s)", type(exc).__name__)
        if polling:
            try:
                await polling
            except Exception as exc:
                logger.error("Telegram polling task failed (%s)", type(exc).__name__)
        if bot:
            try:
                await bot.session.close()
            except Exception as exc:
                logger.error("Telegram client close failed (%s)", type(exc).__name__)
        if transcriber:
            try:
                await transcriber.close()
            except Exception as exc:
                logger.error("Transcription client close failed (%s)", type(exc).__name__)
        if interpreter:
            try:
                interpreter.close()
            except Exception as exc:
                logger.error("Interpretation client close failed (%s)", type(exc).__name__)


app = FastAPI(title="Agro Notes MVP", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    polling = getattr(app.state, "polling_task", None)
    if polling is None or polling.done():
        raise HTTPException(status_code=503, detail="Telegram polling is unavailable")
    return {"status": "ok"}
