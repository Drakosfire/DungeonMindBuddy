# REPORT — TL01F: Proposition-Type Temporal Lane Gate

**Created:** 2026-07-31  
**Control:** frozen `tl01e-v1`  
**Candidate:** frozen `tl01f-v1`  
**Packet / renderer:** `tl01c-packet-v1` / `render_temporal_shadow_user_content_v2`  
**Model:** `gpt-5.4-mini` · **Repetitions:** 3

## Executive result

| Matrix | Machine decision | Blocking diagnostics |
| --- | --- | --- |
| regression-current | `ITERATE_PROMPT` | `candidate_unsafe_over_resolution=3` |
| regression-legacy | `ITERATE_PROMPT` | `candidate_unsafe_over_resolution=2` |
| promotion | `ITERATE_PROMPT` | `candidate_unsafe_over_resolution=2` |

**Human roadmap recommendation:** `ITERATE_LANE_PROMPT`

TL01 may **not** advance. The V5 authority lane failure that motivated TL01F is fixed under the candidate on the observed current-regression holdout, and fresh V6 shows strong exact matches on occurrence / valid-start / valid-end / restatement / structure rows. Remaining blockers are unsafe over-resolution, grounding instability, residual wrong-lane cases, and unstable ambiguous/unresolved behavior.

## Frozen identities

| Identity | Value |
| --- | --- |
| Control prompt | `tl01e-v1` |
| Control SHA256 | `8373cb2d40e532c648faff88064d95b0e862dfe947e9a0c80e72183bf48a7d4c` |
| Candidate prompt | `tl01f-v1` |
| Candidate SHA256 | `7a9d27c3a9980893f18757d7a5fe0612cf67f9aad8dfd2ccb20f9e3c667b7143` |
| Packet | `tl01c-packet-v1` |
| Renderer | `render_temporal_shadow_user_content_v2` |
| Model | `gpt-5.4-mini` |
| Prompt-freeze SHA | `83034c8c83611e2cdde9ae0279f7a508b71e5dcd` |
| Holdout / adversarial / execution seal SHA | `d358fbe6bdccc2841565f6b6b52427fb2409958d` |
| Repetitions | 3 |

## Aggregate artifacts

* `evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01f/regression-current/calibration/aggregate.json` — `temporal-prompt-calibration:ccbe3198dacc5fd4`
* `evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01f/regression-legacy/calibration/aggregate.json` — `temporal-prompt-calibration:ad02b0df0cb79ce7`
* `evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01f/promotion/calibration/aggregate.json` — `temporal-prompt-calibration:7c7843c3e1143b74`

## Gold audit summary

| Cohort | Rows reviewed | Coverage | Rejected rows | Post-run gold edits |
| --- | --- | --- | --- | --- |
| holdout V6 | 8 | occurrence, valid-start, valid-end, restatement, non-temporal, source-different, unresolved, ambiguous | none after final selection | none |
| adversarial V5 | 8 | eventive-on-state, stative-on-event, tempting source, source-different, valid-start, valid-end, restatement, ambiguous | none after final selection | none |

Audit files:

* `evals/graph_memory_layer/examples/temporal_shadow_holdout_v6/GOLD-AUDIT.md`
* `evals/graph_memory_layer/examples/temporal_shadow_adversarial_v5/GOLD-AUDIT.md`

## Matrix results

### regression-current (holdout V5 / adversarial V3)

| Lane | Success | Status min | NA min | Wrong lane | Wrong value | Unsafe | Source→occ | Source→valid | Grounding | Model-output |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | ---: | ---: |
| candidate development | 0/3 | 0.0 | 0.0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 |
| candidate holdout | 3/3 | 1.0 | 0.0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 |
| candidate adversarial | 3/3 | 0.875 | 0.667 | 3 | 8 | 3 | 0 | 1 | 0 | 0 |

Observed TL01F motivation check on V5 holdout:

* Authority / reporting relationship: `valid_time.start=session-13` in **3/3** candidate repetitions; **0** occurrence-lane leaks.
* Historical founding: occurrence textual in **3/3**; exact-value mismatches only (`Founded over 200 years ago` vs longer gold phrase).

### regression-legacy (holdout V1 / adversarial V2)

| Lane | Success | Status min | NA min | Wrong lane | Wrong value | Unsafe | Source→occ | Source→valid | Grounding | Model-output |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | ---: | ---: |
| candidate development | 0/3 | 0.0 | 0.0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 |
| candidate holdout | 0/3 | 0.0 | 0.0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 |
| candidate adversarial | 3/3 | — | — | 0 | 9 | 2 | 0 | 0 | 0 | 0 |

Legacy remains blocked by grounding incompleteness and residual unsafe over-resolution on adversarial re-attestation / source-different surfaces.

### promotion (holdout V6 / adversarial V5)

| Lane | Success | Status min | NA min | Wrong lane | Wrong value | Unsafe | Source→occ | Source→valid | Grounding | Model-output |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | ---: | ---: |
| candidate development | 0/3 | 0.0 | 0.0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 |
| candidate holdout | 3/3 | 0.75 | 1.0 | 1 | 2 | 1 | 0 | 0 | 0 | 0 |
| candidate adversarial | 1/3 | 0.875 | 0.667 | 0 | 2 | 1 | 0 | 1 | 2 | 0 |

## Lane confusion table

Candidate holdout predictions across successful repetitions:

### Current regression (V5)

| Gold lane | Predicted occurrence | Predicted valid-start | Predicted valid-end | Predicted both | Predicted none |
| --- | ---: | ---: | ---: | ---: | ---: |
| occurrence | 3 | 0 | 0 | 0 | 0 |
| valid-start | 0 | 3 | 0 | 0 | 0 |

### Fresh promotion (V6)

| Gold lane | Predicted occurrence | Predicted valid-start | Predicted valid-end | Predicted both | Predicted none |
| --- | ---: | ---: | ---: | ---: | ---: |
| occurrence | 5 | 0 | 1 | 0 | 0 |
| valid-start | 0 | 3 | 0 | 0 | 0 |
| valid-end | 0 | 0 | 3 | 0 | 0 |
| none | 1 | 0 | 0 | 0 | 11 |

Legacy holdout produced no successful candidate overlays (all grounding failures), so no lane table is claimed there.

## Assertion stability

### Promotion holdout V6 (candidate)

| Assertion | Result | Notes / provider IDs |
| --- | --- | --- |
| Song of Shattering | exact 3/3 | stable occurrence |
| Winna door charge | exact 3/3 | stable valid-start |
| Compulsion end | exact 3/3 | stable valid-end |
| Moss farmers | exact 3/3 | stable not_applicable |
| Summoning circle | exact 3/3 | stable not_applicable |
| Forest arrival | unresolved 2 / unsafe resolved 1 | provider `resp_0cdd8d74…`, `resp_0fd924c0…`, `resp_0e73b214…` |
| Abandoned restaurant | wrong_value 2 / wrong_lane 1 | textual value or end-lane confusion |
| Dustwalker cell | status_mismatch 3 | predicted `not_applicable` vs gold `ambiguous` |

### Current regression V5 (candidate)

Authority and founding statuses are stable across all three holdout repetitions (`resp_0d53aa9e…`, `resp_02f1ecf4…`, `resp_0e4e4c16…`).

## Normalization findings

Textual-value mismatches remain and are reported separately from lane failures:

* V5 Mirathorn founding: shorter `Founded over 200 years ago` vs sealed longer phrase.
* V6 abandoned restaurant: phrase-span / certainty variation; one repetition emitted valid-end instead of occurrence.
* Adversarial historical rows: raw_expression span and certainty variation without always changing lane.

These alone would support a later textual-normalization slice only after lane/safety/grounding gates are green.

## Interpretation

TL01F’s proposition-type gate produced a real win on the motivating V5 lane failure and strong exact lane coverage on several fresh V6 classes. It did not clear readiness:

1. Unsafe over-resolution remains on current, legacy, and promotion matrices.
2. Grounding remains unstable on development (and legacy holdout / most promotion adversarial reps).
3. Fresh promotion still has wrong-lane, status-mismatch, and unsafe residuals on unresolved/ambiguous/source-different rows.

Do not mutate `tl01f-v1`. Successor work should freeze a new prompt version focused on remaining unsafe abstention and ambiguous/unresolved calibration, or isolate grounding incompleteness only after lane gates are green.

## Recommendation

```text
ITERATE_LANE_PROMPT
```
