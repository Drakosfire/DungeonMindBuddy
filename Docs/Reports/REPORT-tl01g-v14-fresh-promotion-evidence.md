# REPORT — TL01G Fresh Promotion Evidence (V14 / Adv V12)

**Status:** Observed matrix retained; roadmap disposition **`PROMOTION_EVIDENCE_INCOMPLETE`**  
**Handoff:** `Docs/Plans/HANDOFF-TIMELINE-tl01g-fresh-promotion-evidence.md`  
**PR:** https://github.com/Drakosfire/DungeonMindBuddy/pull/496  
**Branch:** `timeline/tl01g-fresh-promotion-evidence`

## Verdict (authoritative)

V14 / Adv V12 **cannot** remain promotion authority. Sealed Adv V12 gold assigns
`valid_time.start.raw_expression = "since the equinox flood"` while owned source
`valid-start-textual.md` only contains `"became shuttered at the equinox flood"`.
That violates Gate E3 / value grounding. Because all **18** provider attempts have
already been observed, the handoff forbids patching gold or rerunning the matrix.

- Preserve observed cohort bytes unchanged.
- Retire V14 and Adv V12 as invalid / incomplete promotion evidence.
- Human disposition: **`PROMOTION_EVIDENCE_INCOMPLETE`** (overrides machine
  `ITERATE_PROMPT` in the aggregate).
- Require a fresh successor cohort pair before another promotion claim.
- Do **not** name or implement `tl01h-v1` from this matrix.

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
| Machine decision (aggregate, non-authoritative) | `ITERATE_PROMPT` |
| Human roadmap disposition | **`PROMOTION_EVIDENCE_INCOMPLETE`** |

### Frozen identities (unchanged)

| Identity | Value |
|---|---|
| Control | `tl01f-v1` / `7a9d27c3a9980893f18757d7a5fe0612cf67f9aad8dfd2ccb20f9e3c667b7143` |
| Candidate | `tl01g-v1` / `3af1e470e304008d2490ba73e1a53628519c211bb54e17a10cd4c694beae9013` |
| Packet | `tl01c-packet-v1` |
| Renderer | `render_temporal_shadow_user_content_v2` |

Prior cohorts V8–V13 / Adv V6–V11 remain retired regression-only.
V14 / Adv V12 fixture, gold, audit, case, and source bytes are **immutable** after
observation; only retirement documentation and Gate-faithfulness regression tests
were added post-matrix.

## Six-lane × three-repetition outcomes (observed)

| Lane | Cohort | run-01 | run-02 | run-03 |
|---|---|---|---|---|
| baseline (`tl01f-v1`) | development | grounding_failure | grounding_failure | ok |
| baseline | holdout V14 | ok | ok | ok |
| baseline | Adv V12 | ok | invalid_model_output | ok |
| candidate (`tl01g-v1`) | development | grounding_failure | grounding_failure | grounding_failure |
| candidate | holdout V14 | ok | target_set_mismatch | ok |
| candidate | Adv V12 | ok | ok | ok |

All 18 manifests share provider execution SHA `d1b5cc60…`. Aggregate comparison
totals below remain descriptive regression evidence only.

## Aggregate comparison metrics (descriptive; not promotion authority)

| Lane | Cohort | success/fail | unsafe_over_resolution | wrong_temporal_value | wrong_temporal_lane | grounding_failures |
|---|---|---:|---:|---:|---:|---:|
| baseline | development | 1/2 | 0 | 0 | 0 | 2 |
| baseline | holdout V14 | 3/0 | **9** | **9** | 0 | 0 |
| baseline | Adv V12 | 2/1 | 0 | **10** | 0 | 0 |
| candidate | development | 0/3 | 0* | 0* | 0* | **3** |
| candidate | holdout V14 | 2/1 | **0** | **9** | 0 | 0 |
| candidate | Adv V12 | 3/0 | **0** | **14** | **1** | 0 |

\*candidate development comparison metrics unobserved (all runs failed).

## Failure classification (required before any prompt-iteration claim)

Headline `wrong_temporal_value` totals are **not** isolated candidate temporal
reasoning proof. Unique non-exact assertion outcomes across successful runs were
classified as:

| Class | Meaning | Notable examples |
|---|---|---|
| **invalid_gold** | Sealed gold value absent from owned evidence | Adv V12 `assertion:5ebdb8abe4bc43db` — gold `since the equinox flood` vs source `became shuttered at the equinox flood` |
| **evaluator_gold_representation_mismatch** | Semantically aligned payloads that differ by gold/evaluator contract fields | Textual points with gold `campaign_id: null` vs model `campaign_id: "longmont-c2"` |
| **exact_text_normalization_difference** | Same temporal kind/lane; phrase extent / substring differences | Full transition phrase vs temporal substring in `raw_expression` |
| **actual_temporal_semantic_failure** | Kind/value/status that is not a representation-only mismatch | Control and candidate both: session vs textual kind swaps on holdout rows (e.g. kiln-warden / bridge-chaplain / wake-bell; market / ledger) |
| **actual_temporal_lane_failure** | Occurrence vs valid-time lane presence differs | Candidate Adv V12 run-02 only: `assertion:1888fabc054e29a8` (*Pel Raith abandoned the south stair four summers earlier*) — gold `occurrence_time` textual point; prediction `valid_time.end` with the same raw expression |

### Lane row (named)

- **`assertion:1888fabc054e29a8`** — candidate Adv V12 **run-02** only classified
  `wrong_temporal_lane` (`occurrence/valid-time lane presence differs`). Runs 01/03
  for the same assertion were `wrong_temporal_value` (representation / payload
  differences). This intermittent lane miss is observed regression signal, **not**
  promotion-authority proof for `tl01h-v1`, because the cohort gold is already
  invalid.

### Why `ITERATE_PROMPT` is withdrawn

1. Invalid sealed gold collapses promotion authority regardless of model behavior.
2. Large wrong-value totals are shared across control and candidate and largely
   mix representation mismatches with semantic kind swaps — not a clean candidate
   isolation.
3. Shared development grounding failures remain on both lanes.
4. Handoff precedence: **`PROMOTION_EVIDENCE_INCOMPLETE`** when integrity of the
   promotion cohort is not established.

## Roadmap disposition (human precedence)

**`PROMOTION_EVIDENCE_INCOMPLETE`**

1. Applied because sealed Adv V12 gold fails Gate E3 / value grounding; V14/Adv V12
   are retired as a pair.
2. Not `ITERATE_PROMPT` — candidate-specific prompt defects are not isolated on
   trustworthy gold.
3. Not `ADVANCE_TO_TEXTUAL_NORMALIZATION` — invalid gold and mixed semantic/kind
   mismatches remain.
4. Not `PROMPT_READY_FOR_BROADER_SHADOW`.

### Next authorized work

Author a fresh successor cohort pair with **pre-live** Gate E3 + occurrence /
boundary-value grounding over every resolved annotation (the corrective test now
documents why V14/Adv V12 retired; it does not authorize editing them).

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

No `tl01h-v1` from this PR. Successor prompt work requires a new handoff after a
Gate-faithful fresh cohort pair is sealed and observed.

## Non-claims

- No producer cutover, graph write, timeline API, or UI.
- No retry, no post-observation gold repair, no second live matrix on V14/Adv V12.
- Aggregate machine `ITERATE_PROMPT` is retained as observed runner output only.
- PR486 `GROUNDING_PATH_READY` remains a smoke-path prerequisite only — not
  promotion authority.
