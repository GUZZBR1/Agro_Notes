import hashlib
import logging
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import pytest
from cryptography.fernet import Fernet

from agro_notes.exports import ExportDocument, match_export_intent
from agro_notes.google_drive import DRIVE_FILE_SCOPE, DriveUnavailableError, GoogleDriveOAuth, _safe_filename
from agro_notes.settings import Settings


class MemoryStore:
    def __init__(self):
        self.tabs = {"Google_OAuth_States": [], "Google_Connections": []}

    def read_rows(self, tab):
        return list(self.tabs[tab])

    def append_rows(self, tab, rows):
        self.tabs[tab].extend(dict(row) for row in rows)


class FakeAccess:
    def __init__(self, authorized=None):
        self.authorized = authorized or {42: "farm-1"}

    def authorized_property_id(self, user_id):
        return self.authorized.get(user_id)


class FakeFlow:
    def __init__(self, state=None, credentials=None):
        self.state = state
        self.code_verifier = None
        self.credentials = credentials or SimpleNamespace(
            scopes=[DRIVE_FILE_SCOPE],
            granted_scopes=[DRIVE_FILE_SCOPE],
            refresh_token="refresh-secret-value",
            expiry=datetime.now(UTC) + timedelta(hours=1),
        )

    def authorization_url(self, **kwargs):
        self.authorization_options = kwargs
        if kwargs.get("code_challenge_method"):
            self.code_verifier = "pkce-verifier-secret"
        return f"https://accounts.google.test/authorize?state={self.state}", self.state

    def fetch_token(self, *, code):
        assert code == "authorization-code"
        assert self.code_verifier == "pkce-verifier-secret"


class FakeFlowFactory:
    def __init__(self):
        self.flows = []

    def __call__(self, _client_config, *, state=None, **_kwargs):
        flow = FakeFlow(state=state)
        self.flows.append(flow)
        return flow


def make_service(*, access=None, token_revoker=None):
    store = MemoryStore()
    settings = Settings(
        GOOGLE_OAUTH_CLIENT_ID="client-id",
        GOOGLE_OAUTH_CLIENT_SECRET="client-secret",
        GOOGLE_OAUTH_REDIRECT_URI="https://example.test/oauth/google/callback",
        GOOGLE_DRIVE_SCOPE=DRIVE_FILE_SCOPE,
        GOOGLE_OAUTH_TOKEN_ENCRYPTION_KEY=Fernet.generate_key().decode("ascii"),
    )
    flow_factory = FakeFlowFactory()
    service = GoogleDriveOAuth(
        store,
        settings,
        access or FakeAccess(),
        flow_factory=flow_factory,
        token_revoker=token_revoker,
    )
    service.drive_builder = lambda *_args, **_kwargs: FakeDrive()
    return store, service, flow_factory


def state_from_url(url):
    return url.split("state=", 1)[1]


def finish_pending(service):
    url = service.create_authorization_url(42)
    state = state_from_url(url)
    pending = service.handle_callback(state=state, code="authorization-code", error=None)
    return state, pending


def test_authorization_state_is_opaque_expiring_single_use_and_uses_pkce():
    store, service, flows = make_service()

    url = service.create_authorization_url(42)

    state = state_from_url(url)
    row = store.tabs["Google_OAuth_States"][0]
    assert len(state) >= 40
    assert str(42) not in state
    assert hashlib.sha256(state.encode()).hexdigest() == row["state_hash"]
    assert row["telegram_user_id"] == "42"
    assert row["property_id"] == "farm-1"
    assert row["encrypted_code_verifier"] != "pkce-verifier-secret"
    assert flows.flows[0].authorization_options["access_type"] == "offline"
    assert flows.flows[0].authorization_options["code_challenge_method"] == "S256"

    with pytest.raises(ValueError, match="expirou ou já foi usado"):
        service.handle_callback(state="forged", code="authorization-code", error=None)
    with pytest.raises(ValueError, match="retornou um código"):
        service.handle_callback(state=state, code=None, error=None)
    with pytest.raises(ValueError, match="expirou ou já foi usado"):
        service.handle_callback(state=state, code="authorization-code", error=None)


def test_official_google_oauth_flow_generates_s256_challenge_without_network_access():
    store = MemoryStore()
    settings = Settings(
        GOOGLE_OAUTH_CLIENT_ID="client-id",
        GOOGLE_OAUTH_CLIENT_SECRET="client-secret",
        GOOGLE_OAUTH_REDIRECT_URI="https://example.test/oauth/google/callback",
        GOOGLE_DRIVE_SCOPE=DRIVE_FILE_SCOPE,
        GOOGLE_OAUTH_TOKEN_ENCRYPTION_KEY=Fernet.generate_key().decode("ascii"),
    )
    service = GoogleDriveOAuth(store, settings, FakeAccess())

    url = service.create_authorization_url(42)
    query = parse_qs(urlparse(url).query)

    assert query["scope"] == [DRIVE_FILE_SCOPE]
    assert query["code_challenge_method"] == ["S256"]
    assert query["code_challenge"]
    assert "code_verifier" not in query


def test_oauth_rejects_broad_scopes_and_mismatched_callback_uris():
    settings = Settings(
        GOOGLE_OAUTH_CLIENT_ID="client-id",
        GOOGLE_OAUTH_CLIENT_SECRET="client-secret",
        GOOGLE_OAUTH_REDIRECT_URI="https://example.test/other/callback",
        GOOGLE_DRIVE_SCOPE="https://www.googleapis.com/auth/drive",
        GOOGLE_OAUTH_TOKEN_ENCRYPTION_KEY=Fernet.generate_key().decode("ascii"),
    )

    assert not settings.google_oauth_configured


def test_missing_oauth_credentials_do_not_block_core_application_configuration():
    settings = Settings(
        TELEGRAM_BOT_TOKEN="telegram-token",
        GOOGLE_SHEET_ID="sheet-id",
        GROQ_API_KEY="groq-token",
    )

    settings.validate_runtime()
    assert not settings.google_oauth_configured


def test_expired_and_google_denial_states_are_consumed_and_rejected():
    store, service, _ = make_service()
    url = service.create_authorization_url(42)
    state = state_from_url(url)
    store.tabs["Google_OAuth_States"][0]["expires_at"] = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
    with pytest.raises(ValueError, match="expirou ou já foi usado"):
        service.handle_callback(state=state, code="authorization-code", error=None)

    denied_url = service.create_authorization_url(42)
    denied_state = state_from_url(denied_url)
    with pytest.raises(ValueError, match="cancelada ou recusada"):
        service.handle_callback(state=denied_state, code=None, error="access_denied")
    assert store.tabs["Google_OAuth_States"][-1]["status"] == "CONSUMED"


def test_callback_persists_only_encrypted_refresh_token_pending_confirmation_then_connects():
    store, service, _ = make_service()

    _state, pending = finish_pending(service)

    row = store.tabs["Google_Connections"][-1]
    assert row["status"] == "PENDING"
    assert row["telegram_user_id"] == "42"
    assert row["property_id"] == "farm-1"
    assert row["encrypted_refresh_token"] != "refresh-secret-value"
    assert "refresh-secret-value" not in str(store.tabs)
    assert not service.is_connected(42)
    assert not service.confirm_connection(43, pending["connection_id"])
    assert service.confirm_connection(42, pending["connection_id"])
    assert service.is_connected(42)
    assert store.tabs["Google_Connections"][-1]["status"] == "CONNECTED"


def test_callback_rejects_missing_refresh_token_and_missing_scope():
    store, service, flows = make_service()
    state = state_from_url(service.create_authorization_url(42))
    missing_refresh_flow = FakeFlow(
        state=state, credentials=SimpleNamespace(scopes=[DRIVE_FILE_SCOPE], refresh_token=None)
    )
    missing_refresh_flow.code_verifier = "pkce-verifier-secret"
    service.flow_factory = lambda *_args, **_kwargs: missing_refresh_flow
    with pytest.raises(ValueError, match="credencial renovável"):
        service.handle_callback(state=state, code="authorization-code", error=None)

    service.flow_factory = flows
    state2 = state_from_url(service.create_authorization_url(42))
    missing_scope_flow = FakeFlow(
        state=state2,
        credentials=SimpleNamespace(scopes=[DRIVE_FILE_SCOPE], granted_scopes=["openid"], refresh_token="x"),
    )
    missing_scope_flow.code_verifier = "pkce-verifier-secret"
    service.flow_factory = lambda *_args, **_kwargs: missing_scope_flow
    with pytest.raises(ValueError, match="não concedeu o escopo"):
        service.handle_callback(state=state2, code="authorization-code", error=None)


def test_disconnect_revokes_google_token_and_cancels_pending_state_and_connection():
    revoked = []
    store, service, _ = make_service(token_revoker=revoked.append)
    _state, pending = finish_pending(service)
    assert service.confirm_connection(42, pending["connection_id"])
    assert service.disconnect(42)
    assert revoked == ["refresh-secret-value"]
    assert not service.is_connected(42)
    assert not service.confirm_connection(42, pending["connection_id"])
    assert store.tabs["Google_Connections"][-1]["status"] == "REVOKED"


def test_disconnect_invalidates_authorization_state_and_unauthorized_user_cannot_start_or_upload():
    _store, service, _ = make_service(access=FakeAccess({42: "farm-1"}))
    with pytest.raises(PermissionError):
        service.create_authorization_url(43)
    with pytest.raises(PermissionError):
        service.upload_for_user(43, ExportDocument("farm.xlsx", b"xlsx"))

    url = service.create_authorization_url(42)
    state = state_from_url(url)
    service.disconnect(42)
    with pytest.raises(ValueError, match="expirou ou já foi usado"):
        service.handle_callback(state=state, code="authorization-code", error=None)


def test_transient_refresh_errors_keep_connection_and_do_not_log_token(monkeypatch, caplog):
    store, service, _ = make_service()
    _state, pending = finish_pending(service)
    assert service.confirm_connection(42, pending["connection_id"])

    from google.oauth2.credentials import Credentials

    def fail_refresh(_self, _request):
        raise RuntimeError("provider response mentions refresh-secret-value")

    monkeypatch.setattr(Credentials, "refresh", fail_refresh)
    caplog.set_level(logging.WARNING)
    with pytest.raises(DriveUnavailableError, match="temporarily unavailable"):
        service.upload_for_user(42, ExportDocument("farm.xlsx", b"xlsx"))
    assert "refresh-secret-value" not in caplog.text
    assert service.is_connected(42)
    assert store.tabs["Google_Connections"][-1]["status"] == "CONNECTED"


def test_permanent_invalid_grant_refresh_error_revokes_connection(monkeypatch):
    _store, service, _ = make_service()
    _state, pending = finish_pending(service)
    assert service.confirm_connection(42, pending["connection_id"])

    from google.auth.exceptions import RefreshError
    from google.oauth2.credentials import Credentials

    def fail_refresh(_self, _request):
        raise RefreshError("invalid_grant: revoked", None, None)

    monkeypatch.setattr(Credentials, "refresh", fail_refresh)
    with pytest.raises(Exception, match="needs renewal"):
        service._credentials(42, "farm-1")
    assert not service.is_connected(42)


def test_successful_refresh_persists_rotated_encrypted_refresh_token_without_access_token(monkeypatch):
    store, service, _ = make_service()
    _state, pending = finish_pending(service)
    assert service.confirm_connection(42, pending["connection_id"])

    from google.oauth2.credentials import Credentials

    def refresh(credentials, _request):
        credentials._token = "short-lived-access-token"
        credentials._refresh_token = "rotated-refresh-token"
        credentials._expiry = datetime.now(UTC) + timedelta(hours=1)

    monkeypatch.setattr(Credentials, "refresh", refresh)
    service._credentials(42, "farm-1")

    latest = store.tabs["Google_Connections"][-1]
    decrypted = service._cipher().decrypt(latest["encrypted_refresh_token"].encode("ascii")).decode("utf-8")
    assert decrypted == "rotated-refresh-token"
    assert "rotated-refresh-token" not in str(store.tabs)
    assert "short-lived-access-token" not in str(store.tabs)
    assert latest["status"] == "CONNECTED"


def test_callback_rechecks_authorization_and_property_after_state_creation():
    access = FakeAccess()
    _store, service, _ = make_service(access=access)
    state = state_from_url(service.create_authorization_url(42))
    access.authorized[42] = "different-property"

    with pytest.raises(PermissionError):
        service.handle_callback(state=state, code="authorization-code", error=None)


class FakeRequest:
    def __init__(self, response):
        self.response = response

    def execute(self):
        return self.response


class FakeDriveFiles:
    def __init__(self):
        self.records = []
        self.created = []
        self.updated = []
        self._next = 0

    def list(self, *, q, **_kwargs):
        name = q.split("name = '", 1)[1].split("'", 1)[0]
        return FakeRequest({"files": [row for row in self.records if row["name"] == name]})

    def create(self, *, body, **_kwargs):
        self._next += 1
        row = {"id": f"file-{self._next}", **body}
        if body.get("mimeType") != "application/vnd.google-apps.folder":
            row["webViewLink"] = "https://drive.google.test/view/file"
        self.records.append(row)
        self.created.append(row)
        return FakeRequest(row)

    def update(self, *, fileId, **_kwargs):
        self.updated.append(fileId)
        row = next(row for row in self.records if row["id"] == fileId)
        return FakeRequest(row)


class FakeDrive:
    def __init__(self):
        self._files = FakeDriveFiles()

    def files(self):
        return self._files

    def about(self):
        return SimpleNamespace(get=lambda **_kwargs: FakeRequest({"user": {"emailAddress": "farmer@gmail.com"}}))


def test_drive_export_creates_folders_then_updates_same_export_without_duplicates():
    _store, service, _ = make_service()
    service._credentials = lambda _user, _property: object()
    drive = FakeDrive()
    service._drive = lambda _credentials: drive
    document = ExportDocument("Agro_Notes_farm_2026-10-13.xlsx", b"xlsx", "application/test")

    first = service.upload_for_user(42, document)
    second = service.upload_for_user(42, document)

    folders = [row for row in drive._files.created if row["mimeType"] == "application/vnd.google-apps.folder"]
    files = [row for row in drive._files.created if row["mimeType"] != "application/vnd.google-apps.folder"]
    assert [row["name"] for row in folders] == ["Agro Notes", "Exportações"]
    assert len(files) == 1
    assert drive._files.updated == [files[0]["id"]]
    assert first["file_id"] == second["file_id"] == files[0]["id"]
    assert first["web_view_link"] == "https://drive.google.test/view/file"


def test_drive_upload_failure_does_not_create_public_file_or_expose_provider_error(caplog):
    _store, service, _ = make_service()

    class FailingFiles(FakeDriveFiles):
        def create(self, *, body, **kwargs):
            if body.get("mimeType") != "application/vnd.google-apps.folder":
                raise RuntimeError("provider detail and refresh-secret-value")
            return super().create(body=body, **kwargs)

    drive = FakeDrive()
    drive._files = FailingFiles()
    service._credentials = lambda _user, _property: object()
    service._drive = lambda _credentials: drive

    with pytest.raises(RuntimeError):
        service.upload_for_user(42, ExportDocument("../../farm.xlsx", b"xlsx"))

    assert all(row["mimeType"] == "application/vnd.google-apps.folder" for row in drive._files.created)
    assert "refresh-secret-value" not in caplog.text
    assert "permissions" not in str(drive._files.created).lower()


def test_export_intent_routes_drive_saves_and_keeps_telegram_download_default():
    assert match_export_intent("salva minha planilha no Drive").destination == "drive"
    assert match_export_intent("/salvar_drive").destination == "drive"
    assert match_export_intent("/exportar").destination == "telegram"
    assert _safe_filename("../../farm.xlsx") == "farm.xlsx"
    assert _safe_filename("farm' OR trashed=false.xlsx") == "farm_OR_trashed_false.xlsx"
