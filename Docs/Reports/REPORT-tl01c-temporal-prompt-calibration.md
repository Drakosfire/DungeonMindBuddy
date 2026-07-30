# TL01C Temporal Prompt Calibration

## Executive result

**Calibration decision:** `ITERATE_PROMPT`

Source-aware packet V2 + frozen `tl01c-v1` still improves development resolved exact matches (baseline 0 → candidate 3) and median exact matches (1 → 4). Aggregate diagnostic: `candidate_unsafe_over_resolution=12`. Schema-invalid adversarial responses (`invalid_model_output`: ambiguous + extents) are counted as `total_model_output_failures` and route to `ITERATE_PROMPT`, not `BLOCKED_BY_CONTRACT` — the frozen contract already represents ambiguous-with-null-extents.

Durable aggregate (committed): `evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/live/calibration/aggregate.json` with `seals_verified=true`. All cohorts report `manifest_consistency_ok=true`, and every lane validates its exact expected case ID.

Evaluator-integrity hardening reflected in this report refresh:

1. `invalid_model_output` / `target_set_mismatch` → `total_model_output_failures` → `ITERATE_PROMPT`.
2. `BLOCKED_BY_CONTRACT` reserved for true contract gaps (`overlay_assembly_failed`, `unsupported_prompt_version`).
3. Post-provider typed failures publish `failure-manifest.json` with `provider_response_id` (no success artifacts).
4. Live cleanliness still uses `git status --porcelain` without `-uno`; development/baseline fixtures verified against execution-commit blobs.

Development improvements remain non-independent. Holdout is independent. Adversarial V2 is synthetic and independent of few-shots; not canonical corpus.

## Dependency and execution SHAs

| Item | Value |
| --- | --- |
| PR #452 merge (dependency) | `6eeffe239c582f129f0c6bf167b0f6d6fc51f6c6` |
| Implementation commit (live matrix) | `6d0d3ce6b2eefec63f77cf2aead409973220f835` |
| Holdout seal commit | `2c3be373fdaf6a713c4cae9c5ab75f9ffad5bc1d` |
| Adversarial V2 seal commit | `cd9463f254f86390bddd43081d1ba3f7de272383` |
| Aggregate `repository_sha` / `aggregate_build_sha` | `6d0d3ce6b2eefec63f77cf2aead409973220f835` |
| `provider_run_repository_shas` | `["6d0d3ce6b2eefec63f77cf2aead409973220f835"]` |
| Calibration id | `temporal-prompt-calibration:45e67fb4b8175da2` |

Provider-run revisions match the aggregate-build revision (single clean execution SHA). This report/aggregate commit is documentation-only relative to that implementation commit.

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

Runner verified: seal commits exist; each is an ancestor of execution `HEAD`; case/base/gold/evidence blobs at the seal commit match executed worktree bytes. Development and baseline-mirror fixtures match blobs at the execution commit.

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
| Exact matches (min/med/max) | 1 / 1 / 1 | 4 / 4 / 4 |
| Resolved exact (min/med/max) | 0 / 0 / 0 | 3 / 3 / 3 |
| Unsafe over-resolution (total) | 3 | 4 |
| Source→occurrence FP (total) | 0 | 3 |
| Source→valid-time FP (total) | 0 | 1 |
| Min status accuracy | 0.67 | 0.67 |
| Success / failure reps | 2 / 1 (grounding) | 3 / 0 |

## Holdout cohort

Case: `tl01c-temporal-shadow-holdout-v1` (7 assertions; IDs/evidence disjoint from development).

| Metric | Baseline | Candidate |
| --- | ---: | ---: |
| Exact matches (min/med/max) | 0 / 0 / 0 | 2 / 3 / 3 |
| Resolved exact (min/med/max) | 0 / 0 / 0 | 2 / 2 / 3 |
| Exact occurrence (min/med/max) | 0 / 0 / 0 | 2 / 2 / 2 |
| Exact valid-time (min/med/max) | 0 / 0 / 0 | 0 / 0 / 1 |
| Unsafe over-resolution (total) | 9 | 8 |
| Source→occurrence FP (total) | 0 | 6 |
| Source→valid-time FP (total) | 0 | 4 |
| Min status accuracy | 0.57 | 0.57 |
| Success / failure reps | 3 / 0 | 3 / 0 |

Holdout READY lane gate requires `exact_occurrence_match.min >= 1` and `exact_valid_time_match.min >= 1`. This matrix fails the valid-time `.min` gate (0).

## Synthetic adversarial V2 (independent)

Case: `tl01c-temporal-shadow-adversarial-v2`  
Cast: Jorin / Pella / Tovin / Quill Harbor / frost seal / Ash Riders (wholly different from `tl01c-v1` few-shots).  
V1 adversarial retained only as contaminated historical reference.

| Run | Exact | Resolved exact | Unsafe | Src→occ FP | Status acc | NA acc | Notes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 01 | — | — | — | — | — | — | `invalid_model_output` (ambiguous + extents); response id preserved |
| 02 | — | — | — | — | — | — | `invalid_model_output` (ambiguous + extents); response id preserved |
| 03 | 1 | 0 | 0 | 0 | 0.80 | 1.00 |  |

Aggregate: success 1/3; `total_model_output_failures=2`, `total_invalid_payloads=0` → model noncompliance contributes to `ITERATE_PROMPT`, not contract block.

## Repetition methodology

- Model: `gpt-5.4-mini`
- Repetitions: 3 per prompt×cohort pair
- Pairs: baseline development, baseline holdout, candidate development, candidate holdout, candidate adversarial V2
- Artifacts: `evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/live/calibration/` (run dirs gitignored; `aggregate.json` tracked)
- Durable rollup: `.../calibration/aggregate.json` (`dmb_temporal_prompt_calibration_v1`)

## Aggregate safety metrics (candidate)

From `aggregate.json` cohort totals:

- Model-output failures: 2 (adversarial run-01/02) → contribute to `ITERATE_PROMPT`
- Invalid payloads (true contract): 0
- Unsafe over-resolutions: 12 across development+holdout (first diagnostic match)
- Source→occurrence FP: 9; source→valid-time FP: 5 (leakage total 14)
- Grounding failures: 0 candidate (baseline development had 1)
- Evidence/case failures: 0
- Provider failures: 0
- Manifest consistency: OK on every cohort

## Aggregate quality metrics

Candidate clears development median-exact ≥4 and resolved-exact ≥2 on successful runs, but does not reach READY: unsafe over-resolution short-circuits first; source leakage and holdout valid-time `.min=0` remain independently blocking.

Candidate slice `case_ids`: `tl01c-temporal-shadow-adversarial-v2`, `tl01c-temporal-shadow-cohort-v1`, `tl01c-temporal-shadow-holdout-v1`.

## Per-assertion stability

Assertion stability in aggregate includes classification counts, predicted-status counts, normalized occurrence/valid-time value distributions, and `run_failed` failure counts when applicable.

## Provider metadata

Response IDs live in each run’s `provider-metadata.json`, typed `failure-manifest.json` (post-provider failures), and `run_records` in aggregate. Adversarial V2:

| Run | Outcome | Response ID |
| --- | --- | --- |
| 01 | `invalid_model_output` | `resp_088804419dcb994a006a6b8d1d0880819695b055d326f05ef1` |
| 02 | `invalid_model_output` | `resp_0e20e747f8ce41d8006a6b8d39995c81938c1ee7738723aabb` |
| 03 | success | `resp_034724b5bbaafc31006a6b8d55e6908194adbd425ba5dba9ee` |

## Coverage limitations

- Live corpus still thin on sealed source≠occurrence / valid-time-end cases (adversarial V2 covers synthetically, independently of few-shots).
- Two adversarial repetitions failed model-output validation (ambiguous + extents) while preserving provider response IDs.

## Calibration decision

`ITERATE_PROMPT`

Rationale (aggregate diagnostics: `candidate_unsafe_over_resolution=12`):

- Unsafe over-resolution is the highest-priority blocking safety finding.
- Source leakage and zero exact holdout valid-time coverage (`.min=0`) independently prevent READY.
- Adversarial `invalid_model_output` (ambiguous + extents) is model/prompt noncompliance against a representable contract → `ITERATE_PROMPT`, not `BLOCKED_BY_CONTRACT`.
- Do **not** edit `tl01c-v1`; next candidate needs a new version id (and should reinforce ambiguous-without-extents).

## Successor recommendation

Dispatch a bounded **TL01D prompt candidate** (new version id) targeting:

1. stricter ambiguous / not_applicable guards (no extents when status is ambiguous);
2. stronger not_applicable guards for structure, scene framing, and name/password mentions;
3. explicit anti-copy rules when evidence states a different session than `source_context`;
4. repetition-stable valid-time extraction on holdout (`.min >= 1`).

Do not advance to participant roles (TL02) or broader shadow cohort until READY thresholds are met.
