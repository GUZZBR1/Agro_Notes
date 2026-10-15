import pytest

from agro_notes.access_admin import revoke_code_when_bot_stopped
from agro_notes.process_lock import ProcessLock, ProcessLockError


def test_revoke_code_requires_bot_to_be_stopped(tmp_path, monkeypatch):
    class Access:
        revoked = False

        def revoke_code(self, _code_id):
            self.revoked = True

    access = Access()
    settings_sheet = "sheet-id"
    active_bot = ProcessLock(settings_sheet, lock_directory=tmp_path)
    active_bot.acquire()
    monkeypatch.setattr(
        "agro_notes.access_admin.ProcessLock",
        lambda _key: ProcessLock(settings_sheet, lock_directory=tmp_path),
    )
    try:
        with pytest.raises(ProcessLockError, match="bot is active"):
            revoke_code_when_bot_stopped(access, settings_sheet, "code-id")
        assert not access.revoked
    finally:
        active_bot.release()

    revoke_code_when_bot_stopped(access, settings_sheet, "code-id")
    assert access.revoked
