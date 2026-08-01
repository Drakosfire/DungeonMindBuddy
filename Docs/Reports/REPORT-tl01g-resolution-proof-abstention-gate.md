# REPORT — TL01G: Resolution-Proof Abstention Gate

**Created:** 2026-08-01
**Updated:** 2026-08-01 (V10/Adv V8 after V9/V7 gold-integrity request-changes)
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
| observed V8 / Adv V6 | exploratory / regression only | `ITERATE_PROMPT` | `candidate_source_leakage=3` |
| observed V9 / Adv V7 | exploratory / regression only (gold contradicts Gates B/C/D) | `ITERATE_PROMPT` | `candidate_unsafe_over_resolution=1` |
| **promotion (V10 / Adv V8)** | **authoritative** | **`ITERATE_PROMPT`** | **`candidate_unsafe_over_resolution=3`** |

**Human roadmap recommendation:** `ITERATE_ABSTENTION_PROMPT`

TL01 may **not** advance to broader-shadow readiness. Authoritative promotion under freeze `3af1e470…` with Gate-faithful V10/Adv V8 still fails: Adv V8 retains unsafe over-resolution; holdout V10 and development show grounding instability (0/3 successes). Prior V8–V9 / Adv V6–V7 matrices remain exploratory or regression-only.

## Integrity recovery timeline

| Step | SHA | Role |
| --- | --- | --- |
| Prompt-only freeze after Example 6 / Gate C repair | `67408bd871ba684e70ddf6e53dd7088d0036a475` | immutable candidate text |
| Retire V8/V6; span-text fingerprints; Adv template guards | `09c2c75e…` | process |
| Author then seal V9 / Adv V7 | `b1843ff6681ed92f12ba3657527d2b608f49cc95` | **retired** — gold contradicted Gates B/C/D after observation |
| Retire V9/V7; fail-closed span guard; seal V10 / Adv V8 | `046093fd899e1b286329b0e0bf6b09b6aa0e60d6` | **authoritative promotion seal / execution** |

### Why V9/V7 cannot remain promotion authority

Do **not** patch V9/V7 gold in place (provider outputs already observed). Defects retained as regression evidence:

- V9: persistent observation (`has not been able to get any rest`) marked resolved valid-start; incomplete costume-signup event marked not_applicable; identity/origin classification marked ambiguous.
- Adv V7: future with grounded `tomorrow` marked unresolved; grounding trap resolved with object-NP `Ashen Compact oath-bell` as `raw_expression`.
- Ambiguous-row tests only required `or`/`either`, not temporal eligibility under Gate B.

### Fail-closed span independence (P2)

Resolved-span fingerprints now fail before hashing when evidence refs are missing, paths are absent, line ranges are invalid/empty, normalized text is empty, or an assertion yields zero source-span fingerprints. `sha256("")` is never treated as a successful independence proof.

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
| Promotion cohort seal / execution SHA | `046093fd899e1b286329b0e0bf6b09b6aa0e60d6` |
| Repetitions | 3 |

## Aggregate artifacts

* Exploratory / regression-only (not authority for freeze `3af1e470…` + V10/V8):
  * `.../tl01g/regression-lane|abstention|legacy/calibration/aggregate.json`
  * Prior V8/V6 promotion `temporal-prompt-calibration:8fa650923db848b2` (git history)
  * Prior V9/V7 promotion `temporal-prompt-calibration:ad6a53a7ed8e9714` (git history / overwritten on disk)
* **Authoritative promotion (V10 / Adv V8):**
  * `evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01g/promotion/calibration/aggregate.json` — `temporal-prompt-calibration:27f9e68971c575ee`

## Cohorts

| Cohort | Rows | Role |
| --- | ---: | --- |
| holdout V10 | 12 | **authoritative promotion holdout** — Gate B/C audited; authored after freeze; sealed at `046093fd…` |
| adversarial V8 | 10 | **authoritative promotion adversarial** — tomorrow→resolved occurrence; grounding trap→unresolved; novel vocab/templates |
| holdout V9 / Adv V7 | 12 / 10 | observed regression only (gold defects retained) |
| holdout V8 / Adv V6 | 12 / 10 | observed regression only |
| holdout V7 / Adv V5 | 9 / 8 | abstention regression only |

Audits: `evals/graph_memory_layer/examples/temporal_shadow_holdout_v10/GOLD-AUDIT.md`, `.../temporal_shadow_adversarial_v8/GOLD-AUDIT.md`.

## Matrix D — authoritative promotion (holdout V10 / Adv V8)

Seal/execution: `046093fd899e1b286329b0e0bf6b09b6aa0e60d6` · candidate SHA `3af1e470…` · calibration `temporal-prompt-calibration:27f9e68971c575ee`

| Cohort | Success | Status min | Wrong lane | Wrong value | Unsafe | Source leak | Grounding |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| development | 0/3 | — | 0 | 0 | 0 | 0 | 3 |
| holdout V10 | 0/3 | — | 0 | 0 | 0 | 0 | 3 |
| adversarial V8 | 3/3 | 0.8 | 0 | 11 | **3** | 3 (→occurrence) | 0 |

Machine decision: `ITERATE_PROMPT` (`candidate_unsafe_over_resolution=3`). Human gates also fail: grounding collapses on holdout/development; Adv V8 still over-resolves. `PROMPT_READY_FOR_BROADER_SHADOW` remains disallowed.

## Interpretation

1. Process and gold-integrity defects from PR #468 reviews are addressed: prompt freeze precedes V10/V8; V8–V9 / Adv V6–V7 are reclassified; span guard fails closed; ambiguous rows require temporal eligibility cues.
2. Under Gate-faithful authoritative cohorts, TL01G is still honestly red — unsafe over-resolution on Adv V8 and grounding instability on V10 block readiness.
3. Exploratory Adv V5 unsafe-0 wins under the pre-repair draft remain interesting regression signal only.
4. Next prompt version (`tl01h-v1` or equivalent) should target abstention safety and grounding completeness. Do not mutate `tl01g-v1`; do not revive V8–V9 / Adv V6–V7 as promotion authority.

## Recommendation precedence applied

```text
unsafe over-resolution > 0 and grounding failures on authoritative promotion
→ ITERATE_ABSTENTION_PROMPT
(not PROMPT_READY; not ADVANCE_TO_TEXTUAL_NORMALIZATION)
```

## Explicit non-claims

* No Temporal Kernel / packet / renderer / threshold / runner changes.
* No graph writes or Timeline surface work.
* V8–V9 and Adv V6–V7 are **not** independent promotion evidence.
* Matrices A–C under candidate hash `60680e1f…` are not authority for freeze `3af1e470…`.
* World-line / branch-divergence encoding remains deferred; temporal ambiguity stays epistemic.

## Handback

```text
Candidate: tl01g-v1 (freeze 67408bd8…; prompt hash 3af1e470…)
Control: tl01f-v1
Authoritative seal/execution: 046093fd899e1b286329b0e0bf6b09b6aa0e60d6
Promotion cohorts: holdout V10 + adversarial V8
Promotion decision: ITERATE_PROMPT (unsafe over-resolution=3)
Human recommendation: ITERATE_ABSTENTION_PROMPT
Next: new frozen abstention prompt version; keep V10/V8 sealed; do not mutate tl01g-v1; do not revive V8–V9 / Adv V6–V7 as promotion authority
```
