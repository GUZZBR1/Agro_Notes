"""Offline evaluator for the synthetic FIELD_EVAL_V1 benchmark.

The evaluator consumes provider-neutral predictions and never calls an AI or
writes to the production application. Reports are quality measurements, not
evidence of real field speech unless the input recordings were collected and
labeled under the field recording protocol.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .domain import PAYLOAD_MODELS, EventType

ROOT = Path(__file__).resolve().parents[2]
SOURCE_EVAL = ROOT / "eval"
INSTALLED_EVAL = Path(sys.prefix) / "share" / "agro-notes" / "eval"
EVAL_ASSETS = SOURCE_EVAL if SOURCE_EVAL.is_dir() else INSTALLED_EVAL
DEFAULT_DATASET = EVAL_ASSETS / "field_eval_v1.jsonl"
DEFAULT_CORE = EVAL_ASSETS / "field_golden_core.jsonl"
DEFAULT_DEMO = EVAL_ASSETS / "fixtures" / "field_eval_predictions.example.jsonl"
CATEGORIES = {
    "SIMPLE",
    "COMPOUND",
    "AMBIGUOUS",
    "INCOMPLETE",
    "CORRECTION",
    "REGIONALISM",
    "HIGH_RISK",
    "OUT_OF_SCOPE",
}
POLICIES = {"AUTO_APPLY", "CONFIRM", "CLARIFY", "MANUAL_REVIEW", "REJECT"}
RISK_LEVELS = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
CRITICAL_FIELDS = {
    "animal_id",
    "group_id",
    "weight",
    "unit",
    "date",
    "event_type",
    "calf_sex",
    "calf_id",
    "quantity",
}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            raise ValueError(f"{path}:{line_number}: blank_lines_not_allowed")
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid_json") from exc
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{line_number}: case_must_be_object")
        rows.append(row)
    return rows


def load_dataset(path: Path = DEFAULT_DATASET) -> list[dict[str, Any]]:
    cases = _read_jsonl(path)
    if not cases:
        raise ValueError("dataset_must_not_be_empty")
    seen: set[str] = set()
    for index, case in enumerate(cases):
        prefix = f"case_{index}"
        case_id = case.get("case_id")
        if not isinstance(case_id, str) or not case_id.strip() or case_id in seen:
            raise ValueError(f"{prefix}_case_id_missing_or_duplicate")
        seen.add(case_id)
        if case.get("category") not in CATEGORIES:
            raise ValueError(f"{case_id}_category_invalid")
        if not isinstance(case.get("input_text"), str) or not case["input_text"].strip():
            raise ValueError(f"{case_id}_input_text_missing")
        if case.get("source_status") != "SYNTHETIC_ONLY":
            raise ValueError(f"{case_id}_source_status_must_be_synthetic_only")
        if case.get("input_channel") != "VOICE_TRANSCRIPT":
            raise ValueError(f"{case_id}_input_channel_invalid")
        intent = case.get("expected_intent")
        intents = [] if intent is None else intent if isinstance(intent, list) else [intent]
        if any(value is not None and value not in {event_type.value for event_type in EventType} for value in intents):
            raise ValueError(f"{case_id}_intent_invalid")
        expected_events = case.get("expected_events")
        if not isinstance(expected_events, list):
            raise ValueError(f"{case_id}_expected_events_invalid")
        event_types = [event.get("event_type") for event in expected_events if isinstance(event, dict)]
        if len(event_types) != len(expected_events) or event_types != intents:
            raise ValueError(f"{case_id}_intent_event_types_inconsistent")
        if any(event_type not in {value.value for value in EventType} for event_type in event_types):
            raise ValueError(f"{case_id}_expected_event_type_invalid")
        for key in (
            "expected_animal_ids",
            "expected_group_ids",
            "expected_missing_fields",
            "expected_ambiguities",
            "critical_fields",
        ):
            values = case.get(key)
            if not isinstance(values, list) or not all(isinstance(value, str) and value.strip() for value in values):
                raise ValueError(f"{case_id}_{key}_invalid")
        if set(case["critical_fields"]) - CRITICAL_FIELDS:
            raise ValueError(f"{case_id}_critical_fields_invalid")
        for key in ("expected_numeric_fields", "expected_units", "expected_slot_fields", "stt_targets"):
            if not isinstance(case.get(key), dict):
                raise ValueError(f"{case_id}_{key}_invalid")
        for key, value in case["expected_numeric_fields"].items():
            values = value if isinstance(value, list) else [value]
            if not isinstance(key, str) or not all(
                isinstance(item, (int, float)) and not isinstance(item, bool) for item in values
            ):
                raise ValueError(f"{case_id}_numeric_field_invalid")
            if any(isinstance(item, float) and not math.isfinite(item) for item in values):
                raise ValueError(f"{case_id}_numeric_field_not_finite")
        for key, targets in case["stt_targets"].items():
            if (
                not isinstance(key, str)
                or not isinstance(targets, list)
                or not targets
                or not all(
                    isinstance(aliases, list)
                    and aliases
                    and all(isinstance(alias, str) and alias.strip() for alias in aliases)
                    for aliases in targets
                )
            ):
                raise ValueError(f"{case_id}_stt_targets_invalid")
        policy = case.get("expected_confirmation_policy")
        if policy not in POLICIES:
            raise ValueError(f"{case_id}_policy_invalid")
        if "WEIGHING" in event_types and policy == "AUTO_APPLY":
            raise ValueError(f"{case_id}_voice_weighing_requires_confirmation")
        if not isinstance(case.get("expected_write_allowed"), bool):
            raise ValueError(f"{case_id}_expected_write_allowed_invalid")
        if case["expected_write_allowed"] != (policy == "AUTO_APPLY"):
            raise ValueError(f"{case_id}_write_policy_inconsistent")
        if case["expected_write_allowed"] and (case["expected_missing_fields"] or case["expected_ambiguities"]):
            raise ValueError(f"{case_id}_unsafe_expected_auto_write")
        if case.get("risk_level") not in RISK_LEVELS:
            raise ValueError(f"{case_id}_risk_level_invalid")
        if not isinstance(case.get("golden_core"), bool):
            raise ValueError(f"{case_id}_golden_core_flag_invalid")
        if case.get("expected_time_expression") is not None and not isinstance(case["expected_time_expression"], str):
            raise ValueError(f"{case_id}_time_expression_invalid")
        if case.get("expected_question") is not None and not isinstance(case["expected_question"], str):
            raise ValueError(f"{case_id}_expected_question_invalid")
    return cases


def load_golden_core(dataset: list[dict[str, Any]], path: Path = DEFAULT_CORE) -> list[dict[str, Any]]:
    ids = [row.get("case_id") for row in _read_jsonl(path)]
    if len(ids) != len(set(ids)):
        raise ValueError("golden_core_ids_must_be_unique")
    by_id = {case["case_id"]: case for case in dataset}
    if any(case_id not in by_id for case_id in ids):
        raise ValueError("golden_core_contains_unknown_case")
    flagged_ids = {case["case_id"] for case in dataset if case["golden_core"]}
    if set(ids) != flagged_ids:
        raise ValueError("golden_core_manifest_mismatch")
    core = [by_id[case_id] for case_id in ids]
    if not 30 <= len(core) <= 40:
        raise ValueError("golden_core_must_contain_30_to_40_cases")
    if not all(case["golden_core"] for case in core):
        raise ValueError("golden_core_manifest_mismatch")
    return core


def validate_dataset_quality(dataset: list[dict[str, Any]]) -> dict[str, Any]:
    if len(dataset) < 150:
        raise ValueError("field_eval_v1_requires_at_least_150_cases")
    missing = CATEGORIES - {case["category"] for case in dataset}
    if missing:
        raise ValueError("field_eval_v1_missing_categories:" + ",".join(sorted(missing)))
    coverage = {field: sum(field in case["critical_fields"] for case in dataset) for field in sorted(CRITICAL_FIELDS)}
    required = {"animal_id", "group_id", "weight", "unit", "date", "event_type", "calf_sex", "calf_id"}
    absent = sorted(field for field in required if coverage[field] == 0)
    if absent:
        raise ValueError("critical_field_coverage_missing:" + ",".join(absent))
    return {
        "case_count": len(dataset),
        "category_counts": dict(sorted(Counter(case["category"] for case in dataset).items())),
        "critical_field_coverage": coverage,
    }


def normalize_words(text: str) -> list[str]:
    normalized = "".join(
        char for char in unicodedata.normalize("NFKD", text.casefold()) if not unicodedata.combining(char)
    )
    return re.findall(r"[a-z0-9]+", normalized)


def word_error_rate(reference: str, hypothesis: str) -> float:
    expected, actual = normalize_words(reference), normalize_words(hypothesis)
    if not expected:
        return 0.0 if not actual else 1.0
    previous = list(range(len(actual) + 1))
    for row, expected_word in enumerate(expected, start=1):
        current = [row]
        for column, actual_word in enumerate(actual, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[column] + 1,
                    previous[column - 1] + (expected_word != actual_word),
                )
            )
        previous = current
    return previous[-1] / len(expected)


def _contains_phrase(text: str, phrases: list[str]) -> bool:
    tokens = normalize_words(text)
    return any(
        (needle := normalize_words(phrase))
        and any(tokens[index : index + len(needle)] == needle for index in range(len(tokens) - len(needle) + 1))
        for phrase in phrases
    )


def _events(prediction: dict[str, Any]) -> list[dict[str, Any]]:
    proposal = prediction.get("proposal") or {}
    return [event for event in proposal.get("events", []) if isinstance(event, dict)]


def _normalized_events(events: list[dict[str, Any]]) -> list[dict[str, Any]] | None:
    normalized = []
    try:
        for event in events:
            event_type = EventType(event.get("event_type"))
            payload = PAYLOAD_MODELS[event_type].model_validate(event.get("payload") or {}).model_dump(mode="json")
            normalized.append(
                {
                    "event_type": event_type.value,
                    "payload": payload,
                    "time_expression": event.get("time_expression"),
                    "correction_requested": bool(event.get("correction_requested", False)),
                }
            )
    except (TypeError, ValueError, ValidationError):
        return None
    return normalized


def _actual_fields(prediction: dict[str, Any]) -> dict[str, Any]:
    events = _events(prediction)
    payloads = [event.get("payload") or {} for event in events]
    outcomes = [outcome for payload in payloads for outcome in payload.get("outcomes", [])]
    animal_ids = [
        value
        for value in [
            *(payload.get("animal_identifier") for payload in payloads),
            *(payload.get("display_identifier") for payload in payloads),
            *(payload.get("mother_identifier") for payload in payloads),
            *(outcome.get("display_identifier") for outcome in outcomes if isinstance(outcome, dict)),
        ]
        if value is not None
    ]
    group_ids = [
        value
        for value in [
            *(payload.get("group_identifier") for payload in payloads),
            *(payload.get("to_group_identifier") for payload in payloads),
            *(payload.get("from_group_identifier") for payload in payloads),
        ]
        if value is not None
    ]
    numeric_fields = {}
    for key in ("weight_kg", "outcome_count"):
        values = [payload[key] for payload in payloads if payload.get(key) is not None]
        if values:
            numeric_fields[key] = values[0] if len(values) == 1 else values
    units = {}
    if "weight_kg" in numeric_fields and "weight_kg" not in units:
        units = {**units, "weight_kg": "kg"}
    proposal = prediction.get("proposal") or {}
    slot_fields = {}
    for name in ("vaccine", "dose", "observation", "observed_sign", "body_region", "sex", "species", "origin", "notes"):
        values = list(dict.fromkeys(payload[name] for payload in payloads if payload.get(name) is not None))
        if values:
            slot_fields[name] = values[0] if len(values) == 1 else values
    sexes = list(dict.fromkeys(outcome.get("sex") for outcome in outcomes if outcome.get("sex") is not None))
    if sexes:
        slot_fields["calf_sex"] = sexes[0] if len(sexes) == 1 else sexes
    outcome_values = list(
        dict.fromkeys(outcome.get("outcome") for outcome in outcomes if outcome.get("outcome") is not None)
    )
    if outcome_values:
        slot_fields["outcome"] = outcome_values[0] if len(outcome_values) == 1 else outcome_values
    return {
        "intents": [event.get("event_type") for event in events],
        "animal_ids": sorted({str(value) for value in animal_ids}),
        "group_ids": sorted({str(value) for value in group_ids}),
        "numeric_fields": numeric_fields,
        "slot_fields": slot_fields,
        "units": units,
        "time_expressions": [event.get("time_expression") for event in events],
        "correction_requested": any(event.get("correction_requested", False) for event in events),
        "missing_fields": proposal.get("missing_fields", []),
        "ambiguity_detected": bool(proposal.get("ambiguities")) or any(event.get("ambiguities") for event in events),
        "out_of_scope": bool(proposal.get("out_of_scope")),
        "decision": prediction.get("decision"),
        "event_count": len(proposal.get("events") or []),
    }


def evaluate_predictions(dataset: list[dict[str, Any]], predictions: list[dict[str, Any]]) -> dict[str, Any]:
    prediction_by_id: dict[str, dict[str, Any]] = {}
    for prediction in predictions:
        if not isinstance(prediction, dict):
            raise ValueError("prediction_must_be_object")
        case_id = prediction.get("case_id")
        if not isinstance(case_id, str) or case_id in prediction_by_id:
            raise ValueError("prediction_case_ids_missing_or_duplicate")
        transcript = prediction.get("transcript", "")
        if not isinstance(transcript, str):
            raise ValueError(f"{case_id}_transcript_must_be_text")
        proposal = prediction.get("proposal", {})
        if not isinstance(proposal, dict) or not isinstance(proposal.get("events", []), list):
            raise ValueError(f"{case_id}_proposal_events_invalid")
        missing_fields = proposal.get("missing_fields", [])
        ambiguities = proposal.get("ambiguities", [])
        if (
            not isinstance(missing_fields, list)
            or not all(isinstance(field, str) for field in missing_fields)
            or not isinstance(ambiguities, list)
            or not all(isinstance(item, str) for item in ambiguities)
        ):
            raise ValueError(f"{case_id}_proposal_metadata_invalid")
        for event in proposal.get("events", []):
            if not isinstance(event, dict) or not isinstance(event.get("payload", {}), dict):
                raise ValueError(f"{case_id}_event_payload_invalid")
            payload = event.get("payload", {})
            for field in (
                "vaccine",
                "dose",
                "observation",
                "observed_sign",
                "body_region",
                "sex",
                "species",
                "origin",
                "notes",
            ):
                if payload.get(field) is not None and not isinstance(payload[field], str):
                    raise ValueError(f"{case_id}_event_payload_field_invalid:{field}")
            outcomes = payload.get("outcomes", [])
            if not isinstance(outcomes, list) or any(not isinstance(outcome, dict) for outcome in outcomes):
                raise ValueError(f"{case_id}_event_outcomes_invalid")
            if any(
                outcome.get(field) is not None and not isinstance(outcome[field], str)
                for outcome in outcomes
                for field in ("sex", "outcome")
            ):
                raise ValueError(f"{case_id}_event_outcome_field_invalid")
        decision = prediction.get("decision")
        if not isinstance(decision, str) or decision not in POLICIES:
            raise ValueError(f"{case_id}_decision_invalid")
        prediction_by_id[case_id] = prediction
    known_ids = {case["case_id"] for case in dataset}
    if set(prediction_by_id) - known_ids:
        raise ValueError("prediction_contains_unknown_case")

    rows: list[dict[str, Any]] = []
    wer_values: list[float] = []
    stt_checks = stt_correct = false_safe_write = scored = 0
    stt_checks_by_field: Counter[str] = Counter()
    stt_correct_by_field: Counter[str] = Counter()
    field_checks: Counter[str] = Counter()
    field_correct: Counter[str] = Counter()
    for case in dataset:
        prediction = prediction_by_id.get(case["case_id"])
        if prediction is None:
            continue
        scored += 1
        actual = _actual_fields(prediction)
        transcript = prediction.get("transcript", "")
        if not isinstance(transcript, str):
            raise ValueError(f"{case['case_id']}_transcript_must_be_text")
        wer_values.append(word_error_rate(case["input_text"], transcript))
        stt_case_match = True
        for field_name, phrases in case["stt_targets"].items():
            stt_checks += 1
            matches = all(_contains_phrase(transcript, aliases) for aliases in phrases)
            stt_correct += int(matches)
            stt_checks_by_field[field_name] += 1
            stt_correct_by_field[field_name] += int(matches)
            stt_case_match = stt_case_match and matches

        comparisons: dict[str, bool] = {}
        expected_intents = (
            []
            if case["expected_intent"] is None
            else (case["expected_intent"] if isinstance(case["expected_intent"], list) else [case["expected_intent"]])
        )
        if expected_intents or actual["intents"]:
            comparisons["intent"] = actual["intents"] == expected_intents
        if expected_intents or actual["intents"]:
            comparisons["animal_id"] = sorted(actual["animal_ids"]) == sorted(case["expected_animal_ids"])
            comparisons["group_id"] = sorted(actual["group_ids"]) == sorted(case["expected_group_ids"])
        else:
            comparisons["animal_id"] = comparisons["group_id"] = True
        comparisons["numeric_fields"] = actual["numeric_fields"] == case["expected_numeric_fields"]
        comparisons["slot_fields"] = actual["slot_fields"] == case["expected_slot_fields"]
        comparisons["units"] = actual["units"] == case["expected_units"]
        expected_times = [event.get("time_expression") for event in case["expected_events"]]
        comparisons["time_expression"] = actual["time_expressions"] == expected_times
        comparisons["missing_fields"] = sorted(actual["missing_fields"]) == sorted(case["expected_missing_fields"])
        expected_ambiguity = bool(case["expected_ambiguities"])
        comparisons["ambiguity_detection"] = actual["ambiguity_detected"] is expected_ambiguity
        comparisons["confirmation_policy"] = actual["decision"] == case["expected_confirmation_policy"]
        comparisons["correction_requested"] = actual["correction_requested"] is case["expected_correction_requested"]
        comparisons["clarification_decision"] = (actual["decision"] == "CLARIFY") == (
            case["expected_confirmation_policy"] == "CLARIFY"
        )
        comparisons["event_count"] = actual["event_count"] == len(case["expected_events"])
        actual_event_projection = _normalized_events(_events(prediction))
        expected_event_projection = _normalized_events(case["expected_events"])
        comparisons["event_payloads"] = (
            actual_event_projection is not None
            and expected_event_projection is not None
            and actual_event_projection == expected_event_projection
        )
        for name, is_correct in comparisons.items():
            field_checks[name] += 1
            field_correct[name] += int(is_correct)
        critical_comparison = {
            "animal_id": comparisons["animal_id"],
            "group_id": comparisons["group_id"],
            "weight": comparisons["numeric_fields"],
            "unit": comparisons["units"],
            "date": comparisons["time_expression"],
            "event_type": comparisons.get("intent", actual["intents"] == []),
            "calf_sex": "calf_sex" not in case["expected_slot_fields"]
            or actual["slot_fields"].get("calf_sex") == case["expected_slot_fields"].get("calf_sex"),
            "calf_id": comparisons["animal_id"],
            "quantity": comparisons["numeric_fields"],
        }
        critical_mismatch = any(
            not critical_comparison[field] for field in case["critical_fields"] if field in critical_comparison
        )
        critical_mismatch = critical_mismatch or not comparisons["event_payloads"]
        unsafe_expected = not case["expected_write_allowed"] or bool(case["expected_ambiguities"])
        actual_requires_review = (
            actual["ambiguity_detected"]
            or actual["missing_fields"]
            or actual["out_of_scope"]
            or actual_event_projection is None
            or any(
                event.get("confidence") is None
                or not isinstance(event.get("confidence"), (int, float))
                or isinstance(event.get("confidence"), bool)
                or not math.isfinite(event.get("confidence"))
                or event.get("confidence") < 0.8
                or event.get("confidence") > 1.0
                for event in _events(prediction)
            )
        )
        false_safe = actual["decision"] == "AUTO_APPLY" and (
            unsafe_expected or actual_requires_review or critical_mismatch or not stt_case_match
        )
        false_safe_write += int(false_safe)
        rows.append(
            {
                "case_id": case["case_id"],
                "category": case["category"],
                "wer": wer_values[-1],
                "critical_stt_fields_correct": stt_case_match,
                "comparisons": comparisons,
                "false_safe_write": false_safe,
            }
        )
    if not scored:
        raise ValueError("no_predictions_match_dataset")
    return {
        "status": "OFFLINE_PREDICTIONS_SCORED" if scored == len(dataset) else "INCOMPLETE_PREDICTION_COVERAGE",
        "evidence_scope": "synthetic_text_only_or_operator_supplied_predictions",
        "dataset_cases": len(dataset),
        "predictions_scored": scored,
        "predictions_missing": len(dataset) - scored,
        "stt": {
            "mean_wer": sum(wer_values) / len(wer_values),
            "critical_field_accuracy": stt_correct / stt_checks if stt_checks else None,
            "critical_field_checks": stt_checks,
            "field_accuracy": {
                f"{field_name}_accuracy": stt_correct_by_field[field_name] / checks
                for field_name, checks in sorted(stt_checks_by_field.items())
            },
        },
        "interpretation": {
            f"{name}_accuracy": field_correct[name] / checks if checks else None
            for name, checks in sorted(field_checks.items())
        },
        "false_safe_write": {
            "count": false_safe_write,
            "rate": false_safe_write / scored,
            "definition": (
                "AUTO_APPLY when expected policy forbids direct write, a critical field is wrong, "
                "or transcript misses a critical STT target."
            ),
        },
        "cases": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate", "evaluate", "demo"))
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--golden-core", type=Path, default=DEFAULT_CORE)
    parser.add_argument("--predictions", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        dataset = load_dataset(args.dataset)
        core = load_golden_core(dataset, args.golden_core)
        if args.command == "validate":
            quality = validate_dataset_quality(dataset)
            result = {
                "status": "VALID",
                **quality,
                "golden_core_cases": len(core),
                "synthetic_cases": sum(case["source_status"] == "SYNTHETIC_ONLY" for case in dataset),
            }
        else:
            predictions_path = args.predictions or (DEFAULT_DEMO if args.command == "demo" else None)
            if predictions_path is None:
                parser.error("evaluate requires --predictions; demo uses explicitly labeled example predictions")
            result = evaluate_predictions(dataset, _read_jsonl(predictions_path))
            if args.command == "demo":
                result["status"] = "DEMONSTRATION_ONLY_NOT_MODEL_EVIDENCE"
        encoded = json.dumps(result, ensure_ascii=False, indent=2)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(encoded + "\n", encoding="utf-8")
        print(encoded)
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "INVALID_EVALUATION_INPUT", "reason": str(exc)}, ensure_ascii=False))
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
