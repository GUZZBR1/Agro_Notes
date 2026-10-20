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


def test_default_gpt_oss_20b_uses_json_object_and_interprets_vaccination():
    expected = InterpretationProposal(events=[EventProposal(
        event_type="VACCINATION",
        payload={"animal_identifier": "184", "vaccine": "febre aftosa"},
        time_expression="hoje",
    )])
    create = Mock(return_value=response(expected.model_dump_json()))
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)), close=Mock())
    provider = GroqInterpretationProvider(Settings(GROQ_API_KEY="test-key"), client=client)

    result = provider.interpret("A vaca 184 foi vacinada contra febre aftosa hoje")

    event = result.proposal.events[0]
    assert event.event_type == "VACCINATION"
    assert event.payload["animal_identifier"] == "184"
    assert event.payload["vaccine"] == "febre aftosa"
    assert event.time_expression == "hoje"
    assert create.call_args.kwargs["model"] == "openai/gpt-oss-20b"
    assert create.call_args.kwargs["response_format"] == {"type": "json_object"}
    assert result.metadata.schema_valid is True


@pytest.mark.parametrize("model", ["openai/gpt-oss-120b", "qwen/qwen3.8-27b"])
def test_remaining_strict_schema_models_keep_json_schema(model):
    expected = InterpretationProposal(events=[EventProposal(
        event_type="WEIGHING",
        payload={"animal_identifier": "184", "weight_kg": 512},
        time_expression="hoje",
    )])
    create = Mock(return_value=response(expected.model_dump_json()))
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)), close=Mock())
    provider = GroqInterpretationProvider(Settings(GROQ_API_KEY="test-key"), model=model, client=client)

    result = provider.interpret("A 184 pesou 512 kg hoje.")

    assert result.proposal.events[0].payload == expected.events[0].payload
    assert result.metadata.provider == "groq"
    assert result.metadata.schema_valid is True
    assert result.metadata.outcome is ProviderOutcome.SUCCESS
    assert result.metadata.request_id == "req-1"
    kwargs = create.call_args.kwargs
    assert kwargs["model"] == model
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


def test_invalid_closed_payload_is_retried_then_rejected_by_pydantic():
    invalid = (
        '{"events":[{"event_type":"VACCINATION","payload":'
        '{"animal_identifier":"184","unexpected":"value"},"time_expression":"hoje"}]}'
    )
    create = Mock(side_effect=[response(invalid), response(invalid)])
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)), close=Mock())
    provider = GroqInterpretationProvider(Settings(GROQ_API_KEY="test-key"), client=client)

    with pytest.raises(GroqInterpretationError) as error:
        provider.interpret("A vaca 184 foi vacinada contra febre aftosa hoje")

    assert error.value.outcome is ProviderOutcome.INVALID_SCHEMA
    assert error.value.retry_count == 1
    assert create.call_args.kwargs["response_format"] == {"type": "json_object"}


def test_provider_error_text_is_sanitized():
    create = Mock(side_effect=TimeoutError("secret response body"))
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)), close=Mock())
    provider = GroqInterpretationProvider(Settings(GROQ_API_KEY="test-key"), client=client)

    with pytest.raises(GroqInterpretationError) as error:
        provider.interpret("texto sintético")

    assert error.value.outcome is ProviderOutcome.TIMEOUT
    assert "secret response body" not in str(error.value)


@pytest.mark.parametrize(
    ("exception_name", "expected"),
    [
        ("BadRequestError", ProviderOutcome.ERROR),
        ("RateLimitError", ProviderOutcome.RATE_LIMITED),
        ("TimeoutError", ProviderOutcome.TIMEOUT),
        ("RuntimeError", ProviderOutcome.ERROR),
    ],
)
def test_provider_failures_keep_distinct_safe_outcomes(exception_name, expected):
    attributes = {"status_code": 400} if exception_name == "BadRequestError" else {}
    exception_type = type(exception_name, (Exception,), attributes)
    create = Mock(side_effect=exception_type("sensitive provider detail"))
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)), close=Mock())
    provider = GroqInterpretationProvider(Settings(GROQ_API_KEY="test-key"), client=client)

    with pytest.raises(GroqInterpretationError) as error:
        provider.interpret("texto sintético")

    assert error.value.outcome is expected
    assert "sensitive provider detail" not in str(error.value)
