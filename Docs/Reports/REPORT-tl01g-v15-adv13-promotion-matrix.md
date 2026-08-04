# REPORT — TL01G V15 / Adv V13 Promotion Matrix

**Authoritative human disposition:** `PROMOTION_EVIDENCE_INCOMPLETE`
**PR:** https://github.com/Drakosfire/DungeonMindBuddy/pull/500
**Branch:** `timeline/tl01g-v15-adv13-promotion-matrix`
**Handoff:** `Docs/Plans/HANDOFF-TIMELINE-tl01g-v15-adv13-promotion-matrix.md`
**Rebased base / execution ancestry:** `dd1a7f2a2783e2a2fb189150bd837065122bee8f`
**Certification SHA:** `24679b19ac093cdbefa430cb0e930dff8c8a6dae`
**Provider execution SHA (singleton):** `71c8af5480114de4a7f50cc6099df37f46eb237d`
**Evidence commit (aggregate + initial report body):** `3ea7b1d82f5addffbb6021102adaecd8906820fb`
**Review-cycle-1 report correction:** `4a09cad35dd63eb19c5533ccdf6a0bc9e181d2ca`
**Review-cycle-2 report correction:** `ed43f2a7fed7bb33057b3142fb259770a337eb79` (docs-only; no provider retry; no aggregate rewrite)
**Model:** `gpt-5.4-mini`
**Calibration ID:** `temporal-prompt-calibration:9d9b5d09a79af1b2`
**Live invocations:** **1** (zero retry)
**Provider attempts:** **18 / 18** (every attempt has a response ID)
**Machine decision (non-authoritative):** `ITERATE_PROMPT` (`candidate_unsafe_over_resolution=4`)
**Seals verified:** `true`

## Verdict

The one authorized matrix completed with a clean singleton execution SHA and
unchanged certified V15/Adv13 bytes. It does **not** isolate a candidate-only
prompt defect suitable for `tl01h-v1`.

Control and candidate both collapse on the development phrase-grounding path
(3/3 each). On Adv V13, both prompts over-resolve the same source-time trap
rows; control has **more** `unsafe_over_resolution` (6) than candidate (4).
Machine `ITERATE_PROMPT` therefore over-claims candidate isolation.

A separate **candidate-only V15 signal** exists on `assertion:1131fb59ebcaae89`
(baseline exact 3/3; candidate two phrase-grounding failures + one wrong-value
run). That signal is real and must be recorded, but it does **not** outrank the
shared development collapse under §6 precedence.

Human precedence selects **`PROMOTION_EVIDENCE_INCOMPLETE`**.

## Frozen identities (unchanged)

| Identity | Value |
|---|---|
| Control | `tl01f-v1` / `7a9d27c3a9980893f18757d7a5fe0612cf67f9aad8dfd2ccb20f9e3c667b7143` |
| Candidate | `tl01g-v1` / `3af1e470e304008d2490ba73e1a53628519c211bb54e17a10cd4c694beae9013` |
| Packet | `tl01c-packet-v1` |
| Renderer | `render_temporal_shadow_user_content_v2` |
| Runner / schema / tests / extraction blobs | Exact §2 pins at execution SHA (`45b01c78…`, `3e4fcaa2…`, `f233fdab…`, `bcf279c3…`, `05fc8c1a…`) |

## Six-lane × three-repetition outcomes

| Lane | Cohort | run-01 | run-02 | run-03 |
|---|---|---|---|---|
| baseline (`tl01f-v1`) | development | grounding_failure | grounding_failure | grounding_failure |
| baseline | holdout V15 | ok | ok | ok |
| baseline | Adv V13 | ok | ok | ok |
| candidate (`tl01g-v1`) | development | grounding_failure | grounding_failure | grounding_failure |
| candidate | holdout V15 | grounding_failure | grounding_failure | ok |
| candidate | Adv V13 | ok | ok | ok |

All 18 manifests share provider execution SHA `71c8af5480114de4a7f50cc6099df37f46eb237d`.

### Provider response IDs

| Lane | Cohort | run | Response ID |
|---|---|---|---|
| baseline | development | 01 | `resp_009a416b2b17583a006a7122fa77408196b488ddb5e448792a` |
| baseline | development | 02 | `resp_04330907126b6047006a71232396e48195a91c29ab12b50168` |
| baseline | development | 03 | `resp_01141bbee6f1d9c6006a712349d0448193a8c3ff32e6dd51dd` |
| baseline | holdout | 01 | `resp_093f23fefeb72265006a7122ff06c88195b2de66478f468f1b` |
| baseline | holdout | 02 | `resp_06c8d36de57632c9006a712327c9648194b4277a4e64788df2` |
| baseline | holdout | 03 | `resp_0377823763d80c10006a712352c4ec8193b06b6b9eb7882732` |
| baseline | adversarial | 01 | `resp_0f1e8e780e18e766006a712306302c819793aa8289b7cb660f` |
| baseline | adversarial | 02 | `resp_0e9f8896e4b54c4e006a71232ebb0881968bee8b462151c838` |
| baseline | adversarial | 03 | `resp_0114607bc02f5cc7006a71235af6348193876714f2198e00e8` |
| candidate | development | 01 | `resp_07a9139d54f7f22a006a71230da9088194a9d8d540342fad33` |
| candidate | development | 02 | `resp_0ede9e9d5bff434b006a7123366578819095b9f248e9da24ec` |
| candidate | development | 03 | `resp_083ed2e073440a17006a71236223448195bb79e5ba1cf0fd18` |
| candidate | holdout | 01 | `resp_0728a36cc2971df6006a712312fb1881938ea315b10556dba9` |
| candidate | holdout | 02 | `resp_018b4aa103f9f6a8006a71233a7fd08190a06a5283c652828d` |
| candidate | holdout | 03 | `resp_08dc84e4efb23822006a7123666c9481968bb90393bdd79965` |
| candidate | adversarial | 01 | `resp_0327ec109c625eda006a71231a68908196ac8e27d0749a814f` |
| candidate | adversarial | 02 | `resp_0d40e74e8d51e016006a71234248d88196b99a792859b6c6c6` |
| candidate | adversarial | 03 | `resp_046deaec88500863006a71236dd5588195a014a8ef3d3f678a` |

## Aggregate metrics (observed; nulls remain unobserved)

| Lane | Cohort | success/fail | unsafe_over_resolution | wrong_temporal_value | status_mismatch | grounding_failures | source_leakage_fp |
|---|---|---:|---:|---:|---:|---:|---:|
| baseline | development | 0/3 | unobserved | unobserved | unobserved | **3** | unobserved |
| baseline | holdout V15 | 3/0 | **1** | **9** | **6** | 0 | **9** |
| baseline | Adv V13 | 3/0 | **6** | **13** | 0 | 0 | **4** |
| candidate | development | 0/3 | unobserved | unobserved | unobserved | **3** | unobserved |
| candidate | holdout V15 | 1/2 | 0* | **5*** | **1*** | **2** | 0* |
| candidate | Adv V13 | 3/0 | **4** | **14** | 0 | 0 | 0 |

\*candidate holdout comparison totals come from the single successful run only; the two
grounding failures leave those repetitions without comparison metrics (not observed zeros).

## Row-level failure classification

Handoff §6 requires **exactly one** named class per unique non-exact / failed
assertion pattern, drawn from:

`certified_input_or_gold_defect` · `shared_control_candidate_failure` ·
`evaluator_gold_representation_mismatch` · `exact_text_normalization_difference` ·
`actual_temporal_semantic_failure` · `actual_temporal_lane_or_status_failure` ·
`candidate_safety_or_source_time_failure` · `provider_or_infrastructure_failure` ·
`model_or_contract_noncompliance`

Frozen runner rule (`temporal_shadow_prompt_calibration.py`): phrase-grounding
misses are **prompt/model quality** (`model_or_contract_noncompliance`) unless the
evidence itself is unusable (then `BLOCKED_BY_EVIDENCE`). They are **not**
`provider_or_infrastructure_failure`. Every failure manifest here has a provider
response ID; the provider answered, and post-provider phrase grounding rejected the
returned `source_phrase`.

No `certified_input_or_gold_defect` and no `provider_or_infrastructure_failure`
patterns were observed.

| Class | Assertion / pattern | Where | Notes |
|---|---|---|---|
| `shared_control_candidate_failure` | `assertion:a73b9dc9bdfaa72c` (*Road observation*) | baseline+candidate development 5/6 cells (baseline 01–03; candidate 01–02) | `grounding_failure`: `source_phrase` not found verbatim in cited snippets (`'Road observation'` / `'connected_by_road'`). Shared evaluability collapse; mechanism is phrase-grounding quality, not infrastructure. |
| `model_or_contract_noncompliance` | `assertion:4e24f0fa3c99d487` (*Party at Copper and Quartz*) | candidate development run-03 only | Same `grounding_failure` code; phrase `'Party at Copper and Quartz'` not verbatim in snippets. Candidate-lane instance of phrase noncompliance on a different development assertion. |
| `model_or_contract_noncompliance` | `assertion:1131fb59ebcaae89` (*Bram Hollow is quay reckoner*) | candidate holdout run-01, run-02 | Phrase-grounding: `'Bram Hollow is quay reckoner'` not verbatim. **Candidate-only V15 signal:** baseline holdout is exact_match 3/3 on this assertion. |
| `actual_temporal_semantic_failure` | `assertion:1131fb59ebcaae89` | candidate holdout run-03 | Gold `valid.start` is session-21; prediction uses textual kind (`raw_expression` *became quay reckoner after the tally dispute*). Completes the candidate-only triple on this assertion (2 grounding + 1 wrong-value). |
| `shared_control_candidate_failure` | `assertion:0a21dac97f3021a6` (*shelves the Ashpetal folios*) | Adv V13 both lanes 3/3 | Gold `unresolved`; both prompts resolve (often inventing occurrence). Shared source-time / over-resolution trap. |
| `shared_control_candidate_failure` | `assertion:ea6b7307edde4448` (*will open Thornfen Beacon once the fog lifts*) | Adv V13 baseline 3/3 unsafe; candidate 1/3 unsafe (2/3 exact) | Shared over-resolution of certified unresolved future/prerequisite row; control fails more often. |
| `actual_temporal_lane_or_status_failure` | `assertion:6f267289e9f12821` (*tends the tide-horn*) | baseline holdout 2× `status_mismatch`; candidate holdout run-03 1× `status_mismatch` | Gold `unresolved` → predicted `not_applicable`. |
| `actual_temporal_semantic_failure` | `assertion:6f267289e9f12821` | baseline holdout run-03 only | `unsafe_over_resolution` to session-21 (source-time copy). Control-only on this cell. |
| `actual_temporal_lane_or_status_failure` | `assertion:a61c1383591400f3` (*intends to chart every shoal*) | baseline holdout 3/3 `status_mismatch` | Gold `unresolved` → `not_applicable`. Candidate holdout run-03 exact. |
| `actual_temporal_lane_or_status_failure` | `assertion:cdd4df453fb0efef` (*must appoint a pier scribe*) | baseline holdout run-03 `status_mismatch` | Gold `unresolved` → `not_applicable`. |
| `actual_temporal_semantic_failure` | `assertion:1191825403bf6375` (*vault sealed since spring thaw*) | baseline holdout runs where kind becomes session-21 | Gold textual `since the spring thaw`; prediction substitutes session provenance. |
| `exact_text_normalization_difference` | `assertion:1191825403bf6375` | baseline holdout run-02; candidate holdout run-03 | Textual kind retained; phrase/`raw_expression` extent differs (`the spring thaw` vs `became sealed since the spring thaw`). |
| `actual_temporal_semantic_failure` | `assertion:43f19c97a48f5add` (*leaves at dusk tide*) | baseline holdout 3/3 | Gold textual occurrence; prediction uses session-21. |
| `exact_text_normalization_difference` | `assertion:43f19c97a48f5add` | candidate holdout run-03 | Textual kind retained; `dusk tide` vs gold `at dusk tide`. |
| `actual_temporal_semantic_failure` | `assertion:a576743588c19513` (*ceased ringing … after the pier fire*) | baseline holdout 3/3 | Gold textual end; prediction uses session-21. |
| `exact_text_normalization_difference` | `assertion:a576743588c19513` | candidate holdout run-03 | Textual end retained; phrase/`raw_expression` extent differs. |
| `actual_temporal_semantic_failure` | `assertion:b49813f9a03057f6` (*stopped auditing the reef ledger*) | candidate holdout run-03 | Gold session-21 end; prediction textual *after the pier vote*. Baseline exact 3/3. |
| `actual_temporal_semantic_failure` | `assertion:d72fbcdad287e1a5` (*became open since the lantern edict*) | baseline Adv runs substituting session-19 | Source-time kind swap on a resolved textual start. |
| `exact_text_normalization_difference` | `assertion:d72fbcdad287e1a5` | candidate Adv 3/3; baseline Adv run-02 | Textual kind; phrase/`raw_expression` / `campaign_id` extent vs gold. |
| `exact_text_normalization_difference` | `assertion:3057260d5a4c0cdd` (*bolts … at nightfall*) | both lanes Adv 3/3 | One class for this pattern: same textual kind/lane; primary delta is phrase/`raw_expression` extent (`at nightfall` vs longer bolt phrase). Secondary note only (not a second class): gold `campaign_id: null` vs model `campaign_id: "longmont-c2"`. |
| `exact_text_normalization_difference` | `assertion:3ed3e502da2f502a` (*cracked nine winters earlier*) | both lanes Adv 3/3 | Textual kind; primary delta is phrase extent (*during the frost gale*). Secondary note: `campaign_id` null→`longmont-c2`. |
| `exact_text_normalization_difference` | `assertion:bd8eefd165efe613` (*lights … at moonrise*) | both lanes Adv 3/3 | Textual kind; primary delta is phrase extent (*when fog rolls in* / longer phrase). Secondary note: `campaign_id` null→`longmont-c2`. |
| `actual_temporal_semantic_failure` | `assertion:692dbca9df0475f8` (*stopped recording beacon fuel tallies*) | intermittent both lanes | Gold session-19 end; some runs emit textual end (or mixed fields) instead of exact session match. |

Large headline `wrong_temporal_value` totals therefore mix semantic kind swaps and
phrase-extent normalization (often with a secondary gold `campaign_id`
representation delta noted on the same row). They are not alone a prompt-iteration
proof. No separate primary `evaluator_gold_representation_mismatch` row is claimed
for these Adv textual-point cells; that would double-classify overlapping patterns.

## Shared-control / candidate analysis

1. **Development phrase grounding** collapses for **both** prompts on
   `assertion:a73b9dc9bdfaa72c` → comparison unobservable there.
   Class: `shared_control_candidate_failure` (mechanism:
   `model_or_contract_noncompliance` / phrase fidelity — **not** provider
   infrastructure).
2. **Adv source-time traps** (`0a21dac97…`, `ea6b7307…`) fail for **both** prompts;
   control unsafe count is higher (6 vs 4).
3. **Candidate-only V15 signal (must not be hidden):**
   `assertion:1131fb59ebcaae89` is exact for baseline holdout 3/3, while candidate
   holdout has run-01/02 `grounding_failure` and run-03
   `actual_temporal_semantic_failure`. Recorded as candidate-specific quality
   evidence; **does not** authorize `ITERATE_PROMPT` while shared development
   collapse remains.
4. Machine diagnostic `candidate_unsafe_over_resolution=4` counts only candidate
   Adv unsafe totals and ignores larger control Adv unsafe (6) and shared
   development grounding collapse.
5. Therefore `ITERATE_PROMPT` is **not** supported as an isolated candidate claim.

## Human precedence

Selected: **`PROMOTION_EVIDENCE_INCOMPLETE`**

| Precedence check | Result |
|---|---|
| Integrity / seals / digests / singleton SHA / 18 outcomes | Pass |
| Shared control/candidate evaluability on development | Fail — shared phrase-grounding collapse |
| Shared source-time unsafe on certified Adv traps | Fail — both lanes over-resolve |
| Representation-only only? | No — shared unsafe + shared grounding dominate |
| Isolated candidate semantic/safety defect? | Partial candidate-only V15 signal on `1131fb59…`, but shared collapse has higher precedence |
| All readiness gates green? | No |

Machine `ITERATE_PROMPT` is retained as evidence and **overridden**.

## Named successor

```text
TIMELINE: recover shared grounding path and source-time licensing before next certified promotion matrix
```

Do **not** author `tl01h-v1` from this matrix. Do **not** repair or rerun V15/Adv13.
If a later design requires new fixtures, author a fresh certified pair after the shared
grounding/source-time root cause is addressed. The candidate-only V15
`assertion:1131fb59ebcaae89` pattern may inform that later design; it is not
authority to iterate the prompt from this incomplete matrix.

## Explicit non-claims

- No producer cutover, graph adoption, Timeline API/UI, or Build/Statblock integration
- No prompt/packet/renderer/runner/schema/threshold edits in this PR
- No textual-normalization implementation
- No broader-shadow readiness
- No provider retry / second matrix / aggregate rewrite in review cycles 1–2

## Pre-live evidence (before first provider attempt)

Provenance: recorded at clean worktree on branch tip immediately before live CLI;
provider execution SHA became `71c8af5480114de4a7f50cc6099df37f46eb237d` after the
`.gitignore` nano-commit (`chore(eval): track tl01g promotion-v15 aggregate`).

| Command / check | Exact result |
|---|---|
| `git merge-base --is-ancestor origin/main HEAD` (then `dd1a7f2a…`) | yes |
| `git merge-base --is-ancestor 24679b19… HEAD` | yes |
| `git rev-parse HEAD:evals/.../temporal_shadow_prompt_calibration.py` | `45b01c78f24ada02dcaa4b89bfba6da90c745445` |
| `git rev-parse HEAD:tests/test_temporal_shadow_prompt_calibration.py` | `3e4fcaa20ee2ef7aa92f4d485c46c2b671c860d9` |
| `git rev-parse HEAD:tests/test_temporal_shadow_grounding_path.py` | `f233fdaba86673eef760ccf42e015ddc175dc2b6` |
| `git rev-parse HEAD:src/graph_memory/temporal_shadow_extraction.py` | `bcf279c387869f9fe675221894e8dc55d6640b95` |
| `git rev-parse HEAD:src/graph_memory/temporal_shadow_extraction_schema.py` | `05fc8c1a860e187edc4e84cd4b54ea0b3e475e5e` |
| `sha256sum -c /tmp/tl01g-v15-adv13-certified.sha256` | **33/33 OK** |
| `git diff --exit-code 24679b19… -- <certified paths>` | clean (no certified byte drift) |
| `uv run pytest -q tests/test_temporal_shadow_extraction_tl01g.py` | `98 passed` |
| `uv run pytest -q tests/test_temporal_shadow_prompt_calibration.py tests/test_temporal_shadow_grounding_path.py` | `113 passed, 1 skipped` |
| `uv run ruff check tests/test_temporal_shadow_extraction_tl01g.py` | `All checks passed!` |
| `promotion-v15/` artifact directory | **absent** before live call |
| Live CLI invocations before this matrix | **0** |

## Post-live evidence (after matrix; review cycle 2 re-verification)

Provenance: zero-provider deterministic re-run for review cycle 2 on exact head
`ed43f2a7fed7bb33057b3142fb259770a337eb79` (parent `4a09cad35dd63eb19c5533ccdf6a0bc9e181d2ca`).
No provider calls. Aggregate, runner, certified inputs, and provider manifests
unchanged. A follow-up docs pin may name this head without changing aggregate or
provider evidence.

| Command / check | Exact result |
|---|---|
| `uv run pytest -q tests/test_temporal_shadow_extraction_tl01g.py` | `98 passed in 1.72s` |
| `uv run pytest -q tests/test_temporal_shadow_prompt_calibration.py tests/test_temporal_shadow_grounding_path.py` | `113 passed, 1 skipped in 7.94s` |
| `uv run ruff check tests/test_temporal_shadow_extraction_tl01g.py` | `All checks passed!` |
| `sha256sum -c /tmp/tl01g-v15-adv13-certified.sha256` | `33/33 OK (all files)` |
| `git merge-base --is-ancestor 24679b19ac093cdbefa430cb0e930dff8c8a6dae HEAD` | yes (`CERT_ANCESTOR_OK`) |
| `git diff --check` | clean (after cycle-2 trailing-whitespace fix) |
| Pinned blob re-check vs §2 | exact match (`45b01c78f24ada02dcaa4b89bfba6da90c745445`, `3e4fcaa20ee2ef7aa92f4d485c46c2b671c860d9`, `f233fdaba86673eef760ccf42e015ddc175dc2b6`, `bcf279c387869f9fe675221894e8dc55d6640b95`, `05fc8c1a860e187edc4e84cd4b54ea0b3e475e5e`) |
| Live invocations (artifact inventory) | **1** matrix directory; **0** `run-04`; no second promotion root |
| Provider attempts | **18 / 18**; singleton SHA set `{71c8af5480114de4a7f50cc6099df37f46eb237d}` |
| Retry / second matrix | **none** |

### Exact changed-path proof (`dd1a7f2a…`…`ed43f2a7…`)

Literal command output against execution base at verified cycle-2 head
`ed43f2a7fed7bb33057b3142fb259770a337eb79` for the four §4 paths:

```text
git diff --name-only dd1a7f2a2783e2a2fb189150bd837065122bee8f...ed43f2a7fed7bb33057b3142fb259770a337eb79 -- \
  .gitignore \
  Docs/Plans/HANDOFF-TIMELINE-tl01g-v15-adv13-promotion-matrix.md \
  Docs/Reports/REPORT-tl01g-v15-adv13-promotion-matrix.md \
  evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01g/promotion-v15/calibration/aggregate.json
.gitignore
Docs/Plans/HANDOFF-TIMELINE-tl01g-v15-adv13-promotion-matrix.md
Docs/Reports/REPORT-tl01g-v15-adv13-promotion-matrix.md
evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01g/promotion-v15/calibration/aggregate.json
```

```text
git diff --stat dd1a7f2a2783e2a2fb189150bd837065122bee8f...ed43f2a7fed7bb33057b3142fb259770a337eb79 -- \
  .gitignore \
  Docs/Plans/HANDOFF-TIMELINE-tl01g-v15-adv13-promotion-matrix.md \
  Docs/Reports/REPORT-tl01g-v15-adv13-promotion-matrix.md \
  evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01g/promotion-v15/calibration/aggregate.json
 .gitignore                                         |    3 +
 ...FF-TIMELINE-tl01g-v15-adv13-promotion-matrix.md |  893 +++++++++++
 .../REPORT-tl01g-v15-adv13-promotion-matrix.md     |  291 ++++
 .../tl01g/promotion-v15/calibration/aggregate.json | 1695 ++++++++++++++++++++
 4 files changed, 2882 insertions(+)
```

Allowlist equality: sorted changed paths equal the four §4 tracked paths.
**Paths outside §4: none.**

## Aggregate path

`evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01g/promotion-v15/calibration/aggregate.json`

## Baseline failures / waivers / stop conditions

- Baseline failures: **none** on deterministic gates
- Waivers: **none**
- Stop conditions during execution: **none**
- Post-matrix disposition stop for prompt iteration: shared phrase-grounding + shared Adv unsafe (candidate-only V15 `1131fb59…` recorded, not dispositive alone)
