# REPORT — TL01G: Resolution-Proof Abstention Gate

**Created:** 2026-08-01
**Updated:** 2026-08-01 (integrity recovery after PR #468 request-changes)
**Control:** frozen `tl01f-v1`
**Candidate:** frozen `tl01g-v1`
**Packet / renderer:** `tl01c-packet-v1` / `render_temporal_shadow_user_content_v2`
**Model:** `gpt-5.4-mini` · **Repetitions:** 3

## Executive result

| Matrix | Authority | Machine decision | Blocking diagnostics |
| --- | --- | --- | --- |
| regression-lane (V5 / Adv V3) | exploratory only (pre-repair prompt) | `ITERATE_PROMPT` | `candidate_unsafe_over_resolution=1` |
| regression-abstention (V7 / Adv V5) | exploratory only (pre-repair prompt) | `ITERATE_PROMPT` | `candidate_grounding_failures=5` |
| regression-legacy (V1 / Adv V2) | exploratory only (pre-repair prompt) | `ITERATE_PROMPT` | `candidate_unsafe_over_resolution=2` |
| observed V8 / Adv V6 | exploratory / regression only (co-authored with first prompt draft) | `ITERATE_PROMPT` | `candidate_source_leakage=3` |
| **promotion (V9 / Adv V7)** | **authoritative** | **`ITERATE_PROMPT`** | **`candidate_unsafe_over_resolution=1`** |

**Human roadmap recommendation:** `ITERATE_ABSTENTION_PROMPT`

TL01 may **not** advance to broader-shadow readiness. Authoritative promotion under the repaired freeze still fails: holdout V9 shows unsafe over-resolution, grounding failures, residual wrong-lane/value, and source→occurrence leakage. Matrices A–C and the retired V8/V6 run remain useful exploratory/regression evidence only; they do **not** support independent-promotion claims.

## Integrity recovery (why V8/V6 are not promotion authority)

PR #468 review correctly blocked treating the first promotion matrix as durable evidence:

1. **Cohort authorship timing.** Commit `ed65f140…` co-authored `tl01g-v1`, freeze tests, holdout V8, and Adv V6. Git cannot prove holdout rows were unknown at prompt freeze. That cannot be repaired by splitting the old commit after provider observation.
2. **Proposition-first defect.** The original few-shot and V8 taught surrounding-consequence “ambiguous” labels. Example 6 was rewritten so the assertion itself permits dual readings; Gate C bars surrounding consequences. V8 gold was **not** patched in place.
3. **Source-span fingerprints.** Independence now requires semantic proposition overlap == 0 **and** SHA256 of normalized resolved span text overlap == 0 (path/content_sha/line metadata is supporting only).
4. **Adv V6 template replay.** V6 noun-substitutes known V5 templates; it is regression evidence, not independent adversarial promotion evidence. Fresh Adv V7 uses novel constructions with template-overlap guards.

**Recovery sequence actually executed:**

| Step | SHA | Role |
| --- | --- | --- |
| Prompt-only freeze after Example 6 / Gate C repair | `67408bd871ba684e70ddf6e53dd7088d0036a475` | immutable candidate text freeze |
| Retire V8/V6 promotion authority; span-text fingerprints; Adv template guards | `09c2c75e…` (+ join fix) | test/process |
| Author V9 / Adv V7 | `d0d28ccc…` | cohort content |
| Canonical overlay IDs + bound case digests (true seal) | `b1843ff6681ed92f12ba3657527d2b608f49cc95` | **promotion seal / execution** |

## Frozen identities (authoritative)

| Identity | Value |
| --- | --- |
| Control prompt | `tl01f-v1` |
| Control SHA256 | `7a9d27c3a9980893f18757d7a5fe0612cf67f9aad8dfd2ccb20f9e3c667b7143` |
| Candidate prompt | `tl01g-v1` |
| Candidate SHA256 | `3af1e470e304008d2490ba73e1a53628519c211bb54e17a10cd4c694beae9013` |
| Packet | `tl01c-packet-v1` |
| Renderer | `render_temporal_shadow_user_content_v2` |
| Model | `gpt-5.4-mini` |
| Prompt-only freeze SHA | `67408bd871ba684e70ddf6e53dd7088d0036a475` |
| Promotion cohort seal / execution SHA | `b1843ff6681ed92f12ba3657527d2b608f49cc95` |
| Repetitions | 3 |

Anti-oracle: `tl01g-v1` uses reserved synthetic vocabulary (`Vespera`, `Kaelith`, `Rondel`, `Brinegate Wharf`, `Lanternreef Compact`, `Ashlock Primers`). Whole-prompt scan excludes prior prompt reserved terms and observed V7/V5 high-signal phrases.

## Aggregate artifacts

* Exploratory (pre-repair candidate hash `60680e1f…`, co-authored seal `ed65f140…`):
  * `.../tl01g/regression-lane/calibration/aggregate.json` — `temporal-prompt-calibration:7a3e1a3a290cfd92`
  * `.../tl01g/regression-abstention/calibration/aggregate.json` — `temporal-prompt-calibration:c48aff787d69398b`
  * `.../tl01g/regression-legacy/calibration/aggregate.json` — `temporal-prompt-calibration:328ab3c9cc0c5048`
  * Prior promotion under V8/V6 (overwritten on disk; retained in git history at `a6113250…`) — `temporal-prompt-calibration:8fa650923db848b2`
* **Authoritative promotion (V9 / Adv V7):**
  * `evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01g/promotion/calibration/aggregate.json` — `temporal-prompt-calibration:ad6a53a7ed8e9714`

## Cohorts

| Cohort | Rows | Role | Independence |
| --- | ---: | --- | --- |
| holdout V9 | 12 | **authoritative promotion holdout** | authored after freeze `67408bd8…`; sealed at `b1843ff6…`; proposition-level ambiguous row uses assertion-local `or` |
| adversarial V7 | 10 | **authoritative promotion adversarial** | novel constructions; vocab/ID/template-disjoint from prior adversarial cohorts |
| holdout V8 | 12 | observed regression / exploratory only | co-authored with first prompt draft; do not patch gold |
| adversarial V6 | 10 | observed regression / exploratory only | V5 template replay with noun substitution |
| holdout V7 | 9 | abstention **regression only** | corrective replay of V6; not promotion authority |
| adversarial V5 | 8 | abstention **regression only** | known TL01F blockers |

Audits: `evals/graph_memory_layer/examples/temporal_shadow_holdout_v9/GOLD-AUDIT.md`, `.../temporal_shadow_adversarial_v7/GOLD-AUDIT.md`.

## Matrix results

### Matrices A–C — exploratory under pre-repair prompt (not authority for freeze `3af1e470…`)

Candidate hash at those runs was `60680e1f…` (pre–Example-6 repair). Numbers below are retained as exploratory regression evidence only.

#### Matrix A — lane regression (holdout V5 / Adv V3)

| Cohort | Success | Status min | Wrong lane | Wrong value | Unsafe | Source leak | Grounding |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| development | 2/3 | 0.83 | 0 | 0 | 0 | 0 | 1 |
| holdout V5 | 3/3 | 1.0 | 2 | 1 | 0 | 0 | 0 |
| adversarial V3 | 3/3 | 0.75 | 0 | 7 | 1 | 0 | 0 |

#### Matrix B — abstention regression (holdout V7 / Adv V5)

| Cohort | Success | Status min | Wrong lane | Wrong value | Unsafe | Source leak | Grounding |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| development | 0/3 | 0.0 | 0 | 0 | 0 | 0 | 3 |
| holdout V7 | 0/3 | 0.0 | 0 | 0 | 0 | 0 | 2 (+1 model-output) |
| adversarial V5 | 3/3 | **1.0** | **0** | 7 | **0** | **0** | **0** |

Adv V5 remains the clearest exploratory abstention win versus TL01F under the pre-repair draft.

#### Matrix C — legacy safety (holdout V1 / Adv V2)

| Cohort | Success | Status min | Wrong lane | Wrong value | Unsafe | Source leak | Grounding |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| development | 2/3 | 0.83 | 0 | 0 | 0 | 0 | 1 |
| holdout V1 | 0/3 | 0.0 | 0 | 0 | 0 | 0 | 3 |
| adversarial V2 | 3/3 | 0.8 | 0 | 9 | 2 | 0 | 0 |

### Observed V8 / Adv V6 — exploratory only (retired promotion claim)

| Cohort | Success | Status min | Wrong lane | Wrong value | Unsafe | Source leak | Grounding |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| development | 3/3 | 0.83 | 0 | 0 | 0 | 0 | 0 |
| holdout V8 | 3/3 | 0.83 | 0 | 6 | 0 | **3** (all →valid) | 0 |
| adversarial V6 | 2/3 | **1.0** | 0 | 9 | **0** | **0** | 1 |

Useful as regression notes (source→valid leakage on V8; Adv V6 unsafe 0). **Not** independent promotion evidence.

### Matrix D — authoritative promotion (holdout V9 / Adv V7)

Seal/execution: `b1843ff6681ed92f12ba3657527d2b608f49cc95` · candidate SHA `3af1e470…` · calibration `temporal-prompt-calibration:ad6a53a7ed8e9714`

| Cohort | Success | Status min | Wrong lane | Wrong value | Unsafe | Source leak | Grounding |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| development | 0/3 | — | 0 | 0 | 0 | 0 | 3 |
| holdout V9 | 1/3 | 0.67 | 1 | 2 | **1** | 1 (→occurrence) | 2 |
| adversarial V7 | 3/3 | 0.9 | 0 | 13 | **0** | 1 (→occurrence) | 0 |

Machine decision: `ITERATE_PROMPT` (`candidate_unsafe_over_resolution=1`). Human gates also fail: `wrong_temporal_value != 0`, grounding failures on development/holdout, residual source leakage. `PROMPT_READY_FOR_BROADER_SHADOW` remains disallowed.

## Interpretation

1. Process defects in the first promotion claim are acknowledged; V8/V6 are reclassified as observed regression/exploratory only.
2. Under a true prompt-only freeze then sealed V9/V7, TL01G is still red — unsafe over-resolution on holdout, grounding instability, and wrong-value mass remain.
3. Adv V7 shows improved abstention safety versus many prior adversarial cohorts (unsafe 0, status min 0.9) but is not enough while holdout V9 fails human readiness gates.
4. Exploratory Adv V5 win (unsafe 0 / status 1.0 under the pre-repair draft) remains interesting regression signal, not promotion authority for the repaired freeze.
5. Honest roadmap move remains another abstention-focused prompt version (`tl01h-v1` or equivalent), not broader-shadow acceptance. Do not mutate `tl01g-v1` further; freeze a new version ID.

## Recommendation precedence applied

```text
wrong_temporal_value > 0 and unsafe / grounding / leakage remain on authoritative promotion
→ ITERATE_ABSTENTION_PROMPT
(not PROMPT_READY; not ADVANCE_TO_TEXTUAL_NORMALIZATION)
```

## Explicit non-claims

* No Temporal Kernel / packet / renderer / threshold / runner changes.
* No graph writes or Timeline surface work.
* V8/V6 are **not** independent promotion evidence.
* Holdout V7 remains regression-only corrective replay, not promotion evidence.
* Matrices A–C under candidate hash `60680e1f…` are not authority for freeze `3af1e470…`.
* World-line / branch-divergence encoding remains deferred; temporal ambiguity stays epistemic.

## Handback

```text
Candidate: tl01g-v1 (repaired freeze SHA 67408bd8…; prompt hash 3af1e470…)
Control: tl01f-v1
Authoritative seal/execution: b1843ff6681ed92f12ba3657527d2b608f49cc95
Promotion cohorts: holdout V9 + adversarial V7
Promotion decision: ITERATE_PROMPT (unsafe over-resolution)
Human recommendation: ITERATE_ABSTENTION_PROMPT
Next: new frozen abstention prompt version; keep V9/V7 sealed; do not mutate tl01g-v1; do not revive V8/V6 as promotion authority
```
