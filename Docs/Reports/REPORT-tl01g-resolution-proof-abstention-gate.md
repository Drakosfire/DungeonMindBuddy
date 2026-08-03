# REPORT — TL01G: Resolution-Proof Abstention Gate

**Created:** 2026-08-01
**Updated:** 2026-08-03 (PR #496: V14/Adv V12 sealed, observed, retired **`PROMOTION_EVIDENCE_INCOMPLETE`**)
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
| observed V12 / Adv V10 | exploratory / regression only (gold/Gate defects) | `ITERATE_PROMPT` | `candidate_unsafe_over_resolution=1` (defective gold) |
| **observed V13 / Adv V11** | **retired** (Adv replay + V13 Gate E3/value defects; matrix not evaluable) | **`ITERATE_PROMPT`** | **`candidate_grounding_failures=9`** (comparison metrics unobserved) |
| **observed V14 / Adv V12** | **retired** (PR #496; Adv V12 ungrounded `since the equinox flood`; 18/18 attempts observed) | **`ITERATE_PROMPT`** (machine; overridden) | **`PROMOTION_EVIDENCE_INCOMPLETE`** — invalid sealed gold; no authoritative promotion matrix |

**Human roadmap recommendation:** PR #496 completed the attempted fresh promotion matrix as **`PROMOTION_EVIDENCE_INCOMPLETE`**. Author a Gate-faithful successor cohort pair (holdout >14, adversarial >12) before another promotion claim. **Not** yet `ITERATE_ABSTENTION_PROMPT` as an isolated prompt diagnosis. **No** `tl01h-v1` from the V14/Adv V12 matrix.

TL01 may **not** advance to broader-shadow readiness. There is currently **no authoritative promotion matrix**. Candidate runs under seal `33bae348…` all failed before comparison (`0/9`; `candidate_grounding_failures=9`). Control collapsed too (`1/9` success). Aggregate `total_unsafe_over_resolution=0` is **not** an observed safety result: failed run records store `unsafe_over_resolution_count: null`, and those absences were totaled as zero. V13/Adv V11 gold is retained unchanged as regression evidence only.

## Integrity recovery timeline

| Step | SHA | Role |
| --- | --- | --- |
| Prompt-only freeze after Example 6 / Gate C repair | `67408bd871ba684e70ddf6e53dd7088d0036a475` | immutable candidate text |
| Retire V8/V6; span-text fingerprints; Adv template guards | `09c2c75e…` | process |
| Author then seal V9 / Adv V7 | `b1843ff6681ed92f12ba3657527d2b608f49cc95` | **retired** — gold contradicted Gates B/C/D after observation |
| Retire V9/V7; fail-closed span guard; seal V10 / Adv V8 | `046093fd899e1b286329b0e0bf6b09b6aa0e60d6` | **retired** — GOLD-AUDIT≠fixture; Gate C/E2 gold defects after observation |
| Retire V10/Adv V8; audit ID/status tests; span EOF bounds; seal V11 / Adv V9 | `a3f108f2fa64a3ac5c0146acbc25d7b904fcacc2` | **retired** — reused observed spans; Adv V9 paraphrased Adv V8 |
| Retire V11/Adv V9; restore span `isdisjoint`; Jaccard templates; audit proposition/lane/phrase; seal V12 / Adv V10 | `a7a9d5c321e7f57ddc95303705a8a8bac94fcd82` | **retired** — gold/Gate defects |
| Retire V12/Adv V10; proposition-template Jaccard (holdout); seal V13/Adv V11 | `33bae3485babb0d15373b91b0cbcb13282b42491` | **retired after observation** — Adv proposition replay; V13 Gate E3 / postponement-value defects; grounding collapse |
| Preserve grounding diagnostics; fail-closed auto-discovery for fresh adversarial/holdout proposition-template Jaccard; positive Gate E3 boundary narration; exact on-disk matrix match for reaggregate; full-hex immutable provider SHA; rebuild committed aggregate from on-disk manifests | *(PR468 recovery tip)* | process — **no new promotion cohort** |
| Seal V14 / Adv V12; one 18-attempt promotion matrix (PR #496) | `cde3b48d5b95ba4fc1f7c779993c2497f66914f7` seal · `d1b5cc60604ba888985013c0093e0605f0ab158d` provider execution | **retired after observation** — Adv V12 ungrounded `since the equinox flood`; human disposition **`PROMOTION_EVIDENCE_INCOMPLETE`**; machine `ITERATE_PROMPT` overridden; no `tl01h-v1` |
| Gate-faithfulness retirement tests + future-cohort grounding guard (PR #496 review) | `eefc8927c3e679c1688d1dd85f565f8d9eb3d9c8` merge | process — observed V14/Adv V12 bytes preserved; cutoffs now `LAST_RETIRED_HOLDOUT=14`, `LAST_RETIRED_ADVERSARIAL=12` |

### Why V14/Adv V12 cannot remain promotion authority (PR #496)

Do **not** patch V14/Adv V12 gold in place (all **18** provider attempts observed under
`d1b5cc60604ba888985013c0093e0605f0ab158d`). Defects retained as incomplete promotion
evidence; human disposition **`PROMOTION_EVIDENCE_INCOMPLETE`** overrides machine
`ITERATE_PROMPT`:

- **Adv V12** assigns `valid_time.start.raw_expression = "since the equinox flood"` while
  owned source `valid-start-textual.md` only contains `"became shuttered at the equinox flood"`.
  Gate E3 / owned-evidence value grounding fails before promotion authority can attach.
- Large `wrong_temporal_value` totals mix representation mismatches with shared semantic
  kind swaps — not clean candidate isolation on trustworthy gold.
- No `tl01h-v1` may be named from this matrix. Successor work requires holdout >14 and
  adversarial >12 with pre-live `_collect_resolved_value_grounding_defects() == []`.

Durable report: [`REPORT-tl01g-v14-fresh-promotion-evidence.md`](REPORT-tl01g-v14-fresh-promotion-evidence.md).

### Why V13/Adv V11 cannot remain promotion authority

Do **not** patch V13/Adv V11 gold in place (provider outputs already observed under `33bae348…`). Defects retained as regression evidence:

- **Adv V11** reproduces Adv V10’s ten-row functional structure via noun substitution. Source-prose Jaccard can be padded below `0.40` while assertion labels/predicates remain copied (e.g. chancellor election-or-announcement and “left the coast three winters earlier” at proposition-template Jaccard `1.000`). Holdout got proposition-template comparison; adversarial did not.
- **V13** resolves “The rebel humans feel represented in Mirathorn” as `valid_time.end = session-7` from “no longer feel represented.” Session 7 reports a resulting attitude; it does not narrate the boundary occurring in-episode (Gate E3). Correct gold would be unresolved with both lanes null.
- **V13** records postponement occurrence as `raw_expression = "postponed until dawn"`. Dawn grounds the rescheduled raid (or end of postponed state), not when the postponement decision occurred (proposition-first grounding).
- Prior claim that unsafe over-resolution was “cleared to 0” under this matrix is invalid: **no candidate run produced evaluable comparison metrics**.

### Why V12/Adv V10 cannot remain promotion authority

Do **not** patch V12/Adv V10 gold in place. Defects retained as regression evidence:

- V12 spell-end transition marked valid-end; historical relationship marked occurrence; scale custody ambiguous replay of V11; festival postponement span reuse.
- Adv V10 grounding-trap used `now` while gold marked unresolved — defective gold, not trustworthy unsafe evidence.

### Fail-closed span independence

Resolved-span fingerprints fail before hashing when evidence refs are missing, paths are absent, line ranges are invalid/empty, **start or end exceeds file length**, normalized text is empty, or an assertion yields zero source-span fingerprints. Auto-discovered holdout successors (version suffix `> LAST_RETIRED_HOLDOUT_VERSION`) assert span-text **and** semantic-proposition fingerprint `isdisjoint` against all retired canonical dirs **and** earlier discovered successors (cumulative pool grows as each successor passes).

### Proposition / adversarial novelty

- Holdout: proposition-template Jaccard (label+predicate, entity scrub) `< 0.40` vs all prior canonical holdouts **and** earlier discovered holdout successors (cumulative comparison pool).
- Adversarial: source-prose Jaccard is **insufficient**. Fresh adversarial cohorts also require proposition-template Jaccard `< 0.40` vs all prior adversarial assertion labels/predicates **and** earlier discovered adversarial successors (cumulative comparison pool).
- **Fresh-cohort discovery** uses immutable cutoffs `LAST_RETIRED_HOLDOUT_VERSION=14` and `LAST_RETIRED_ADVERSARIAL_VERSION=11` (versioned dirs with suffix `> cutoff`). After PR #496, successor holdout must be >14 and adversarial >12. PRIOR tuple membership does **not** disable guards; non-numeric suffixes fail closed.

### GOLD-AUDIT ↔ fixture binding

Audit rows must bind ID, status, proposition, lane, and supporting phrase to sealed fixtures. **This proves mechanical fixture consistency only — not human Gate-faithfulness.** Additional audit cases check Gate E3 (episode boundary vs resulting-state report) and proposition-first value grounding (value must temporally modify the selected proposition).

**Future holdout overlays** (versions above the holdout cutoff) audit **both** `valid_time.start` and `valid_time.end` when non-null. Acceptance is **positive** boundary proof: at least one attached evidence span must match `_source_narrates_boundary` (transition cues such as became / stopped / ceased / ended / began to / started to / when they). Neutral restatements without those cues (e.g. “The treaty is in effect during Session 8”) fail. The resulting-state heuristic remains diagnostic only and is not the acceptance condition. Postponement-value defects still audit occurrence `raw_expression` on resolved rows.

### Reaggregate provenance (durable evidence)

`--reaggregate-only` now refuses unless the git worktree is clean (calibration artifacts excluded). Before rewriting `aggregate.json` it:

1. Discovers every published `run-manifest.json` / `failure-manifest.json` under `calibration/` and requires the requested lane/cohort/repetition matrix to equal that set exactly (omitted repetitions or omitted baseline-adversarial lanes fail closed).
2. Loads on-disk manifests and rejects ambiguous dirs (both success and failure manifests).
3. Requires each published manifest `case_digest` to match the executed case file SHA256.
4. Requires exactly one provider `repository_sha` across the matrix (`provider_execution_sha`); **exact full lowercase 40-char hex commit SHAs only** — dirty/suffixed values, branch/tag refs, and abbreviated SHAs are rejected; `git rev-parse <sha>` must equal the supplied value.
5. Verifies development/holdout/adversarial case/base/gold/evidence bytes at that provider commit (sealed holdout/adversarial via `verify_cohort_seal` with `execution_commit_sha=provider_execution_sha`).
6. Passes `expected_repository_sha=provider_execution_sha` into cohort aggregation; records `provider_run_repository_shas=[provider_execution_sha]` while `aggregate_build_sha` / aggregate `repository_sha` remain the current clean HEAD rebuild tip.

### Grounding diagnostics

Per-run `failure-manifest.json` already carries `affected_assertion_id`, `diagnostics`, and `foreign_evidence_attempts`. The **rebuilt committed aggregate** (`a1dd130979808f2f`, build SHA `8e2fe045…`) now preserves those fields in `run_records` (not only `failure_code` + `provider_response_id`). All 17 failed runs include `affected_assertion_id` and `failure_diagnostics`; `foreign_evidence_attempts` is `0` on sampled grounding rows. Decision diagnostics include `candidate_grounding_failures=9` and `candidate_comparison_metrics_unobserved`.

## Frozen identities

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
| Last observed cohort seal (retired) | `33bae3485babb0d15373b91b0cbcb13282b42491` (V13 / Adv V11) |
| Repetitions | 3 |

## Aggregate artifacts

* Exploratory / regression-only:
  * `.../tl01g/regression-lane|abstention|legacy/calibration/aggregate.json`
  * Prior V8–V12 / Adv V6–V10 promotion aggregates (git history / overwritten on disk)
* **Last observed matrix (V13 / Adv V11) — not promotion authority:**
  * `evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01g/promotion/calibration/aggregate.json` — `temporal-prompt-calibration:a1dd130979808f2f` (**rebuilt** from on-disk run manifests at `8e2fe045…`; durable evidence with `affected_assertion_id`, `failure_diagnostics`, `foreign_evidence_attempts`, and decision note `candidate_comparison_metrics_unobserved`)
  * Per-run manifests under `.../promotion/calibration/{baseline,candidate}/{development,holdout,adversarial}/run-0N/` remain gitignored; the committed aggregate is the durable evidence surface
* **V14 / Adv V12 matrix (PR #496) — not promotion authority:**
  * `evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01g/promotion-v14/calibration/aggregate.json` — `temporal-prompt-calibration:a4d817300eab3c82` (18/18 attempts observed; human disposition **`PROMOTION_EVIDENCE_INCOMPLETE`**)
  * See [`REPORT-tl01g-v14-fresh-promotion-evidence.md`](REPORT-tl01g-v14-fresh-promotion-evidence.md)

## Cohorts

| Cohort | Rows | Role |
| --- | ---: | --- |
| holdout V14 | 12 | observed incomplete promotion evidence — Adv V12 ungrounded gold; seal `cde3b48d…`; retired PR #496 |
| adversarial V12 | 10 | observed incomplete promotion evidence — ungrounded `since the equinox flood`; retired PR #496 |
| holdout V13 | 12 | observed regression only — Gate E3 / postponement-value defects retained; seal `33bae348…` |
| adversarial V11 | 10 | observed regression only — Adv V10 proposition-template replay retained |
| holdout V12 / Adv V10 | 12 / 10 | observed regression only |
| holdout V11 / Adv V9 … V8 / Adv V6 | … | observed regression only |
| holdout V7 / Adv V5 | 9 / 8 | abstention regression only |

**No authoritative promotion holdout/adversarial pair is currently sealed for a fresh run.** V14/Adv V12 (PR #496) completed the attempted matrix as **`PROMOTION_EVIDENCE_INCOMPLETE`**.

## Matrix D — last observed run (holdout V13 / Adv V11) — not authority

Seal/execution: `33bae3485babb0d15373b91b0cbcb13282b42491` · candidate SHA `3af1e470…` · calibration `temporal-prompt-calibration:a1dd130979808f2f` · aggregate build `8e2fe045…`

### Candidate

| Cohort | Success | Status min | Wrong lane | Wrong value | Unsafe | Source leak | Grounding |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| development | 0/3 | — | — | — | **unobserved** | — | 3 |
| holdout V13 | 0/3 | — | — | — | **unobserved** | — | 3 |
| adversarial V11 | 0/3 | — | — | — | **unobserved** | — | 3 |

### Control (baseline `tl01f-v1`)

| Cohort | Success | Notes |
| --- | ---: | --- |
| development | 0/3 | all `grounding_failure` |
| holdout V13 | 1/3 | 1 grounding + 1 `invalid_model_output` |
| adversarial V11 | 0/3 | all `grounding_failure` |

Machine decision: `ITERATE_PROMPT` (`candidate_grounding_failures=9`). **17 of 18** control+candidate runs failed before normal comparison. The candidate is not promotable, but the experiment does **not** isolate an abstention-prompt defect: both lanes share the post-provider verbatim `source_phrase` grounding validator.

### Grounding failure mode (shared)

Sampled committed aggregate `run_records` (both lanes) show `foreign_evidence_attempts: 0` and diagnostics of the form `source_phrase='…'` — the verbatim-miss branch in `_require_grounded_source_phrase` / `ground_and_convert_model_batch`, not a candidate-only code path. Example: development both lanes fail on `assertion:4e24f0fa3c99d487` with `source_phrase='Party at Copper and Quartz'` (present in rebuilt aggregate `run_records`).

Known-good smoke still exists via FakeClient gold replay and older regression-lane seals (V5/Adv V3) — not via Gate-repaired V13/V11 under live promotion.

## Interpretation

1. V14/Adv V12 (PR #496) are retired without in-place gold edits. Adv V12 gold is ungrounded (`since the equinox flood`); disposition **`PROMOTION_EVIDENCE_INCOMPLETE`**; no `tl01h-v1`.
2. V13/Adv V11 are retired without in-place gold edits. Adv V11 is not independent promotion evidence; V13 retains Gate E3 and postponement-value gold defects.
3. Aggregate unsafe totals of `0` under all-failure cohorts must not be read as “unsafe cleared.” Comparison metrics were unobserved on V13/V11; V14/Adv V12 had evaluable runs but invalid gold blocks promotion authority.
4. Do not mutate `tl01g-v1`. Do not revive V8–V14 / Adv V6–V12 as promotion authority.

## Recommendation precedence applied

```text
candidate comparison metrics unobserved
+ control also grounding-collapsed
→ DIAGNOSE_GROUNDING_PATH
(not ITERATE_ABSTENTION_PROMPT as isolated prompt verdict;
 not PROMPT_READY; not ADVANCE_TO_TEXTUAL_NORMALIZATION)
```

## Explicit non-claims

* No Temporal Kernel / packet / renderer / threshold / runner behavior changes claimed as fixed by this recovery (diagnostic preservation only).
* No graph writes or Timeline surface work.
* V8–V13 and Adv V6–V11 are **not** independent promotion evidence.
* Matrices under pre-freeze candidate hashes are not authority for freeze `3af1e470…`.
* World-line / branch-divergence encoding remains deferred.
* GOLD-AUDIT mechanical binding is not proof of Gate-faithfulness.
* `total_unsafe_over_resolution=0` with `success_count=0` is not an observed safety measurement.

## Handback

```text
Candidate: tl01g-v1 (freeze 67408bd8…; prompt hash 3af1e470…)
Control: tl01f-v1
Last observed seal (V14/Adv V12): cde3b48d5b95ba4fc1f7c779993c2497f66914f7 (RETIRED INCOMPLETE — PR #496)
Prior retired seal (V13/Adv V11): 33bae3485babb0d15373b91b0cbcb13282b42491 (RETIRED)
Promotion authority: none
Last matrix (V14/Adv V12): PROMOTION_EVIDENCE_INCOMPLETE (18/18 observed; Adv V12 ungrounded gold)
Human recommendation: author Gate-faithful successor cohort pair (holdout >14, adversarial >12)
Next: new handoff for fresh cohort pair with pre-live Gate E3/value grounding over every resolved annotation;
      do not mutate tl01g-v1; do not name tl01h-v1 from V14/Adv V12 evidence;
      do not revive V8–V14 / Adv V6–V12 as promotion authority.
      PR486 GROUNDING_PATH_READY remains smoke prerequisite only.
```
