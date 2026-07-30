# TL01C Temporal Prompt Calibration

## Executive result

**Calibration decision:** `ITERATE_PROMPT`

Source-aware packet V2 + frozen `tl01c-v1` still improves development resolved exact matches (baseline 0 → candidate 3) and median exact matches (1 → 4), but candidate development/holdout runs retain unsafe over-resolution and source leakage. Decision diagnostic from durable aggregate: `candidate_unsafe_over_resolution=11`.

Durable aggregate (committed): `evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/live/calibration/aggregate.json` with `seals_verified=true`. All cohorts report `manifest_consistency_ok=true`, and every lane validates its exact expected case ID.

PR453 corrections reflected in this report refresh:

1. Independent adversarial cohort **V2** (no few-shot cast/template overlap).
2. Holdout/adversarial seal fields separated and verified against commit ancestry + fixture blobs (`seals_verified` is a READY precondition; skip-seal requires `--fake`).
3. `aggregate.json` regenerated as report source of truth and checked in.
4. Baseline freeze tests use hardcoded instruction + V1 packet hashes.
5. Full TL01C handoff checked in.
6. READY holdout lane coverage uses `exact_occurrence_match.min` / `exact_valid_time_match.min` (repetition-stable; not `.max`).
7. Live runs require a clean worktree; aggregate records `aggregate_build_sha` and `provider_run_repository_shas`.
8. Expected case IDs validated for every baseline/candidate cohort.

Development improvements remain non-independent. Holdout is independent. Adversarial V2 is synthetic and independent of few-shots; not canonical corpus.

## Dependency and execution SHAs

| Item | Value |
| --- | --- |
| PR #452 merge (dependency) | `6eeffe239c582f129f0c6bf167b0f6d6fc51f6c6` |
| Holdout seal commit | `2c3be373fdaf6a713c4cae9c5ab75f9ffad5bc1d` |
| Adversarial V2 seal commit | `cd9463f254f86390bddd43081d1ba3f7de272383` |
| Aggregate `repository_sha` / `aggregate_build_sha` | `bf1df6abac750b76fe81049a8ccdd00256f80df9` |
| `provider_run_repository_shas` | `["bf1df6abac750b76fe81049a8ccdd00256f80df9"]` |
| Calibration id | `temporal-prompt-calibration:d7b86bf990575b07` |

Provider-run revisions match the aggregate-build revision (single clean execution SHA).

## Seal digests (verified)

| Field | SHA-256 / commit |
| --- | --- |
| `holdout_case_sha256` | `046d0e9cafaf27b54e32049e85aded72806976a814f15ad51b08b4a9fa078373` |
| `holdout_base_sha256` | `d24ce74f614973b6eefce9b31c17e398e906ba4413a8138ce26a0fca03abcbe9` |
| `holdout_gold_sha256` | `e8e62418b689eba5b2b19bf2c6b3581376e1dc72e4e15ca5fe9f6a5f9a8d947c` |
| `holdout_seal_commit_sha` | `2c3be373fdaf6a713c4cae9c5ab75f9ffad5bc1d` |
| `adversarial_case_sha256` | `dfdde4e9a6663b993a258e3e6ca23f7079977b0bfdf42dcb8ed11e44c042a8a2` |
| `adversarial_base_sha256` | `759a4272eca13eda6161068760cb73e0322d35ec1a8f0a91d2f12880dcb43418` |
| `adversarial_gold_sha256` | `5faed58e0e1262eda024096df4f843845a87e6d5462d420accaba4b10376ef9d` |
| `adversarial_seal_commit_sha` | `cd9463f254f86390bddd43081d1ba3f7de272383` |

Runner verified: seal commits exist; each is an ancestor of execution `HEAD`; case/base/gold/evidence blobs at the seal commit match executed worktree bytes.

## Frozen baseline

| Field | Value |
| --- | --- |
| Prompt | `tl01b-v1` (immutable) |
| Packet | `tl01b-packet-v1` |
| Prompt SHA-256 (`compute_prompt_sha256`) | `c7606bb6a97f358dc275c5681f0c819e0db84da14d07e8f19ff56b870402bf51` |
| Instructions SHA-256 (hardcoded freeze test) | `c036558b52b8a44e5358fb7f3062dbf9db5b7f5bf86cb7fa2d986e7fddd0ceec` |
| V1 rendered packet SHA-256 (dev case) | `9925e9fb65c124a560cd231707b174139c5911e3f2eaab5d7088b001f80f8430` |
| Evaluator | TL01B `compare_temporal_overlays` unchanged |

## Candidate prompt

| Field | Value |
| --- | --- |
| Prompt | `tl01c-v1` (**frozen**; do not edit) |
| Packet | `tl01c-packet-v1` |
| Prompt SHA-256 | `86bd13a9b53210ca1229d2d9fb506e607715820ecc7510da7607cdc5e7b16df3` |

Decision sequence unchanged. Few-shots remain Arin/Nera/Veyra/Mara family only; adversarial V2 must not reuse that cast.

## Source-aware packet change

Packet V2 adds `source_context` with `semantic_authority="provenance_only"`, derived only via TL01 `derive_assertion_source_time`.

## Development cohort

Case: `tl01b-temporal-shadow-cohort-v1` / candidate mirror `tl01c-temporal-shadow-cohort-v1`.

| Metric | Baseline (`tl01b-v1`) | Candidate (`tl01c-v1`) |
| --- | ---: | ---: |
| Exact matches (min/med/max) | 1 / 1 / 1 | 3 / 4 / 5 |
| Resolved exact (min/med/max) | 0 / 0 / 0 | 3 / 3 / 3 |
| Unsafe over-resolution (total) | 6 | 4 |
| Source→occurrence FP (total) | 0 | 3 |
| Source→valid-time FP (total) | 0 | 1 |
| Min status accuracy | 0.67 | 0.50 |
| Success / failure reps | 3 / 0 | 3 / 0 |

## Holdout cohort

Case: `tl01c-temporal-shadow-holdout-v1` (7 assertions; IDs/evidence disjoint from development).

| Metric | Baseline | Candidate |
| --- | ---: | ---: |
| Exact matches (min/med/max) | 0 / 0 / 0 | 2 / 2 / 2 |
| Resolved exact (min/med/max) | 0 / 0 / 0 | 2 / 2 / 2 |
| Exact occurrence (min/med/max) | 0 / 0 / 0 | 2 / 2 / 2 |
| Exact valid-time (min/med/max) | 0 / 0 / 0 | 0 / 0 / 0 |
| Unsafe over-resolution (total) | 9 | 6 |
| Source→occurrence FP (total) | 0 | 2 |
| Source→valid-time FP (total) | 0 | 6 |
| Min status accuracy | 0.43 | 0.57 |
| Success / failure reps | 3 / 0 | 2 / 1 (grounding) |

Holdout READY lane gate requires `exact_occurrence_match.min >= 1` and `exact_valid_time_match.min >= 1`. This matrix fails the valid-time `.min` gate (0).

## Synthetic adversarial V2 (independent)

Case: `tl01c-temporal-shadow-adversarial-v2`  
Cast: Jorin / Pella / Tovin / Quill Harbor / frost seal / Ash Riders (wholly different from `tl01c-v1` few-shots).  
V1 adversarial retained only as contaminated historical reference.

| Run | Exact | Resolved exact | Unsafe | Src→occ FP | Src→valid FP | Status acc | NA acc |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 01 | 1 | 0 | 1 | 0 | 0 | 0.80 | 1.00 |
| 02 | 1 | 0 | 0 | 0 | 0 | 0.80 | 1.00 |
| 03 | 1 | 0 | 0 | 0 | 0 | 0.80 | 1.00 |

Aggregate: success 3/3; unsafe 1; leakage 0; min status 0.80; exact min/med/max = 1.

## Repetition methodology

- Model: `gpt-5.4-mini`
- Repetitions: 3 per prompt×cohort pair
- Pairs: baseline development, baseline holdout, candidate development, candidate holdout, candidate adversarial V2
- Artifacts: `evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/live/calibration/` (run dirs gitignored; `aggregate.json` tracked)
- Durable rollup: `.../calibration/aggregate.json` (`dmb_temporal_prompt_calibration_v1`)

## Aggregate safety metrics (candidate)

From `aggregate.json` cohort totals:

- Unsafe over-resolutions: 11 across development+holdout+adversarial
- Source→occurrence FP: 5; source→valid-time FP: 7 (split fields present)
- Grounding failures: 1 candidate holdout (phrase paraphrase)
- Evidence/case failures: 0
- Provider failures: 0 (`blocked_count` = 0)
- Manifest consistency: OK on every cohort

## Aggregate quality metrics

Candidate clears development median-exact ≥4 and resolved-exact ≥2 on successful runs, but fails READY: unsafe/leakage remain; holdout valid-time exact `.min` is 0; holdout not-applicable accuracy remains 0.0 on successful holdout runs.

Candidate slice `case_ids`: `tl01c-temporal-shadow-adversarial-v2`, `tl01c-temporal-shadow-cohort-v1`, `tl01c-temporal-shadow-holdout-v1`.

## Per-assertion stability

Assertion stability in aggregate includes classification counts, predicted-status counts, normalized occurrence/valid-time value distributions, and `run_failed` failure counts when applicable.

Dominant candidate development patterns unchanged: resolved event rows often exact; Maelthor-style ambiguous still unsafe; structural road edge still status-mismatched.

Adversarial V2: exact≈1/5 with NA accuracy held; one unsafe over-resolution in run-01.

## Provider metadata

Response IDs live in each run’s `provider-metadata.json` and `run_records` in aggregate. Adversarial V2:

| Run | Response ID |
| --- | --- |
| 01 | `resp_0a6982d06cd3515b006a6b805283c481969281f52a4a20d732` |
| 02 | `resp_0eaac70ebaf892bf006a6b806ff6d08197b2592a8ba3bf1770` |
| 03 | `resp_067bce3eb0b6cbe2006a6b808ae6388193abad84e2c42dc297` |

## Coverage limitations

- Live corpus still thin on sealed source≠occurrence / valid-time-end cases (adversarial V2 covers synthetically, independently of few-shots).
- One candidate holdout repetition failed grounding (visible in aggregate `run_records` / failure manifests).

## Calibration decision

`ITERATE_PROMPT`

Rationale (aggregate diagnostics: `candidate_unsafe_over_resolution=11`):

- Packet/prompt recovers same-source resolved rows on development.
- Safety not READY: unsafe over-resolution and source leakage remain on development/holdout.
- Holdout valid-time lane coverage is not repetition-stable (`exact_valid_time_match.min = 0`).
- Adversarial V2 no longer measures few-shot recall; it shows low exact-match quality with rare unsafe.
- Do **not** edit `tl01c-v1`; next candidate needs a new version id.

## Successor recommendation

Dispatch a bounded **TL01D prompt candidate** (new version id) targeting:

1. stronger not_applicable / ambiguous guards for structure, scene framing, and name/password mentions;
2. explicit anti-copy rules when evidence states a different session than `source_context`;
3. relative/textual preservation for “N years ago” without inventing sessions;
4. repetition-stable valid-time extraction on holdout (`.min >= 1`).

Do not advance to participant roles (TL02) or broader shadow cohort until READY thresholds are met.
