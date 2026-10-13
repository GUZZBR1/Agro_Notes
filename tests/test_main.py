import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from agro_notes.main import app, health


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
