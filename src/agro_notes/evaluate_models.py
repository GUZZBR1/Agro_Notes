"""Opt-in evaluation of available production Groq models on synthetic prompts.

This tool sends only the checked-in synthetic fixture text to Groq. It does not
write to Telegram, Google Sheets, or persistent storage.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from statistics import median
from typing import Any

from openai import OpenAI

from .groq_interpreter import STRICT_SCHEMA_MODELS, GroqInterpretationError, GroqInterpretationProvider

FIXTURE = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "provider-golden.json"
EXTRA_FIXTURE = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "provider-evaluation-extra.json"
PRODUCTION_STRICT_MODELS = frozenset({"openai/gpt-oss-20b", "openai/gpt-oss-120b"})
MODEL_PRICES_USD_PER_MILLION = {
    "openai/gpt-oss-20b": {"input": 0.075, "output": 0.30},
    "openai/gpt-oss-120b": {"input": 0.15, "output": 0.60},
}
PRICE_SOURCE = "https://console.groq.com/docs/models"
PRICE_CHECKED_ON = "2026-10-13"


def select_candidate_models(active_ids: set[str], requested: list[str] | None = None) -> list[str]:
    candidates = sorted(active_ids & PRODUCTION_STRICT_MODELS & STRICT_SCHEMA_MODELS)
    return [model for model in candidates if not requested or model in requested]


def score_proposal(case: dict[str, Any], proposal: Any) -> dict[str, Any]:
    events = proposal.events
    expected_type = case["event_type"]
    intent_ok = (not events and expected_type is None) or (bool(events) and events[0].event_type == expected_type)
    payload_ok = False
    if intent_ok and expected_type is not None and events:
        actual = events[0].payload
        payload_ok = _matches_expected(actual, case["required_payload"])
        payload_ok = payload_ok and all(
            getattr(proposal, key, None) == value for key, value in case.get("required_proposal", {}).items()
        )
        payload_ok = payload_ok and len(events) == case.get("event_count", 1)
    ambiguity_ok = not case.get("must_be_ambiguous") or bool(proposal.ambiguities) or bool(
        events and events[0].ambiguities
    )
    scope_ok = not case.get("must_be_out_of_scope") or proposal.out_of_scope
    event_count_ok = len(events) == case.get("event_count", 0 if expected_type is None else 1)
    return {
        "id": case["id"],
        "intent_ok": intent_ok,
        "required_payload_ok": payload_ok if expected_type is not None else True,
        "ambiguity_ok": ambiguity_ok,
        "scope_ok": scope_ok,
        "event_count_ok": event_count_ok,
        "pass": (
            intent_ok
            and event_count_ok
            and (payload_ok if expected_type is not None else True)
            and ambiguity_ok
            and scope_ok
        ),
    }


def _matches_expected(actual: Any, expected: Any) -> bool:
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(
            key in actual and _matches_expected(actual[key], value) for key, value in expected.items()
        )
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(
            _matches_expected(got, want) for got, want in zip(actual, expected, strict=True)
        )
    return actual == expected


def evaluate_model(api_key: str, model: str) -> dict[str, Any]:
    provider = GroqInterpretationProvider(api_key=api_key, model=model)
    try:
        cases = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cases.extend(json.loads(EXTRA_FIXTURE.read_text(encoding="utf-8")))
        results = []
        for case in cases:
            if case.get("idempotency_is_application_test"):
                results.append({"id": case["id"], "status": "APPLICATION_INTEGRATION_REQUIRED", "pass": None})
                continue
            try:
                response = provider.interpret(case["text"])
                result = score_proposal(case, response.proposal)
                result.update(
                    {
                        "schema_valid": response.metadata.schema_valid,
                        "latency_ms": response.metadata.latency_ms,
                        "retry_count": response.metadata.retry_count,
                        "input_tokens": response.metadata.input_tokens,
                        "output_tokens": response.metadata.output_tokens,
                        "outcome": response.metadata.outcome.value,
                    }
                )
                results.append(result)
            except GroqInterpretationError as exc:
                results.append(
                    {
                        "id": case["id"],
                        "pass": False,
                        "schema_valid": False if exc.outcome.value == "INVALID_SCHEMA" else None,
                        "latency_ms": exc.latency_ms,
                        "retry_count": exc.retry_count,
                        "input_tokens": None,
                        "output_tokens": None,
                        "outcome": exc.outcome.value,
                    }
                )
        scored = [case for case in results if case["pass"] is not None]
        input_tokens = sum(case["input_tokens"] or 0 for case in scored)
        output_tokens = sum(case["output_tokens"] or 0 for case in scored)
        usage_complete = bool(scored) and all(
            case["input_tokens"] is not None and case["output_tokens"] is not None for case in scored
        )
        prices = MODEL_PRICES_USD_PER_MILLION.get(model)
        estimated_cost = (
            (input_tokens * prices["input"] + output_tokens * prices["output"]) / 1_000_000
            if prices and usage_complete
            else None
        )
        successful = [case for case in scored if case.get("outcome") == "SUCCESS"]
        schema_valid = [case for case in scored if case.get("schema_valid") is True]
        retries = sum(case.get("retry_count", 0) for case in scored)
        latencies = [case["latency_ms"] for case in scored if case.get("latency_ms") is not None]
        return {
            "provider": "groq",
            "model": model,
            "cases": results,
            "passed": sum(case["pass"] for case in scored),
            "total": len(scored),
            "application_cases": [case["id"] for case in results if case["pass"] is None],
            "score": sum(case["pass"] for case in scored) / len(scored) if scored else 0,
            "schema_compliance_rate": len(schema_valid) / len(scored) if scored else None,
            "error_count": len(scored) - len(successful),
            "retry_count": retries,
            "median_latency_ms": median(latencies) if latencies else None,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "estimated_cost_usd": estimated_cost,
            "cost_status": "ESTIMATED" if estimated_cost is not None else "USAGE_UNAVAILABLE",
            "price_source": PRICE_SOURCE,
            "price_checked_on": PRICE_CHECKED_ON,
        }
    finally:
        provider.close()


def main() -> None:
    key = os.environ.get("GROQ_API_KEY", "").strip()
    if not key:
        print(json.dumps({"status": "WAITING_FOR_EXTERNAL_CREDENTIALS", "required": "GROQ_API_KEY"}))
        raise SystemExit(2)
    requested = sys.argv[1:] or None
    client = OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1", timeout=30.0, max_retries=0)
    try:
        active_ids = {model.id for model in client.models.list().data}
    except Exception as exc:
        print(json.dumps({"status": "EXTERNAL_PROVIDER_BLOCKED", "reason": type(exc).__name__}))
        raise SystemExit(3) from None
    finally:
        client.close()
    candidates = select_candidate_models(active_ids, requested)
    if not candidates:
        print(
            json.dumps(
                {"status": "EXTERNAL_PROVIDER_BLOCKED", "reason": "no_requested_production_strict_model_available"}
            )
        )
        raise SystemExit(3)
    results = [evaluate_model(key, model) for model in candidates]
    results.sort(
        key=lambda result: (
            -result["score"],
            -(result["schema_compliance_rate"] or 0),
            result["error_count"],
            result["estimated_cost_usd"] if result["estimated_cost_usd"] is not None else float("inf"),
            result["median_latency_ms"] if result["median_latency_ms"] is not None else float("inf"),
        )
    )
    winner = results[0]["model"] if len(results) > 1 else None
    status = "COMPLETED" if len(results) > 1 else "SINGLE_MODEL_AVAILABLE"
    rationale = (
        "Ranqueado por acerto do golden set, compliance de schema, erros, custo estimado e latência."
        if winner
        else "Somente um modelo de produção com strict schema está ativo e foi avaliado."
    )
    print(
        json.dumps(
            {
                "status": status,
                "models_tested": candidates,
                "winner": winner,
                "rationale": rationale,
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
