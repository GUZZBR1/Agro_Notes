# FIELD_EVAL_V1 recording protocol

This protocol is for a future opt-in field round. The current corpus has no real
recordings. Synthetic text or TTS must never be labeled `REAL_FIELD_SPEECH`.

## Initial sampling

Target either five speakers reading ten varied prompts each (50 recordings), or
two to three speakers reading twenty prompts each. A smaller first round is
acceptable when fewer volunteers are available. Recruit variation in speaking
rate, regional vocabulary, and recording distance; do not treat multiple clips
from one person as independent speakers.

Use case IDs from `field_eval_v1.jsonl`; include simple, compound, numeric,
regional, incomplete, clarification, correction, and negative cases. Do not
coach participants to produce a specific ASR-friendly pronunciation. Record the
spoken words verbatim, including hesitations, self-corrections, and uncertainty.

## Recording conditions

Use the participant's own phone when practical. Record one prompt per clip in
the format Telegram will deliver where possible. Capture the prompt ID,
anonymous speaker ID (`speaker_001`), date, device class, and conditions. Mark
conditions such as `quiet`, `barn_noise`, `wind`, `fast_speech`, `low_voice`,
`phone_near`, `phone_distant`; not every condition is required in round one.
Do not add noise or edit speech to make a clip appear field-recorded.

## Consent and privacy

Explain that the voice is being used to evaluate transcription and event
interpretation, which provider may process it, retention, and deletion contact
before recording. Obtain explicit consent before recording or uploading. Use
anonymous speaker IDs. Do not collect names, CPF, phone numbers, precise home
locations, or unrelated personal/sensitive details. Remove incidental personal
information from the annotation and do not upload it to providers.

Keep audio in an access-restricted local directory outside Git. Never commit
voice clips, service credentials, Telegram IDs, or consent forms. Provide a
separate manifest that maps `case_id` to a relative clip path, speaker ID,
conditions, consent reference, and annotation status; keep the consent record
separately from the audio/model result.

## Human reference annotation

Two reviewers should independently transcribe critical IDs, numbers, dates,
units, negation, correction spans, ambiguity, and event boundaries. Resolve
disagreements against the audio and retain an adjudication note. Preserve a
verbatim transcript as well as normalized field labels. Do not let a model
transcript become its own reference. Mark clips `REAL_FIELD_SPEECH` only after
consent and human review; otherwise keep them `UNREVIEWED` and out of scoring.

## Suggested manifest fields

`case_id`, `audio_path`, `speaker_id`, `conditions`, `consent_reference`,
`annotation_status`, `reference_transcript`, `critical_field_labels`,
`adjudication_status`, and `synthetic` (false for real recordings). The STT
evaluator's manifest remains a provider-specific runtime input; do not place
recordings inside `eval/field_eval_v1.jsonl`.
