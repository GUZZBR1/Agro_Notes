"""Select configured providers while keeping application/domain code neutral."""

from .interpreter import ProviderInterpreter
from .llm import OpenAIInterpretationProvider
from .settings import Settings
from .transcription import OpenAITranscriber


def build_interpreter(settings: Settings):
    if settings.ai_provider == "groq":
        from .groq_interpreter import GroqInterpretationProvider

        return ProviderInterpreter(GroqInterpretationProvider(settings))
    return ProviderInterpreter(OpenAIInterpretationProvider(settings))


def build_transcriber(settings: Settings):
    if settings.transcription_provider == "groq":
        from .groq_transcription import GroqTranscriber

        return GroqTranscriber(settings)
    return OpenAITranscriber(settings)
