import json
from types import SimpleNamespace

from agro_notes.evaluate_models import EXTRA_FIXTURE, FIXTURE, score_proposal, select_candidate_models


def test_provider_golden_fixture_contains_the_eight_required_flow_ids():
    cases = json.loads(FIXTURE.read_text(encoding="utf-8"))

    assert [case["id"] for case in cases] == [
        "1_WEIGHING",
        "2_HEALTH",
        "3_TRANSFER",
        "4_VACCINATION",
        "5_CALVING",
        "6_CLARIFICATION",
        "7_DUPLICATE",
        "8_UNSUPPORTED",
    ]
    assert any(case.get("idempotency_is_application_test") for case in cases)


def test_evaluation_checks_event_intent_required_slots_and_clarification():
    case = {
        "id": "6_CLARIFICATION",
        "event_type": "WEIGHING",
        "required_payload": {"animal_identifier": "184"},
        "must_be_ambiguous": True,
    }
    proposal = SimpleNamespace(
        events=[SimpleNamespace(event_type="WEIGHING", payload={"animal_identifier": "184"}, ambiguities=[])],
        ambiguities=["peso ausente"],
        out_of_scope=False,
    )

    assert score_proposal(case, proposal)["pass"] is True


def test_evaluation_rejects_unexpected_extra_events():
    case = {"id": "WEIGHING", "event_type": "WEIGHING", "required_payload": {"weight_kg": 512}}
    proposal = SimpleNamespace(
        events=[
            SimpleNamespace(event_type="WEIGHING", payload={"weight_kg": 512}, ambiguities=[]),
            SimpleNamespace(event_type="HEALTH_OBSERVATION", payload={}, ambiguities=[]),
        ],
        ambiguities=[],
        out_of_scope=False,
    )

    assert score_proposal(case, proposal)["event_count_ok"] is False
    assert score_proposal(case, proposal)["pass"] is False


def test_evaluation_requires_unsupported_requests_to_be_out_of_scope():
    case = {"id": "8_UNSUPPORTED", "event_type": None, "required_payload": {}, "must_be_out_of_scope": True}
    proposal = SimpleNamespace(events=[], ambiguities=[], out_of_scope=True)

    assert score_proposal(case, proposal)["pass"] is True


def test_model_candidates_are_discovered_from_active_production_strict_models():
    active = {"openai/gpt-oss-20b", "openai/gpt-oss-120b", "qwen/qwen3.8-27b", "llama-3.3-70b-versatile"}

    assert select_candidate_models(active) == ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]
    assert select_candidate_models(active, ["openai/gpt-oss-20b"]) == ["openai/gpt-oss-20b"]
    assert select_candidate_models({"qwen/qwen3.8-27b"}) == []


def test_evaluation_extras_include_corrections_regionalism_and_composite_event():
    cases = json.loads(EXTRA_FIXTURE.read_text(encoding="utf-8"))
    ids = {case["id"] for case in cases}

    assert {"AMBIGUOUS_TRANSFER", "CORRECTION_EXPLICIT", "REGIONAL_HEALTH", "CALVING_COMPOSITE"} <= ids
