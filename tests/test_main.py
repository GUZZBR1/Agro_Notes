import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from agro_notes.main import _drain_update_handlers, _oauth_page, app, health


def test_health_reports_unavailable_when_polling_is_missing_or_stopped():
    if hasattr(app.state, "polling_task"):
        del app.state.polling_task
    with pytest.raises(HTTPException) as missing:
        asyncio.run(health())
    assert missing.value.status_code == 503

    app.state.polling_task = SimpleNamespace(done=lambda: True)
    with pytest.raises(HTTPException) as stopped:
        asyncio.run(health())
    assert stopped.value.status_code == 503


def test_health_reports_ok_while_polling_task_is_running():
    app.state.polling_task = SimpleNamespace(done=lambda: False)
    assert asyncio.run(health()) == {"status": "ok"}


def test_oauth_callback_page_disables_caching_referrers_and_embedded_content():
    response = _oauth_page("Autorização recebida.")

    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


def test_shutdown_waits_for_inflight_dispatcher_handlers():
    async def check():
        release = asyncio.Event()
        completed = asyncio.Event()

        async def handler():
            await release.wait()
            completed.set()

        task = asyncio.create_task(handler())
        dispatcher = SimpleNamespace(_handle_update_tasks={task})
        drain = asyncio.create_task(_drain_update_handlers(dispatcher))
        await asyncio.sleep(0)
        assert not drain.done()
        release.set()
        await drain
        assert completed.is_set()

    asyncio.run(check())
