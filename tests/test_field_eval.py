import json
from collections import Counter
from pathlib import Path

import pytest

from agro_notes.field_eval import (
    evaluate_predictions,
    load_dataset,
    load_golden_core,
    validate_dataset_quality,
    word_error_rate,
)

ROOT = Path(__file__).resolve().parents[1]


def test_field_eval_v1_dataset_has_required_categories_and_critical_coverage():
    dataset = load_dataset(ROOT / "eval" / "field_eval_v1.jsonl")
    quality = validate_dataset_quality(dataset)

    assert quality["case_count"] == 150
    assert quality["category_counts"] == {
        "AMBIGUOUS": 18,
        "COMPOUND": 18,
        "CORRECTION": 18,
        "HIGH_RISK": 20,
        "INCOMPLETE": 18,
        "OUT_OF_SCOPE": 16,
        "REGIONALISM": 18,
        "SIMPLE": 24,
    }
    assert all(count > 0 for count in quality["critical_field_coverage"].values())
    assert all(case["source_status"] == "SYNTHETIC_ONLY" for case in dataset)


def test_golden_core_is_stable_unique_subset_of_36_cases():
    dataset = load_dataset(ROOT / "eval" / "field_eval_v1.jsonl")
    core = load_golden_core(dataset, ROOT / "eval" / "field_golden_core.jsonl")

    assert len(core) == 36
    assert len({case["case_id"] for case in core}) == 36
    assert all(case["golden_core"] for case in core)


def test_dataset_rejects_duplicate_ids_and_policy_write_contradictions(tmp_path):
    dataset_path = ROOT / "eval" / "field_eval_v1.jsonl"
    first = json.loads(dataset_path.read_text(encoding="utf-8").splitlines()[0])
    duplicate_path = tmp_path / "duplicate.jsonl"
    duplicate_path.write_text(json.dumps(first) + "\n" + json.dumps(first) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="case_id_missing_or_duplicate"):
        load_dataset(duplicate_path)

    first["expected_write_allowed"] = True
    contradiction_path = tmp_path / "contradiction.jsonl"
    contradiction_path.write_text(json.dumps(first) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="write_policy_inconsistent"):
        load_dataset(contradiction_path)


def test_numeric_substitution_is_critical_even_when_wer_is_low():
    dataset = load_dataset(ROOT / "eval" / "field_eval_v1.jsonl")
    case = next(case for case in dataset if case["case_id"] == "FIELD_EVAL_V1_115")
    prediction = {
        "case_id": case["case_id"],
        "transcript": "A 184 pesou 712 kg hoje.",
        "decision": "AUTO_APPLY",
        "proposal": {
            "events": [
                {
                    "event_type": "WEIGHING",
                    "time_expression": "hoje",
                    "correction_requested": False,
                    "payload": {"animal_identifier": "184", "weight_kg": 712},
                }
            ]
        },
    }

    report = evaluate_predictions([case], [prediction])

    assert report["stt"]["mean_wer"] < 0.5
    assert report["stt"]["field_accuracy"]["weight_accuracy"] == 0
    assert report["false_safe_write"]["count"] == 1
    assert report["cases"][0]["false_safe_write"] is True


def test_ambiguous_case_autowrite_is_false_safe_write():
    dataset = load_dataset(ROOT / "eval" / "field_eval_v1.jsonl")
    case = next(case for case in dataset if case["case_id"] == "FIELD_EVAL_V1_043")
    prediction = {
        "case_id": case["case_id"],
        "transcript": case["input_text"],
        "decision": "AUTO_APPLY",
        "proposal": {"events": [{"event_type": "LOT_TRANSFER", "time_expression": None, "payload": {}}]},
    }

    report = evaluate_predictions([case], [prediction])

    assert report["false_safe_write"]["count"] == 1


def test_prediction_coverage_is_explicit_and_wer_normalizes_accents():
    dataset = load_dataset(ROOT / "eval" / "field_eval_v1.jsonl")
    case = dataset[0]
    prediction = {
        "case_id": case["case_id"],
        "transcript": case["input_text"],
        "decision": case["expected_confirmation_policy"],
        "proposal": {"events": case["expected_events"]},
        "extracted_animal_ids": case["expected_animal_ids"],
        "extracted_group_ids": case["expected_group_ids"],
        "extracted_slot_fields": case["expected_slot_fields"],
    }
    report = evaluate_predictions(dataset[:2], [prediction])

    assert report["status"] == "INCOMPLETE_PREDICTION_COVERAGE"
    assert report["predictions_missing"] == 1
    assert word_error_rate("A novilha está mancando", "A novilha esta mancando") == 0


@pytest.mark.parametrize(
    ("proposal", "reason"),
    [
        (["invalid"], "proposal_events_invalid"),
        ({"events": [{"event_type": "CALVING", "payload": {"outcomes": None}}]}, "event_outcomes_invalid"),
        ({"events": [{"event_type": "HEALTH_OBSERVATION", "payload": {"observation": []}}]}, "payload_field_invalid"),
        ({"events": [], "missing_fields": None}, "proposal_metadata_invalid"),
        ({"events": [], "missing_fields": ["weight_kg", {}]}, "proposal_metadata_invalid"),
    ],
)
def test_malformed_prediction_payloads_return_input_errors_not_crashes(proposal, reason):
    dataset = load_dataset(ROOT / "eval" / "field_eval_v1.jsonl")
    case = dataset[0]
    prediction = {
        "case_id": case["case_id"],
        "transcript": case["input_text"],
        "decision": case["expected_confirmation_policy"],
        "proposal": proposal,
    }

    with pytest.raises(ValueError, match=reason):
        evaluate_predictions(dataset[:1], [prediction])


def test_malformed_prediction_decision_returns_input_error():
    dataset = load_dataset(ROOT / "eval" / "field_eval_v1.jsonl")
    case = dataset[0]
    prediction = {
        "case_id": case["case_id"],
        "transcript": case["input_text"],
        "decision": [],
        "proposal": {"events": []},
    }

    with pytest.raises(ValueError, match="decision_invalid"):
        evaluate_predictions(dataset[:1], [prediction])


def test_builder_category_totals_match_the_committed_corpus():
    dataset = load_dataset(ROOT / "eval" / "field_eval_v1.jsonl")
    counts = Counter(case["category"] for case in dataset)

    assert sum(counts.values()) == 150
    assert counts["HIGH_RISK"] == 20


def test_expected_oracle_round_trip_scores_all_cases_without_shadow_metadata():
    dataset = load_dataset(ROOT / "eval" / "field_eval_v1.jsonl")
    predictions = [
        {
            "case_id": case["case_id"],
            "transcript": case["input_text"],
            "decision": case["expected_confirmation_policy"],
            "proposal": {
                "events": [{**event, "confidence": 1.0} for event in case["expected_events"]],
                "missing_fields": case["expected_missing_fields"],
                "ambiguities": case["expected_ambiguities"],
            },
        }
        for case in dataset
    ]

    report = evaluate_predictions(dataset, predictions)

    assert report["stt"]["mean_wer"] == 0
    assert all(all(row["comparisons"].values()) for row in report["cases"])
    assert report["false_safe_write"]["count"] == 0


def test_proposal_fields_override_untrusted_shadow_metadata_and_detect_false_safe():
    dataset = load_dataset(ROOT / "eval" / "field_eval_v1.jsonl")
    case = next(case for case in dataset if case["case_id"] == "FIELD_EVAL_V1_006")
    prediction = {
        "case_id": case["case_id"],
        "transcript": case["input_text"],
        "decision": "AUTO_APPLY",
        "extracted_animal_ids": case["expected_animal_ids"],
        "proposal": {"events": [{**case["expected_events"][0], "payload": {"animal_identifier": "999"}}]},
    }

    report = evaluate_predictions([case], [prediction])

    assert report["cases"][0]["comparisons"]["animal_id"] is False
    assert report["cases"][0]["comparisons"]["event_payloads"] is False
    assert report["false_safe_write"]["count"] == 1


def test_event_binding_and_every_stt_entity_are_scored():
    dataset = load_dataset(ROOT / "eval" / "field_eval_v1.jsonl")
    case = next(case for case in dataset if case["case_id"] == "FIELD_EVAL_V1_027")
    events = json.loads(json.dumps(case["expected_events"]))
    events[0]["payload"]["animal_identifier"], events[1]["payload"]["animal_identifier"] = (
        events[1]["payload"]["animal_identifier"],
        events[0]["payload"]["animal_identifier"],
    )
    prediction = {
        "case_id": case["case_id"],
        "transcript": case["input_text"],
        "decision": case["expected_confirmation_policy"],
        "proposal": {"events": events},
    }

    swapped = evaluate_predictions([case], [prediction])
    assert swapped["cases"][0]["comparisons"]["event_payloads"] is False

    compound = next(case for case in dataset if case["case_id"] == "FIELD_EVAL_V1_029")
    changed_transcript = compound["input_text"].replace("319", "999")
    prediction = {
        "case_id": compound["case_id"],
        "transcript": changed_transcript,
        "decision": compound["expected_confirmation_policy"],
        "proposal": {"events": compound["expected_events"]},
    }
    partial_stt = evaluate_predictions([compound], [prediction])
    assert partial_stt["stt"]["field_accuracy"]["animal_id_accuracy"] == 0


def test_voice_weighing_auto_apply_and_invalid_vaccination_status_are_unsafe():
    dataset = load_dataset(ROOT / "eval" / "field_eval_v1.jsonl")
    case = next(case for case in dataset if case["case_id"] == "FIELD_EVAL_V1_001")
    event = json.loads(json.dumps(case["expected_events"][0]))
    weighing_prediction = {
        "case_id": case["case_id"],
        "transcript": case["input_text"],
        "decision": "AUTO_APPLY",
        "proposal": {"events": [event]},
    }
    vaccination_case = next(
        case for case in dataset if any(event["event_type"] == "VACCINATION" for event in case["expected_events"])
    )
    vaccination_event = next(
        event for event in vaccination_case["expected_events"] if event["event_type"] == "VACCINATION"
    )
    event = json.loads(json.dumps(vaccination_event))
    event["payload"]["status"] = "DIAGNOSED"
    vaccination_prediction = {
        "case_id": vaccination_case["case_id"],
        "transcript": vaccination_case["input_text"],
        "decision": "AUTO_APPLY",
        "proposal": {"events": [event]},
    }

    report = evaluate_predictions([case, vaccination_case], [weighing_prediction, vaccination_prediction])

    assert report["cases"][0]["comparisons"]["event_payloads"] is True
    assert report["cases"][1]["comparisons"]["event_payloads"] is False
    assert report["false_safe_write"]["count"] == 2


@pytest.mark.parametrize(
    ("case_id", "field", "values"),
    [
        ("FIELD_EVAL_V1_126", "lot_id", {"13", "30"}),
        ("FIELD_EVAL_V1_127", "lot_id", {"16", "60"}),
        ("FIELD_EVAL_V1_128", "lot_id", {"17", "70"}),
        ("FIELD_EVAL_V1_123", "animal_id", {"184", "194"}),
        ("FIELD_EVAL_V1_045", "weight", {"512", "712"}),
        ("FIELD_EVAL_V1_131", "weight", {"512", "712"}),
    ],
)
def test_adversarial_minimal_pair_targets_preserve_both_spoken_values(case_id, field, values):
    dataset = load_dataset(ROOT / "eval" / "field_eval_v1.jsonl")
    case = next(case for case in dataset if case["case_id"] == case_id)
    aliases = case["stt_targets"][field]
    target_text = " ".join(alias for group in aliases for alias in group)

    assert all(any(value in group for group in aliases) for value in values)
    assert target_text


@pytest.mark.parametrize("unsafe_marker", ["event_ambiguity", "proposal_out_of_scope"])
def test_auto_apply_is_false_safe_when_actual_proposal_requires_review(unsafe_marker):
    dataset = load_dataset(ROOT / "eval" / "field_eval_v1.jsonl")
    case = next(case for case in dataset if case["case_id"] == "FIELD_EVAL_V1_006")
    event = json.loads(json.dumps(case["expected_events"][0]))
    proposal = {"events": [event]}
    if unsafe_marker == "event_ambiguity":
        event["ambiguities"] = ["Animal identifier uncertain"]
    else:
        proposal["out_of_scope"] = True
    prediction = {
        "case_id": case["case_id"],
        "transcript": case["input_text"],
        "decision": "AUTO_APPLY",
        "proposal": proposal,
    }

    report = evaluate_predictions([case], [prediction])

    assert report["false_safe_write"]["count"] == 1


def test_auto_apply_with_missing_or_low_event_confidence_is_false_safe():
    dataset = load_dataset(ROOT / "eval" / "field_eval_v1.jsonl")
    case = next(case for case in dataset if case["case_id"] == "FIELD_EVAL_V1_077")
    event = json.loads(json.dumps(case["expected_events"][0]))
    event["confidence"] = 0.79
    prediction = {
        "case_id": case["case_id"],
        "transcript": case["input_text"],
        "decision": "AUTO_APPLY",
        "proposal": {"events": [event]},
    }

    report = evaluate_predictions([case], [prediction])

    assert report["false_safe_write"]["count"] == 1


@pytest.mark.parametrize("confidence", [2.0, float("nan")])
def test_auto_apply_with_out_of_range_or_nonfinite_confidence_is_false_safe(confidence):
    dataset = load_dataset(ROOT / "eval" / "field_eval_v1.jsonl")
    case = next(case for case in dataset if case["case_id"] == "FIELD_EVAL_V1_077")
    event = json.loads(json.dumps(case["expected_events"][0]))
    event["confidence"] = confidence
    prediction = {
        "case_id": case["case_id"],
        "transcript": case["input_text"],
        "decision": "AUTO_APPLY",
        "proposal": {"events": [event]},
    }

    report = evaluate_predictions([case], [prediction])

    assert report["false_safe_write"]["count"] == 1


def test_event_comparison_normalizes_domain_defaults_but_rejects_invalid_payload():
    dataset = load_dataset(ROOT / "eval" / "field_eval_v1.jsonl")
    vaccine_case = next(case for case in dataset if case["expected_intent"] == "VACCINATION")
    event = json.loads(json.dumps(vaccine_case["expected_events"][0]))
    event["payload"].pop("status", None)
    prediction = {
        "case_id": vaccine_case["case_id"],
        "transcript": vaccine_case["input_text"],
        "decision": vaccine_case["expected_confirmation_policy"],
        "proposal": {"events": [event]},
    }

    report = evaluate_predictions([vaccine_case], [prediction])
    assert report["cases"][0]["comparisons"]["event_payloads"] is True

    event["payload"]["forbidden"] = "unexpected"
    report = evaluate_predictions([vaccine_case], [{**prediction, "proposal": {"events": [event]}}])
    assert report["cases"][0]["comparisons"]["event_payloads"] is False
