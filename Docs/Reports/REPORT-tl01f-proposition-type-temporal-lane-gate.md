# REPORT — TL01F: Proposition-Type Temporal Lane Gate

**Created:** 2026-07-31  
**Updated:** 2026-07-31 (PR #463 review: V7 reframed as corrective replay of V6; restaurant gold → valid-start; strip `cohort_tag`)  
**Control:** frozen `tl01e-v1`  
**Candidate:** frozen `tl01f-v1`  
**Packet / renderer:** `tl01c-packet-v1` / `render_temporal_shadow_user_content_v2`  
**Model:** `gpt-5.4-mini` · **Repetitions:** 3

## Executive result

| Matrix | Machine decision | Blocking diagnostics |
| --- | --- | --- |
| regression-current | `ITERATE_PROMPT` | `candidate_unsafe_over_resolution=3` |
| regression-legacy | `ITERATE_PROMPT` | `candidate_unsafe_over_resolution=2` |
| promotion (V7 corrective replay) | `ITERATE_PROMPT` | `candidate_unsafe_over_resolution=4` |

**Human roadmap recommendation:** `ITERATE_LANE_PROMPT`

TL01 may **not** advance. The V5 authority lane failure that motivated TL01F remains fixed under the candidate on current-regression holdout. Holdout **V7 is a corrective replay of retired V6**, not independent promotion evidence: eight rows reuse V6 propositions and source spans (shared assertion IDs after removing `cohort_tag`); only the Lysandra unresolved pledge is new. Residual blockers remain on adversarial and corrective-holdout unsafe over-resolution, grounding instability, restaurant lane miss under corrected valid-start gold, and unresolved/ambiguous calibration failures.

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
| Regression / adversarial V5 seal SHA | `d358fbe6bdccc2841565f6b6b52427fb2409958d` |
| Promotion holdout V7 corrective-replay seal / execution SHA | `bea4821f40bbc292470bfcc149548e639b5ab3d2` |
| Repetitions | 3 |

## Aggregate artifacts

* `evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01f/regression-current/calibration/aggregate.json` — `temporal-prompt-calibration:ccbe3198dacc5fd4`
* `evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01f/regression-legacy/calibration/aggregate.json` — `temporal-prompt-calibration:ad02b0df0cb79ce7`
* `evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01f/promotion/calibration/aggregate.json` — `temporal-prompt-calibration:43cf7df9da7e189b` (V7 corrective replay; supersedes prior V7 aggregate `f7db0e7e8c8f353c` and retired V6 `7c7843c3e1143b74`)

## Gold audit summary

| Cohort | Rows | Coverage | Notes |
| --- | --- | --- | --- |
| holdout V6 | 8 | sealed historical | **RETIRED** as promotion evidence: forest-arrival marked unresolved despite `in 4-5 hours` |
| holdout V7 | 9 | corrective replay of V6 + Lysandra unresolved | forest → textual occurrence; restaurant attribute → textual valid-start; **not** independent/fresh authority |
| adversarial V5 | 8 | lane-focused synthetic | unchanged; still promotion adversarial |

Audit files:

* `evals/graph_memory_layer/examples/temporal_shadow_holdout_v6/GOLD-AUDIT.md` (retired authority)
* `evals/graph_memory_layer/examples/temporal_shadow_holdout_v7/GOLD-AUDIT.md` (corrective replay)
* `evals/graph_memory_layer/examples/temporal_shadow_adversarial_v5/GOLD-AUDIT.md`

## Matrix results

### regression-current (holdout V5 / adversarial V3)

| Lane | Success | Status min | NA min | Wrong lane | Wrong value | Unsafe | Source→occ | Source→valid | Grounding | Model-output |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| candidate development | 0/3 | 0.0 | 0.0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 |
| candidate holdout | 3/3 | 1.0 | 0.0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 |
| candidate adversarial | 3/3 | 0.875 | 0.667 | 3 | 8 | 3 | 0 | 1 | 0 | 0 |

Observed TL01F motivation check on V5 holdout:

* Authority / reporting relationship: `valid_time.start=session-13` in **3/3** candidate repetitions; **0** occurrence-lane leaks.
* Historical founding: occurrence textual in **3/3**; exact-value mismatches only.

### regression-legacy (holdout V1 / adversarial V2)

| Lane | Success | Status min | NA min | Wrong lane | Wrong value | Unsafe | Source→occ | Source→valid | Grounding | Model-output |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| candidate development | 0/3 | 0.0 | 0.0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 |
| candidate holdout | 0/3 | 0.0 | 0.0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 |
| candidate adversarial | 3/3 | — | — | 0 | 9 | 2 | 0 | 0 | 0 | 0 |

### promotion (holdout V7 corrective replay / adversarial V5)

| Lane | Success | Status min | NA min | Wrong lane | Wrong value | Unsafe | Source→occ | Source→valid | Grounding | Model-output |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| candidate development | 1/3 | 0.833 | 1.0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 |
| candidate holdout | 2/3 | 0.667 | 1.0 | 2 | 1 | 3 | 0 | 3 | 1 | 0 |
| candidate adversarial | 1/3 | 0.875 | 0.667 | 0 | 1 | 1 | 1 | 0 | 2 | 0 |

## Lane confusion table

### Current regression (V5) — candidate holdout (3 successful reps)

| Gold lane | Predicted occurrence | Predicted valid-start | Predicted valid-end | Predicted both | Predicted none |
| --- | ---: | ---: | ---: | ---: | ---: |
| occurrence | 3 | 0 | 0 | 0 | 0 |
| valid-start | 0 | 3 | 0 | 0 | 0 |

### Corrective promotion (V7) — candidate holdout (2 successful reps; 1 grounding failure)

| Assertion class | Observed on successful reps |
| --- | --- |
| Song of Shattering (occurrence session) | exact ×2 |
| Winna door (valid-start) | exact ×2 |
| Compulsion end (valid-end) | exact ×2 |
| Moss farmers / summoning circle (NA) | exact ×2 |
| Abandoned restaurant (attribute → valid-start textual) | wrong_temporal_lane ×2 (predicted occurrence textual) |
| Forest forecast (resolved textual occurrence) | safe_under_resolution ×1; wrong_temporal_value ×1 |
| Lysandra pledge (unresolved) | unsafe_over_resolution ×2 → session-3 valid-start |
| Dustwalker cell (ambiguous) | status_mismatch ×1; unsafe_over_resolution ×1 |

## Assertion stability (promotion V7 corrective holdout)

| Assertion | Result across 3 reps | Notes |
| --- | --- | --- |
| Abandoned restaurant | grounding_failure×1; wrong_temporal_lane×2 | gold is valid-start; model keeps occurrence |
| Forest forecast | grounding_failure×1; safe_under_resolution×1; wrong_temporal_value×1 | phrase span / abstention instability |
| Lysandra pledge | grounding_failure×1; unsafe_over_resolution×2 | over-resolve to session-3 valid-start |
| Dustwalker cell | grounding_failure×1; status_mismatch×1; unsafe×1 | ambiguous calibration failure |
| Other rows | grounding_failure×1; exact×2 | holdout success rate 2/3 |

## Normalization findings

Textual-value mismatches remain separate from lane failures (V5 founding phrase span; adversarial historical spans; forest phrase truncation). Restaurant is now a clean lane miss under attribute→valid-start gold, not an occurrence/source-different scoring artifact. Evaluation-only `cohort_tag` is stripped from `semantic_assertion_value` and absent from V7 fixtures.

## Interpretation

1. **V6 promotion evidence invalidated** by indefensible unresolved gold on an explicit relative forecast; V6 fixtures remain sealed/immutable and marked RETIRED.
2. **V7** is a **corrective replay**, not fresh authority: shared V6 proposition/source fingerprints and assertion IDs; restaurant gold corrected to `valid_time.start`; forest remains textual occurrence; Lysandra pledge remains the only new unresolved row.
3. After correction, promotion still fails readiness via adversarial + holdout unsafe over-resolution, restaurant wrong-lane under corrected gold, residual source→valid leakage, and unresolved/ambiguous mistakes.
4. Do not mutate `tl01f-v1`. A later genuinely fresh holdout (new propositions + source spans + semantic-overlap tests) is required before claiming independent promotion evidence. Successor prompt work should target unsafe abstention + ambiguous/unresolved calibration after lane/safety evidence is trustworthy.

## Recommendation

```text
ITERATE_LANE_PROMPT
```
