"""Same-host process locks for the single-writer bot and its admin CLI."""

from __future__ import annotations

import hashlib
import sqlite3
import tempfile
from pathlib import Path
from typing import Any


class ProcessLockError(RuntimeError):
    """The process-scoped operation lock is already held."""


class ProcessLock:
    """Hold an exclusive SQLite file lock keyed by the configured spreadsheet.

    SQLite's file locking coordinates separate processes on the same host. The
    bot holds this for its lifetime; administrative revocation acquires it only
    while the bot is stopped.
    """

    def __init__(self, key: str, *, lock_directory: str | Path | None = None) -> None:
        if not key:
            raise ValueError("A process lock key is required")
        directory = Path(lock_directory) if lock_directory else Path(tempfile.gettempdir()) / "agro-notes-locks"
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        self.path = directory / f"{digest}.sqlite3"
        self._connection: Any | None = None

    def acquire(self) -> None:
        if self._connection is not None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=0.2)
        try:
            connection.execute("BEGIN EXCLUSIVE")
        except sqlite3.OperationalError as exc:
            connection.close()
            if "locked" in str(exc).casefold():
                raise ProcessLockError("Agro Notes bot is active; stop it before revoking an invitation.") from None
            raise
        self._connection = connection

    def release(self) -> None:
        connection, self._connection = self._connection, None
        if connection is not None:
            try:
                connection.rollback()
            finally:
                connection.close()
