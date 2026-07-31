# REPORT — TL01F: Proposition-Type Temporal Lane Gate

**Created:** 2026-07-31  
**Updated:** 2026-07-31 (PR #463 review corrections: retire V6 promotion gold; seal/rerun V7)  
**Control:** frozen `tl01e-v1`  
**Candidate:** frozen `tl01f-v1`  
**Packet / renderer:** `tl01c-packet-v1` / `render_temporal_shadow_user_content_v2`  
**Model:** `gpt-5.4-mini` · **Repetitions:** 3

## Executive result

| Matrix | Machine decision | Blocking diagnostics |
| --- | --- | --- |
| regression-current | `ITERATE_PROMPT` | `candidate_unsafe_over_resolution=3` |
| regression-legacy | `ITERATE_PROMPT` | `candidate_unsafe_over_resolution=2` |
| promotion (V7) | `ITERATE_PROMPT` | `candidate_unsafe_over_resolution=3` |

**Human roadmap recommendation:** `ITERATE_LANE_PROMPT`

TL01 may **not** advance. The V5 authority lane failure that motivated TL01F remains fixed under the candidate on current-regression holdout. Fresh promotion authority is **holdout V7** after V6 was retired: the V6 forest-arrival row marked `unresolved` despite an explicit relative phrase representable as textual occurrence, which invalidated V6 promotion unsafe/unresolved counts. V7 corrects that gold and adds a genuine unresolved pledge row. Residual blockers remain: adversarial unsafe over-resolution, grounding instability, and unresolved/ambiguous calibration failures.

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
| Promotion holdout V7 seal / execution SHA | `53a699f3f2ca4dcd35faac720badef68057181b9` |
| Repetitions | 3 |

## Aggregate artifacts

* `evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01f/regression-current/calibration/aggregate.json` — `temporal-prompt-calibration:ccbe3198dacc5fd4`
* `evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01f/regression-legacy/calibration/aggregate.json` — `temporal-prompt-calibration:ad02b0df0cb79ce7`
* `evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01f/promotion/calibration/aggregate.json` — `temporal-prompt-calibration:f7db0e7e8c8f353c` (V7; supersedes retired V6 promotion aggregate `7c7843c3e1143b74`)

## Gold audit summary

| Cohort | Rows | Coverage | Notes |
| --- | --- | --- | --- |
| holdout V6 | 8 | sealed historical | **RETIRED** as promotion evidence: forest-arrival marked unresolved despite `in 4-5 hours` |
| holdout V7 | 9 | occurrence, forecast textual, valid-start/end, restatement, structure, source-different, unresolved, ambiguous | forest → resolved textual; Lysandra pledge → unresolved |
| adversarial V5 | 8 | lane-focused synthetic | unchanged; still promotion adversarial |

Audit files:

* `evals/graph_memory_layer/examples/temporal_shadow_holdout_v6/GOLD-AUDIT.md` (retired authority)
* `evals/graph_memory_layer/examples/temporal_shadow_holdout_v7/GOLD-AUDIT.md`
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
* Historical founding: occurrence textual in **3/3**; exact-value mismatches only.

### regression-legacy (holdout V1 / adversarial V2)

| Lane | Success | Status min | NA min | Wrong lane | Wrong value | Unsafe | Source→occ | Source→valid | Grounding | Model-output |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | ---: | ---: |
| candidate development | 0/3 | 0.0 | 0.0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 |
| candidate holdout | 0/3 | 0.0 | 0.0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 |
| candidate adversarial | 3/3 | — | — | 0 | 9 | 2 | 0 | 0 | 0 | 0 |

### promotion (holdout V7 / adversarial V5)

| Lane | Success | Status min | NA min | Wrong lane | Wrong value | Unsafe | Source→occ | Source→valid | Grounding | Model-output |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | ---: | ---: |
| candidate development | 0/3 | 0.0 | 0.0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 |
| candidate holdout | 1/3 | 0.667 | 1.0 | 1 | 0 | 1 | 1 | 0 | 2 | 0 |
| candidate adversarial | 2/3 | 0.875 | 0.667 | 0 | 2 | 2 | 1 | 1 | 1 | 0 |

## Lane confusion table

### Current regression (V5) — candidate holdout (3 successful reps)

| Gold lane | Predicted occurrence | Predicted valid-start | Predicted valid-end | Predicted both | Predicted none |
| --- | ---: | ---: | ---: | ---: | ---: |
| occurrence | 3 | 0 | 0 | 0 | 0 |
| valid-start | 0 | 3 | 0 | 0 | 0 |

### Fresh promotion (V7) — candidate holdout (1 successful rep; 2 grounding failures)

| Assertion class | Observed on successful rep |
| --- | --- |
| Song of Shattering (occurrence session) | exact |
| Winna door (valid-start) | exact |
| Compulsion end (valid-end) | exact |
| Moss farmers / summoning circle (NA) | exact |
| Abandoned restaurant (source-different) | wrong_temporal_lane |
| Forest forecast (resolved textual) | safe_under_resolution → predicted unresolved |
| Lysandra pledge (unresolved) | unsafe_over_resolution → session-3 occurrence |
| Dustwalker cell (ambiguous) | status_mismatch → not_applicable |

## Assertion stability (promotion V7 holdout)

| Assertion | Result across 3 reps | Notes |
| --- | --- | --- |
| Forest forecast | grounding_failure×2; safe_under_resolution×1 | no longer counted as unsafe; gold is resolved textual |
| Lysandra pledge | grounding_failure×2; unsafe_over_resolution×1 | genuine unresolved over-resolve to session-3 |
| Other rows | grounding_failure×2; mixed exact/mismatch×1 | holdout success rate 1/3 |

## Normalization findings

Textual-value mismatches remain separate from lane failures (V5 founding phrase span; adversarial historical spans). Forest under-resolution is a lane/status miss against corrected gold, not a textual span issue.

## Interpretation

1. **V6 promotion evidence invalidated** by indefensible unresolved gold on an explicit relative forecast; V6 fixtures remain sealed/immutable and marked RETIRED.
2. **V7** restores contract-aligned gold: forest → textual occurrence; Lysandra pledge → unresolved.
3. After correction, promotion still fails readiness via adversarial unsafe over-resolution, holdout grounding instability, residual wrong-lane/source leakage, and unresolved/ambiguous mistakes.
4. Do not mutate `tl01f-v1`. Successor work should target unsafe abstention + ambiguous/unresolved calibration after lane/safety evidence is trustworthy.

## Recommendation

```text
ITERATE_LANE_PROMPT
```
