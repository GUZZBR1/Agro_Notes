import subprocess
import sys

import pytest

from agro_notes.process_lock import ProcessLock, ProcessLockError


def test_process_lock_prevents_second_process_lock_until_released(tmp_path):
    bot_lock = ProcessLock("sheet-id", lock_directory=tmp_path)
    cli_lock = ProcessLock("sheet-id", lock_directory=tmp_path)

    bot_lock.acquire()
    try:
        with pytest.raises(ProcessLockError, match="bot is active"):
            cli_lock.acquire()
    finally:
        bot_lock.release()

    cli_lock.acquire()
    cli_lock.release()


def test_process_lock_coordinates_distinct_processes(tmp_path):
    script = (
        "from agro_notes.process_lock import ProcessLock; "
        "import sys; lock=ProcessLock('sheet-id', lock_directory=sys.argv[1]); "
        "lock.acquire(); print('READY', flush=True); input(); lock.release()"
    )
    child = subprocess.Popen(
        [sys.executable, "-c", script, str(tmp_path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert child.stdout is not None
        assert child.stdout.readline().strip() == "READY"
        with pytest.raises(ProcessLockError, match="bot is active"):
            ProcessLock("sheet-id", lock_directory=tmp_path).acquire()
    finally:
        if child.stdin:
            child.stdin.write("release\n")
            child.stdin.flush()
        child.wait(timeout=5)
    assert child.returncode == 0, child.stderr.read() if child.stderr else "child failed"
