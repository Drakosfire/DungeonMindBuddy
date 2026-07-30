# TL01C Temporal Prompt Calibration

## Executive result

**Calibration decision:** `ITERATE_PROMPT`

Source-aware packet V2 + `tl01c-v1` materially improved development resolved exact matches (0 → 3) and median exact matches (1 → 4), but candidate runs still produce unsafe over-resolutions, source→occurrence leakage on some rows, and holdout not-applicable / ambiguous failures. One candidate holdout repetition failed phrase grounding (paraphrase, not truncated spans).

Development improvements are **not** independent evidence. Holdout results are independent. Synthetic adversarial results are **not** canonical-corpus results.

## Dependency and execution SHAs

| Item | SHA |
| --- | --- |
| PR #452 merge (dependency) | `6eeffe239c582f129f0c6bf167b0f6d6fc51f6c6` |
| Holdout seal commit | `2c3be373fdaf6a713c4cae9c5ab75f9ffad5bc1d` |
| Live execution commit (`aggregate.repository_sha`) | `8880a18b9a031da314171ccb393eb9b5bf6503f3` |

## Frozen baseline

| Field | Value |
| --- | --- |
| Prompt | `tl01b-v1` |
| Packet | `tl01b-packet-v1` |
| Prompt SHA-256 | `c7606bb6a97f358dc275c5681f0c819e0db84da14d07e8f19ff56b870402bf51` |
| Evaluator | TL01B `compare_temporal_overlays` unchanged |

## Candidate prompt

| Field | Value |
| --- | --- |
| Prompt | `tl01c-v1` |
| Packet | `tl01c-packet-v1` |
| Prompt SHA-256 | `86bd13a9b53210ca1229d2d9fb506e607715820ecc7510da7607cdc5e7b16df3` |

Decision sequence: assertion proposition → temporal lane → provenance-only source reuse rules → conservative normalization → grounding. Six synthetic few-shots (Arin/Nera/Veyra/Mara/East Road/Vale/Tor/Red Company) only.

## Source-aware packet change

Packet V2 adds:

```json
"source_context": {
  "source_time": { "... TL01 derive_assertion_source_time ..." },
  "derivation": "evidence_session|legacy_session_scope|existing_v1_source_time|none",
  "semantic_authority": "provenance_only"
}
```

Derived exclusively through `derive_assertion_source_time`. No session parsing from evidence IDs or filenames. Unsafe/skipped derivation fails before provider call.

## Development cohort

Case: `tl01b-temporal-shadow-cohort-v1` (frozen base/gold/evidence). Candidate case selects `prompt_version=tl01c-v1` only.

| Metric | Baseline (`tl01b-v1`) | Candidate (`tl01c-v1`) |
| --- | ---: | ---: |
| Exact matches (runs) | 1, 1 (run-03 grounding fail) | 3, 4, 4 |
| Median exact | 1 | 4 |
| Resolved exact | 0, 0 | 3, 3, 3 |
| Unsafe over-resolution | 1, 2 | 1, 1, 2 |
| Source→occurrence FP | 0, 0 | 1, 1, 2 |
| Source→valid-time FP | 0, 0 | 0, 0, 0 |
| Status accuracy | 0.67, 0.67 | 0.50, 0.67, 0.67 |
| Not-applicable accuracy | 0.50, 0.50 | 0.00, 0.50, 0.50 |

Best candidate development run (run-02): 4/6 exact including all three resolved gold rows; Maelthor still `unsafe_over_resolution`; road edge still status mismatch (`unresolved` vs `not_applicable`).

## Holdout sealing

| Field | Value |
| --- | --- |
| Case ID | `tl01c-temporal-shadow-holdout-v1` |
| Assertions | 7 (no overlap with development IDs/evidence) |
| Categories | same-source event ×2, valid-time start, structural, scene framing, ambiguous name, relative/incomplete historical |
| Seal SHA | `2c3be373fdaf6a713c4cae9c5ab75f9ffad5bc1d` |
| Prompt frozen before holdout execution | yes |

## Canonical holdout

| Metric | Baseline | Candidate |
| --- | ---: | ---: |
| Exact matches | 0, 0, 0 | 3, 2 (run-03 grounding fail) |
| Resolved exact | 0, 0, 0 | 3, 2 |
| Unsafe over-resolution | 3, 3, 3 | 3, 3 |
| Source→occurrence FP | 0, 0, 0 | 1, 1 |
| Source→valid-time FP | 0, 0, 0 | 2, 3 |
| Min status accuracy | 0.57 | 0.57 |
| Not-applicable accuracy | 0.00 | 0.00 |

Candidate recovers occurrence/valid-time rows that baseline never hits, but still resolves structural/scene/ambiguous rows unsafely and leaks source time into valid-time on some runs.

## Synthetic adversarial supplement

Case: `tl01c-temporal-shadow-adversarial-v1` (candidate only; not merged into canonical metrics).

| Run | Exact | Resolved exact | Unsafe | Src→occ FP | Status acc | NA acc |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 01 | 1 | 0 | 1 | 1 | 0.80 | 1.00 |
| 02 | 1 | 0 | 1 | 0 | 0.80 | 1.00 |
| 03 | 1 | 0 | 1 | 1 | 0.80 | 1.00 |

Source-different and valid-time-end rows remain imperfect; re-attestation NA accuracy held at 1.0 across adversarial runs.

## Repetition methodology

- Model: `gpt-5.4-mini`
- Repetitions: 3 per prompt×cohort pair
- Pairs: baseline development, baseline holdout, candidate development, candidate holdout, candidate adversarial
- Artifacts: `evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/live/calibration/` (gitignored)

## Aggregate safety metrics

Across successful **candidate** comparisons:

- Unsafe over-resolutions: present in every successful candidate cohort run
- Source→occurrence false positives: present on development, holdout, and adversarial
- Source→valid-time false positives: present on holdout
- Grounding failures: 1 candidate holdout run (paraphrased phrase `discovers` vs snippet `discovering`)
- Baseline development also had 1 grounding failure (overlong non-verbatim phrase)

## Aggregate quality metrics

See development/holdout tables above. Candidate clears the development median-exact ≥4 and resolved-exact ≥2 bars on successful runs, but fails READY because unsafe/leakage/NA accuracy requirements are unmet.

## Per-assertion stability

### Candidate development

| Assertion | Dominant classifications |
| --- | --- |
| Stafl revives | exact_match (after packet V2) with occasional wrong_value on baseline |
| Lysandra lead | exact_match on candidate |
| Hybrid destroyed | exact_match on candidate |
| Party scene | mixed exact / unsafe |
| Road edge | status_mismatch / unresolved vs NA |
| Maelthor password | unsafe_over_resolution (never safely ambiguous on candidate) |

### Candidate holdout

Occurrence events (portal, Mother) often exact; professor relative row wrong_value; structural/scene/ambiguous frequently unsafe_over_resolution.

## Normalized semantic diffs

Example (holdout professor relative — `wrong_temporal_value`):

```json
{
  "gold": {"occurrence_time": {"kind": "textual", "raw_expression": "left about 30 years ago"}},
  "predicted": {"occurrence_time": {"kind": "textual", "raw_expression": "about 30 years ago"}}
}
```

Example (adversarial source≠occurrence leakage elsewhere in the cohort): source_context `session-20` with gold occurrence `session-4`; some runs copy `session-20` into occurrence/valid time (counted in source-leakage metrics).

## Provider metadata

All response IDs recorded under each run’s `provider-metadata.json`. Representative:

| Lane | Cohort | Run | Response ID |
| --- | --- | --- | --- |
| baseline | development | 01 | `resp_05b74b6c629b737b006a6acd1c4d7081908c17d9b7cfcc5015` |
| candidate | development | 02 | `resp_013698df522b55da006a6acd852aa48190b9683948da52d521` |
| candidate | holdout | 01 | `resp_0a295c72a0c9d32f006a6acd2bea408195aa6d8d4c2fb86d2d` |
| candidate | adversarial | 01 | `resp_0f649c9c6f0cdafd006a6acd328bd48197ba5a30f7726849e7` |

## Coverage limitations

- Live corpus still lacks sealed source≠occurrence and valid-time-end cases (synthetic adversarial only).
- Missing live categories remain missing live categories.
- One baseline development and one candidate holdout repetition failed grounding (visible; not hidden).

## Calibration decision

`ITERATE_PROMPT`

Rationale:

- Packet/prompt representation is sufficient to recover same-source resolved rows on development.
- Safety is not yet READY: unsafe over-resolution and source leakage remain across candidate runs.
- Ambiguous mention (Maelthor-style) is still resolved unsafely.
- Holdout not-applicable accuracy is 0.0.
- Do **not** edit `tl01c-v1` after holdout observation; next candidate needs a new version id.

## Successor recommendation

Dispatch a bounded **TL01D prompt candidate** (new version id) targeting:

1. stronger not_applicable / ambiguous guards for structure, scene framing, and name/password mentions;
2. explicit anti-copy rules when evidence states a different session than `source_context`;
3. relative/textual preservation for “N years ago” without inventing sessions.

Do not advance to participant roles (TL02) or broader shadow cohort until READY thresholds are met.
