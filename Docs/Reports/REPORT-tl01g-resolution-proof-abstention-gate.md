# REPORT — TL01G: Resolution-Proof Abstention Gate

**Created:** 2026-08-01  
**Control:** frozen `tl01f-v1`  
**Candidate:** frozen `tl01g-v1`  
**Packet / renderer:** `tl01c-packet-v1` / `render_temporal_shadow_user_content_v2`  
**Model:** `gpt-5.4-mini` · **Repetitions:** 3  
**Execution / seal SHA:** `ed65f1409ff389238c6a7d8233b2c7309d7d436d`

## Executive result

| Matrix | Machine decision | Blocking diagnostics |
| --- | --- | --- |
| regression-lane (V5 / Adv V3) | `ITERATE_PROMPT` | `candidate_unsafe_over_resolution=1` |
| regression-abstention (V7 / Adv V5) | `ITERATE_PROMPT` | `candidate_grounding_failures=5` |
| regression-legacy (V1 / Adv V2) | `ITERATE_PROMPT` | `candidate_unsafe_over_resolution=2` |
| promotion (V8 / Adv V6) | `ITERATE_PROMPT` | `candidate_source_leakage=3` |

**Human roadmap recommendation:** `ITERATE_ABSTENTION_PROMPT`

TL01 may **not** advance to broader-shadow readiness. `wrong_temporal_value` remains non-zero on promotion and several regressions, so `PROMPT_READY_FOR_BROADER_SHADOW` is disallowed even where slice pass counts look strong. Residual blockers are source→valid-time leakage on fresh V8, grounding failures on corrective V7 abstention replay, and leftover unsafe over-resolution on lane/legacy adversarial cohorts.

Observed abstention win: on Matrix B adversarial V5, candidate reached **status accuracy 1.0**, **unsafe over-resolution 0**, and **source leakage 0** (control still unsafe). That is real progress on the Corveth-class failure, but it is not sufficient for readiness while V7 grounding and V8 leakage remain.

## Frozen identities

| Identity | Value |
| --- | --- |
| Control prompt | `tl01f-v1` |
| Control SHA256 | `7a9d27c3a9980893f18757d7a5fe0612cf67f9aad8dfd2ccb20f9e3c667b7143` |
| Candidate prompt | `tl01g-v1` |
| Candidate SHA256 | `60680e1f5f574e76cfa2c9809f1292ef7daa17bab9b4b320d0427440c661b0f9` |
| Packet | `tl01c-packet-v1` |
| Renderer | `render_temporal_shadow_user_content_v2` |
| Model | `gpt-5.4-mini` |
| Prompt + cohort seal / execution SHA | `ed65f1409ff389238c6a7d8233b2c7309d7d436d` |
| Repetitions | 3 |

Anti-oracle: `tl01g-v1` uses reserved synthetic vocabulary (`Vespera`, `Kaelith`, `Rondel`, `Brinegate Wharf`, `Lanternreef Compact`, `Ashlock Primers`). Whole-prompt scan excludes prior prompt reserved terms and observed V7/V5 high-signal phrases. V7/V5 names appear only in regression assertions and this report.

## Aggregate artifacts

* `evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01g/regression-lane/calibration/aggregate.json` — `temporal-prompt-calibration:7a3e1a3a290cfd92`
* `evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01g/regression-abstention/calibration/aggregate.json` — `temporal-prompt-calibration:c48aff787d69398b`
* `evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01g/regression-legacy/calibration/aggregate.json` — `temporal-prompt-calibration:328ab3c9cc0c5048`
* `evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01g/promotion/calibration/aggregate.json` — `temporal-prompt-calibration:8fa650923db848b2`

## Fresh cohorts

| Cohort | Rows | Role | Independence |
| --- | --- | --- | --- |
| holdout V8 | 12 | independent promotion holdout | separate semantic + source fingerprint gates vs prior canonical cohorts |
| adversarial V6 | 10 | independent promotion adversarial | new reserved vocab; ID/vocab disjoint from prior adversarial cohorts |
| holdout V7 | 9 | abstention **regression only** | corrective replay of V6; not promotion authority |
| adversarial V5 | 8 | abstention **regression only** | known TL01F blockers |

Audits: `evals/graph_memory_layer/examples/temporal_shadow_holdout_v8/GOLD-AUDIT.md`, `.../temporal_shadow_adversarial_v6/GOLD-AUDIT.md`.

## Matrix results (candidate totals)

### Matrix A — lane regression (holdout V5 / Adv V3)

| Cohort | Success | Status min | Wrong lane | Wrong value | Unsafe | Source leak | Grounding |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| development | 2/3 | 0.83 | 0 | 0 | 0 | 0 | 1 |
| holdout V5 | 3/3 | 1.0 | 2 | 1 | 0 | 0 | 0 |
| adversarial V3 | 3/3 | 0.75 | 0 | 7 | 1 | 0 | 0 |

Authority/reporting valid-start behavior remains in the holdout lane suite; residual wrong-lane/value and one unsafe adversarial count block green.

### Matrix B — abstention regression (holdout V7 / Adv V5)

| Cohort | Success | Status min | Wrong lane | Wrong value | Unsafe | Source leak | Grounding |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| development | 0/3 | 0.0 | 0 | 0 | 0 | 0 | 3 |
| holdout V7 | 0/3 | 0.0 | 0 | 0 | 0 | 0 | 2 (+1 model-output) |
| adversarial V5 | 3/3 | **1.0** | **0** | 7 | **0** | **0** | **0** |

Adv V5 is the clearest TL01G win versus TL01F. V7 corrective replay did not clear as a stable abstention regression under candidate (grounding / model-output).

### Matrix C — legacy safety (holdout V1 / Adv V2)

| Cohort | Success | Status min | Wrong lane | Wrong value | Unsafe | Source leak | Grounding |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| development | 2/3 | 0.83 | 0 | 0 | 0 | 0 | 1 |
| holdout V1 | 0/3 | 0.0 | 0 | 0 | 0 | 0 | 3 |
| adversarial V2 | 3/3 | 0.8 | 0 | 9 | 2 | 0 | 0 |

Legacy adversarial still shows unsafe over-resolution.

### Matrix D — independent promotion (holdout V8 / Adv V6)

| Cohort | Success | Status min | Wrong lane | Wrong value | Unsafe | Source leak | Grounding |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| development | 3/3 | 0.83 | 0 | 0 | 0 | 0 | 0 |
| holdout V8 | 3/3 | 0.83 | 0 | 6 | 0 | **3** (all →valid) | 0 |
| adversarial V6 | 2/3 | **1.0** | 0 | 9 | **0** | **0** | 1 |

Machine decision remains `ITERATE_PROMPT` because candidate source leakage is non-zero. Human gates also fail: `wrong_temporal_value != 0`, so `PROMPT_READY` must not be selected. Residual value mismatches are not audited as textual-span-only exclusivity here; recommendation stays abstention/prompt iteration rather than `ADVANCE_TO_TEXTUAL_NORMALIZATION`.

## Interpretation

1. Resolution-proof instructions improved Adv V5 abstention safety (unsafe 0, status 1.0).
2. Fresh Adv V6 also shows unsafe 0 with status 1.0, but wrong-value and one grounding miss remain.
3. Fresh V8 still copies source time into valid-time (3 leaks) and mismatches status/value on several rows.
4. Lane regression and legacy still carry unsafe over-resolution and wrong-value mass.
5. Therefore the honest roadmap move is another abstention-focused prompt version (`tl01h-v1` or equivalent), not broader-shadow acceptance.

## Recommendation precedence applied

```text
wrong_temporal_value > 0 and source leakage / unsafe remain
→ ITERATE_ABSTENTION_PROMPT
(not PROMPT_READY; not ADVANCE_TO_TEXTUAL_NORMALIZATION)
```

## Explicit non-claims

* No Temporal Kernel / packet / renderer / threshold / runner changes.
* No graph writes or Timeline surface work.
* V7 remains regression-only corrective replay, not promotion evidence.
* World-line / branch-divergence encoding remains deferred; temporal ambiguity stays epistemic.

## Handback

```text
Candidate: tl01g-v1
Control: tl01f-v1
Seal/execution: ed65f1409ff389238c6a7d8233b2c7309d7d436d
Promotion decision: ITERATE_PROMPT (source leakage)
Human recommendation: ITERATE_ABSTENTION_PROMPT
Next: new frozen abstention prompt version; keep V8/V6 sealed; do not mutate tl01g-v1
```
