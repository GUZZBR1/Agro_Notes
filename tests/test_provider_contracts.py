import pytest
from pydantic import ValidationError

from agro_notes.domain import EventProposal, InterpretationProposal
from agro_notes.provider_contracts import (
    InterpretationResult,
    ProposedCommand,
    ProviderMetadata,
    ProviderOutcome,
    TranscriptionResult,
)


def metadata(**changes):
    return ProviderMetadata.model_validate({
        "provider": "example",
        "model": "speech-or-text-model",
        "latency_ms": 12.5,
        "outcome": "SUCCESS",
        **changes,
    })


def test_transcription_does_not_invent_confidence_or_schema_evidence():
    result = TranscriptionResult(text="A 184 pesou 512 quilos hoje.", language="pt", metadata=metadata())

    assert result.confidence is None
    assert result.metadata.schema_valid is None
    assert result.metadata.retry_count == 0
    assert result.metadata.outcome is ProviderOutcome.SUCCESS


def test_interpretation_reuses_the_domain_proposal_without_creating_facts():
    proposal = InterpretationProposal(events=[EventProposal(
        event_type="WEIGHING", payload={"animal_identifier": "184", "weight_kg": 512},
    )])
    result = InterpretationResult(proposal=proposal, metadata=metadata(schema_valid=True, request_id="req-1"))

    assert ProposedCommand is InterpretationProposal
    assert result.proposal is proposal
    assert result.proposal.events[0].event_id is None
    assert result.metadata.request_id == "req-1"
    assert InterpretationResult.model_validate_json(result.model_dump_json()) == result


@pytest.mark.parametrize("changes", [
    {"provider": ""},
    {"model": ""},
    {"latency_ms": -1},
    {"latency_ms": float("nan")},
    {"latency_ms": float("inf")},
    {"retry_count": -1},
    {"api_key": "must-not-enter-metadata"},
])
def test_metadata_rejects_invalid_measurements_and_undeclared_fields(changes):
    with pytest.raises(ValidationError):
        metadata(**changes)


@pytest.mark.parametrize("confidence", [-0.1, 1.1, float("nan")])
def test_transcription_rejects_invalid_confidence(confidence):
    with pytest.raises(ValidationError):
        TranscriptionResult(text="test", confidence=confidence, metadata=metadata())


def test_interpretation_result_rejects_non_proposal_json():
    with pytest.raises(ValidationError):
        InterpretationResult(proposal={"diagnosis": "invented"}, metadata=metadata())


def test_provider_metadata_exposes_safe_observability_fields(caplog):
    item = metadata(input_tokens=11, output_tokens=5, audio_seconds=2.5)

    with caplog.at_level("INFO", logger="agro_notes.providers"):
        item.emit_log(operation="interpret")

    record = caplog.records[-1]
    assert record.provider_name == "example"
    assert record.provider_model == "speech-or-text-model"
    assert record.provider_latency_ms == 12.5
    assert record.provider_outcome == "SUCCESS"
    assert record.provider_schema_valid is None
    assert record.provider_retry_count == 0
    assert record.provider_input_tokens == 11
    assert record.provider_output_tokens == 5
    assert record.provider_audio_seconds == 2.5
    assert "api_key" not in record.__dict__
