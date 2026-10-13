from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from agro_notes.domain import EventProposal, InterpretationProposal
from agro_notes.groq_interpreter import GroqInterpretationError, GroqInterpretationProvider
from agro_notes.provider_contracts import ProviderOutcome
from agro_notes.settings import Settings


def response(content, request_id="req-1"):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))], _request_id=request_id
    )


def test_groq_interpreter_uses_strict_closed_schema_and_returns_provider_neutral_result():
    expected = InterpretationProposal(events=[EventProposal(
        event_type="WEIGHING",
        payload={"animal_identifier": "184", "weight_kg": 512},
        time_expression="hoje",
    )])
    create = Mock(return_value=response(expected.model_dump_json()))
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)), close=Mock())
    provider = GroqInterpretationProvider(Settings(GROQ_API_KEY="test-key"), client=client)

    result = provider.interpret("A 184 pesou 512 kg hoje.")

    assert result.proposal.events[0].payload == expected.events[0].payload
    assert result.metadata.provider == "groq"
    assert result.metadata.schema_valid is True
    assert result.metadata.outcome is ProviderOutcome.SUCCESS
    assert result.metadata.request_id == "req-1"
    kwargs = create.call_args.kwargs
    assert kwargs["model"] == "openai/gpt-oss-20b"
    assert kwargs["response_format"]["type"] == "json_schema"
    assert kwargs["response_format"]["json_schema"]["strict"] is True
    assert kwargs["messages"][-1]["content"] == "A 184 pesou 512 kg hoje."


def test_unlisted_model_uses_json_object_and_still_validates_locally():
    proposal = InterpretationProposal(out_of_scope=True)
    create = Mock(return_value=response(proposal.model_dump_json()))
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)), close=Mock())
    provider = GroqInterpretationProvider(api_key="test-key", model="custom/model", client=client)

    result = provider.interpret("texto sintético")

    assert result.proposal.out_of_scope
    assert create.call_args.kwargs["response_format"] == {"type": "json_object"}


def test_invalid_json_is_retried_once_then_reported_without_provider_body():
    create = Mock(side_effect=[response("not-json"), response("still-not-json")])
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)), close=Mock())
    provider = GroqInterpretationProvider(Settings(GROQ_API_KEY="test-key"), client=client)

    with pytest.raises(GroqInterpretationError) as error:
        provider.interpret("texto sintético")

    assert error.value.outcome is ProviderOutcome.INVALID_SCHEMA
    assert error.value.retry_count == 1
    assert "not-json" not in str(error.value)
    assert create.call_count == 2


def test_provider_error_text_is_sanitized():
    create = Mock(side_effect=TimeoutError("secret response body"))
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)), close=Mock())
    provider = GroqInterpretationProvider(Settings(GROQ_API_KEY="test-key"), client=client)

    with pytest.raises(GroqInterpretationError) as error:
        provider.interpret("texto sintético")

    assert error.value.outcome is ProviderOutcome.TIMEOUT
    assert "secret response body" not in str(error.value)
