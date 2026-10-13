from agro_notes.evaluate_transcription_models import (
    PRICE_USD_PER_AUDIO_HOUR,
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


def test_stt_candidates_include_only_active_groq_whisper_models():
    active = {"whisper-large-v3", "whisper-large-v3-turbo", "whisper-large-v3-preview"}

    assert select_active_models(active) == ["whisper-large-v3-turbo", "whisper-large-v3"]
    assert select_active_models(active, ["whisper-large-v3"]) == ["whisper-large-v3"]
    assert set(PRICE_USD_PER_AUDIO_HOUR) == set(select_active_models(active))
