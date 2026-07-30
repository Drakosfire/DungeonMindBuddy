# TL01D Conservative Temporal Decision Gate

## Executive result

**Promotion decision:** `ITERATE_PROMPT`

Frozen prompt-only candidate `tl01d-v1` was evaluated against frozen control `tl01c-v1` on identical packet V2. Evidence is intentionally split:

1. **Observed regression** (prior development / prior holdout / adversarial V2) — may block promotion; **must not** be treated as independent readiness.
2. **Fresh promotion** (development + sealed holdout V2 + adversarial V3) — independent promotion evidence.

Both matrices decide `ITERATE_PROMPT`:

| Matrix | Calibration id | Diagnostics |
| --- | --- | --- |
| Regression | `temporal-prompt-calibration:09a602eaedc00ab0` | `candidate_unsafe_over_resolution=1` |
| Promotion | `temporal-prompt-calibration:099763aa184b8fdc` | `candidate_unsafe_over_resolution=2` |

`tl01d-v1` is **not** `PROMPT_READY_FOR_BROADER_SHADOW`. Thresholds were not weakened.

Relative to control `tl01c-v1`, the conservative gate improves several safety surfaces when comparisons complete (near-zero source leakage on many candidate lanes; no schema-invalid output on prior adversarial V2 candidate runs). Remaining blockers: intermittent `grounding_failure` on `not_applicable` explanations, residual unsafe over-resolution on re-attestation / ambiguous textual history, and incomplete structured session anchoring on source-different cases.

## Evidence separation (non-negotiable)

| Evidence class | Cohorts | Verdict role |
| --- | --- | --- |
| Observed regression | original development; prior holdout; adversarial V2 | may block; **not** independent readiness |
| Fresh promotion | original development; holdout V2; adversarial V3 | independent promotion evidence |

Do not conflate the two aggregates.

## Dependency and execution SHAs

| Item | Value |
| --- | --- |
| PR #453 merge ancestry (TL01C) | `14f7a0d385e1a986cee9edb007f670dc505f148d` |
| Prompt/runner freeze commit | `13b3b85468263bf475e8e06aed0743f7adbabe5f` |
| Fresh cohort seal + live execution commit | `74662e93b89d1506bfc4934ec9c1f80e5cc0564e` |
| Regression seal used for candidate mirrors | `13b3b85468263bf475e8e06aed0743f7adbabe5f` |
| Promotion holdout V2 / adversarial V3 seal | `74662e93b89d1506bfc4934ec9c1f80e5cc0564e` |
| Aggregate `repository_sha` / `aggregate_build_sha` (both) | `74662e93b89d1506bfc4934ec9c1f80e5cc0564e` |
| `provider_run_repository_shas` (both) | `["74662e93b89d1506bfc4934ec9c1f80e5cc0564e"]` |
| Model | `gpt-5.4-mini` |
| Repetitions | 3 per prompt/case pair |
| Control adversarial lane | enabled |

This report/aggregate commit is documentation-and-artifact-only relative to execution `74662e93…`.

## Frozen prompt identities

| Field | Control | Candidate |
| --- | --- | --- |
| Prompt version | `tl01c-v1` | `tl01d-v1` |
| Packet | `tl01c-packet-v1` (unchanged) | same |
| Renderer | `render_temporal_shadow_user_content_v2` | same |
| Prompt SHA-256 | `86bd13a9b53210ca1229d2d9fb506e607715820ecc7510da7607cdc5e7b16df3` | `410a2d1ba1f497dc1dcc4904f04f09b119586205533e925ff3d060e21a600bae` |

Preserved TL01B fingerprints remain unchanged in freeze tests:

- instructions `c036558b…`
- prompt `c7606bb6…`
- V1 packet `9925e9fb…`

Reserved few-shot vocabulary (candidate only): Dessa / Orun / Caldrin / Glass Causeway / Lantern Court / Ivory Ledger.

## Calibration runner generalization

Control/candidate versions are derived from loaded case files before provider calls. Optional `--baseline-adversarial-case` adds the sixth control-adversarial lane; historical five-lane TL01C invocation remains when omitted. Aggregate contract additives: `baseline_prompt_version`, `candidate_prompt_version` (see `Docs/Design/CONTRACT-temporal-prompt-calibration-v2.md`). `compute_calibration_decision` priority and READY thresholds are unchanged.

---

# Part A — Observed regression (non-promotional)

**Artifact:** `evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01d/regression/calibration/aggregate.json`

**Seals verified:** `true`  
**Holdout/adversarial case digests (candidate mirrors):**

| Field | SHA-256 / commit |
| --- | --- |
| `holdout_case_sha256` | `dedb050ebae7618ed949b78d0366468dadf33a4b8505643d30ca70e4f3bbad2b` |
| `holdout_base_sha256` | `d24ce74f614973b6eefce9b31c17e398e906ba4413a8138ce26a0fca03abcbe9` |
| `holdout_gold_sha256` | `e8e62418b689eba5b2b19bf2c6b3581376e1dc72e4e15ca5fe9f6a5f9a8d947c` |
| `holdout_seal_commit_sha` | `13b3b85468263bf475e8e06aed0743f7adbabe5f` |
| `adversarial_case_sha256` | `823602be2f05576be0c0ec43304ef388f999c8ec15ef2b129229e71d180d4530` |
| `adversarial_base_sha256` | `759a4272eca13eda6161068760cb73e0322d35ec1a8f0a91d2f12880dcb43418` |
| `adversarial_gold_sha256` | `5faed58e0e1262eda024096df4f843845a87e6d5462d420accaba4b10376ef9d` |
| `adversarial_seal_commit_sha` | `13b3b85468263bf475e8e06aed0743f7adbabe5f` |

## Regression matrix summary

| Cohort | Control (`tl01c-v1`) | Candidate (`tl01d-v1`) |
| --- | --- | --- |
| Development exact min/med/max | 3 / 4 / 4 | 6 / 6 / 6 |
| Development unsafe total | 5 | 0 |
| Development source leakage total | 5 | 0 |
| Development success/fail | 3 / 0 | 1 / 2 (`grounding_failure`) |
| Prior holdout exact min/med/max | 2 / 2 / 3 | n/a (0 successful compares) |
| Prior holdout unsafe total | 8 | 0 (no completed compares) |
| Prior holdout source leakage total | 11 | 0 |
| Prior holdout success/fail | 3 / 0 | 0 / 3 (`grounding_failure` on Wolf Manor NA explanation) |
| Adv V2 exact min/med/max | 1 / 1 / 1 (successful reps) | 1 / 2 / 2 |
| Adv V2 unsafe total | 0 | 1 |
| Adv V2 source leakage total | 2 | **0** |
| Adv V2 model-output failures | 1 (`invalid_model_output`) | **0** |
| Adv V2 success/fail | 2 / 1 | 3 / 0 |

## §14 known regression expectations

| Expectation | Result |
| --- | --- |
| Same-session events remain exact (when compare completes) | Pass on development run-02 (6/6 exact) |
| Exact valid starts do not regress | Pass on development run-02 (Lysandra lead exact) |
| Wolf Manor containment always `not_applicable` | **Blocked:** all 3 prior-holdout candidate reps failed grounding before compare (`not_applicable annotation requires a nonblank explanation`) |
| Copper and Quartz scene framing always `not_applicable` | Pass on development run-02; 2/3 development reps failed grounding on the same NA explanation rule |
| Sorin Holdrom always `ambiguous` with null extents | **Blocked** by prior-holdout grounding failures (no candidate overlay assembled) |
| Professor historical time receives no invented anchor | **Blocked** by prior-holdout grounding failures |
| Prior adversarial V2 produces no schema-invalid output | **Pass** (candidate: 0 `invalid_model_output`; control still had 1) |
| Source-different cases do not copy source time | **Pass** on candidate adv V2 (`source_*_false_positives=0`) |
| Valid-time end emitted in valid-time lane | Pass on adv V2 runs 02–03 (Pella relinquish exact with session end); run-01 used textual end (`wrong_temporal_value`) |
| Re-attestation does not invent a start | Pass on adv V2 (Tovin re-attest exact `not_applicable` all 3 reps) |

**Regression blocks promotion** via aggregate `candidate_unsafe_over_resolution=1` (adv V2 run-01 resolved ambiguous textual history instead of leaving it ambiguous) and via incomplete prior-holdout compare coverage from grounding failures.

---

# Part B — Fresh independent promotion

**Artifact:** `evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01d/promotion/calibration/aggregate.json`

**Seals verified:** `true`

| Field | SHA-256 / commit |
| --- | --- |
| `holdout_case_sha256` | `0aec328e97c8b2d68ca20bc3bed9f2c5290fb05c550842a3743e39fe99f22765` |
| `holdout_base_sha256` | `71b2a934b1a497c14fbda8bfec7e63341e2f37eaf5cbc27de3111827561c25d6` |
| `holdout_gold_sha256` | `381ce74a747811b6970d41cc0ce61e026c6bada898f77e0bcf6f45f6001acfdd` |
| `holdout_seal_commit_sha` | `74662e93b89d1506bfc4934ec9c1f80e5cc0564e` |
| `adversarial_case_sha256` | `c66f61467ca1106f041272a395ed919564f42b7ca6f1084530609e90e0004384` |
| `adversarial_base_sha256` | `a28ec6223f48ea28a256ded406187eb28e9b7e22f330c8eff6b039134c448f58` |
| `adversarial_gold_sha256` | `75a8249c62319858dea5a1713ebf3bbd8e51bad43a2c4b58bdeff37ca9fcca28` |
| `adversarial_seal_commit_sha` | `74662e93b89d1506bfc4934ec9c1f80e5cc0564e` |

## Fresh cohorts authored

### Holdout V2 (canonical)

Path: `evals/graph_memory_layer/examples/temporal_shadow_holdout_v2/`  
Paired cases: `tl01d-temporal-shadow-holdout-v2-control` / `…-candidate`  
Sessions preferred outside prior holdout (8/11/14/18): **10, 15, 19, 20, 21**.

| # | Category | Gold |
| --- | --- | --- |
| 1 | Same-source event (ale elemental) | resolved occurrence session-10 |
| 2 | Same-source event (Thunderwave) | resolved occurrence session-20 |
| 3 | Valid-time start (Lysandra command) | resolved valid start session-15 |
| 4 | Structural (Mirathorn walls) | not_applicable |
| 5 | Scene framing (Mossford Inn) | not_applicable |
| 6 | Ambiguous identity (hooded figure) | ambiguous + null extents |
| 7 | Textual historical (“in the past”) | textual occurrence |
| 8 | Re-attestation (thanks again) | not_applicable |

**Canonical coverage gaps (documented, not fabricated):** persistent valid-time end and explicit source≠occurrence/valid-start were not safely available in unused sessions; covered only in adversarial V3.

### Adversarial V3 (synthetic)

Path: `evals/graph_memory_layer/examples/temporal_shadow_adversarial_v3/`  
Cast: **Nerys / Bram / Vell / Saltspan Quay / ember lock / Pale Wardens / Corin Vale** (disjoint from TL01D few-shots and adversarial V2).

Covers all eight required patterns, including valid-time end and source-different occurrence/valid-start.

## Promotion matrix summary

| Cohort | Control (`tl01c-v1`) | Candidate (`tl01d-v1`) |
| --- | --- | --- |
| Development exact min/med/max | 3 / 4 / 4 | 6 / 6 / 6 |
| Development unsafe total | 6 | 0 |
| Development source leakage total | 6 | 0 |
| Development success/fail | 3 / 0 | 2 / 1 |
| Holdout V2 exact min/med/max | 1 / 4 / 4 | 5 / 5 / 5 |
| Holdout V2 occurrence min/med/max | 1 / 3 / 3 | 2 / 2 / 2 |
| Holdout V2 valid-time min/med/max | 0 / 1 / 1 | 1 / 1 / 1 |
| Holdout V2 unsafe total | 12 | **2** |
| Holdout V2 source→occ FP total | 4 | **2** |
| Holdout V2 source→valid FP total | 3 | **0** |
| Holdout V2 success/fail | 3 / 0 | 2 / 1 |
| Adv V3 exact min/med/max | 4 / 4 / 4 | 5 / 5 / 5 |
| Adv V3 unsafe total | 2 | 0 |
| Adv V3 source leakage total | 3 | **0** |
| Adv V3 success/fail | 2 / 1 | 1 / 2 |

## Promotion blockers

1. **Unsafe over-resolution (holdout V2):** re-attestation “thanks again” predicted `resolved` instead of `not_applicable` on both successful candidate holdout reps → aggregate `candidate_unsafe_over_resolution=2`.
2. **Source→occurrence leakage (holdout V2):** 2 false positives across successful candidate holdout reps (still far below control’s 4, but READY requires 0).
3. **Grounding failures:** intermittent blank/insufficient `not_applicable` explanations (development, holdout, adversarial) prevent full compare coverage.
4. **Status mismatches on holdout V2:** textual historical under-resolved to `not_applicable`; ambiguous hooded figure under-resolved to `not_applicable`.
5. **Adv V3 structured session anchors:** candidate often keeps textual session phrases instead of structured `session-*` points (`wrong_temporal_value`), even when status is correct and source time is not copied.

READY gates therefore fail. Decision remains `ITERATE_PROMPT`.

## Lane stability notes

- Candidate development, when it completes, is highly stable (exact 6/6, unsafe 0, leakage 0).
- Candidate holdout V2 stable on the five exact rows (two events, valid start, structural, scene) across successful reps; unstable on re-attestation and ambiguity/historical status.
- Candidate adv V3 eliminates control’s source leakage and schema-shaped validity issues on completed reps, but grounding failures reduce repetition coverage.

---

# Provider response IDs

All post-provider typed failures preserve `provider_response_id` on `failure-manifest.json`.

## Regression (selected)

| Lane | Response id | Outcome |
| --- | --- | --- |
| baseline/adversarial/run-02 | `resp_028c6f101281a8e4006a6ba45688788196b1d9a7dbbf442086` | `invalid_model_output` |
| candidate/holdout/run-01 | `resp_00065b220a40e745006a6ba43f2b508197bd2cb1dea3d73623` | `grounding_failure` |
| candidate/holdout/run-02 | `resp_00f461edfce86666006a6ba461e3748194b4d20ba63854239f` | `grounding_failure` |
| candidate/holdout/run-03 | `resp_0d34efb21f3cf043006a6ba485c7f08197a8e681454a37dad2` | `grounding_failure` |
| candidate/adversarial/run-01 | `resp_0fa8a95e04df0d7d006a6ba444dcc48193b5389248a9935ee9` | compared (unsafe=1) |
| candidate/development/run-02 | `resp_0ac82495d71e2a85006a6ba45c96748194b03d9bd4101b728a` | compared (6/6 exact) |

Full set under `…/tl01d/regression/**/provider-metadata.json` and failure manifests.

## Promotion (selected)

| Lane | Response id | Outcome |
| --- | --- | --- |
| candidate/holdout/run-02 | `resp_0b48c11583e352b9006a6ba4daecac8190831f271f3a8c0776` | compared (unsafe on re-attest) |
| candidate/holdout/run-03 | `resp_0fdec7df4dbb2a2d006a6ba5017ca081938a4c4ef9cadb6de3` | compared (unsafe on re-attest) |
| candidate/adversarial/run-03 | `resp_02d1fae23e34073c006a6ba507ad8c8196aeb920bb831ec9e0` | compared |
| candidate/adversarial/run-01 | `resp_00c524c926fd94b8006a6ba4bc66fc8195af3f41229d4ea87b` | `grounding_failure` |
| candidate/development/run-02 | `resp_08a6659ccb770836006a6ba4d58b5c8197aa90aff51a9d0e73` | compared (6/6 exact) |

## Scope confirmation

Allowlisted changes only for this workstream: prompt registry + tests, calibration identity generalization + contract doc, regression case mirrors, fresh holdout V2 / adversarial V3 fixtures, bounded aggregates, this report, handoff. No TL00/TL01 kernel, packet V2, comparator, graph state, or prior TL01C aggregate edits.

## Next iterate targets (out of scope for this PR)

1. Require nonblank diagnostics/explanations for every `not_applicable` few-shot and instruction path (reduce grounding failures).
2. Strengthen re-attestation → `not_applicable` without inventing occurrence.
3. Keep ambiguous textual history ambiguous (null extents); do not “helpfully” resolve to textual points when gold is ambiguous.
4. Prefer structured session anchors when the text explicitly names `Session N`, without copying provenance source session.
