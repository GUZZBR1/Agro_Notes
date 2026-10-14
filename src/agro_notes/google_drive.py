"""User-owned Google Drive export using offline OAuth credentials."""

from __future__ import annotations

import hashlib
import logging
import secrets
import threading
from datetime import UTC, datetime, timedelta
from io import BytesIO
from typing import Any
from uuid import uuid4

from .exports import ExportDocument

logger = logging.getLogger(__name__)
DRIVE_FILE_SCOPE = "https://www.googleapis.com/auth/drive.file"
FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"
STATE_TTL = timedelta(minutes=10)
STATE_INVALID = "Este link expirou ou já foi usado. Solicite um novo pelo bot."


class DriveNotConnectedError(RuntimeError):
    pass


class DriveUnavailableError(RuntimeError):
    """A connected user's Drive could not be reached temporarily."""


class DriveConfigurationError(RuntimeError):
    pass


class GoogleDriveOAuth:
    """OAuth state and connection ledger backed by append-only Google Sheets rows."""

    def __init__(
        self,
        store: Any,
        settings: Any,
        access: Any,
        *,
        flow_factory: Any = None,
        drive_builder: Any = None,
        request_factory: Any = None,
        token_revoker: Any = None,
    ) -> None:
        self.store = store
        self.settings = settings
        self.access = access
        self.flow_factory = flow_factory
        self.drive_builder = drive_builder
        self.request_factory = request_factory
        self.token_revoker = token_revoker
        self._lock = threading.RLock()
        self._folder_lock = threading.Lock()

    @property
    def configured(self) -> bool:
        if not self.settings.google_oauth_configured:
            return False
        try:
            self._cipher()
        except (ValueError, TypeError):
            return False
        return True

    def _require_configured(self) -> None:
        if not self.configured:
            raise DriveConfigurationError("Google Drive OAuth is not configured")

    def _cipher(self) -> Any:
        from cryptography.fernet import Fernet

        key = self.settings.google_oauth_token_encryption_key.encode("ascii")
        return Fernet(key)

    def _flow(self, *, state: str | None = None) -> Any:
        self._require_configured()
        if self.flow_factory is None:
            from google_auth_oauthlib.flow import Flow

            factory = Flow.from_client_config
        else:
            factory = self.flow_factory
        flow = factory(
            {
                "web": {
                    "client_id": self.settings.google_oauth_client_id,
                    "client_secret": self.settings.google_oauth_client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=[DRIVE_FILE_SCOPE],
            state=state,
            redirect_uri=self.settings.google_oauth_redirect_uri,
        )
        return flow

    def _active_connection(self, user_id: int, property_id: str) -> dict[str, Any] | None:
        latest_by_id: dict[str, tuple[int, dict[str, Any]]] = {}
        for index, row in enumerate(self._connection_rows(user_id, property_id)):
            latest_by_id[row.get("connection_id", "")] = (index, row)
        active = [
            entry
            for entry in latest_by_id.values()
            if entry[1].get("status") == "CONNECTED" and entry[1].get("encrypted_refresh_token")
        ]
        return max(active, key=lambda item: item[0])[1] if active else None

    def is_connected(self, user_id: int) -> bool:
        property_id = self.access.authorized_property_id(user_id)
        if not property_id:
            return False
        return self._active_connection(user_id, property_id) is not None

    def _check_owner(self, user_id: int, property_id: str) -> None:
        if self.access.authorized_property_id(user_id) != property_id:
            raise PermissionError("Telegram user is not authorized for this property")

    def create_authorization_url(self, user_id: int) -> str:
        self._require_configured()
        property_id = self.access.authorized_property_id(user_id)
        if not property_id:
            raise PermissionError("Telegram user is not authorized")
        with self._lock:
            if self._active_connection(user_id, property_id):
                raise ValueError("Google Drive is already connected")
            self.invalidate_pending_states(user_id, property_id)
            previous_connections = self._connection_rows(user_id, property_id)
            pending_ids = {
                row.get("connection_id")
                for row in previous_connections
                if row.get("status") == "PENDING" and row.get("connection_id")
            }
            for pending_id in pending_ids:
                self._append_connection(
                    user_id=user_id,
                    property_id=property_id,
                    status="REVOKED",
                    connection_id=pending_id,
                )
            state = secrets.token_urlsafe(32)
            now = datetime.now(UTC)
            flow = self._flow(state=state)
            url, _ = flow.authorization_url(
                access_type="offline",
                prompt="consent",
                code_challenge_method="S256",
            )
            verifier = getattr(flow, "code_verifier", None)
            encrypted_verifier = self._cipher().encrypt(verifier.encode("ascii")).decode("ascii") if verifier else ""
            self.store.append_rows(
                "Google_OAuth_States",
                [
                    {
                        "event_id": str(uuid4()),
                        "state_hash": hashlib.sha256(state.encode("ascii")).hexdigest(),
                        "telegram_user_id": str(user_id),
                        "property_id": property_id,
                        "created_at": now.isoformat(),
                        "expires_at": (now + STATE_TTL).isoformat(),
                        "status": "PENDING",
                        "encrypted_code_verifier": encrypted_verifier,
                    }
                ],
            )
            return url

    def _consume_state(self, state: str) -> dict[str, str] | None:
        state_hash = hashlib.sha256(state.encode("utf-8")).hexdigest()
        rows = self.store.read_rows("Google_OAuth_States")
        latest = next((row for row in reversed(rows) if row.get("state_hash") == state_hash), None)
        now = datetime.now(UTC)
        expires = _instant(latest.get("expires_at")) if latest else None
        if not latest or latest.get("status") != "PENDING" or not expires or now >= expires:
            return None
        result = {
            "telegram_user_id": latest["telegram_user_id"],
            "property_id": latest["property_id"],
            "encrypted_code_verifier": latest.get("encrypted_code_verifier", ""),
        }
        self.store.append_rows(
            "Google_OAuth_States",
            [
                {
                    "event_id": str(uuid4()),
                    "state_hash": state_hash,
                    "telegram_user_id": result["telegram_user_id"],
                    "property_id": result["property_id"],
                    "created_at": now.isoformat(),
                    "expires_at": latest["expires_at"],
                    "status": "CONSUMED",
                    "consumed_at": now.isoformat(),
                }
            ],
        )
        return result

    def invalidate_pending_states(self, user_id: int, property_id: str) -> None:
        with self._lock:
            rows = self.store.read_rows("Google_OAuth_States")
            latest_by_hash: dict[str, dict[str, Any]] = {}
            for row in rows:
                if row.get("telegram_user_id") == str(user_id) and row.get("property_id") == property_id:
                    latest_by_hash[row.get("state_hash", "")] = row
            now = datetime.now(UTC)
            pending = [row for row in latest_by_hash.values() if row.get("status") == "PENDING"]
            if pending:
                self.store.append_rows(
                    "Google_OAuth_States",
                    [
                        {
                            "event_id": str(uuid4()),
                            "state_hash": row["state_hash"],
                            "telegram_user_id": str(user_id),
                            "property_id": property_id,
                            "created_at": now.isoformat(),
                            "expires_at": row.get("expires_at", ""),
                            "status": "REVOKED",
                            "consumed_at": now.isoformat(),
                        }
                        for row in pending
                    ],
                )

    def _connection_rows(self, user_id: int, property_id: str) -> list[dict[str, Any]]:
        return [
            row
            for row in self.store.read_rows("Google_Connections")
            if row.get("telegram_user_id") == str(user_id) and row.get("property_id") == property_id
        ]

    def _append_connection(
        self,
        *,
        user_id: int,
        property_id: str,
        status: str,
        encrypted_token: str = "",
        scopes: str = "",
        expires_at: str = "",
        connection_id: str | None = None,
        connected_at: str | None = None,
        google_account_ref: str = "",
    ) -> str:
        connection_id = connection_id or str(uuid4())
        now = datetime.now(UTC).isoformat()
        self.store.append_rows(
            "Google_Connections",
            [
                {
                    "connection_id": connection_id,
                    "telegram_user_id": str(user_id),
                    "property_id": property_id,
                    "provider": "google_drive",
                    "google_account_ref": google_account_ref,
                    "encrypted_refresh_token": encrypted_token,
                    "scopes": scopes,
                    "connected_at": connected_at or now,
                    "expires_at": expires_at,
                    "status": status,
                    "revoked_at": now if status in {"REVOKED", "EXPIRED"} else "",
                }
            ],
        )
        return connection_id

    def handle_callback(self, *, state: str | None, code: str | None, error: str | None) -> dict[str, Any]:
        """Consume a state once and create a pending link requiring Telegram confirmation."""
        self._require_configured()
        if not state or len(state) > 256:
            raise ValueError(STATE_INVALID)
        with self._lock:
            owner = self._consume_state(state)
            if not owner:
                raise ValueError(STATE_INVALID)
            user_id = int(owner["telegram_user_id"])
            property_id = owner["property_id"]
            self._check_owner(user_id, property_id)
            if error:
                raise ValueError("A autorização do Google foi cancelada ou recusada.")
            if not code or len(code) > 4096:
                raise ValueError("A autorização do Google não retornou um código válido.")
            flow = self._flow(state=state)
            verifier = owner.get("encrypted_code_verifier")
            if verifier:
                flow.code_verifier = self._cipher().decrypt(verifier.encode("ascii")).decode("ascii")
            flow.fetch_token(code=code)
            credentials = flow.credentials
            granted_scopes = getattr(credentials, "granted_scopes", None)
            scopes = set(granted_scopes if granted_scopes is not None else (credentials.scopes or []))
            if DRIVE_FILE_SCOPE not in scopes:
                raise ValueError("O Google não concedeu o escopo Drive solicitado.")
            refresh_token = credentials.refresh_token
            if not refresh_token:
                raise ValueError("O Google não retornou uma credencial renovável. Tente conectar novamente.")
            self._check_owner(user_id, property_id)
            account_ref = self._google_account_ref(credentials)
            self._check_owner(user_id, property_id)
            encrypted = self._cipher().encrypt(refresh_token.encode("utf-8")).decode("ascii")
            expiry = credentials.expiry.astimezone(UTC).isoformat() if credentials.expiry else ""
            connection_id = self._append_connection(
                user_id=user_id,
                property_id=property_id,
                status="PENDING",
                encrypted_token=encrypted,
                scopes=" ".join(sorted(scopes)),
                expires_at=expiry,
                google_account_ref=account_ref,
            )
            return {
                "connection_id": connection_id,
                "telegram_user_id": user_id,
                "property_id": property_id,
                "google_account_ref": account_ref,
            }

    def confirm_connection(self, user_id: int, connection_id: str) -> bool:
        if not connection_id or len(connection_id) > 64:
            return False
        property_id = self.access.authorized_property_id(user_id)
        if not property_id:
            return False
        with self._lock:
            rows = self._connection_rows(user_id, property_id)
            pending = next(
                (row for row in reversed(rows) if row.get("connection_id") == connection_id), None
            )
            if not pending or pending.get("status") != "PENDING" or not pending.get("encrypted_refresh_token"):
                return False
            active = self._active_connection(user_id, property_id)
            if active:
                old_refresh = self._cipher().decrypt(active["encrypted_refresh_token"].encode("ascii")).decode("utf-8")
                self._revoke_token(old_refresh)
                self._append_connection(
                    user_id=user_id,
                    property_id=property_id,
                    status="REVOKED",
                    connection_id=active["connection_id"],
                )
            self._append_connection(
                user_id=user_id,
                property_id=property_id,
                status="CONNECTED",
                encrypted_token=pending["encrypted_refresh_token"],
                scopes=pending.get("scopes", ""),
                expires_at=pending.get("expires_at", ""),
                connection_id=connection_id,
            )
            return True

    def _revoke_token(self, token: str) -> bool:
        if self.token_revoker:
            return bool(self.token_revoker(token))
        try:
            from urllib.parse import urlencode

            from google.auth.transport.requests import Request

            Request()(
                "https://oauth2.googleapis.com/revoke",
                method="POST",
                body=urlencode({"token": token}).encode("ascii"),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10,
            )
            return True
        except Exception as exc:
            logger.warning("Google OAuth token revocation failed (%s)", type(exc).__name__)
            return False

    def disconnect(self, user_id: int) -> bool:
        property_id = self.access.authorized_property_id(user_id)
        if not property_id:
            raise PermissionError("Telegram user is not authorized")
        with self._lock:
            self.invalidate_pending_states(user_id, property_id)
            rows = self._connection_rows(user_id, property_id)
            latest_by_id: dict[str, dict[str, Any]] = {}
            for row in rows:
                latest_by_id[row.get("connection_id", "")] = row
            active = [row for row in latest_by_id.values() if row.get("status") in {"CONNECTED", "PENDING"}]
            if not active:
                return False
            refresh_tokens = [
                self._cipher().decrypt(row["encrypted_refresh_token"].encode("ascii")).decode("utf-8")
                for row in active
                if row.get("encrypted_refresh_token")
            ]
            for row in active:
                self._append_connection(
                    user_id=user_id,
                    property_id=property_id,
                    status="REVOKED",
                    connection_id=row.get("connection_id"),
                )
            for token in refresh_tokens:
                self._revoke_token(token)
            return True

    def _credentials(self, user_id: int, property_id: str) -> Any:
        self._require_configured()
        self._check_owner(user_id, property_id)
        with self._lock:
            connection = self._active_connection(user_id, property_id)
            if (
                not connection
                or connection.get("status") != "CONNECTED"
                or not connection.get("encrypted_refresh_token")
            ):
                raise DriveNotConnectedError("Google Drive is not connected")
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials

            refresh_token = self._cipher().decrypt(connection["encrypted_refresh_token"].encode("ascii")).decode(
                "utf-8"
            )
            credentials = Credentials(
                token=None,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.settings.google_oauth_client_id,
                client_secret=self.settings.google_oauth_client_secret,
                scopes=[DRIVE_FILE_SCOPE],
            )
            try:
                credentials.refresh(self.request_factory() if self.request_factory else Request())
            except Exception as exc:
                logger.warning("Google Drive credential refresh failed (%s)", type(exc).__name__)
                if self._permanent_refresh_failure(exc):
                    self._append_connection(
                        user_id=user_id,
                        property_id=property_id,
                        status="REVOKED",
                        connection_id=connection["connection_id"],
                    )
                    raise DriveNotConnectedError("Google Drive connection needs renewal") from None
                raise DriveUnavailableError("Google Drive is temporarily unavailable; retry later") from None
            new_refresh = credentials.refresh_token or refresh_token
            expiry = credentials.expiry.astimezone(UTC).isoformat() if credentials.expiry else ""
            self._append_connection(
                user_id=user_id,
                property_id=property_id,
                status="CONNECTED",
                encrypted_token=self._cipher().encrypt(new_refresh.encode("utf-8")).decode("ascii"),
                scopes=connection.get("scopes", ""),
                expires_at=expiry,
                connection_id=connection["connection_id"],
                connected_at=connection.get("connected_at"),
            )
            return credentials

    @staticmethod
    def _permanent_refresh_failure(exc: Exception) -> bool:
        error = getattr(exc, "failure_reason", None) or getattr(exc, "error", None)
        if str(error).casefold() in {"invalid_grant", "invalid_client", "unauthorized_client"}:
            return True
        # google-auth RefreshError may only expose the OAuth error in its response text.
        message = str(exc).casefold()
        return any(code in message for code in ("invalid_grant", "invalid_client", "unauthorized_client"))

    def _google_account_ref(self, credentials: Any) -> str:
        try:
            about = self._drive(credentials).about().get(fields="user(emailAddress)").execute()
            email = str(about.get("user", {}).get("emailAddress", ""))[:254]
            if not email:
                raise ValueError("Google account email is unavailable")
            return email
        except Exception as exc:
            logger.warning("Google Drive account lookup failed (%s)", type(exc).__name__)
            raise ValueError("Não foi possível identificar a conta Google autorizada. Tente novamente.") from None

    def _drive(self, credentials: Any) -> Any:
        if self.drive_builder:
            return self.drive_builder("drive", "v3", credentials=credentials, cache_discovery=False)
        from googleapiclient.discovery import build

        return build("drive", "v3", credentials=credentials, cache_discovery=False)

    @staticmethod
    def _escape_query(value: str) -> str:
        return value.replace("\\", "\\\\").replace("'", "\\'")

    @staticmethod
    def _files_list(drive: Any, query: str) -> list[dict[str, Any]]:
        response = drive.files().list(
            q=query,
            spaces="drive",
            pageSize=100,
            fields="nextPageToken,files(id,name,mimeType,webViewLink)",
        ).execute()
        return response.get("files", [])

    def _folder(self, drive: Any, name: str, parent_id: str | None = None) -> str:
        parent_query = f" and '{self._escape_query(parent_id)}' in parents" if parent_id else " and 'root' in parents"
        query = (
            f"name = '{self._escape_query(name)}' and mimeType = '{FOLDER_MIME_TYPE}'"
            f" and trashed = false{parent_query}"
        )
        found = self._files_list(drive, query)
        if found:
            return found[0]["id"]
        body: dict[str, Any] = {"name": name, "mimeType": FOLDER_MIME_TYPE}
        if parent_id:
            body["parents"] = [parent_id]
        created = drive.files().create(body=body, fields="id").execute()
        return created["id"]

    def upload_for_user(self, user_id: int, document: ExportDocument) -> dict[str, str]:
        property_id = self.access.authorized_property_id(user_id)
        if not property_id:
            raise PermissionError("Telegram user is not authorized")
        with self._lock:
            credentials = self._credentials(user_id, property_id)
            drive = self._drive(credentials)
            with self._folder_lock:
                app_folder = self._folder(drive, "Agro Notes")
                export_folder = self._folder(drive, "Exportações", app_folder)
            filename = _safe_filename(document.filename)
            query = (
                f"name = '{self._escape_query(filename)}' and '{self._escape_query(export_folder)}' in parents"
                " and trashed = false"
            )
            existing = self._files_list(drive, query)
            try:
                from googleapiclient.http import MediaIoBaseUpload

                media = MediaIoBaseUpload(BytesIO(document.content), mimetype=document.mime_type, resumable=False)
                if existing:
                    self._check_owner(user_id, property_id)
                    result = drive.files().update(
                        fileId=existing[0]["id"], media_body=media, fields="id,webViewLink"
                    ).execute()
                else:
                    self._check_owner(user_id, property_id)
                    result = drive.files().create(
                        body={"name": filename, "mimeType": document.mime_type, "parents": [export_folder]},
                        media_body=media,
                        fields="id,webViewLink",
                    ).execute()
            except Exception as exc:
                logger.warning("Google Drive upload failed (%s)", type(exc).__name__)
                raise
            return {"file_id": str(result.get("id", "")), "web_view_link": str(result.get("webViewLink", ""))}


def _instant(value: Any) -> datetime | None:
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return result.astimezone(UTC) if result.tzinfo else None
    except (TypeError, ValueError):
        return None


def _safe_filename(value: str) -> str:
    import re

    basename = value.replace("\\", "/").rsplit("/", 1)[-1]
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", basename).lstrip(".")
    return name[:180] if name.casefold().endswith(".xlsx") else f"{name[:174]}.xlsx"


def match_drive_connection_intent(text: str) -> str | None:
    normalized = " ".join(text.casefold().split())
    if normalized.startswith("/desconectar_drive") or ("drive" in normalized and "desconectar" in normalized):
        return "disconnect"
    if normalized.startswith("/conectar_drive") or ("drive" in normalized and "conectar" in normalized):
        return "connect"
    return None


