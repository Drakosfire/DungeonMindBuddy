# TL01D Conservative Temporal Decision Gate

## Executive result

**Promotion decision:** `ITERATE_PROMPT`

Frozen prompt-only candidate `tl01d-v1` was evaluated against frozen control `tl01c-v1` on identical packet V2. Evidence is intentionally split:

1. **Observed regression** (prior development / prior holdout / adversarial V2) — may block promotion; **must not** be treated as independent readiness.
2. **Fresh promotion** (development + sealed holdout V3 + adversarial V3) — independent promotion evidence.

Holdout V2 was **retired as invalid promotion evidence** after review: two gold rows misclassified event propositions as re-attestation / identity-ambiguous. This report uses holdout V3 only for promotion.

Both matrices decide `ITERATE_PROMPT`:

| Matrix | Calibration id | `experiment_role` | Diagnostics |
| --- | --- | --- | --- |
| Regression | `temporal-prompt-calibration:5e3683a8233ca4c6` | `observed_regression` | `candidate_unsafe_over_resolution=1` |
| Promotion | `temporal-prompt-calibration:a6b466cc6cb6a4a2` | `promotion` | `candidate_unsafe_over_resolution=1` |

`tl01d-v1` is **not** `PROMPT_READY_FOR_BROADER_SHADOW`. Thresholds were not weakened.

### Corrected root-cause note (post holdout V2 retirement)

The prior promotion headline (`candidate_unsafe_over_resolution=2` on holdout V2) was an artifact of incorrect gold (eventive “thanks again” marked re-attestation; Session-10 observation marked ambiguous for identity reasons). Those rows must not drive successor-prompt design.

After holdout V3, the remaining candidate holdout unsafe is a **genuine** re-attestation miss:

- gold `not_applicable` for `assertion:20341a3812cd8590` (`is_mayor_of` / “As mayor, Orik Tane…”)
- candidate predicted `resolved` on holdout run-03 → classified `unsafe_over_resolution` (+ source-to-valid-time FP)

Independent blockers also remain: recurrent `grounding_failure` (`not_applicable annotation requires a nonblank explanation`) on candidate adversarial/development/holdout runs, and incomplete compare coverage when those failures discard runs.

## Evidence separation (non-negotiable)

| Evidence class | Cohorts | Verdict role |
| --- | --- | --- |
| Observed regression | original development; prior holdout; adversarial V2 | may block; **not** independent readiness |
| Fresh promotion | original development; **holdout V3**; adversarial V3 | independent promotion evidence |
| Retired | holdout V2 | invalid; do not use |

Do not conflate the two aggregates. Aggregate identity now includes `experiment_role` and the sorted run matrix (see below).

## Dependency and execution SHAs

| Item | Value |
| --- | --- |
| PR #453 merge ancestry (TL01C) | `14f7a0d385e1a986cee9edb007f670dc505f148d` |
| Prompt freeze commit (`tl01d-v1`) | `13b3b85468263bf475e8e06aed0743f7adbabe5f` |
| Adversarial V3 seal | `74662e93b89d1506bfc4934ec9c1f80e5cc0564e` |
| Holdout V3 seal + identity fix + live execution | `3561fda227c48c22b8ed1f94c0d8c481cc095405` |
| Regression prior-holdout / adv V2 seal | `13b3b85468263bf475e8e06aed0743f7adbabe5f` |
| Aggregate `repository_sha` / `aggregate_build_sha` (both) | `3561fda227c48c22b8ed1f94c0d8c481cc095405` |
| `provider_run_repository_shas` (both) | `["3561fda227c48c22b8ed1f94c0d8c481cc095405"]` |
| Model | `gpt-5.4-mini` |
| Repetitions | 3 per prompt/case pair |
| Control adversarial lane | enabled (changes `calibration_id`) |

This report/aggregate commit is documentation-and-artifact-only relative to execution `3561fda…`.

## Frozen prompt identities

| Field | Control | Candidate |
| --- | --- | --- |
| Prompt version | `tl01c-v1` | `tl01d-v1` |
| Packet | `tl01c-packet-v1` (unchanged) | same |
| Renderer | `render_temporal_shadow_user_content_v2` | same |
| Prompt SHA-256 | `86bd13a9b53210ca1229d2d9fb506e607715820ecc7510da7607cdc5e7b16df3` | `410a2d1ba1f497dc1dcc4904f04f09b119586205533e925ff3d060e21a600bae` |

`tl01d-v1` remains frozen; only cohorts/runner identity/docs changed after the freeze.

## Calibration identity (P1 fix)

`calibration_id` now hashes:

- prompt versions + SHAs
- holdout/adversarial seal digests
- model, repetitions, repo / provider-run SHAs
- **`experiment_role`** (`observed_regression` | `promotion`)
- **`control_adversarial_enabled`** + **`control_adversarial_case_id`**
- **sorted `run_matrix`** of `{prompt_lane, cohort, case_id}`

Five-lane vs six-lane matrices at the same commit therefore cannot share an id. Regression vs promotion cannot share an id. Contract: `Docs/Design/CONTRACT-temporal-prompt-calibration-v2.md`.

---

# Part A — Observed regression (non-promotional)

**Artifact:** `evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01d/regression/calibration/aggregate.json`

| Field | Value |
| --- | --- |
| `experiment_role` | `observed_regression` |
| `calibration_id` | `temporal-prompt-calibration:5e3683a8233ca4c6` |
| Seals verified | `true` |
| Decision | `ITERATE_PROMPT` |
| Diagnostics | `candidate_unsafe_over_resolution=1` |
| Control adversarial | `tl01c-temporal-shadow-adversarial-v2` |

### Candidate slice (successful runs)

| Cohort | Success / fail | Notes |
| --- | --- | --- |
| development | completes with strong exactness when grounded | intermittent grounding failures still discard some reps |
| prior holdout | mixed | grounding / NA explanation failures reduce compare coverage |
| adversarial V2 | unsafe residual | `candidate_unsafe_over_resolution=1` on textual/ambiguous history over-resolution |

Regression still **blocks promotion** and remains non-promotional evidence.

---

# Part B — Fresh independent promotion

**Artifact:** `evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01d/promotion/calibration/aggregate.json`

| Field | Value |
| --- | --- |
| `experiment_role` | `promotion` |
| `calibration_id` | `temporal-prompt-calibration:a6b466cc6cb6a4a2` |
| Holdout seal | `3561fda…` (holdout V3) |
| Adversarial seal | `74662e93…` (adversarial V3) |
| Seals verified | `true` |
| Decision | `ITERATE_PROMPT` |
| Diagnostics | `candidate_unsafe_over_resolution=1` |
| Control adversarial | `tl01d-temporal-shadow-adversarial-v3-control` |

## Holdout V2 retirement

Path `evals/graph_memory_layer/examples/temporal_shadow_holdout_v2/` is retained as a sealed historical artifact and marked **RETIRED** in its README. Invalid gold:

1. `assertion:b042d6ef548a1ce0` (`thanks`) — bounded event, not persistent-state re-attestation.
2. `assertion:1f8580500f4fa97c` (`observed_watching`) — Session-10 observation event; identity uncertainty ≠ temporal ambiguity.
3. Audit: Lysandra “command” used “reminds … in command” evidence while labeled as a valid-time start.

## Holdout V3 (replacement)

Path: `evals/graph_memory_layer/examples/temporal_shadow_holdout_v3/`  
Paired cases: `tl01d-temporal-shadow-holdout-v3-control` / `…-candidate`

| # | Category | Gold |
| --- | --- | --- |
| 1 | Same-source event (Dust Devil) | resolved occurrence session-16 |
| 2 | Same-source event (Hunger of Hadar) | resolved occurrence session-23 |
| 3 | Structural (Glimmering Globe / lake) | not_applicable |
| 4 | Scene framing (back to the Inn) | not_applicable |
| 5 | Ambiguous mention (Seraphine roster) | ambiguous + null extents |
| 6 | Relative/incomplete historical | textual occurrence `not long before the group arrived` |
| 7 | Persistent-state re-attestation (Orik is mayor) | not_applicable |

Canonical gaps (valid-time start/end; source≠fiction time) remain covered only in adversarial V3.

### Candidate holdout V3 (successful compare: run-03)

| Metric | Value |
| --- | --- |
| Exact matches | 6 / 7 |
| Resolved exact | 3 / 3 |
| Status accuracy | ~0.857 |
| NA accuracy | ~0.667 |
| Unsafe over-resolution | 1 (`is_mayor_of` re-attestation → resolved) |
| Source-to-valid-time FP | 1 (same row) |
| Ambiguous roster mention | correct (`ambiguous`, null extents) |

Runs 01–02 failed closed with `grounding_failure` (blank NA explanations), so READY thresholds cannot be met from this matrix.

### Candidate adversarial V3

All three repetitions: `grounding_failure` on structural NA (`assertion:6906453d55f7de4f`) — `not_applicable annotation requires a nonblank explanation`. No successful adversarial compares for the candidate in this rerun.

### Control contrast (promotion matrix)

Control `tl01c-v1` still shows substantial unsafe / source-leakage totals on development and holdout V3 successful runs. Candidate is safer when grounded, but grounding failures and the mayor re-attestation miss independently prevent readiness.

---

# Decision and successor guidance

**Decision:** `ITERATE_PROMPT` — do not promote `tl01d-v1` to broader shadow.

Design the successor from **holdout V3 + adversarial V3** failures, not from retired holdout V2:

1. Strengthen persistent-state re-attestation (mayor / membership restated without start/end) → keep `not_applicable`.
2. Require nonblank diagnostics/explanations for every `not_applicable` prediction (grounding_failure cluster).
3. Preserve correct ambiguous-mention null extents (Seraphine roster / Corin Vale patterns).
4. Keep packet V2 / renderer V2 / comparator / READY thresholds unchanged unless a later slice explicitly owns them.

## Scope check

Allowlisted changes for the correction: calibration identity fields + tests/contract, holdout V2 retirement README, sealed holdout V3 fixtures, regenerated aggregates, this report, PR body. `tl01d-v1` prompt text and hash unchanged. No TL00/TL01 kernel, packet V2, comparator, graph state, or prior TL01C aggregate edits.
