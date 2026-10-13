"""Single-process application entry point; do not run multiple workers."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from fastapi import FastAPI, HTTPException

from .application import MVPProcessor
from .interpreter import StructuredOutputInterpreter
from .llm import OpenAIResponsesClient
from .settings import get_settings
from .sheets import GoogleSheetsStore
from .telegram_bot import build_router
from .transcription import OpenAITranscriber

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate_runtime()
    store = GoogleSheetsStore.from_credentials(settings)
    await asyncio.to_thread(store.bootstrap)
    responses_client = None
    transcriber = None
    bot = None
    dispatcher = None
    polling = None
    try:
        responses_client = OpenAIResponsesClient(settings)
        transcriber = OpenAITranscriber(settings)
        processor = MVPProcessor(settings, store, StructuredOutputInterpreter(responses_client))
        dispatcher = Dispatcher()
        dispatcher.include_router(build_router(processor, settings, transcriber))
        bot = Bot(settings.telegram_bot_token)
        polling = asyncio.create_task(dispatcher.start_polling(bot))
        app.state.store = store
        app.state.processor = processor
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
                logger.error("OpenAI transcription client close failed (%s)", type(exc).__name__)
        if responses_client:
            try:
                responses_client.close()
            except Exception as exc:
                logger.error("OpenAI responses client close failed (%s)", type(exc).__name__)


app = FastAPI(title="Agro Notes MVP", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    polling = getattr(app.state, "polling_task", None)
    if polling is None or polling.done():
        raise HTTPException(status_code=503, detail="Telegram polling is unavailable")
    return {"status": "ok"}
