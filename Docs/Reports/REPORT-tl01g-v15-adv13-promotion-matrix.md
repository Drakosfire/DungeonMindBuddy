# REPORT — TL01G V15 / Adv V13 Promotion Matrix

**Authoritative human disposition:** `PROMOTION_EVIDENCE_INCOMPLETE`  
**PR:** https://github.com/Drakosfire/DungeonMindBuddy/pull/500  
**Branch:** `timeline/tl01g-v15-adv13-promotion-matrix`  
**Handoff:** `Docs/Plans/HANDOFF-TIMELINE-tl01g-v15-adv13-promotion-matrix.md`  
**Rebased base / `origin/main`:** `dd1a7f2a2783e2a2fb189150bd837065122bee8f`  
**Certification SHA:** `24679b19ac093cdbefa430cb0e930dff8c8a6dae`  
**Provider execution SHA (singleton):** `71c8af5480114de4a7f50cc6099df37f46eb237d`  
**Final head (this report commit):** `3ea7b1d82f5addffbb6021102adaecd8906820fb`  
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

Control and candidate both collapse on the development grounding path (3/3 each).
On Adv V13, both prompts over-resolve the same source-time trap rows; control has
**more** `unsafe_over_resolution` (6) than candidate (4). Machine `ITERATE_PROMPT`
therefore over-claims candidate isolation.

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

| Lane | Cohort | success/fail | unsafe_over_resolution | wrong_temporal_value | grounding_failures | source_leakage_fp |
|---|---|---:|---:|---:|---:|---:|
| baseline | development | 0/3 | unobserved | unobserved | **3** | unobserved |
| baseline | holdout V15 | 3/0 | **1** | **9** | 0 | **9** |
| baseline | Adv V13 | 3/0 | **6** | **13** | 0 | **4** |
| candidate | development | 0/3 | unobserved | unobserved | **3** | unobserved |
| candidate | holdout V15 | 1/2 | 0* | **5*** | **2** | 0* |
| candidate | Adv V13 | 3/0 | **4** | **14** | 0 | 0 |

\*candidate holdout comparison totals come from the single successful run only; the two
grounding failures leave those repetitions without comparison metrics (not observed zeros).

## Row-level failure classification

| Class | Where observed | Named patterns |
|---|---|---|
| `provider_or_infrastructure_failure` / grounding path | baseline+candidate development (3/3); candidate holdout (2/3) | Shared `grounding_failure` — not candidate-isolated |
| `candidate_safety_or_source_time_failure` **shared with control** | Adv V13 both lanes | `assertion:0a21dac97f3021a6` (*shelves the Ashpetal folios*) gold `unresolved`; both prompts resolve (often to session-19). Baseline 3/3 unsafe; candidate 3/3 unsafe |
| `candidate_safety_or_source_time_failure` **shared with control** | Adv V13 both lanes | `assertion:ea6b7307edde4448` (*will open Thornfen Beacon once the fog lifts*) gold `unresolved`; baseline unsafe 3/3; candidate unsafe 1/3 (2/3 exact unresolved) |
| `candidate_safety_or_source_time_failure` (control) | baseline holdout | `assertion:6f267289e9f12821` source-time trap: 1× unsafe / 2× status_mismatch |
| `exact_text_normalization_difference` / `evaluator_gold_representation_mismatch` | Adv/holdout wrong_temporal_value mass | Phrase-extent and payload representation diffs (e.g. nightfall phrase variants; campaign_id presence). Not sufficient alone for normalization disposition while shared unsafe/grounding dominate |
| `actual_temporal_semantic_failure` / lane/status | mixed wrong_value / status_mismatch rows | Present on both prompts; not isolated to candidate |

No post-observation certified-input digest defect was found (`sha256sum -c` OK before and after).

## Shared-control / candidate analysis

1. **Development grounding** collapses for **both** prompts → comparison unobservable there.
2. **Adv source-time traps** fail for **both** prompts; control unsafe count is higher.
3. Machine diagnostic `candidate_unsafe_over_resolution=4` counts only candidate Adv unsafe
   totals and ignores the larger control Adv unsafe total (6) and shared development
   grounding collapse.
4. Therefore `ITERATE_PROMPT` is **not** supported as an isolated candidate claim.

## Human precedence

Selected: **`PROMOTION_EVIDENCE_INCOMPLETE`**

| Precedence check | Result |
|---|---|
| Integrity / seals / digests / singleton SHA / 18 outcomes | Pass |
| Shared control/candidate evaluability on development | Fail — grounding collapse both lanes |
| Shared source-time unsafe on certified Adv traps | Fail — both lanes over-resolve |
| Representation-only only? | No — unsafe + grounding dominate |
| Isolated candidate semantic/safety defect? | No — control shares (and exceeds) Adv unsafe |
| All readiness gates green? | No |

Machine `ITERATE_PROMPT` is retained as evidence and **overridden**.

## Named successor

```text
TIMELINE: recover shared grounding path and source-time licensing before next certified promotion matrix
```

Do **not** author `tl01h-v1` from this matrix. Do **not** repair or rerun V15/Adv13.
If a later design requires new fixtures, author a fresh certified pair after the shared
grounding/source-time root cause is addressed.

## Explicit non-claims

- No producer cutover, graph adoption, Timeline API/UI, or Build/Statblock integration
- No prompt/packet/renderer/runner/schema/threshold edits in this PR
- No textual-normalization implementation
- No broader-shadow readiness

## Pre-live / post-live evidence

| Check | Result |
|---|---|
| `origin/main` ancestor of HEAD | yes (`dd1a7f2a…`) |
| Certification ancestor | yes (`24679b19…`) |
| Pinned Git blobs | exact match to handoff §2 |
| Certified digests before calls | all OK |
| Certified digests after calls | all OK |
| TL01G tests | `98 passed` |
| Calibration + grounding tests (pre-live) | `113 passed, 1 skipped` |
| Ruff on TL01G tests | clean |
| `promotion-v15` absent before call | yes |
| Live invocations | 1 |
| Attempts | 18 |
| Retry / second matrix | none |
| Paths outside §4 tracked allowlist | none intended (handoff + `.gitignore` + aggregate + this report) |

## Aggregate path

`evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01g/promotion-v15/calibration/aggregate.json`

## Baseline failures / waivers / stop conditions

- Baseline failures: **none** on deterministic gates
- Waivers: **none**
- Stop conditions during execution: **none**
- Post-matrix disposition stop for prompt iteration: shared grounding + shared Adv unsafe
