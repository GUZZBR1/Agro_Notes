import asyncio
from datetime import UTC, datetime

from agro_notes.application import MVPProcessor
from agro_notes.domain import EventProposal, InterpretationProposal
from agro_notes.local_cli import LocalSettings, _run_action
from agro_notes.local_interpreter import JsonProposalInterpreter
from agro_notes.local_store import LocalEventStore


def setup_runtime():
    store = LocalEventStore()
    store.append_animal({"animal_id": "animal-42", "property_id": "farm"})
    store.append_identifier(
        {"animal_id": "animal-42", "property_id": "farm", "value": "42", "status": "ACTIVE", "valid_to": ""}
    )
    settings = LocalSettings(
        farm_property_id="farm",
        farm_timezone="America/Sao_Paulo",
        allowed_user_ids=frozenset({7}),
    )
    return MVPProcessor(settings, store, JsonProposalInterpreter()), store


def weighing_proposal():
    return InterpretationProposal(
        events=[
            EventProposal(
                event_type="WEIGHING",
                payload={"animal_identifier": "42", "weight_kg": 701},
                time_expression="hoje",
                confidence=0.99,
            )
        ]
    )


def test_local_json_flow_previews_confirms_and_inspects_memory_store():
    async def scenario():
        processor, store = setup_runtime()
        response = await _run_action(
            processor,
            store,
            7,
            {
                "action": "record",
                "proposal": weighing_proposal().model_dump(mode="json"),
                "captured_at": datetime(2026, 10, 22, tzinfo=UTC).isoformat(),
            },
            1,
        )
        assert response["pending_id"].startswith("LOCAL:7:")
        assert "701" in response["text"]
        assert store.tabs["06_Eventos"] == []

        confirmed = await _run_action(
            processor, store, 7, {"action": "confirm", "pending_id": response["pending_id"]}, 2
        )
        assert confirmed["text"].startswith("✅")
        snapshot = await _run_action(processor, store, 7, {"action": "inspect"}, 3)
        event = snapshot["store"]["06_Eventos"][0]
        assert event["command_id"].startswith("LOCAL:7:")
        assert event["event_type"] == "WEIGHING"
        assert snapshot["store"]["20_Event_Effects"]

    asyncio.run(scenario())


def test_local_json_flow_can_cancel_preview_without_writing_event():
    async def scenario():
        processor, store = setup_runtime()
        response = await _run_action(
            processor,
            store,
            7,
            {"action": "record", "proposal": weighing_proposal().model_dump(mode="json")},
            1,
        )
        cancelled = await _run_action(
            processor, store, 7, {"action": "cancel", "pending_id": response["pending_id"]}, 2
        )
        assert "cancelado" in cancelled["text"].lower()
        assert not store.tabs["06_Eventos"]
        assert store.tabs["18_Conversas"][-1]["state"] == "CANCELLED"

    asyncio.run(scenario())


def test_json_interpreter_parses_explicit_proposal_deterministically():
    proposal = weighing_proposal()
    interpreter = JsonProposalInterpreter()
    assert interpreter.interpret(proposal.model_dump_json()) == proposal
