import pytest

import agro_notes.groq_interpreter as groq_interpreter
import agro_notes.groq_transcription as groq_transcription
import agro_notes.provider_factory as provider_factory
from agro_notes.interpreter import ProviderInterpreter
from agro_notes.settings import Settings


def test_groq_is_the_initial_provider_and_uses_the_compatible_default_models():
    settings = Settings(GROQ_API_KEY="test-key")

    assert settings.ai_provider == "groq"
    assert settings.transcription_provider == "groq"
    assert settings.interpretation_model == "openai/gpt-oss-20b"
    assert settings.transcription_model == "whisper-large-v3-turbo"
    settings.validate_provider_configuration()


def test_openai_remains_selectable_for_both_provider_seams():
    settings = Settings(AI_PROVIDER="openai", TRANSCRIPTION_PROVIDER="openai", OPENAI_API_KEY="test-key")

    assert settings.interpretation_model == "gpt-4.1-mini"
    assert settings.transcription_model == "gpt-4o-mini-transcribe"
    settings.validate_provider_configuration()


@pytest.mark.parametrize("field,value", [("AI_PROVIDER", "other"), ("TRANSCRIPTION_PROVIDER", "other")])
def test_unknown_providers_are_rejected(field, value):
    settings = Settings(GROQ_API_KEY="test-key", **{field: value})

    with pytest.raises(ValueError, match="precisa ser groq ou openai"):
        settings.validate_provider_configuration()


def test_selected_provider_requires_its_own_credential():
    settings = Settings(AI_PROVIDER="openai", TRANSCRIPTION_PROVIDER="groq", OPENAI_API_KEY="openai-key")

    with pytest.raises(ValueError, match="GROQ_API_KEY"):
        settings.validate_provider_configuration()


def test_factory_variable_aliases_cover_briefing_and_existing_names():
    settings = Settings(
        INTERPRETATION_PROVIDER="groq",
        TRANSCRIPTION_PROVIDER="groq",
        GROQ_LLM_MODEL="openai/gpt-oss-120b",
        PROPERTY_ID="FARM-TEST",
        PROPERTY_TIMEZONE="America/Sao_Paulo",
        GOOGLE_APPLICATION_CREDENTIALS="credentials/test.json",
    )
    legacy = Settings(
        AI_PROVIDER="openai",
        OPENAI_API_KEY="test-key",
        FARM_PROPERTY_ID="FARM-LEGACY",
        GOOGLE_CREDENTIALS_FILE="credentials/legacy.json",
    )

    assert settings.ai_provider == "groq"
    assert settings.groq_model == "openai/gpt-oss-120b"
    assert settings.farm_property_id == "FARM-TEST"
    assert settings.google_credentials_file == "credentials/test.json"
    assert legacy.ai_provider == "openai"
    assert legacy.farm_property_id == "FARM-LEGACY"
    assert legacy.google_credentials_file == "credentials/legacy.json"


def test_factory_selects_the_configured_groq_adapters(monkeypatch):
    class FakeGroqInterpreter:
        def __init__(self, settings):
            self.settings = settings

    class FakeGroqTranscriber:
        def __init__(self, settings):
            self.settings = settings

    monkeypatch.setattr(groq_interpreter, "GroqInterpretationProvider", FakeGroqInterpreter)
    monkeypatch.setattr(groq_transcription, "GroqTranscriber", FakeGroqTranscriber)
    settings = Settings(GROQ_API_KEY="test-key")

    interpreter = provider_factory.build_interpreter(settings)
    transcriber = provider_factory.build_transcriber(settings)

    assert isinstance(interpreter, ProviderInterpreter)
    assert isinstance(interpreter.provider, FakeGroqInterpreter)
    assert isinstance(transcriber, FakeGroqTranscriber)


def test_factory_keeps_openai_available_for_each_seam(monkeypatch):
    class FakeOpenAIInterpreter:
        def __init__(self, settings):
            self.settings = settings

    class FakeOpenAITranscriber:
        def __init__(self, settings):
            self.settings = settings

    monkeypatch.setattr(provider_factory, "OpenAIInterpretationProvider", FakeOpenAIInterpreter)
    monkeypatch.setattr(provider_factory, "OpenAITranscriber", FakeOpenAITranscriber)
    settings = Settings(AI_PROVIDER="openai", TRANSCRIPTION_PROVIDER="openai", OPENAI_API_KEY="test-key")

    interpreter = provider_factory.build_interpreter(settings)

    assert isinstance(interpreter, ProviderInterpreter)
    assert isinstance(interpreter.provider, FakeOpenAIInterpreter)
    assert isinstance(provider_factory.build_transcriber(settings), FakeOpenAITranscriber)
