# FIELD_EVAL_V1 metrics

Reports use one record per prediction and include missing-case coverage. A
partial result is labeled `INCOMPLETE_PREDICTION_COVERAGE`; it is not a complete
benchmark score.

## Speech recognition

- **WER:** normalized word edit distance divided by reference word count.
- **Critical field accuracy:** exact contiguous phrase matching for every
  target in each `stt_targets` field; aliases are alternatives only within one
  target, so each distinct ID, number, and date must be present.
- **Animal ID, lot ID, number/weight, unit, and date accuracy:** separate rates
  over available critical phrase targets. Never treat two different values
  (for example 512 and 712) as aliases.

WER is diagnostic only. A low WER cannot compensate for a changed critical
identifier, weight, lot, unit, or date.

## Interpretation and policy

The evaluator reports event intent, animal ID, group ID, numeric slots, text
slots, units, time expression, missing-field, ambiguity-detection, clarification
decision, confirmation-policy, correction flag, and event-count accuracy.
It also compares ordered event payloads, preserving the association between a
target and its event and detecting extra or invalid fields. Interpretation
metrics are derived from `proposal`; auxiliary extraction metadata cannot
override it. The harness checks structural parity with expected payloads but is
not a substitute for production domain validation.

## FALSE_SAFE_WRITE

For a case, `FALSE_SAFE_WRITE = true` when the evaluated decision is
`AUTO_APPLY` while immediate writing is forbidden by the expected policy, a
critical field is wrong, or any expected critical STT phrase was lost. This
includes an auto-write on a clarification/manual-review case. The aggregate
reports count and rate; every case retains its boolean evidence. A required
confirmation is not counted as a safe immediate write. Actual proposal
ambiguity, out-of-scope marking, missing fields, invalid payload schema, and
absent, non-finite, out-of-range, or sub-0.8 event confidence also make an
auto-write unsafe. The accepted confidence range is `[0.8, 1.0]`.

This is a benchmark warning metric, not a production safety gate. Do not change
production confirmation policy from this score alone.
