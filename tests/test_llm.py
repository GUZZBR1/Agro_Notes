from types import SimpleNamespace
from unittest.mock import Mock

from agro_notes.domain import EventProposal, InterpretationProposal, WeighingPayload
from agro_notes.llm import (
    OpenAIInterpretationProvider,
    OpenAIResponsesClient,
    StrictEventProposal,
    StrictInterpretationProposal,
)
from agro_notes.settings import Settings


def test_responses_adapter_uses_structured_schema_and_returns_parsed_contract():
    proposal = InterpretationProposal(
        events=[
            EventProposal(
                event_type="WEIGHING",
                payload={"animal_identifier": "184", "weight_kg": 512},
                time_expression="hoje",
            )
        ]
    )
    wire = StrictInterpretationProposal(events=[StrictEventProposal(
        event_type="WEIGHING", payload=WeighingPayload(animal_identifier="184", weight_kg=512),
        time_expression="hoje",
    )])
    parse = Mock(return_value=SimpleNamespace(output_parsed=wire))
    client = SimpleNamespace(responses=SimpleNamespace(parse=parse))
    adapter = OpenAIResponsesClient(Settings(OPENAI_API_KEY="test-key"), client)

    result = adapter.generate(
        system_prompt="system",
        user_text="A 184 pesou 512 kg hoje.",
        response_model=InterpretationProposal,
    )

    assert result.events[0].payload == proposal.events[0].payload
    parse.assert_called_once_with(
        model="gpt-4.1-mini",
        instructions="system",
        input="A 184 pesou 512 kg hoje.",
        text_format=StrictInterpretationProposal,
    )

    from openai.lib._pydantic import to_strict_json_schema

    schema = to_strict_json_schema(StrictInterpretationProposal)

    def assert_closed(value):
        if isinstance(value, dict):
            assert value.get("additionalProperties") is not True
            for child in value.values():
                assert_closed(child)
        elif isinstance(value, list):
            for child in value:
                assert_closed(child)

    assert_closed(schema)


def test_responses_adapter_rejects_missing_structured_result():
    client = SimpleNamespace(responses=SimpleNamespace(parse=Mock(return_value=SimpleNamespace(output_parsed=None))))
    adapter = OpenAIResponsesClient(Settings(OPENAI_API_KEY="test-key"), client)

    try:
        adapter.generate(system_prompt="system", user_text="test", response_model=InterpretationProposal)
    except ValueError as exc:
        assert "interpretação estruturada" in str(exc)
    else:
        raise AssertionError("Expected absent structured output to fail")


def test_openai_provider_adapter_returns_the_shared_contract_and_observability():
    proposal = InterpretationProposal(ambiguities=["peso ausente"])
    client = SimpleNamespace(generate=Mock(return_value=proposal), close=Mock())
    provider = OpenAIInterpretationProvider(Settings(OPENAI_API_KEY="test-key"), client)

    result = provider.interpret("Pesei a 184.", context={"farm_timezone": "America/Sao_Paulo"})

    assert result.proposal is proposal
    assert result.metadata.provider == "openai"
    assert result.metadata.model == "gpt-4.1-mini"
    assert result.metadata.schema_valid is True
    assert result.metadata.input_tokens is None
    client.generate.assert_called_once()
    assert client.generate.call_args.kwargs["user_text"] == "Pesei a 184."
    assert client.generate.call_args.kwargs["response_model"] is InterpretationProposal


def test_openai_provider_adapter_hides_raw_failure_details():
    client = SimpleNamespace(generate=Mock(side_effect=TimeoutError("secret body")), close=Mock())
    provider = OpenAIInterpretationProvider(Settings(OPENAI_API_KEY="test-key"), client)

    try:
        provider.interpret("synthetic")
    except RuntimeError as exc:
        assert "TIMEOUT" in str(exc)
        assert "secret body" not in str(exc)
    else:
        raise AssertionError("Expected sanitized provider failure")
