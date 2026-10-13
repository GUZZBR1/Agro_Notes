from types import SimpleNamespace
from unittest.mock import Mock

from agro_notes.domain import EventProposal, InterpretationProposal, WeighingPayload
from agro_notes.llm import OpenAIResponsesClient, StrictEventProposal, StrictInterpretationProposal
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
