# REPORT — TL01G: Resolution-Proof Abstention Gate

**Created:** 2026-08-01
**Updated:** 2026-08-01 (V13/Adv V11 pending seal after V12/Adv V10 retirement)
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
| observed V10 / Adv V8 | exploratory / regression only (audit drift + Gate C/E2 gold defects) | `ITERATE_PROMPT` | `candidate_unsafe_over_resolution=3` |
| observed V11 / Adv V9 | exploratory / regression only (span reuse + paraphrased Adv skeletons) | `ITERATE_PROMPT` | `candidate_unsafe_over_resolution=3` |
| **promotion (V12 / Adv V10)** | **retired** (gold/Gate defects) | **`ITERATE_PROMPT`** (observed) | **`candidate_unsafe_over_resolution=1`** |
| **promotion (V13 / Adv V11)** | **authoritative (pending seal)** | *not yet run* | *pending* |

**Human roadmap recommendation:** `ITERATE_ABSTENTION_PROMPT`

TL01 may **not** advance to broader-shadow readiness. V12/Adv V10 observed promotion under seal `a7a9d5c3…` failed (`candidate_unsafe_over_resolution=1`). Authoritative promotion authority moves to holdout **V13** and adversarial **V11** (Gate-faithful gold, pending seal — no provider runs yet). Prior V8–V11 / Adv V6–V9 matrices remain exploratory or regression-only.

## Integrity recovery timeline

| Step | SHA | Role |
| --- | --- | --- |
| Prompt-only freeze after Example 6 / Gate C repair | `67408bd871ba684e70ddf6e53dd7088d0036a475` | immutable candidate text |
| Retire V8/V6; span-text fingerprints; Adv template guards | `09c2c75e…` | process |
| Author then seal V9 / Adv V7 | `b1843ff6681ed92f12ba3657527d2b608f49cc95` | **retired** — gold contradicted Gates B/C/D after observation |
| Retire V9/V7; fail-closed span guard; seal V10 / Adv V8 | `046093fd899e1b286329b0e0bf6b09b6aa0e60d6` | **retired** — GOLD-AUDIT≠fixture; Gate C/E2 gold defects after observation |
| Retire V10/Adv V8; audit ID/status tests; span EOF bounds; seal V11 / Adv V9 | `a3f108f2fa64a3ac5c0146acbc25d7b904fcacc2` | **retired** — reused observed spans; Adv V9 paraphrased Adv V8 |
| Retire V11/Adv V9; restore span `isdisjoint`; Jaccard templates; audit proposition/lane/phrase; seal V12 / Adv V10 | `a7a9d5c321e7f57ddc95303705a8a8bac94fcd82` | **retired promotion execution** — gold/Gate defects (see below) |
| Retire V12/Adv V10; proposition-template Jaccard; Gate-faithful V13/Adv V11 gold | `SEAL_PENDING` | **authoritative promotion (pending seal)** |

### Why V12/Adv V10 cannot remain promotion authority

Do **not** patch V12/Adv V10 gold in place (provider outputs already observed under `a7a9d5c3…`). Defects retained as regression evidence:

- V12 spell-end transition (`Lysandra comes out of the spell`) marked valid-end session — Gate B/C treats spell emergence as occurrence, not persistent-state end.
- V12 historical relationship (`Delwen … almost-fiancée … ~8 years ago`) marked occurrence; persistent relationship state without boundary is not_applicable under Gate B/C, not an occurrence.
- V12 scale custody row (`Karsemine holds … or only picked it up then`) was an unsupported ambiguous replay of V11 spores custody fork.
- V12 festival postponement reused Mirathorn-festival ledger span already observed in prior holdouts.
- Adv V10 grounding-trap row used `now` in source but gold marked unresolved — under frozen gates the claim is resolvable (embedded `now` / session occurrence), likely manufacturing the sole `unsafe_over_resolution=1` blocker.

Authoritative promotion moves to holdout **V13** + adversarial **V11** with Gate-faithful gold and proposition-template Jaccard guards. Seal pending (`SEAL_PENDING`).

### Why V11/Adv V9 cannot remain promotion authority

Do **not** patch V11/Adv V9 gold in place (provider outputs already observed). Defects retained as regression evidence:

- V11 computed `v11_span_text` / `prior_span_text` but never asserted `isdisjoint`; reused Session 22 line 30 (abandoned restaurant) and Session 23 line 36 (compulsion-end) already observed in holdout V7, with renamed identifiers evading semantic fingerprints.
- Adv V9 preserved Adv V8’s ten functional skeletons via synonym/reordering that bypassed exact normalized-template equality (e.g. quay-fire custody/recovery ambiguity).
- V11 gold resolved “Lieutenant Lysandra” as session valid-start from a title correction (“it’s Lieutenant Lysandra now”) without an in-episode appointment boundary (Gate B/E3).
- Audit binding was ID/status-only; proposition/lane/phrase were not machine-checked.

### Fail-closed span independence

Resolved-span fingerprints fail before hashing when evidence refs are missing, paths are absent, line ranges are invalid/empty, **start or end exceeds file length**, normalized text is empty, or an assertion yields zero source-span fingerprints. Promotion holdouts must assert `vN_span_text.isdisjoint(prior_span_text)` against **all** `PRIOR_CANONICAL_COHORT_DIRS` including `temporal_shadow_cohort` (no folder skips).

### Adversarial template novelty

Exact template equality after noun scrubbing is insufficient. Adv V10 requires token-set Jaccard `< 0.40` against every prior adversarial source after the same scrub.

### GOLD-AUDIT ↔ fixture binding

Promotion cohorts require `GOLD-AUDIT.md` assertion IDs to equal the sealed base set; each audit row’s gold status, proposition label, lane class (occurrence / valid-start / valid-end / none), and supporting phrase must match the sealed overlay (phrase equals `source_phrase` or is a contiguous substring of it). **This binding proves mechanical fixture consistency only — not human Gate-faithfulness.**

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
| Promotion cohort seal / execution SHA | `a7a9d5c321e7f57ddc95303705a8a8bac94fcd82` (V12/Adv V10 observed; retired) |
| Next promotion seal | `SEAL_PENDING` (V13 / Adv V11) |
| Repetitions | 3 |

## Aggregate artifacts

* Exploratory / regression-only (not authority for freeze `3af1e470…` + V12/V10):
  * `.../tl01g/regression-lane|abstention|legacy/calibration/aggregate.json`
  * Prior V8/V6 promotion `temporal-prompt-calibration:8fa650923db848b2` (git history)
  * Prior V9/V7 promotion `temporal-prompt-calibration:ad6a53a7ed8e9714` (git history / overwritten on disk)
  * Prior V10/Adv V8 promotion `temporal-prompt-calibration:27f9e68971c575ee` (git history / overwritten on disk)
  * Prior V11/Adv V9 promotion `temporal-prompt-calibration:2c149b55752a5e63` (git history / overwritten on disk)
* **Authoritative promotion (V12 / Adv V10):**
  * `evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01g/promotion/calibration/aggregate.json` — `temporal-prompt-calibration:3db8507237419d92`

## Cohorts

| Cohort | Rows | Role |
| --- | ---: | --- |
| holdout V13 | 12 | **authoritative promotion holdout (pending seal)** — span-text disjoint; proposition-template Jaccard `<0.40`; Gate-faithful gold |
| adversarial V11 | 10 | **authoritative promotion adversarial (pending seal)** — novel Glimmerfen vocab + Jaccard `<0.40`; Gate E2 textual; no-`now` grounding trap |
| holdout V12 / Adv V10 | 12 / 10 | observed regression only (gold/Gate defects retained) |
| holdout V11 / Adv V9 | 12 / 10 | observed regression only (span reuse + paraphrased skeletons retained) |
| holdout V10 / Adv V8 | 12 / 10 | observed regression only (audit drift + Gate C/E2 defects retained) |
| holdout V9 / Adv V7 | 12 / 10 | observed regression only (gold defects retained) |
| holdout V8 / Adv V6 | 12 / 10 | observed regression only |
| holdout V7 / Adv V5 | 9 / 8 | abstention regression only |

Audits: `evals/graph_memory_layer/examples/temporal_shadow_holdout_v13/GOLD-AUDIT.md`, `.../temporal_shadow_adversarial_v11/GOLD-AUDIT.md`.

## Matrix D — observed promotion (holdout V12 / Adv V10, retired)

Seal/execution: `a7a9d5c321e7f57ddc95303705a8a8bac94fcd82` · candidate SHA `3af1e470…` · calibration `temporal-prompt-calibration:3db8507237419d92` · run repo SHA `e63bc58d…`

| Cohort | Success | Status min | Wrong lane | Wrong value | Unsafe | Source leak | Grounding |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| development | 0/3 | — | 0 | 0 | 0 | 0 | 3 |
| holdout V12 | 0/3 | — | 0 | 0 | 0 | 0 | 3 |
| adversarial V10 | 1/3 | 0.9 | 0 | 5 | **1** | 0 | 2 |

Machine decision: `ITERATE_PROMPT` (`candidate_unsafe_over_resolution=1`). Human gates also fail: grounding collapses on development and holdout; Adv V10 still over-resolves on one run. `PROMPT_READY_FOR_BROADER_SHADOW` remains disallowed.

## Interpretation

1. Process defects from PR #468 reviews are addressed in V13/Adv V11 authoring: span-text `isdisjoint` including evaluation cohort; adversarial and holdout proposition-template Jaccard guards; GOLD-AUDIT binds proposition/lane/phrase mechanically (not Gate correctness).
2. V12/Adv V10 observed promotion under `a7a9d5c3…` was honestly red — unsafe over-resolution and grounding instability blocked readiness; those cohorts are retired without in-place gold edits.
3. V13/Adv V11 await seal and first provider run before any new promotion decision.
4. Next prompt version (`tl01h-v1` or equivalent) should target abstention safety and grounding completeness. Do not mutate `tl01g-v1`; do not revive V8–V12 / Adv V6–V10 as promotion authority.

## Recommendation precedence applied

```text
unsafe over-resolution > 0 and grounding failures on authoritative promotion
→ ITERATE_ABSTENTION_PROMPT
(not PROMPT_READY; not ADVANCE_TO_TEXTUAL_NORMALIZATION)
```

## Explicit non-claims

* No Temporal Kernel / packet / renderer / threshold / runner changes.
* No graph writes or Timeline surface work.
* V8–V11 and Adv V6–V9 are **not** independent promotion evidence.
* Matrices A–C under candidate hash `60680e1f…` are not authority for freeze `3af1e470…`.
* World-line / branch-divergence encoding remains deferred; temporal ambiguity stays epistemic.

## Handback

```text
Candidate: tl01g-v1 (freeze 67408bd8…; prompt hash 3af1e470…)
Control: tl01f-v1
Last observed seal/execution: a7a9d5c321e7f57ddc95303705a8a8bac94fcd82 (V12/Adv V10 — retired)
Promotion cohorts: holdout V13 + adversarial V11 (SEAL_PENDING)
Last observed promotion decision: ITERATE_PROMPT (V12/Adv V10 unsafe over-resolution=1)
Human recommendation: ITERATE_ABSTENTION_PROMPT
Next: seal V13/Adv V11; run promotion calibration; do not mutate tl01g-v1; do not revive V8–V12 / Adv V6–V10 as promotion authority
```
