# REPORT — TL01G Fresh Promotion Evidence (V14 / Adv V12)

**Status:** Complete sealed matrix observed; roadmap disposition **`ITERATE_PROMPT`**  
**Handoff:** `Docs/Plans/HANDOFF-TIMELINE-tl01g-fresh-promotion-evidence.md`  
**PR:** https://github.com/Drakosfire/DungeonMindBuddy/pull/496  
**Branch:** `timeline/tl01g-fresh-promotion-evidence`

## Provenance

| Item | Value |
|---|---|
| Rebased `origin/main` base | `4811741eb3f784171c3f9840a3b0f0ad345470e1` |
| Cohort fixture seal | `cde3b48d5b95ba4fc1f7c779993c2497f66914f7` |
| Provider execution SHA (singleton) | `d1b5cc60604ba888985013c0093e0605f0ab158d` |
| Aggregate path | `evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01g/promotion-v14/calibration/aggregate.json` |
| Calibration ID | `temporal-prompt-calibration:a4d817300eab3c82` |
| Model | `gpt-5.4-mini` |
| Seals verified | `true` |
| Live invocations | **1** (no retry) |
| Provider attempts | **18 / 18** (each with a response ID) |

### Frozen identities (unchanged)

| Identity | Value |
|---|---|
| Control | `tl01f-v1` / `7a9d27c3a9980893f18757d7a5fe0612cf67f9aad8dfd2ccb20f9e3c667b7143` |
| Candidate | `tl01g-v1` / `3af1e470e304008d2490ba73e1a53628519c211bb54e17a10cd4c694beae9013` |
| Packet | `tl01c-packet-v1` |
| Renderer | `render_temporal_shadow_user_content_v2` |

Prior cohorts V8–V13 / Adv V6–V11 and the V13/Adv V11 aggregate were not modified.
V14/Adv V12 fixture, gold, audit, case, source, and test bytes did not change after the
first provider attempt (README seal pointers were recorded in a pre-live follow-on commit).

## Six-lane × three-repetition outcomes

| Lane | Cohort | run-01 | run-02 | run-03 |
|---|---|---|---|---|
| baseline (`tl01f-v1`) | development | grounding_failure | grounding_failure | ok |
| baseline | holdout V14 | ok | ok | ok |
| baseline | Adv V12 | ok | invalid_model_output | ok |
| candidate (`tl01g-v1`) | development | grounding_failure | grounding_failure | grounding_failure |
| candidate | holdout V14 | ok | target_set_mismatch | ok |
| candidate | Adv V12 | ok | ok | ok |

All 18 manifests share provider execution SHA `d1b5cc60…`.

## Aggregate comparison metrics (observed successful runs)

| Lane | Cohort | success/fail | unsafe_over_resolution | wrong_temporal_value | wrong_temporal_lane | grounding_failures | notes |
|---|---|---:|---:|---:|---:|---:|---|
| baseline | development | 1/2 | 0 | 0 | 0 | 2 | shared exact-copy grounding on legacy development case |
| baseline | holdout V14 | 3/0 | **9** | **9** | 0 | 0 | source-time leakage also elevated |
| baseline | Adv V12 | 2/1 | 0 | **10** | 0 | 0 | 1 invalid_model_output |
| candidate | development | 0/3 | 0* | 0* | 0* | **3** | *comparison metrics unobserved (all runs failed) |
| candidate | holdout V14 | 2/1 | **0** | **9** | 0 | 0 | 1 target_set_mismatch |
| candidate | Adv V12 | 3/0 | **0** | **14** | **1** | 0 | |

Machine decision diagnostics: `candidate_grounding_failures=3`.

## Roadmap disposition (human precedence)

**`ITERATE_PROMPT`**

Precedence applied:

1. Not `PROMOTION_EVIDENCE_INCOMPLETE` — seal verified, single clean provider SHA, exact 18-cell matrix present, holdout/adversarial comparison metrics observed.
2. Not `ADVANCE_TO_TEXTUAL_NORMALIZATION` — observed defects are not limited to exact phrase copy. Fresh V14/Adv V12 show wrong temporal values on both lanes; baseline holdout also shows unsafe over-resolution.
3. Not `PROMPT_READY_FOR_BROADER_SHADOW` — readiness requires candidate `wrong_temporal_value == 0`, zero grounding/model/contract failures across the matrix, and machine `PROMPT_READY`. None of those hold.
4. **`ITERATE_PROMPT`** — machine decision `ITERATE_PROMPT`; candidate fails readiness on fresh evidence (`wrong_temporal_value` on V14 and Adv V12; `wrong_temporal_lane` on Adv V12; development grounding failures). Named successor `tl01h-v1` remains **unimplemented**.

### Isolation notes (honest)

- Legacy **development** grounding failures appear on **both** lanes (exact `source_phrase` copy). Treat those as shared textual-grounding pressure on the old development fixture, not as sole candidate-isolated proof.
- Fresh **holdout V14** / **Adv V12** still do not authorize promotion: candidate wrong-value totals remain non-zero; control additionally shows unsafe over-resolution on V14.
- Do not read candidate `unsafe_over_resolution == 0` on V14/Adv V12 as readiness — wrong-value and incomplete development evaluability block `PROMPT_READY_FOR_BROADER_SHADOW`.

## Provider response IDs (18)

| Cell | Outcome | Response ID |
|---|---|---|
| baseline/development/run-01 | grounding_failure | `resp_09f698dab74d4304006a6f961f420c819ba346f2abe8153151` |
| baseline/development/run-02 | grounding_failure | `resp_061fa6ba1d9ec99e006a6f964558f0819b8893acdcb13ea855` |
| baseline/development/run-03 | ok | `resp_091f4d15697c5421006a6f966d93c48198ae51c855914417d7` |
| baseline/holdout/run-01 | ok | `resp_0d23b60baaa30e96006a6f96244594819b90452675f44e6bca` |
| baseline/holdout/run-02 | ok | `resp_02dc239c51042e18006a6f9649f1048199ba5c79c477c0c2e7` |
| baseline/holdout/run-03 | ok | `resp_0ae8b4c1134846f3006a6f96719114819aa7dcb5d0f268250c` |
| baseline/adversarial/run-01 | ok | `resp_0181c228db3309a2006a6f962dc1c8819a98a22a77bbe9d305` |
| baseline/adversarial/run-02 | invalid_model_output | `resp_0c59a1ece2ebf64a006a6f9651d580819bb6791fd754f333c7` |
| baseline/adversarial/run-03 | ok | `resp_0ca0b0a53872d284006a6f9678f8248199add3e89b88f29310` |
| candidate/development/run-01 | grounding_failure | `resp_040937eb4e01dbd9006a6f9634bcb481999ea209cbd5903ed6` |
| candidate/development/run-02 | grounding_failure | `resp_0eb0c465ad38bb50006a6f965a369881998b77cfe36d7ab341` |
| candidate/development/run-03 | grounding_failure | `resp_058412e94ef00271006a6f9681738c81998c7763317903a2ea` |
| candidate/holdout/run-01 | ok | `resp_04151b0bfd4f08ac006a6f963888e881988be806e0cc066a69` |
| candidate/holdout/run-02 | target_set_mismatch | `resp_093d3136fab25335006a6f965dd938819990b3466b1d3c61b6` |
| candidate/holdout/run-03 | ok | `resp_0ceeb48ec082c004006a6f9686cd988198a4142802147bd84a` |
| candidate/adversarial/run-01 | ok | `resp_0203e3dfa0ce67c0006a6f963f997081998d07f50897a1fe58` |
| candidate/adversarial/run-02 | ok | `resp_06580890a78059e6006a6f9666e91c8199be752cf15a6a4f55` |
| candidate/adversarial/run-03 | ok | `resp_009259374ca275d2006a6f968d8294819b9ee49232a3a64779` |

## Named successor (unimplemented)

Design a separate `tl01h-v1` prompt-iteration capability only after a new handoff that consumes these observed V14/Adv V12 defects (wrong temporal value / lane; abstention vs over-resolution asymmetries). Do not edit `tl01g-v1`, packet, renderer, matcher, or these sealed cohorts in this PR.

## Non-claims

- No producer cutover, graph write, timeline API, or UI.
- No retry, no post-observation gold repair, no second implementation PR.
- PR486 `GROUNDING_PATH_READY` remains a smoke-path prerequisite only — not promotion authority.
