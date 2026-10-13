from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    telegram_allowed_user_ids: str = Field(default="", alias="TELEGRAM_ALLOWED_USER_IDS")
    farm_property_id: str = Field(default="FARM-001", alias="FARM_PROPERTY_ID")
    farm_timezone: str = Field(default="America/Sao_Paulo", alias="FARM_TIMEZONE")
    google_sheet_id: str = Field(default="", alias="GOOGLE_SHEET_ID")
    google_credentials_file: str = Field(
        default="credentials/google-service-account.json", alias="GOOGLE_CREDENTIALS_FILE"
    )
    ai_provider: str = Field(default="groq", alias="AI_PROVIDER")
    transcription_provider: str = Field(default="groq", alias="TRANSCRIPTION_PROVIDER")
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    groq_model: str = Field(default="openai/gpt-oss-20b", alias="GROQ_MODEL")
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
                ("TELEGRAM_ALLOWED_USER_IDS", self.telegram_allowed_user_ids),
                ("GOOGLE_SHEET_ID", self.google_sheet_id),
                ("GROQ_API_KEY" if self.ai_provider == "groq" else "OPENAI_API_KEY",
                 self.groq_api_key if self.ai_provider == "groq" else self.openai_api_key),
            )
            if not value.strip()
        ]
        if missing:
            raise ValueError("Configuração ausente: " + ", ".join(missing))
        if not self.allowed_user_ids:
            raise ValueError("A whitelist Telegram precisa ter pelo menos um usuário.")

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
            self.groq_transcription_model
            if self.transcription_provider == "groq"
            else self.openai_transcription_model
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
