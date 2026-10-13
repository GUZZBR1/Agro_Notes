"""Compare Groq Whisper production models against a human-labeled local manifest.

The manifest/audio are supplied by the operator and never written to results.
Only numeric quality/latency/cost measurements are emitted.
"""

from __future__ import annotations

import json
import math
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
REQUIRED_MATRIX_TAGS = frozenset(
    {
        "clean_voice",
        "low_voice",
        "short_audio",
        "long_audio",
        "background_noise",
        "numbers",
        "lot_names",
        "animal_identifiers",
        "regionalisms",
        "accents",
        "fast_speech",
    }
)
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


def score_transcription(
    reference: str,
    hypothesis: str,
    critical_terms: list[str],
    critical_term_aliases: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    normalized_hypothesis = normalize_words(hypothesis)
    aliases = critical_term_aliases or {}
    normalized_critical = [
        [normalize_words(term), *(normalize_words(alias) for alias in aliases.get(term, []))]
        for term in critical_terms
    ]
    matched = [
        variants
        for variants in normalized_critical
        if any(
            terms
            and any(
                normalized_hypothesis[index : index + len(terms)] == terms
                for index in range(len(normalized_hypothesis) - len(terms) + 1)
            )
            for terms in variants
        )
    ]
    return {
        "wer": word_error_rate(reference, hypothesis),
        "critical_terms_total": len(normalized_critical),
        "critical_terms_matched": len(matched),
        "critical_term_recall": len(matched) / len(normalized_critical) if normalized_critical else None,
    }


def load_manifest(manifest_path: Path) -> list[dict[str, Any]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, list) or not manifest:
        raise ValueError("manifest_must_be_non_empty_list")
    seen_ids: set[str] = set()
    for index, case in enumerate(manifest):
        if not isinstance(case, dict):
            raise ValueError(f"case_{index}_must_be_object")
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id.strip() or case_id in seen_ids:
            raise ValueError(f"case_{index}_id_missing_or_duplicate")
        seen_ids.add(case_id)
        audio_path = case.get("audio_path")
        reference = case.get("reference_text")
        critical_terms = case.get("critical_terms")
        duration = case.get("duration_seconds")
        if not isinstance(audio_path, str) or not audio_path.strip():
            raise ValueError(f"case_{index}_audio_path_missing")
        if not isinstance(reference, str) or not reference.strip():
            raise ValueError(f"case_{index}_reference_text_missing")
        if not isinstance(critical_terms, list) or not critical_terms or not all(
            isinstance(term, str) and term.strip() for term in critical_terms
        ):
            raise ValueError(f"case_{index}_critical_terms_invalid")
        if (
            not isinstance(duration, (int, float))
            or isinstance(duration, bool)
            or not math.isfinite(duration)
            or duration <= 0
        ):
            raise ValueError(f"case_{index}_duration_invalid")
        resolved_audio = (manifest_path.parent / audio_path).resolve()
        if not resolved_audio.is_file():
            raise ValueError(f"case_{index}_audio_file_missing")
        tags = case.get("matrix_tags", [])
        if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
            raise ValueError(f"case_{index}_matrix_tags_invalid")
        unknown_tags = set(tags) - REQUIRED_MATRIX_TAGS
        if unknown_tags:
            raise ValueError(f"case_{index}_matrix_tags_unknown")
        aliases = case.get("critical_term_aliases", {})
        if not isinstance(aliases, dict) or any(
            term not in critical_terms
            or not isinstance(values, list)
            or not values
            or not all(isinstance(v, str) and v.strip() for v in values)
            for term, values in aliases.items()
        ):
            raise ValueError(f"case_{index}_critical_term_aliases_invalid")
    return manifest


def missing_matrix_tags(manifest: list[dict[str, Any]]) -> list[str]:
    covered = {tag for case in manifest for tag in case.get("matrix_tags", [])}
    return sorted(REQUIRED_MATRIX_TAGS - covered)


def model_result_is_complete(result: dict[str, Any], expected_case_count: int) -> bool:
    cases = result.get("cases", [])
    return len(cases) == expected_case_count and all(
        case.get("outcome") == "SUCCESS"
        and case.get("wer") is not None
        and case.get("critical_term_recall") is not None
        for case in cases
    )


def has_complete_model_results(results: list[dict[str, Any]], expected_case_count: int) -> bool:
    return bool(results) and all(model_result_is_complete(result, expected_case_count) for result in results)


def select_active_models(active_ids: set[str], requested: list[str] | None = None) -> list[str]:
    available = [model for model in MODELS if model in active_ids]
    return [model for model in available if not requested or model in requested]


async def evaluate_model(api_key: str, model: str, manifest_path: Path) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
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
                score = score_transcription(
                    case["reference_text"],
                    result.text,
                    case.get("critical_terms", []),
                    case.get("critical_term_aliases"),
                )
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
    try:
        manifest = load_manifest(manifest_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"status": "INVALID_FIXTURE", "reason": str(exc)}))
        raise SystemExit(2) from None
    missing_tags = missing_matrix_tags(manifest)
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
            -(result["critical_term_recall"] if result["critical_term_recall"] is not None else 0),
            result["mean_wer"] if result["mean_wer"] is not None else float("inf"),
            result["error_count"],
            result["estimated_cost_usd"] if result["estimated_cost_usd"] is not None else float("inf"),
            result["median_latency_ms"] if result["median_latency_ms"] is not None else float("inf"),
        )
    )
    matrix_complete = not missing_tags
    evaluation_complete = has_complete_model_results(results, len(manifest))
    winner = results[0]["model"] if len(results) > 1 and matrix_complete and evaluation_complete else None
    status = (
        "SINGLE_MODEL_AVAILABLE"
        if len(results) == 1
        else "INCOMPLETE_TEST_MATRIX"
        if not matrix_complete
        else "COMPLETED"
        if evaluation_complete
        else "INCOMPLETE_MODEL_EVALUATION"
    )
    rationale = (
        "Ordenado por recall de termos críticos, WER, erros, custo estimado e latência."
        if winner
        else "Só um modelo de produção está ativo; a avaliação de qualidade não concluiu todos os casos."
        if len(results) == 1 and not evaluation_complete
        else "Somente um dos modelos Whisper de produção está ativo e foi avaliado."
        if len(results) == 1
        else "Sem recomendação: faltam categorias obrigatórias de áudio real na matriz."
        if not matrix_complete
        else "Sem recomendação: todos os modelos devem concluir todos os casos para comparação justa."
    )
    print(
        json.dumps(
            {
                "status": status,
                "models_tested": models,
                "winner": winner,
                "matrix_complete": matrix_complete,
                "missing_matrix_tags": missing_tags,
                "evaluation_complete": evaluation_complete,
                "incomplete_models": [
                    result["model"] for result in results if not model_result_is_complete(result, len(manifest))
                ],
                "rationale": rationale,
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
