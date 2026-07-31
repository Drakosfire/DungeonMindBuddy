# TL01E Grounded Abstention + State-Restatement

## Executive result

**Promotion decision:** `ITERATE_PROMPT`

The V4 promotion holdout is retired as evidence because its Lysandra and shiny-rain gold rows were not semantically supported by their sources. Frozen `tl01e-v1` was not changed. A fresh two-row canonical V5 holdout was sealed and used for the replacement promotion run.

| Matrix | Decision | Blocking diagnostics |
| --- | --- | --- |
| regression-current | `ITERATE_PROMPT` | `candidate_unsafe_over_resolution=3` |
| regression-legacy | `ITERATE_PROMPT` | `candidate_unsafe_over_resolution=6` |
| promotion V5 | `ITERATE_PROMPT` | `candidate_source_leakage=2` |

## Frozen identities

| Field | Value |
| --- | --- |
| Control | `tl01d-v1` / `410a2d1ba1f497dc1dcc4904f04f09b119586205533e925ff3d060e21a600bae` |
| Candidate | `tl01e-v1` / `8373cb2d40e532c648faff88064d95b0e862dfe947e9a0c80e72183bf48a7d4c` |
| Packet | `tl01c-packet-v1` |
| Renderer | `render_temporal_shadow_user_content_v2` |
| Model | `gpt-5.4-mini` |
| V5 holdout seal / execution SHA | `0c9164070dcb12aebe2094f55a70d97a03b3567f` |
| V4 adversarial seal SHA | `d566ff7a7ed1e202e399316140bde1375ea02ac2` |
| Regression mirror seal SHA | `20804aadae40bf07183c8aac2dff555fb4959b79` |

## Aggregate artifacts

* `evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01e/regression-current/calibration/aggregate.json` — `temporal-prompt-calibration:7753c40761aa7081`
* `evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01e/regression-legacy/calibration/aggregate.json` — `temporal-prompt-calibration:0e686bc114b9aed8`
* `evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01e/promotion/calibration/aggregate.json` — retained V4 history; not current promotion evidence
* `evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01e/promotion-v5/calibration/aggregate.json` — `temporal-prompt-calibration:dd93aab21eb90981`

## Holdout V4 disposition

V4 is preserved unchanged for historical traceability but is no longer promotion evidence:

1. The Lysandra source observes an already-held new rank; it does not narrate an appointment or promotion.
2. The shiny-rain assertion, predicate, label, and evidence disagree about whether the forest moved or merely needed to move.

Therefore the prior report's claim that TL01E over-abstained on those two canonical rows is withdrawn. The V4 aggregate remains useful only as a record of the superseded experiment.

## Replacement promotion (holdout V5 / adversarial V4)

V5 contains two independent canonical rows:

* An explicit Session 13 authority assignment for the Questionable Company's reporting relationship to Lysandra. Gold is a resolved persistent-state start at Session 13.
* A canonical world-document founding event with an explicit historical phrase. Gold is a resolved textual occurrence with no invented session anchor.

The candidate holdout lane completed **3/3** repetitions with **status accuracy 1.0** and **0 grounding failures**. The two remaining semantic findings are genuine candidate behavior:

* The authority row used `occurrence_time=session-13` in **2/3** runs instead of `valid_time.start=session-13`, producing the aggregate's `candidate_source_leakage=2`.
* The founding row was resolved textually in all three runs, but the model selected the shorter verb-plus-time expression rather than the sealed gold's longer source phrase, so exact temporal-value matching was **0/3**. This is a normalization-sensitivity finding, not a status mismatch.

Adversarial V4 remained strong for the candidate: **3/3** successful, status accuracy **1.0**, not_applicable accuracy **1.0**, grounding failures **0**, and unsafe over-resolution **0**. The candidate development lane had one grounding failure in this run.

## Regression results

The two regression matrices were not rerun. Their executable inputs and prior aggregates remain valid:

* Current-failure regression fixed the observed V3 mayor-restatement surface, while retaining unsafe source-different behavior.
* Legacy regression still exposes unsafe over-resolution and grounding instability.

## Interpretation

The correction removes the unsupported V4 promotion claim, but TL01E is still not ready:

1. Explicit persistent-state boundaries can still leak into the occurrence lane.
2. Grounding and source-different adversarial behavior remain unstable.
3. Textual temporal exactness needs a clearer minimal-expression convention before its exact-match gate is used as a promotion claim.

Do not weaken the grounding validator or mutate `tl01e-v1`. Successor work should remain inside TL01, with any new prompt or textual-normalization experiment separately frozen and sealed.
