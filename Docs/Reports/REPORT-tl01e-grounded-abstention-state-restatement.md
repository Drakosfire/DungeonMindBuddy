# TL01E Grounded Abstention + State-Restatement

## Executive result

**Promotion decision:** `ITERATE_PROMPT`

Frozen candidate `tl01e-v1` was evaluated against frozen control `tl01d-v1` on identical packet V2 / renderer V2 / `gpt-5.4-mini`. All three matrices ran from one clean implementation SHA.

TL01E fixed the two TL01D promotion blockers on the observed holdout V3 surface, but did not clear all hard gates across regression and fresh promotion cohorts.

| Matrix | Decision | Blocking diagnostics |
| --- | --- | --- |
| regression-current | `ITERATE_PROMPT` | `candidate_unsafe_over_resolution=3` |
| regression-legacy | `ITERATE_PROMPT` | `candidate_unsafe_over_resolution=6` |
| promotion | `ITERATE_PROMPT` | `candidate_grounding_failures=4` |

## Frozen identities

| Field | Value |
| --- | --- |
| Control | `tl01d-v1` / `410a2d1ba1f497dc1dcc4904f04f09b119586205533e925ff3d060e21a600bae` |
| Candidate | `tl01e-v1` / `8373cb2d40e532c648faff88064d95b0e862dfe947e9a0c80e72183bf48a7d4c` |
| Packet | `tl01c-packet-v1` |
| Renderer | `render_temporal_shadow_user_content_v2` |
| Model | `gpt-5.4-mini` |
| Implementation / promotion seal SHA | `d566ff7a7ed1e202e399316140bde1375ea02ac2` |
| Regression mirror seal SHA | `20804aadae40bf07183c8aac2dff555fb4959b79` |

## Aggregate artifacts

* `evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01e/regression-current/calibration/aggregate.json` — `temporal-prompt-calibration:7753c40761aa7081`
* `evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01e/regression-legacy/calibration/aggregate.json` — `temporal-prompt-calibration:0e686bc114b9aed8`
* `evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01e/promotion/calibration/aggregate.json` — `temporal-prompt-calibration:8e76f7002d000418`

## Current-failure regression (holdout V3 / adversarial V3)

Against the exact TL01D failure surface:

* Holdout V3 candidate: **3/3 successful**, status accuracy **1.0**, not_applicable accuracy **1.0**, grounding failures **0**, unsafe **0**.
* Orik-style mayor restatement is exact `not_applicable` with null extents on all three repetitions.
* Adversarial V3 candidate: **3/3 successful** and **0 grounding failures** (control still grounding-fails all three), but **unsafe_over_resolution=3** plus source-time leakage on historical/source-different rows.
* Development candidate: 1/3 successful; 2 grounding failures from non-verbatim `source_phrase`.

## Legacy regression

Development remains strong when grounding succeeds. Legacy holdout and adversarial still show unsafe over-resolution / grounding incompleteness under the stronger abstention wording. Decision remains `ITERATE_PROMPT`.

## Fresh promotion (holdout V4 / adversarial V4)

* Adversarial V4 candidate: **3/3**, status **1.0**, not_applicable **1.0**, grounding **0**, unsafe **0**. Role restatement and `As <role>` patterns are correct.
* Holdout V4 candidate: not_applicable accuracy **1.0** (mayor restatement held), but status mismatches on the Lysandra new-rank valid-start and shiny-rain textual rows (over-abstention to `not_applicable`), plus one grounding failure.
* Development candidate: **3/3 grounding failures** (`source_phrase='connected_by_road'`).

## Interpretation

TL01E achieved its primary observed goals on holdout V3:

1. Nonblank diagnostics / grounding completion on that batch.
2. Persistent role restatement without inventing a valid-time start.

It did not reach readiness because:

1. Source-different adversarial leakage still produces unsafe classifications.
2. Grounding completeness is not yet stable on development structural rows (`source_phrase` must be a verbatim evidence substring).
3. Fresh holdout valid-start / textual rows were over-abstained.

Do not weaken the grounding validator. Successor work should remain prompt-only inside TL01 (new version), or a separate constrained-output experiment if grounding incompleteness persists after semantic gates are green.
