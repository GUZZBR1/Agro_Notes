import json
from pathlib import Path

import pytest

from agro_notes.evaluate_transcription_models import (
    PRICE_USD_PER_AUDIO_HOUR,
    has_complete_model_results,
    load_manifest,
    missing_matrix_tags,
    score_transcription,
    select_active_models,
    word_error_rate,
)


def test_transcription_metrics_normalize_accents_and_score_critical_numbers():
    metrics = score_transcription(
        "A 184 pesou 512 quilos hoje",
        "A 184 pesou 512 quilos hoje",
        ["184", "512", "lote 7"],
    )

    assert metrics["wer"] == 0
    assert metrics["critical_terms_matched"] == 2
    assert metrics["critical_term_recall"] == 2 / 3


def test_word_error_rate_counts_substitution_insertion_and_deletion():
    assert word_error_rate("a vaca 184 pesou 512", "a vaca 184 pesou 712 hoje") == 2 / 5


def test_critical_multiword_terms_require_ordered_adjacent_words():
    metrics = score_transcription("lote 7", "7 lote", ["lote 7"])

    assert metrics["critical_terms_matched"] == 0
    assert metrics["critical_term_recall"] == 0


def test_critical_term_aliases_accept_spoken_and_numeric_lot_forms():
    metrics = score_transcription(
        "Passei para o lote sete",
        "Passei para o lote 7",
        ["lote sete"],
        {"lote sete": ["lote 7"]},
    )

    assert metrics["critical_terms_matched"] == 1
    assert metrics["critical_term_recall"] == 1


def test_critical_term_aliases_still_require_phrase_order():
    metrics = score_transcription("lote sete", "7 lote", ["lote sete"], {"lote sete": ["lote 7"]})

    assert metrics["critical_terms_matched"] == 0


def test_manifest_requires_cases_and_existing_audio(tmp_path: Path):
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="manifest_must_be_non_empty_list"):
        load_manifest(manifest_path)

    audio_path = tmp_path / "audio.ogg"
    audio_path.write_bytes(b"audio")
    manifest_path.write_text(
        json.dumps(
            [
                {
                    "id": "case-1",
                    "audio_path": "audio.ogg",
                    "reference_text": "A 184 pesou 512 quilos.",
                    "critical_terms": ["184", "512"],
                    "duration_seconds": 4,
                }
            ]
        ),
        encoding="utf-8",
    )

    assert len(load_manifest(manifest_path)) == 1


@pytest.mark.parametrize("audio_path", ["../outside.ogg", "/etc/hosts"])
def test_manifest_rejects_audio_paths_outside_manifest_directory(tmp_path: Path, audio_path: str):
    manifest_dir = tmp_path / "manifest"
    manifest_dir.mkdir()
    (tmp_path / "outside.ogg").write_bytes(b"audio")
    manifest_path = manifest_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps([{
            "id": "case-1",
            "audio_path": audio_path,
            "reference_text": "A 184 pesou 512 quilos.",
            "critical_terms": ["184", "512"],
            "duration_seconds": 4,
        }]),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="audio_path_outside_manifest_directory"):
        load_manifest(manifest_path)


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("duration_seconds", float("nan"), "duration_invalid"),
        ("critical_terms", [" "], "critical_terms_invalid"),
        ("matrix_tags", ["accnt"], "matrix_tags_unknown"),
        ("critical_term_aliases", {"184": [" "]}, "critical_term_aliases_invalid"),
    ],
)
def test_manifest_rejects_nonfinite_or_empty_quality_inputs(tmp_path: Path, field, value, reason):
    manifest_path = tmp_path / "manifest.json"
    audio_path = tmp_path / "audio.ogg"
    audio_path.write_bytes(b"audio")
    case = {
        "id": "case-1",
        "audio_path": "audio.ogg",
        "reference_text": "A 184 pesou 512 quilos.",
        "critical_terms": ["184", "512"],
        "duration_seconds": 4,
    }
    case[field] = value
    manifest_path.write_text(json.dumps([case]), encoding="utf-8")

    with pytest.raises(ValueError, match=reason):
        load_manifest(manifest_path)


def test_example_matrix_does_not_claim_missing_real_audio_categories():
    example_path = Path(__file__).resolve().parents[1] / "docs" / "stt-evaluation-manifest.example.json"
    example = json.loads(example_path.read_text(encoding="utf-8"))

    assert missing_matrix_tags(example) == ["accents", "long_audio"]


def test_model_evaluation_requires_complete_successful_case_coverage():
    successful_case = {"outcome": "SUCCESS", "wer": 0.0, "critical_term_recall": 1.0}
    complete = [
        {"model": "model-a", "cases": [successful_case, successful_case]},
        {"model": "model-b", "cases": [successful_case, successful_case]},
    ]
    partial = [
        {"model": "model-a", "cases": [successful_case, successful_case]},
        {"model": "model-b", "cases": [{**successful_case, "outcome": "ERROR"}, successful_case]},
    ]

    assert has_complete_model_results(complete, expected_case_count=2)
    assert not has_complete_model_results(partial, expected_case_count=2)
    assert has_complete_model_results(complete[:1], expected_case_count=2)


def test_stt_candidates_include_only_active_groq_whisper_models():
    active = {"whisper-large-v3", "whisper-large-v3-turbo", "whisper-large-v3-preview"}

    assert select_active_models(active) == ["whisper-large-v3-turbo", "whisper-large-v3"]
    assert select_active_models(active, ["whisper-large-v3"]) == ["whisper-large-v3"]
    assert set(PRICE_USD_PER_AUDIO_HOUR) == set(select_active_models(active))
