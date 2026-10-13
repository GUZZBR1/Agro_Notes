# FIELD_EVAL_V1 specification

## Purpose and evidence boundary

`eval/field_eval_v1.jsonl` is a reproducible, **synthetic-only** benchmark for
the language and safety cases that should be measured when real, consented
recordings become available. It contains no claims about real producer speech
or model accuracy. `eval/field_golden_core.jsonl` selects 36 stable case IDs
from the 150-case corpus. `eval/build_field_eval_v1.py` rebuilds both files.

All utterances are authored test prompts, not transcripts collected from
people. `input_channel` is `VOICE_TRANSCRIPT`: text-only harness inputs stand in
for transcripts from the voice workflow, so expected policies include voice
confirmation requirements. In particular, every valid weighing requires
`CONFIRM` before write. Future real recordings must be stored separately and linked to case IDs
with a consent and annotation record. Do not replace synthetic labels with
unreviewed model output.

## Case schema

Each JSONL line contains:

- `case_id`, `category`, `tags`, `source_status`, `input_channel`, `input_text`;
- `expected_intent` and ordered `expected_events` (including event payload,
  time expression, and correction flag);
- expected animal/group identifiers, numeric fields, units, text slots, time,
  missing fields, ambiguities, question, and scenario context;
- `expected_confirmation_policy`, `expected_write_allowed`, critical fields,
  risk level, STT phrase targets, and golden-core membership.

`expected_write_allowed` means safe to persist immediately without a user
confirmation. `CONFIRM` cases may be persisted only after an explicit accepted
preview; clarification, manual-review, and reject cases must not write facts.
Animal IDs remain strings, even when all characters are digits. They are never
treated as measured quantities.

## Category allocation

| Category | Cases |
| --- | ---: |
| SIMPLE | 24 |
| COMPOUND | 18 |
| AMBIGUOUS | 18 |
| INCOMPLETE | 18 |
| CORRECTION | 18 |
| REGIONALISM | 18 |
| HIGH_RISK | 20 |
| OUT_OF_SCOPE | 16 |
| **Total** | **150** |

Numeric stress and adversarial scenarios are cross-cutting tags, not extra
primary categories. The benchmark covers all seven supported event families.
It uses rural Portuguese vocabulary such as `terneiro`, `bezerro`, `novilha`,
`matriz`, `boi`, `gado`, `piquete`, `potreiro`, `curral`, `amojada`, `cio`,
`pariu`, `cria`, `brinco`, and `lote`. Ambiguous shorthand such as `bicho` or
`passa ela pro sete` must not gain an invented identity.

## Context and annotation

Cases that depend on prior events declare `scenario_context`; it is a fixture
description, not trusted model input. The fixture owner must provide matching
animal/group/history state before running an application-level test. Where
explicit liveness is needed, the expected text says `nasceu viva/vivo`; the
benchmark does not infer live status from `pariu` alone. Date expressions are
retained as spoken; date resolution needs an explicit fixed capture time and
property timezone.

`python -m agro_notes.field_eval validate` checks unique IDs, enums, policy
consistency, required categories, critical-field presence, minimum case count,
and golden-core membership. Review any change to a core case as a labeled
regression-set change; do not alter it just to make a current model pass.

## Offline inputs

`python -m agro_notes.field_eval evaluate --predictions <jsonl>` scores
provider-neutral predictions with case ID, recognized transcript, structured
proposal, and decision. It requires no API credentials. `python -m
agro_notes.field_eval demo` uses a deliberately wrong weight to demonstrate
that a low WER does not hide a critical numeric error; its output is expressly
not model evidence. The harness does not call providers or the production app.

To evaluate future audio, transcribe it through a selected STT adapter, record
the transcript with the case ID, then supply the resulting transcript and
provider-neutral interpretation output. Keep raw recordings outside this
synthetic corpus and follow [the recording protocol](FIELD_RECORDING_PROTOCOL.md).
