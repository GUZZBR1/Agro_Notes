"""Opt-in evaluation of Groq interpretation models on synthetic golden prompts.

This tool sends only the checked-in synthetic fixture text to Groq. It does not
write to Telegram, Google Sheets, or persistent storage.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from .groq_interpreter import GroqInterpretationProvider

FIXTURE = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "provider-golden.json"
DEFAULT_MODELS = ("openai/gpt-oss-20b", "openai/gpt-oss-120b", "qwen/qwen3.8-27b")


def score_proposal(case: dict[str, Any], proposal: Any) -> dict[str, Any]:
    events = proposal.events
    expected_type = case["event_type"]
    intent_ok = (not events and expected_type is None) or (bool(events) and events[0].event_type == expected_type)
    payload_ok = False
    if intent_ok and expected_type is not None and events:
        actual = events[0].payload
        payload_ok = all(actual.get(key) == value for key, value in case["required_payload"].items())
    ambiguity_ok = not case.get("must_be_ambiguous") or bool(proposal.ambiguities) or bool(
        events and events[0].ambiguities
    )
    scope_ok = not case.get("must_be_out_of_scope") or proposal.out_of_scope
    return {
        "id": case["id"],
        "intent_ok": intent_ok,
        "required_payload_ok": payload_ok if expected_type is not None else True,
        "ambiguity_ok": ambiguity_ok,
        "scope_ok": scope_ok,
        "pass": intent_ok and (payload_ok if expected_type is not None else True) and ambiguity_ok and scope_ok,
    }


def evaluate_model(api_key: str, model: str) -> dict[str, Any]:
    provider = GroqInterpretationProvider(api_key=api_key, model=model)
    try:
        cases = json.loads(FIXTURE.read_text(encoding="utf-8"))
        results = []
        for case in cases:
            if case.get("idempotency_is_application_test"):
                results.append({"id": case["id"], "status": "APPLICATION_INTEGRATION_REQUIRED", "pass": None})
                continue
            response = provider.interpret(case["text"])
            results.append(score_proposal(case, response.proposal))
        scored = [case for case in results if case["pass"] is not None]
        return {
            "provider": "groq",
            "model": model,
            "cases": results,
            "passed": sum(case["pass"] for case in scored),
            "total": len(scored),
            "application_cases": [case["id"] for case in results if case["pass"] is None],
            "score": sum(case["pass"] for case in scored) / len(scored) if scored else 0,
        }
    finally:
        provider.close()


def main() -> None:
    key = os.environ.get("GROQ_API_KEY", "").strip()
    if not key:
        print(json.dumps({"status": "WAITING_FOR_EXTERNAL_CREDENTIALS", "required": "GROQ_API_KEY"}))
        raise SystemExit(2)
    requested = sys.argv[1:] or list(DEFAULT_MODELS)
    results = [evaluate_model(key, model) for model in requested]
    results.sort(key=lambda result: (-result["score"], result["model"]))
    print(json.dumps({"status": "COMPLETED", "results": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
