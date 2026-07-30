# Temporal Prompt Calibration V1 (TL01C)

**Status:** Implemented (evaluation seam)  
**Authority modules:** `evals/graph_memory_layer/temporal_shadow_prompt_calibration.py`, `src/graph_memory/temporal_shadow_extraction_schema.py`  
**CLI:** `uv run python evals/graph_memory_layer/temporal_shadow_prompt_calibration.py`  
**Handoff:** `Docs/Plans/HANDOFF-tl01c-source-aware-temporal-prompt-calibration.md`  
**Depends on:** `CONTRACT-temporal-shadow-extraction-v1.md` (TL01B), TL01B handoff §16 verdict semantics

## Purpose

Compare **frozen TL01B baseline** prompt behavior (`tl01b-v1`) against **candidate TL01C source-aware** prompt behavior (`tl01c-v1`) across development, holdout, and adversarial V2 cohorts. Produce a **calibration aggregate** with min/median/max metrics, per-assertion repetition stability, separated source-leakage splits, and a **promotion decision** for broader shadow rollout.

No graph writes, no kernel changes, no live provider calls required for unit tests (`--fake`).

## Frozen baseline

- Prompt version: `tl01b-v1`
- Instructions: `TL01B_BASELINE_INSTRUCTIONS` (immutable; verified via hardcoded fingerprints in tests)
- Packet: `tl01b-packet-v1` (no `source_context`)
- Baseline lane runs: development sealed case + holdout TL01B mirror case

### Baseline freeze fingerprints (non-tautological)

Tests assert against frozen constants — not recomputed live strings:

| Artifact | SHA256 |
| --- | --- |
| `TL01B_BASELINE_INSTRUCTIONS` | `c036558b52b8a44e5358fb7f3062dbf9db5b7f5bf86cb7fa2d986e7fddd0ceec` |
| `compute_prompt_sha256("tl01b-v1")` | `c7606bb6a97f358dc275c5681f0c819e0db84da14d07e8f19ff56b870402bf51` |
| V1 rendered packet (sealed development case) | `9925e9fb65c124a560cd231707b174139c5911e3f2eaab5d7088b001f80f8430` |

Baseline exists to detect prompt drift and provide an A/B control during calibration. Any baseline change is a contract amendment, not calibration iteration.

## Candidate freeze

- Prompt version: `tl01c-v1` (frozen for TL01C slice)
- Successor on `ITERATE_PROMPT`: **TL01D** with a new version id (e.g. `tl01d-v1`)
- Do not mutate `tl01c-v1` in place after the first live calibration attempt

## Prompt registry

Registry lives in `graph_memory.temporal_shadow_extraction.TEMPORAL_PROMPT_SPECS`:

| Version | Packet | User content renderer |
| --- | --- | --- |
| `tl01b-v1` | `tl01b-packet-v1` | `render_temporal_shadow_user_content_v1` |
| `tl01c-v1` | `tl01c-packet-v1` | `render_temporal_shadow_user_content_v2` |

Unknown `prompt_version` in a sealed case fails closed before provider invocation (`unsupported_prompt_version`).

## Packet V2 source_context

TL01C packets add `source_context` per assertion:

```json
{
  "source_time": { "...": "TemporalPointV1 transport or null" },
  "derivation": "single_session | ...",
  "semantic_authority": "provenance_only"
}
```

Built only via TL01 `derive_assertion_source_time`. Unsafe or skipped derivation fails closed at packet build time.

V1 packets omit `source_context` entirely.

## Candidate decision sequence

TL01C instructions require this per-assertion order:

1. Identify proposition from assertion metadata (evidence must not override proposition type)
2. Choose temporal lane: occurrence, valid, not_applicable, ambiguous, unresolved
3. Treat `source_context.source_time` as **provenance_only** — never auto-copy into occurrence/valid
4. Normalize conservatively; preserve relative/textual incompleteness
5. Ground per TL01B rules (resolved requires snippet-grounded payloads)

## Cohort definitions

| Cohort | Baseline case | Candidate case | Role |
| --- | --- | --- | --- |
| Development | `temporal_shadow_cohort/temporal-case.json` | `.../temporal-case-tl01c.json` | Shared 6 assertions; mirror for A/B |
| Holdout | `temporal_shadow_holdout/temporal-case-tl01b.json` | `.../temporal-case.json` | Independent 7 assertions + evidence |
| Adversarial V2 | — | `temporal_shadow_adversarial_v2/temporal-case.json` | Synthetic stress; candidate only |

### Independence rules

- Holdout **must not overlap** development on assertion IDs or evidence IDs.
- Adversarial V2 **must not overlap** TL01C few-shot cast (Arin/Nera/Mara/Veyra/Red Company patterns).
- Adversarial V2 uses **Jorin/Pella/Tovin/Quill Harbor/frost seal/Ash Riders**.
- TL01C few-shots **must not** contain sealed development cohort terms (Stafl, Caelynn, Lysandra, Maelthor, Hybrid, Copper and Quartz).
- **Deprecated:** `temporal_shadow_adversarial/` (V1) — contaminated; do not use for calibration.

## Sealing (holdout + adversarial)

Fixtures are bound to a **git seal commit**, not an arbitrary digest override.

### Verification (`verify_cohort_seal`)

Before live runs, the runner verifies:

1. Seal commit exists.
2. Seal commit is an **ancestor** of the execution commit.
3. Case-declared `base_contribution_sha256` and `gold_overlay_sha256` match executed file bytes.
4. Every verified path (case, base, gold, evidence sources) exists in the worktree.
5. Worktree SHA256 for each path equals the blob at the seal commit.

CLI:

```bash
--holdout-seal-commit <sha>       # required for live runs
--adversarial-seal-commit <sha>   # required for live runs
--skip-seal-verification          # requires --fake; rejected for real provider runs
```

There is **no** `--holdout-seal-sha` arbitrary digest override. Aggregate records `seals_verified`; READY requires `seals_verified=true`.

Live cleanliness uses `git status --porcelain` **without** `-uno`, so non-ignored untracked files block execution. Ignored/generated calibration artifacts remain excluded via pathspec. Development and baseline-mirror case/base/gold/evidence paths are verified against blobs at the execution commit (`verify_fixtures_tracked_at_commit`).

### Aggregate seal fields (separated)

`TemporalPromptCalibrationAggregateV1` records:

| Field | Description |
| --- | --- |
| `holdout_case_sha256` | Candidate holdout case file |
| `holdout_base_sha256` | Holdout base contribution |
| `holdout_gold_sha256` | Holdout gold overlay |
| `holdout_seal_commit_sha` | Git seal commit |
| `adversarial_case_sha256` | Adversarial V2 case file |
| `adversarial_base_sha256` | Adversarial V2 base contribution |
| `adversarial_gold_sha256` | Adversarial V2 gold overlay |
| `adversarial_seal_commit_sha` | Git seal commit |
| `seals_verified` | True only after successful commit/blob verification |

## Repetition protocol

Default **3 repetitions** per lane/cohort pair. Run matrix per repetition:

```text
baseline/development, baseline/holdout,
candidate/development, candidate/holdout, candidate/adversarial
```

Failed repetitions remain on disk (`failure-manifest.json`) and count in aggregates.

## Run layout

```text
calibration/
  baseline/development/run-01/ ...
  baseline/holdout/run-01/
  candidate/development/run-01/
  candidate/holdout/run-01/
  candidate/adversarial/run-01/
  aggregate.json
```

## Calibration aggregate

Schema: `dmb_temporal_prompt_calibration_v1` (`TemporalPromptCalibrationAggregateV1`)

The aggregate is the **durable source of truth** for report regeneration.

### Top-level fields

- `calibration_id`, `repository_sha`, `model_id`, `repetitions`
- `aggregate_build_sha` — HEAD SHA when the aggregate was written (equals `repository_sha`)
- `provider_run_repository_shas` — sorted unique SHAs from every run/failure manifest
- `baseline_prompt_sha256`, `candidate_prompt_sha256`
- Holdout seal fields: `holdout_case_sha256`, `holdout_base_sha256`, `holdout_gold_sha256`, `holdout_seal_commit_sha`
- Adversarial seal fields: `adversarial_case_sha256`, `adversarial_base_sha256`, `adversarial_gold_sha256`, `adversarial_seal_commit_sha`
- `seals_verified`
- `slices` (baseline + candidate), `decision`, `diagnostics`

### Metrics slice (`TemporalPromptCalibrationMetricsSliceV1`)

- `prompt_lane`, `prompt_version`, `prompt_sha256`
- `case_ids` — **populated** from cohorts and run records
- `pass_count`, `partial_count`, `fail_count`
- `blocked_count` — **provider failures only** (not total run failures)
- `cohort_aggregates`

### Cohort aggregate (`CalibrationCohortAggregateV1`)

- `exact_match` / `resolved_exact_match` — min/median/max across repetitions
- `min_status_accuracy`, `min_not_applicable_accuracy`
- `min_exact_match_ratio` — uses per-run total gold denominator
- `min_resolved_exact_ratio` — uses resolved gold row denominator
- Safety totals:
  - `total_unsafe_over_resolution`
  - `total_source_to_occurrence_false_positives` (occurrence leakage)
  - `total_source_to_valid_time_false_positives` (valid-time leakage)
  - `total_source_leakage_false_positives` (sum)
- Failure totals (separated):
  - `total_evidence_selection_mismatches` — evidence ID mismatches
  - `total_evidence_or_case_failures` — case/evidence seam
  - `total_provider_failures`
  - `total_grounding_failures` — phrase grounding misses
  - `total_model_output_failures` — schema-invalid / target-set model noncompliance
  - `total_invalid_payloads` — true contract gaps (`overlay_assembly_failed`, `unsupported_prompt_version`)
- Quality tallies: `total_wrong_temporal_value`, `total_wrong_temporal_lane`, `total_status_mismatch`
- `assertion_stability` — classification, status, **occurrence_normalized_counts**, **valid_time_normalized_counts**, **failure_counts** (includes failed reps as `run_failed`)
- `run_records` — per-repetition audit rows
- `manifest_consistency_ok`, `manifest_diagnostics`

## Failure code routing

| Code set | Aggregate bucket | Decision impact |
| --- | --- | --- |
| `provider_refusal`, `provider_incomplete`, `provider_error` | `total_provider_failures` | `PROVIDER_FAILURE` |
| `overlay_assembly_failed`, `unsupported_prompt_version` | `total_invalid_payloads` | `BLOCKED_BY_CONTRACT` |
| `invalid_model_output`, `target_set_mismatch` | `total_model_output_failures` | `ITERATE_PROMPT` |
| `evidence_unresolved`, `digest_mismatch`, `invalid_case`, `invalid_gold_overlay` | `total_evidence_or_case_failures` | `BLOCKED_BY_EVIDENCE` |
| `grounding_failure` | `total_grounding_failures` | `ITERATE_PROMPT` |

Evidence selection mismatches are tracked in `total_evidence_selection_mismatches` separately from evidence/case failures.

**Contract vs model-output:** `BLOCKED_BY_CONTRACT` is reserved for cases where the correct interpretation cannot be represented by the frozen TL00/TL01 contract or prompt registry. Schema-invalid model output against a representable answer (e.g. `ambiguous` with temporal extents, when null extents are valid) is `total_model_output_failures` → `ITERATE_PROMPT`.

Post-provider failures (`invalid_model_output`, `target_set_mismatch`, `grounding_failure`, `overlay_assembly_failed`, evidence/case codes after a provider return) publish a typed `failure-manifest.json` that preserves `provider_response_id` and identity fields; success artifacts are not emitted.

## Decision thresholds

Encoded as named constants in `temporal_shadow_prompt_calibration.py` (`compute_calibration_decision`).

### Exact priority order

| Priority | Decision | Condition |
| --- | --- | --- |
| 1 | `PROVIDER_FAILURE` | Any candidate `total_provider_failures > 0` |
| 2 | `BLOCKED_BY_CONTRACT` | Any candidate `total_invalid_payloads > 0` |
| 3 | `BLOCKED_BY_EVIDENCE` | Any candidate `total_evidence_or_case_failures > 0` |
| 4 | `ITERATE_PROMPT` | Any candidate `total_unsafe_over_resolution > 0` |
| 5 | `ITERATE_PROMPT` | Any candidate `total_source_leakage_false_positives > 0` |
| 6 | `ITERATE_PROMPT` | Any candidate `total_grounding_failures > 0` |
| 7 | `ITERATE_PROMPT` | Any candidate `total_model_output_failures > 0` |
| 8 | `BLOCKED_BY_INPUT_REPRESENTATION` | `total_wrong_temporal_value >= 2` with zero wrong lane and zero status mismatch |
| 9 | `ITERATE_PROMPT` | Missing holdout/development aggregate, any failed run, any-cohort manifest inconsistency, or live provider-run revision ≠ `aggregate_build_sha` |
| 10 | `PROMPT_READY_FOR_BROADER_SHADOW` | All READY thresholds met (holdout lane coverage uses `.min`, not `.max`) |
| 11 | `ITERATE_PROMPT` | Default |

Unsafe and source-leakage are evaluated **before** the input-representation heuristic.

**Grounding phrase failures → `ITERATE_PROMPT`.** Schema-invalid model output → `ITERATE_PROMPT`. Evidence/case seam failures → `BLOCKED_BY_EVIDENCE`. True contract gaps (`overlay_assembly_failed`, `unsupported_prompt_version`) → `BLOCKED_BY_CONTRACT`.

### READY constants

| Constant | Value |
| --- | --- |
| `READY_DEV_MEDIAN_EXACT_MATCHES` | 4 (of 6 development gold rows) |
| `READY_DEV_RESOLVED_EXACT_MATCHES` | 2 (per-run qualifying threshold) |
| `READY_DEV_RESOLVED_EXACT_RUNS` | 2 (qualifying development runs with resolved exact ≥ 2) |
| `READY_MIN_HOLDOUT_STATUS_ACCURACY` | 0.80 |
| `READY_MIN_NOT_APPLICABLE_ACCURACY` | 1.0 |
| `READY_MIN_HOLDOUT_EXACT_OCCURRENCE` | 1 (`exact_occurrence_match.min`) |
| `READY_MIN_HOLDOUT_EXACT_VALID_TIME` | 1 (`exact_valid_time_match.min`) |

Additional READY requirements: `seals_verified=true`; zero unsafe; zero source leakage; zero failed runs; manifest consistency OK on **all** cohorts (every run supplies case_id/model_id/prompt_version/repository_sha, and each cohort validates against its exact expected case ID). Live runs require a clean git worktree. Aggregate records `aggregate_build_sha` plus `provider_run_repository_shas`; READY requires a single provider-run revision equal to the aggregate build SHA. Paired baseline/candidate cases must share contribution, gold, assertions, and evidence before provider execution.

**Non-negotiable:** one successful repetition cannot hide unsafe repetitions.

### TL01B verdict mapping

| TL01B | TL01C |
| --- | --- |
| `SAFE_FOR_NEXT_EXPERIMENT` | `PROMPT_READY_FOR_BROADER_SHADOW` |
| `ITERATE_PROMPT` | `ITERATE_PROMPT` |
| `BLOCKED_BY_EVIDENCE` | `BLOCKED_BY_EVIDENCE` |
| `BLOCKED_BY_CONTRACT` | `BLOCKED_BY_CONTRACT` |
| `PROVIDER_FAILURE` | `PROVIDER_FAILURE` |
| — | `BLOCKED_BY_INPUT_REPRESENTATION` (TL01C-specific) |

## Non-goals

- Publishing temporal data to the graph
- Changing TL00 temporal kernel types
- Replacing per-run TL01B comparison with calibration-only scoring
- Auto-promoting prompt versions without human review
- Using adversarial V1 fixtures
- Arbitrary seal digest overrides
- In-place `tl01c-v1` mutation after live calibration (use TL01D)

## Successor decision

When `PROMPT_READY_FOR_BROADER_SHADOW`:

- Broader shadow extraction cohort (beyond sealed development/holdout/adversarial)
- Participant-role / TL02 experimentation per threat-statblock roadmap

When `ITERATE_PROMPT`:

- **TL01D** — new prompt version id; revise instructions or packet representation
- Re-run calibration with same holdout/adversarial seal commits for comparability

When `BLOCKED_BY_EVIDENCE`:

- Repair source-span or case/evidence seam

When `BLOCKED_BY_INPUT_REPRESENTATION`:

- Revise packet V2 transport or evidence representation

When `BLOCKED_BY_CONTRACT` or `PROVIDER_FAILURE`:

- Contract decision or provider dependency before re-run
