"""Persistent Telegram invitation redemption and authorization.

The application is intentionally a single writer. Google Sheets does not offer
compare-and-swap, so redemption reads and appends are serialized in this process.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import secrets
import tempfile
import threading
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

try:
    import fcntl
except ImportError:  # pragma: no cover - exercised on Windows deployments
    fcntl = None
    import msvcrt
else:
    msvcrt = None

INVALID_CODE_REPLY = "Código inválido ou indisponível."
WAITING_REPLY = "Envie seu código de acesso em uma mensagem privada."
AUTHORIZED_REPLY = "Acesso liberado. Envie um texto ou áudio com a movimentação da fazenda."
BLOCKED_REPLY = "Não foi possível liberar o acesso agora. Contate o administrador."
MAX_ATTEMPTS = 5
ATTEMPT_WINDOW = timedelta(minutes=15)
COOLDOWN = timedelta(minutes=15)


def _instant(value: Any) -> datetime | None:
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if result.tzinfo is None:
            return None
        return result.astimezone(UTC)
    except (TypeError, ValueError):
        return None


def normalize_code(value: str) -> str:
    """Accept the generated 20-hex code, with optional AGRO prefix and separators."""
    compact = value.strip().upper()
    if compact.startswith("AGRO-"):
        compact = compact[5:]
    compact = compact.replace("-", "").replace(" ", "")
    if len(compact) != 20 or any(char not in "0123456789ABCDEF" for char in compact):
        return ""
    return compact


def hash_code(code: str) -> str:
    normalized = normalize_code(code)
    if not normalized:
        raise ValueError("Código de acesso inválido.")
    return hashlib.sha256(normalized.encode("ascii")).hexdigest()


class AccessService:
    """Authorization source of truth shared by router and processor."""

    def __init__(self, store: Any, settings: Any):
        self.store = store
        self.settings = settings
        self._lock = threading.RLock()
        sheet_key = hashlib.sha256(str(settings.google_sheet_id).encode("utf-8")).hexdigest()[:24]
        self._process_lock_path = Path(tempfile.gettempdir()) / f"agro-notes-access-{sheet_key}.lock"
        self._blocked_until: dict[int, datetime] = {}

    @contextmanager
    def _exclusive(self):
        with self._lock:
            with self._process_lock_path.open("a+b") as lock_file:
                if fcntl:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                else:
                    lock_file.seek(0)
                    if not lock_file.read(1):
                        lock_file.write(b"0")
                        lock_file.flush()
                    lock_file.seek(0)
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
                try:
                    yield
                finally:
                    if fcntl:
                        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                    else:
                        lock_file.seek(0)
                        msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)

    def _rows(self) -> list[dict[str, Any]]:
        return self.store.read_rows("Telegram_Access")

    def _append(self, **row: Any) -> None:
        row.setdefault("event_id", str(uuid4()))
        row.setdefault("created_at", datetime.now(UTC).isoformat())
        self.store.append_rows("Telegram_Access", [row])

    def _latest_user(self, rows: list[dict[str, Any]], user_id: int) -> dict[str, Any] | None:
        return next(
            (
                row
                for row in reversed(rows)
                if row.get("telegram_user_id") == str(user_id)
                and row.get("property_id") == self.settings.farm_property_id
                and row.get("event_type") in {"USER_STATE", "REDEEMED"}
            ),
            None,
        )

    def _state(self, rows: list[dict[str, Any]], user_id: int) -> str:
        row = self._latest_user(rows, user_id)
        if row:
            state = str(row.get("state", "")).upper()
            until = _instant(row.get("blocked_until"))
            if state == "BLOCKED" and row.get("reason") == "FAILED_ATTEMPTS" and until:
                if datetime.now(UTC) >= until:
                    return "WAITING_ACCESS_CODE"
                self._blocked_until[user_id] = until
            return state or "UNREGISTERED"
        # One-time compatibility migration. Any later persisted state overrides it.
        if user_id in self.settings.allowed_user_ids:
            self._append(
                event_type="USER_STATE",
                telegram_user_id=str(user_id),
                property_id=self.settings.farm_property_id,
                role="FARMER",
                state="AUTHORIZED",
                reason="LEGACY_WHITELIST_MIGRATION",
                attempt_count="0",
            )
            return "AUTHORIZED"
        return "UNREGISTERED"

    def _is_authorized(self, user_id: int) -> bool:
        with self._exclusive():
            now = datetime.now(UTC)
            cached_block = self._blocked_until.get(user_id)
            if cached_block and now < cached_block:
                return False
            self._blocked_until.pop(user_id, None)
            rows = self._rows()
            current = self._latest_user(rows, user_id)
            if current and str(current.get("state", "")).upper() == "BLOCKED":
                blocked_until = _instant(current.get("blocked_until"))
                if blocked_until and now < blocked_until:
                    self._blocked_until[user_id] = blocked_until
                    return False
            if not current:
                return self._state(rows, user_id) == "AUTHORIZED"
            return (
                str(current.get("state", "")).upper() == "AUTHORIZED"
                and current.get("property_id") == self.settings.farm_property_id
            )

    async def is_authorized(self, user_id: int) -> bool:
        return await asyncio.to_thread(self._is_authorized, user_id)

    def authorized_property_id(self, user_id: int) -> str | None:
        """Return the property bound to an active Telegram grant, never a caller-supplied value."""
        with self._exclusive():
            rows = self._rows()
            current = self._latest_user(rows, user_id)
            if current is None and self._state(rows, user_id) == "AUTHORIZED":
                rows = self._rows()
                current = self._latest_user(rows, user_id)
            if (
                current
                and str(current.get("state", "")).upper() == "AUTHORIZED"
                and current.get("property_id") == self.settings.farm_property_id
            ):
                return str(current["property_id"])
            return None

    def _start(self, user_id: int, display_name: str = "", username: str = "") -> str:
        with self._exclusive():
            blocked_until = self._blocked_until.get(user_id)
            if blocked_until and datetime.now(UTC) < blocked_until:
                return BLOCKED_REPLY
            self._blocked_until.pop(user_id, None)
            rows = self._rows()
            state = self._state(rows, user_id)
            if state == "AUTHORIZED":
                return AUTHORIZED_REPLY
            if state in {"BLOCKED", "REVOKED"}:
                return BLOCKED_REPLY
            if state == "UNREGISTERED":
                self._append(
                    event_type="USER_STATE",
                    telegram_user_id=str(user_id),
                    display_name=display_name,
                    username=username,
                    property_id=self.settings.farm_property_id,
                    role="FARMER",
                    state="WAITING_ACCESS_CODE",
                    attempt_count="0",
                )
            return WAITING_REPLY

    async def start(self, user_id: int, display_name: str = "", username: str = "") -> str:
        return await asyncio.to_thread(self._start, user_id, display_name, username)

    def _redeem(self, user_id: int, raw_code: str, display_name: str = "", username: str = "") -> str:
        with self._exclusive():
            cached_block = self._blocked_until.get(user_id)
            if cached_block and datetime.now(UTC) < cached_block:
                return BLOCKED_REPLY
            self._blocked_until.pop(user_id, None)
            rows = self._rows()
            now = datetime.now(UTC)
            state = self._state(rows, user_id)
            if state == "AUTHORIZED":
                return AUTHORIZED_REPLY
            if state in {"BLOCKED", "REVOKED"}:
                return BLOCKED_REPLY
            latest_user = self._latest_user(rows, user_id)
            if state == "UNREGISTERED":
                self._append(
                    event_type="USER_STATE",
                    telegram_user_id=str(user_id),
                    display_name=display_name,
                    username=username,
                    property_id=self.settings.farm_property_id,
                    role="FARMER",
                    state="WAITING_ACCESS_CODE",
                    attempt_count="0",
                )
                rows = self._rows()
                latest_user = self._latest_user(rows, user_id)
            until = _instant(latest_user.get("blocked_until")) if latest_user else None
            if latest_user and latest_user.get("state") == "BLOCKED" and until and now < until:
                return BLOCKED_REPLY
            cutoff = now - ATTEMPT_WINDOW
            recent_attempts = [
                row
                for row in rows
                if row.get("event_type") == "FAILED_ATTEMPT"
                and row.get("telegram_user_id") == str(user_id)
                and (created := _instant(row.get("created_at"))) is not None
                and created >= cutoff
            ]
            if len(recent_attempts) >= MAX_ATTEMPTS:
                until = now + COOLDOWN
                self._blocked_until[user_id] = until
                self._append(
                    event_type="USER_STATE",
                    telegram_user_id=str(user_id),
                    property_id=self.settings.farm_property_id,
                    role="FARMER",
                    state="BLOCKED",
                    reason="FAILED_ATTEMPTS",
                    attempt_count=str(len(recent_attempts)),
                    blocked_until=until.isoformat(),
                )
                return BLOCKED_REPLY
            code = normalize_code(raw_code)
            code_hash = hash_code(code) if code else hashlib.sha256(b"invalid-code-dummy-value").hexdigest()
            code_row = None
            compared = False
            for row in rows:
                if row.get("event_type") != "CODE_CREATED":
                    continue
                stored_hash = str(row.get("code_hash", ""))
                valid_digest = len(stored_hash) == 64 and all(
                    char in "0123456789abcdef" for char in stored_hash
                )
                matches = hmac.compare_digest(code_hash, stored_hash if valid_digest else "0" * 64)
                compared = True
                if matches:
                    code_row = row
            if not compared:
                hmac.compare_digest(code_hash, "0" * 64)
            code_events = [
                row for row in rows if code_row and row.get("access_code_id") == code_row.get("access_code_id")
            ]
            revoked = any(row.get("event_type") == "CODE_REVOKED" for row in code_events)
            uses = sum(row.get("event_type") == "REDEEMED" for row in code_events)
            expires = _instant(code_row.get("expires_at")) if code_row else None
            try:
                max_uses = int(code_row.get("max_uses") or 0) if code_row else 0
            except (TypeError, ValueError):
                max_uses = 0
            eligible = bool(
                code_row
                and not revoked
                and expires
                and now < expires
                and code_row.get("property_id") == self.settings.farm_property_id
                and code_row.get("role") == "FARMER"
                and max_uses > 0
                and uses < max_uses
            )
            if not eligible:
                self._append(
                    event_type="FAILED_ATTEMPT",
                    telegram_user_id=str(user_id),
                    property_id=self.settings.farm_property_id,
                    state="WAITING_ACCESS_CODE",
                    reason="INVALID_OR_UNAVAILABLE",
                )
                attempts = len(recent_attempts) + 1
                if attempts >= MAX_ATTEMPTS:
                    until = now + COOLDOWN
                    self._blocked_until[user_id] = until
                    self._append(
                        event_type="USER_STATE",
                        telegram_user_id=str(user_id),
                        property_id=self.settings.farm_property_id,
                        role="FARMER",
                        state="BLOCKED",
                        reason="FAILED_ATTEMPTS",
                        attempt_count=str(attempts),
                        blocked_until=until.isoformat(),
                    )
                    return BLOCKED_REPLY
                return INVALID_CODE_REPLY
            if any(
                row.get("event_type") == "REDEEMED"
                and row.get("access_code_id") == code_row["access_code_id"]
                and row.get("telegram_user_id") == str(user_id)
                for row in rows
            ):
                return AUTHORIZED_REPLY
            # One append request is the durable, indivisible grant and use record.
            self._append(
                event_type="REDEEMED",
                telegram_user_id=str(user_id),
                display_name=display_name,
                username=username,
                property_id=code_row["property_id"],
                role=code_row["role"],
                state="AUTHORIZED",
                access_code_id=code_row["access_code_id"],
            )
            return AUTHORIZED_REPLY

    async def redeem(self, user_id: int, raw_code: str, display_name: str = "", username: str = "") -> str:
        if len(raw_code) > 64:
            raw_code = ""
        return await asyncio.to_thread(self._redeem, user_id, raw_code, display_name, username)

    async def set_waiting(self, user_id: int) -> str:
        def cancel() -> str:
            with self._exclusive():
                blocked_until = self._blocked_until.get(user_id)
                if blocked_until and datetime.now(UTC) < blocked_until:
                    return BLOCKED_REPLY
                self._blocked_until.pop(user_id, None)
                rows = self._rows()
                state = self._state(rows, user_id)
                if state == "AUTHORIZED":
                    return AUTHORIZED_REPLY
                if state in {"BLOCKED", "REVOKED"}:
                    return BLOCKED_REPLY
                self._append(
                    event_type="USER_STATE",
                    telegram_user_id=str(user_id),
                    property_id=self.settings.farm_property_id,
                    role="FARMER",
                    state="UNREGISTERED",
                    reason="ONBOARDING_CANCELLED",
                    attempt_count="0",
                )
                return "Solicitação cancelada. Envie /start para tentar novamente."

        return await asyncio.to_thread(cancel)

    def revoke_code(self, code_id: str, actor_id: str = "admin") -> None:
        with self._exclusive():
            if not any(
                row.get("event_type") == "CODE_CREATED" and row.get("access_code_id") == code_id for row in self._rows()
            ):
                raise ValueError("Código não encontrado.")
            self._append(event_type="CODE_REVOKED", access_code_id=code_id, actor_id=str(actor_id), state="REVOKED")

    def revoke_user(self, user_id: int, actor_id: str = "admin") -> None:
        with self._exclusive():
            rows = self._rows()
            current = self._latest_user(rows, user_id)
            if not current or current.get("state") != "AUTHORIZED":
                raise ValueError("Usuário autorizado não encontrado.")
            self._append(
                event_type="USER_STATE",
                telegram_user_id=str(user_id),
                property_id=current.get("property_id", ""),
                role=current.get("role", "FARMER"),
                state="REVOKED",
                reason="ADMIN_REVOKED",
                attempt_count="0",
                actor_id=str(actor_id),
            )


def generate_invitation(
    store: Any, settings: Any, *, expires_at: datetime, max_uses: int = 1, actor_id: str = "admin"
) -> tuple[str, str]:
    """Persist an invitation hash and return its plaintext exactly once."""
    if expires_at.tzinfo is None or expires_at <= datetime.now(UTC):
        raise ValueError("expires_at precisa ser futuro e incluir fuso horário")
    if not 1 <= max_uses <= 1000:
        raise ValueError("max_uses precisa estar entre 1 e 1000")
    code = secrets.token_hex(10).upper()
    code_id = str(uuid4())
    store.append_rows(
        "Telegram_Access",
        [
            {
                "event_id": str(uuid4()),
                "event_type": "CODE_CREATED",
                "property_id": settings.farm_property_id,
                "role": "FARMER",
                "state": "AVAILABLE",
                "access_code_id": code_id,
                "code_hash": hash_code(code),
                "created_at": datetime.now(UTC).isoformat(),
                "expires_at": expires_at.astimezone(UTC).isoformat(),
                "max_uses": str(max_uses),
                "actor_id": str(actor_id),
            }
        ],
    )
    grouped_code = "-".join(code[index : index + 5] for index in range(0, 20, 5))
    return code_id, f"AGRO-{grouped_code}"
