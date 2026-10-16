from functools import lru_cache
from urllib.parse import urlsplit

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    telegram_allowed_user_ids: str = Field(default="", alias="TELEGRAM_ALLOWED_USER_IDS")
    farm_property_id: str = Field(default="FARM-001", validation_alias=AliasChoices("PROPERTY_ID", "FARM_PROPERTY_ID"))
    farm_timezone: str = Field(
        default="America/Sao_Paulo", validation_alias=AliasChoices("PROPERTY_TIMEZONE", "FARM_TIMEZONE")
    )
    google_sheet_id: str = Field(default="", alias="GOOGLE_SHEET_ID")
    google_credentials_file: str = Field(
        default="credentials/google-service-account.json",
        validation_alias=AliasChoices("GOOGLE_APPLICATION_CREDENTIALS", "GOOGLE_CREDENTIALS_FILE"),
    )
    google_oauth_client_id: str = Field(default="", alias="GOOGLE_OAUTH_CLIENT_ID")
    google_oauth_client_secret: str = Field(default="", alias="GOOGLE_OAUTH_CLIENT_SECRET")
    google_oauth_redirect_uri: str = Field(default="", alias="GOOGLE_OAUTH_REDIRECT_URI")
    google_drive_scope: str = Field(
        default="https://www.googleapis.com/auth/drive.file", alias="GOOGLE_DRIVE_SCOPE"
    )
    google_oauth_token_encryption_key: str = Field(default="", alias="GOOGLE_OAUTH_TOKEN_ENCRYPTION_KEY")
    ai_provider: str = Field(default="groq", validation_alias=AliasChoices("AI_PROVIDER", "INTERPRETATION_PROVIDER"))
    transcription_provider: str = Field(default="groq", alias="TRANSCRIPTION_PROVIDER")
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    groq_model: str = Field(default="openai/gpt-oss-20b", validation_alias=AliasChoices("GROQ_LLM_MODEL", "GROQ_MODEL"))
    groq_transcription_model: str = Field(default="whisper-large-v3-turbo", alias="GROQ_TRANSCRIPTION_MODEL")
    groq_base_url: str = Field(default="https://api.groq.com/openai/v1", alias="GROQ_BASE_URL")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4.1-mini", alias="OPENAI_MODEL")
    openai_transcription_model: str = Field(default="gpt-4o-mini-transcribe", alias="OPENAI_TRANSCRIPTION_MODEL")
    voice_max_bytes: int = Field(default=18_000_000, gt=0, le=20_000_000)
    min_interpretation_confidence: float = Field(default=0.75, ge=0, le=1)

    @field_validator("farm_timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"FARM_TIMEZONE inválido: {value}") from exc
        return value

    @property
    def allowed_user_ids(self) -> frozenset[int]:
        values: set[int] = set()
        for raw in self.telegram_allowed_user_ids.split(","):
            item = raw.strip()
            if item:
                values.add(int(item))
        return frozenset(values)

    def validate_runtime(self) -> None:
        self.validate_provider_configuration()
        missing = [
            name
            for name, value in (
                ("TELEGRAM_BOT_TOKEN", self.telegram_bot_token),
                ("GOOGLE_SHEET_ID", self.google_sheet_id),
                (
                    "GROQ_API_KEY" if self.ai_provider == "groq" else "OPENAI_API_KEY",
                    self.groq_api_key if self.ai_provider == "groq" else self.openai_api_key,
                ),
            )
            if not value.strip()
        ]
        if missing:
            raise ValueError("Configuração ausente: " + ", ".join(missing))

    def validate_provider_configuration(self) -> None:
        if self.ai_provider not in {"groq", "openai"}:
            raise ValueError("AI_PROVIDER precisa ser groq ou openai.")
        if self.transcription_provider not in {"groq", "openai"}:
            raise ValueError("TRANSCRIPTION_PROVIDER precisa ser groq ou openai.")
        if self.ai_provider == "groq" and not self.groq_api_key.strip():
            raise ValueError("Configuração ausente: GROQ_API_KEY")
        if self.transcription_provider == "groq" and not self.groq_api_key.strip():
            raise ValueError("Configuração ausente: GROQ_API_KEY")
        if self.ai_provider == "openai" and not self.openai_api_key.strip():
            raise ValueError("Configuração ausente: OPENAI_API_KEY")
        if self.transcription_provider == "openai" and not self.openai_api_key.strip():
            raise ValueError("Configuração ausente: OPENAI_API_KEY")

    @property
    def interpretation_model(self) -> str:
        return self.groq_model if self.ai_provider == "groq" else self.openai_model

    @property
    def transcription_model(self) -> str:
        return (
            self.groq_transcription_model if self.transcription_provider == "groq" else self.openai_transcription_model
        )

    @property
    def google_oauth_configured(self) -> bool:
        required_values = all(
            value.strip()
            for value in (
                self.google_oauth_client_id,
                self.google_oauth_client_secret,
                self.google_oauth_redirect_uri,
                self.google_oauth_token_encryption_key,
            )
        )
        try:
            callback = urlsplit(self.google_oauth_redirect_uri)
            valid_callback = (
                callback.hostname is not None
                and callback.path == "/oauth/google/callback"
                and not callback.username
                and not callback.password
                and not callback.query
                and not callback.fragment
                and (
                    callback.scheme == "https"
                    or (callback.scheme == "http" and callback.hostname in {"localhost", "127.0.0.1"})
                )
            )
        except ValueError:
            valid_callback = False
        return (
            required_values
            and valid_callback
            and self.google_drive_scope == "https://www.googleapis.com/auth/drive.file"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
