"""Compare Groq Whisper production models against a human-labeled local manifest.

The manifest/audio are supplied by the operator and never written to results.
Only numeric quality/latency/cost measurements are emitted.
"""

from __future__ import annotations

import json
import os
import re
import sys
import unicodedata
from pathlib import Path
from statistics import median
from typing import Any

from openai import OpenAI

from .groq_transcription import GroqTranscriber
from .settings import Settings

MODELS = ("whisper-large-v3-turbo", "whisper-large-v3")
PRICE_USD_PER_AUDIO_HOUR = {"whisper-large-v3-turbo": 0.04, "whisper-large-v3": 0.111}
PRICE_SOURCE = "https://console.groq.com/docs/models"
PRICE_CHECKED_ON = "2026-10-13"


def normalize_words(text: str) -> list[str]:
    normalized = "".join(
        char for char in unicodedata.normalize("NFKD", text.casefold()) if not unicodedata.combining(char)
    )
    return re.findall(r"[a-z0-9]+", normalized)


def word_error_rate(reference: str, hypothesis: str) -> float:
    expected = normalize_words(reference)
    actual = normalize_words(hypothesis)
    if not expected:
        return 0.0 if not actual else 1.0
    previous = list(range(len(actual) + 1))
    for row, expected_word in enumerate(expected, start=1):
        current = [row]
        for col, actual_word in enumerate(actual, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[col] + 1,
                    previous[col - 1] + (expected_word != actual_word),
                )
            )
        previous = current
    return previous[-1] / len(expected)


def score_transcription(reference: str, hypothesis: str, critical_terms: list[str]) -> dict[str, Any]:
    normalized_hypothesis = set(normalize_words(hypothesis))
    normalized_critical = [normalize_words(term) for term in critical_terms]
    matched = [terms for terms in normalized_critical if terms and all(term in normalized_hypothesis for term in terms)]
    return {
        "wer": word_error_rate(reference, hypothesis),
        "critical_terms_total": len(normalized_critical),
        "critical_terms_matched": len(matched),
        "critical_term_recall": len(matched) / len(normalized_critical) if normalized_critical else None,
    }


def select_active_models(active_ids: set[str], requested: list[str] | None = None) -> list[str]:
    available = [model for model in MODELS if model in active_ids]
    return [model for model in available if not requested or model in requested]


async def evaluate_model(api_key: str, model: str, manifest_path: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    settings = Settings(GROQ_API_KEY=api_key, GROQ_TRANSCRIPTION_MODEL=model)
    transcriber = GroqTranscriber(settings)
    cases = []
    try:
        for case in manifest:
            audio_path = (manifest_path.parent / case["audio_path"]).resolve()
            audio = audio_path.read_bytes()
            if len(audio) > 20_000_000:
                cases.append(
                    {
                        "id": case["id"],
                        "wer": None,
                        "critical_terms_total": len(case.get("critical_terms", [])),
                        "critical_terms_matched": 0,
                        "critical_term_recall": 0.0 if case.get("critical_terms") else None,
                        "latency_ms": None,
                        "audio_seconds": case.get("duration_seconds"),
                        "retry_count": 0,
                        "outcome": "AUDIO_TOO_LARGE",
                        "estimated_cost_usd": None,
                    }
                )
                continue
            try:
                result = await transcriber.transcribe(audio)
                duration = result.metadata.audio_seconds or case.get("duration_seconds")
                score = score_transcription(case["reference_text"], result.text, case.get("critical_terms", []))
                metadata = result.metadata
                outcome = metadata.outcome.value
            except Exception as exc:
                metadata = getattr(exc, "metadata", None)
                duration = case.get("duration_seconds")
                score = {
                    "wer": None,
                    "critical_terms_total": len(case.get("critical_terms", [])),
                    "critical_terms_matched": 0,
                    "critical_term_recall": 0.0 if case.get("critical_terms") else None,
                }
                outcome = metadata.outcome.value if metadata else type(exc).__name__
            cases.append(
                {
                    "id": case["id"],
                    **score,
                    "latency_ms": metadata.latency_ms if metadata else None,
                    "audio_seconds": duration,
                    "retry_count": metadata.retry_count if metadata else None,
                    "outcome": outcome,
                    "estimated_cost_usd": (
                        duration / 3600 * PRICE_USD_PER_AUDIO_HOUR[model] if duration is not None else None
                    ),
                }
            )
        wers = [case["wer"] for case in cases if case["wer"] is not None]
        recalls = [case["critical_term_recall"] for case in cases if case["critical_term_recall"] is not None]
        latency = [case["latency_ms"] for case in cases if case["latency_ms"] is not None]
        total_cost = sum(case["estimated_cost_usd"] or 0 for case in cases)
        return {
            "provider": "groq",
            "model": model,
            "cases": cases,
            "case_count": len(cases),
            "mean_wer": sum(wers) / len(wers) if wers else None,
            "critical_term_recall": sum(recalls) / len(recalls) if recalls else None,
            "median_latency_ms": median(latency) if latency else None,
            "retry_count": sum(case["retry_count"] or 0 for case in cases),
            "error_count": sum(case["outcome"] != "SUCCESS" for case in cases),
            "estimated_cost_usd": (
                total_cost
                if cases and all(case["audio_seconds"] is not None for case in cases)
                else None
            ),
            "price_source": PRICE_SOURCE,
            "price_checked_on": PRICE_CHECKED_ON,
        }
    finally:
        await transcriber.close()


def main() -> None:
    import asyncio

    key = os.environ.get("GROQ_API_KEY", "").strip()
    if not key:
        print(json.dumps({"status": "WAITING_FOR_EXTERNAL_CREDENTIALS", "required": "GROQ_API_KEY"}))
        raise SystemExit(2)
    if len(sys.argv) < 2:
        print(json.dumps({"status": "FIXTURE_REQUIRED", "required": "human-labeled manifest JSON path"}))
        raise SystemExit(2)
    manifest_path = Path(sys.argv[1]).resolve()
    requested = sys.argv[2:] or None
    client = OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1", timeout=30.0, max_retries=0)
    try:
        active_ids = {model.id for model in client.models.list().data}
    except Exception as exc:
        print(json.dumps({"status": "EXTERNAL_PROVIDER_BLOCKED", "reason": type(exc).__name__}))
        raise SystemExit(3) from None
    finally:
        client.close()
    models = select_active_models(active_ids, requested)
    if not models:
        print(json.dumps({"status": "EXTERNAL_PROVIDER_BLOCKED", "reason": "no_requested_whisper_model_available"}))
        raise SystemExit(3)
    results = [asyncio.run(evaluate_model(key, model, manifest_path)) for model in models]
    results.sort(
        key=lambda result: (
            result["mean_wer"] if result["mean_wer"] is not None else float("inf"),
            -(result["critical_term_recall"] if result["critical_term_recall"] is not None else 0),
            result["error_count"],
            result["estimated_cost_usd"] if result["estimated_cost_usd"] is not None else float("inf"),
            result["median_latency_ms"] if result["median_latency_ms"] is not None else float("inf"),
        )
    )
    winner = results[0]["model"] if len(results) > 1 else None
    status = "COMPLETED" if len(results) > 1 else "SINGLE_MODEL_AVAILABLE"
    rationale = (
        "Ordenado por WER, recall de termos críticos, erros, custo estimado e latência."
        if winner
        else "Somente um dos modelos Whisper de produção está ativo e foi avaliado."
    )
    print(
        json.dumps(
            {
                "status": status,
                "models_tested": models,
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
