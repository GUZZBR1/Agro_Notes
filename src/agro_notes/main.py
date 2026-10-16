"""Single-process application entry point; do not run multiple workers."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from .access_control import AccessService
from .application import MVPProcessor
from .google_drive import GoogleDriveOAuth
from .process_lock import ProcessLock
from .provider_factory import build_interpreter, build_transcriber
from .settings import get_settings
from .sheets import GoogleSheetsStore
from .telegram_bot import DurableTranscriptionQueue, build_router

settings = get_settings()
logger = logging.getLogger(__name__)


async def _drain_update_handlers(dispatcher: Dispatcher) -> None:
    """Wait for aiogram's in-flight handlers before releasing the writer lock."""
    # aiogram tracks `handle_as_tasks` update handlers here; polling shutdown
    # stops new updates but does not await this set before returning.
    tasks = getattr(dispatcher, "_handle_update_tasks", None)
    while tasks:
        pending = [task for task in tasks if not task.done()]
        if not pending:
            return
        await asyncio.gather(*pending, return_exceptions=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate_runtime()
    process_lock = ProcessLock(settings.google_sheet_id)
    process_lock.acquire()
    try:
        store = GoogleSheetsStore.from_credentials(settings)
        await asyncio.to_thread(store.bootstrap)
        access = AccessService(store, settings)
        google_drive = GoogleDriveOAuth(store, settings, access)
        transcriber = None
        transcription_queue = None
        interpreter = None
        bot = None
        dispatcher = None
        polling = None
        try:
            interpreter = build_interpreter(settings)
            processor = MVPProcessor(settings, store, interpreter, access=access, drive_export=google_drive)
            transcriber = build_transcriber(settings)
            transcription_queue = DurableTranscriptionQueue(processor, settings, transcriber)
            dispatcher = Dispatcher()
            dispatcher.include_router(
                build_router(
                    processor,
                    settings,
                    transcriber=transcriber,
                    transcription_queue=transcription_queue,
                    access=access,
                    google_drive=google_drive,
                )
            )
            bot = Bot(settings.telegram_bot_token)
            await transcription_queue.start(bot)
            polling = asyncio.create_task(dispatcher.start_polling(bot, close_bot_session=False))
            app.state.store = store
            app.state.processor = processor
            app.state.google_drive = google_drive
            app.state.bot = bot
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
            if dispatcher:
                await _drain_update_handlers(dispatcher)
            if transcription_queue:
                try:
                    await transcription_queue.close()
                except Exception as exc:
                    logger.error("Transcription recovery shutdown failed (%s)", type(exc).__name__)
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
    finally:
        process_lock.release()


app = FastAPI(title="Agro Notes MVP", lifespan=lifespan)


def _oauth_page(message: str, *, status_code: int = 200) -> HTMLResponse:
    return HTMLResponse(
        f"<!doctype html><html lang='pt-BR'><meta charset='utf-8'><title>Agro Notes</title>"
        f"<body><main><h1>Agro Notes</h1><p>{message}</p></main></body></html>",
        status_code=status_code,
        headers={
            "Cache-Control": "no-store",
            "Referrer-Policy": "no-referrer",
            "Content-Security-Policy": "default-src 'none'; base-uri 'none'; frame-ancestors 'none'",
        },
    )


@app.get("/oauth/google/callback", response_class=HTMLResponse)
async def google_oauth_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> HTMLResponse:
    service = getattr(app.state, "google_drive", None)
    bot = getattr(app.state, "bot", None)
    if service is None or bot is None:
        return _oauth_page("Não foi possível concluir a conexão agora. Tente novamente pelo bot.", status_code=503)
    try:
        pending = await asyncio.to_thread(service.handle_callback, state=state, code=code, error=error)
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Confirmar conexão", callback_data=f"drive_connect:{pending['connection_id']}"
                    )
                ]
            ]
        )
        await bot.send_message(
            chat_id=pending["telegram_user_id"],
            text=(
                f"O Google Drive autorizado é {pending['google_account_ref']}. "
                "Confirme aqui no Telegram para concluir a conexão."
            ),
            reply_markup=keyboard,
        )
    except Exception as exc:
        logger.warning("Google OAuth callback failed (%s)", type(exc).__name__)
        return _oauth_page(
            "Não foi possível validar a autorização. Volte ao bot e solicite um novo link.", status_code=400
        )
    return _oauth_page("Autorização recebida. Volte ao Telegram e confirme a conexão no bot.")


@app.get("/health")
async def health() -> dict[str, str]:
    polling = getattr(app.state, "polling_task", None)
    if polling is None or polling.done():
        raise HTTPException(status_code=503, detail="Telegram polling is unavailable")
    return {"status": "ok"}
