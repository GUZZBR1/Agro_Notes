# FIELD_EVAL_V1 audit record

## Audit status

An independent read-only adversarial audit completed after dataset and metric
implementation. Its two P1 and five P2 findings were reconciled in the corpus,
scorer, or regression tests. No recording or provider result is present.

## Known boundaries

- All 150 input phrases are synthetic, authored examples. They do not establish
  field accuracy or representativeness.
- Context-dependent correction cases declare prior-event assumptions in
  `scenario_context`; a future application test must load that fixture context.
- `expected_write_allowed` means immediate auto-write. `CONFIRM` is a distinct
  policy and requires an accepted preview before persistence.
- The offline harness scores supplied predictions; it does not call STT,
  interpretation, domain validation, Telegram, or Sheets.
- The sample prediction intentionally changes a weight and exists only to test
  metric plumbing. It is not a model result.
- The scorer derives entity, slot, intent, and time values from the structured
  proposal. Optional shadow extraction metadata cannot override the proposal.
- Immediate auto-write is unsafe if the actual proposal has event-level
  ambiguity, is marked out of scope, has missing fields, fails payload schema
  validation, or has absent, non-finite, out-of-range, or below-0.8 event
  confidence. The safe confidence range is `[0.8, 1.0]`.
- Actual and expected payloads are normalized through the domain schema before
  ordered comparison, so legitimate defaults match and undeclared fields fail.
- Event payloads are compared in order, preserving animal-to-event binding;
  every separately spoken identifier, number, and date must match an alias
  group in the STT targets.
- All valid voice-origin weighing cases require confirmation. Corrections for
  event families unsupported by the current correction resolver require manual
  review. These labels describe the existing product path and do not change it.
- An oracle round-trip test builds predictions directly from every expected
  row and checks zero WER plus all applicable interpretation comparisons.

## Reconciliation checklist

## Findings and disposition

- **P1, shadow extraction metadata could conceal incorrect proposal:** fixed by
  deriving metrics from the proposal and testing a mismatched animal ID.
- **P1, voice weighing could be labeled auto-write:** fixed with explicit
  `VOICE_TRANSCRIPT` channel, confirmation labels, and safety regression tests.
- **P2, STT aliases could treat distinct targets as interchangeable:** fixed
  with per-entity alias groups and an all-target match requirement.
- **P2, aggregation lost event-to-animal binding:** fixed by ordered event and
  payload comparison; a vaccine-target swap is covered by a regression test.
- **P2, oracle predictions failed their own metrics:** fixed for display IDs,
  event outcomes, number words, and extracted text slots; the all-case oracle
  round trip passes.
- **P2, utterance labels omitted facts or invented dates:** reconciled for the
  cited compound, incomplete, correction, and multi-target cases; ordered event
  times and explicit details are now represented, including cases 049, 057,
  066, 069, 071, 074, 075, 077, 123, 124, and 131.
- **P2, unsafe auto-write could pass with invalid status/payload:** event
  payload equality detects it and the regression suite verifies the resulting
  `FALSE_SAFE_WRITE` on auto-write.
- **P3, duplicate phrase, missing clarification question, missing `kilos`
  alias, and incomplete core-manifest consistency:** addressed through corpus
  wording/questions, unit aliases, and exact manifest-to-flag validation.
- A follow-up adversarial pass also found ignored actual-proposal safety signals
  and false payload mismatches from domain defaults. Both are covered by
  regression tests; an immediate-write prediction must report sufficient event
  confidence. A final pass found that confidence above 1 or NaN needed rejection;
  both values are now covered by regression tests.

The independent audit covered benchmark consistency and scorer adversarial
cases. The synthetic benchmark remains a readiness artifact only. Human review
of all utterances and validation with consented real recordings remain open.
