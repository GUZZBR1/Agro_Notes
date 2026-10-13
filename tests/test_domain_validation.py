from datetime import UTC, date, datetime

import pytest

from agro_notes.domain import (
    EventProposal,
    InterpretationProposal,
    TrustedContext,
    ValidationStatus,
)
from agro_notes.interpreter import StructuredOutputInterpreter
from agro_notes.validation import DeterministicValidator


@pytest.fixture
def context():
    return TrustedContext(
        property_id="farm",
        actor_id="actor",
        request_id="request",
        timezone="America/Sao_Paulo",
        now=datetime(2026, 10, 13, 1, tzinfo=UTC),
        event_id_factory=lambda: "trusted-event",
    )


def proposal(event_type="WEIGHING", payload=None, **kwargs):
    time_expression = kwargs.pop("time_expression", "hoje")
    return InterpretationProposal(
        events=[
            EventProposal(
                event_type=event_type,
                payload=payload or {"animal_identifier": "42", "weight_kg": 230},
                time_expression=time_expression,
                confidence=kwargs.pop("confidence", 0.98),
                **kwargs,
            )
        ]
    )


def test_server_identity_and_local_date_override_model(context):
    result = DeterministicValidator().validate(
        proposal(property_id="attacker", actor_id="attacker", event_id="attacker"), context
    )
    assert result.status == ValidationStatus.READY
    event = result.events[0]
    assert (event.property_id, event.actor_id, event.event_id) == ("farm", "actor", "trusted-event")
    assert event.occurred_on.isoformat() == "2026-10-12"
    assert event.time_source.value == "EXPLICIT"


@pytest.mark.parametrize(
    "expression,expected_date",
    [("hoje", "2026-10-12"), ("ontem", "2026-10-11"), ("amanhã", "2026-10-13")],
)
def test_relative_dates_resolve_in_property_timezone(expression, expected_date, context):
    result = DeterministicValidator().validate(proposal(time_expression=expression), context)

    assert result.events[0].occurred_on.isoformat() == expected_date


def test_missing_fields_survive_for_clarification(context):
    result = DeterministicValidator().validate(proposal(payload={"animal_identifier": "42"}), context)
    assert result.status == ValidationStatus.NEEDS_CLARIFICATION
    assert result.proposal.events[0].payload["weight_kg"] is None
    assert "events[0].payload.weight_kg" in result.missing_fields
    assert result.events == []


@pytest.mark.parametrize(
    "event_type,payload",
    [
        ("ANIMAL_CREATED", {"display_identifier": "42", "species": "bovine"}),
        ("ANIMAL_ENTERED", {"display_identifier": "42"}),
        ("WEIGHING", {"animal_identifier": "42", "weight_kg": 230}),
        ("LOT_TRANSFER", {"animal_identifier": "42", "to_group_identifier": "B"}),
        ("VACCINATION", {"animal_identifier": "42", "vaccine": "reported vaccine"}),
        ("HEALTH_OBSERVATION", {"animal_identifier": "42", "observation": "cough reported"}),
    ],
)
def test_supported_families(event_type, payload, context):
    result = DeterministicValidator().validate(proposal(event_type, payload), context)
    expected = (
        ValidationStatus.READY
        if event_type in {"WEIGHING", "HEALTH_OBSERVATION"}
        else ValidationStatus.NEEDS_CONFIRMATION
    )
    assert result.status == expected
    assert result.events[0].event_type.value == event_type


@pytest.mark.parametrize(
    "event_type,payload,expected",
    [
        (
            "ANIMAL_CREATED",
            {"display_identifier": "184", "species": "BOVINE"},
            ValidationStatus.NEEDS_CONFIRMATION,
        ),
        ("ANIMAL_ENTERED", {"display_identifier": "184"}, ValidationStatus.NEEDS_CONFIRMATION),
        (
            "CALVING",
            {"mother_identifier": "184", "outcomes": [{"outcome": "LIVE_CALF"}]},
            ValidationStatus.NEEDS_CONFIRMATION,
        ),
        (
            "LOT_TRANSFER",
            {"animal_identifier": "184", "to_group_identifier": "7"},
            ValidationStatus.NEEDS_CONFIRMATION,
        ),
        (
            "VACCINATION",
            {"animal_identifier": "184", "vaccine": "clostridiose"},
            ValidationStatus.NEEDS_CONFIRMATION,
        ),
        (
            "HEALTH_OBSERVATION",
            {"animal_identifier": "184", "observation": "mancando"},
            ValidationStatus.READY,
        ),
    ],
)
def test_events_without_spoken_date_use_property_local_capture_date(event_type, payload, expected, context):
    result = DeterministicValidator().validate(
        proposal(event_type, payload, time_expression=None), context
    )

    assert result.status == expected
    assert result.events[0].occurred_on.isoformat() == "2026-10-12"
    assert result.events[0].original_time_expression == ""
    assert result.events[0].time_source.value == "INFERRED_FROM_CAPTURE_DATE"


def test_inferred_date_uses_original_capture_across_later_clarification(context):
    later = context.model_copy(update={"now": datetime(2026, 10, 13, 1, tzinfo=UTC), "inferred_on": date(2026, 10, 12)})
    result = DeterministicValidator().validate(
        proposal("ANIMAL_ENTERED", {"display_identifier": "42"}, time_expression=None), later
    )

    assert result.events[0].occurred_on == date(2026, 10, 12)


def test_weighing_requires_explicit_date(context):
    result = DeterministicValidator().validate(
        proposal(time_expression=None), context
    )

    assert result.status == ValidationStatus.NEEDS_CLARIFICATION
    assert result.events == []
    assert "events[0].time_expression" in result.missing_fields


def test_compound_calving_requires_preview_and_confirmation(context):
    result = DeterministicValidator().validate(
        proposal(
            "CALVING",
            {
                "mother_identifier": "42",
                "outcome_count": 2,
                "outcomes": [
                    {"display_identifier": "43", "outcome": "live"},
                    {"display_identifier": "44", "outcome": "live"},
                ],
            },
        ),
        context,
    )
    assert result.status == ValidationStatus.NEEDS_CONFIRMATION
    assert result.requires_preview
    assert len(result.events[0].payload["outcomes"]) == 2


def test_calving_missing_outcomes_is_not_silently_completed(context):
    result = DeterministicValidator().validate(
        proposal(
            "CALVING",
            {
                "mother_identifier": "42",
                "outcome_count": 2,
                "outcomes": [{"outcome": "live"}],
            },
        ),
        context,
    )
    assert result.status == ValidationStatus.NEEDS_CLARIFICATION
    assert result.events == []


@pytest.mark.parametrize("changes", [{"confidence": 0.79}, {"ambiguities": ["which animal?"]}])
def test_uncertainty_requires_clarification(context, changes):
    result = DeterministicValidator().validate(proposal(**changes), context)
    assert result.status == ValidationStatus.NEEDS_CLARIFICATION
    assert result.requires_preview


@pytest.mark.parametrize("event_type", ["SALE", "PREGNANCY_DIAGNOSIS", "MEDICATION"])
def test_out_of_scope_events_are_rejected(context, event_type):
    assert DeterministicValidator().validate(proposal(event_type), context).status == ValidationStatus.REJECTED


def test_clinical_status_is_rejected(context):
    result = DeterministicValidator().validate(
        proposal(
            "HEALTH_OBSERVATION",
            {
                "animal_identifier": "42",
                "observation": "cough",
                "status": "DIAGNOSED",
            },
        ),
        context,
    )
    assert result.status == ValidationStatus.REJECTED


@pytest.mark.parametrize("weight", [0, -1, float("inf"), float("nan")])
def test_invalid_weights_rejected(context, weight):
    assert (
        DeterministicValidator()
        .validate(proposal(payload={"animal_identifier": "42", "weight_kg": weight}), context)
        .status
        == ValidationStatus.REJECTED
    )


def test_interpreter_uses_injected_schema_client():
    class Client:
        def generate(self, **kwargs):
            assert kwargs["response_model"] is InterpretationProposal
            assert kwargs["user_text"] == "Pesei 42"
            return {"events": [{"event_type": "WEIGHING", "payload": {"animal_identifier": "42"}}]}

    output = StructuredOutputInterpreter(Client()).interpret("Pesei 42")
    assert output.events[0].time_expression is None
    assert output.events[0].payload == {"animal_identifier": "42"}


def test_missing_model_confidence_requires_clarification(context):
    candidate = proposal()
    candidate.events[0].confidence = None
    result = DeterministicValidator().validate(candidate, context)
    assert result.status == ValidationStatus.NEEDS_CLARIFICATION
    assert any("interpretação" in question for question in result.questions)
