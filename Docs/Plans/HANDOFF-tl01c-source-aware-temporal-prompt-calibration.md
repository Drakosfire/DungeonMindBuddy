# HANDOFF — TL01C: Source-Aware Temporal Prompt Calibration

**Created:** 2026-07-29
**Updated:** 2026-07-30
**Project:** DungeonBuddy / DungeonMindBuddy
**Repository:** `Drakosfire/DungeonMindBuddy`
**Status:** ACTIVE — Timeline evaluation slice
**Suggested canonical path:** `Docs/Plans/HANDOFF-tl01c-source-aware-temporal-prompt-calibration.md`
**Required dependency:** PR `#452`, merged as `6eeffe239c582f129f0c6bf167b0f6d6fc51f6c6`
**Required implementation base:** current clean `origin/main` containing that merge
**Suggested branch:** `feat/tl01c-temporal-prompt-calibration`
**Expected PR count:** one
**Operating mode:** Eval-only prompt and input-context calibration
**Authoritative graph writes:** forbidden
**TL00/TL01 contract changes:** forbidden
**Timeline API, UI, and participant roles:** forbidden

---

## §0 Mission

Calibrate the temporal shadow extractor so it can distinguish **source provenance** from **fictional occurrence time**, **persistent valid time**, and **non-temporal or ambiguous assertions** — without modifying the TL01B evaluator, the temporal kernel, or graph authority.

The completed capability is:

```text
frozen TL01B baseline prompt (tl01b-v1)
+ versioned source-aware candidate prompt (tl01c-v1)
+ explicitly labeled derived source-time context (packet V2)
+ sealed development cohort
+ sealed holdout cohort
+ sealed adversarial V2 cohort (independent of few-shots)
+ repeated paired provider runs (3× per lane/cohort)
→ calibration aggregate (durable source of truth)
→ promotion decision for broader shadow rollout
```

This PR must prove whether the TL01C prompt and packet representation improve temporal interpretation quality **relative to the frozen TL01B baseline**, across development, holdout, and adversarial stress cases, while keeping every unsafe over-resolution and source-leakage failure visible.

The resulting calibration decision is **non-authoritative**. It must not publish temporal data to the graph, change TL01B comparison semantics, or auto-promote prompt versions without human review.

---

## §1 Why this slice exists

TL01B established evidence-bound model shadow extraction:

```text
sealed candidate contribution
+ exact assertion-owned evidence spans
+ structured model extraction
→ validated TemporalAnnotationOverlayV1
→ gold comparison
→ EvaluationVerdict
```

What TL01B did **not** prove is whether a model can **correctly use source provenance metadata** when deciding occurrence time, valid time, ambiguity, and non-applicability — without treating recap session IDs as fiction time.

Before broader shadow extraction or participant-role work, we need evidence about:

1. whether `source_context.source_time` stays **provenance_only** and is never auto-copied into occurrence/valid;
2. whether explicit alternate fiction time in evidence overrides source episode;
3. whether persistent-state boundaries are distinguished from re-attestation;
4. whether relative and incomplete time remain conservative;
5. whether holdout cohort generalizes beyond the sealed development mirror;
6. whether adversarial synthetic cases catch source-leakage regressions **independently** of TL01C few-shot examples;
7. whether repeated live runs produce stable enough metrics to support a promotion decision.

This PR creates that calibration experiment.

---

## §2 Selected capability

### Capability

```text
Given sealed development, holdout, and adversarial extraction cases,
run baseline (tl01b-v1) and candidate (tl01c-v1) lanes with repeated live provider calls,
aggregate min/median/max metrics and per-assertion stability,
and emit a CalibrationDecision for broader shadow rollout.
```

### Primary invariant

```text
Source provenance never becomes occurrence_time or valid_time automatically.
Packet V2 source_context is provenance_only — the model must justify any reuse.
```

### Authority invariant

```text
No output of this PR is graph authority.
Calibration does not replace per-run TL01B EvaluationVerdict semantics.
```

### Baseline invariant

```text
tl01b-v1 instructions and tl01b-packet-v1 rendering remain byte-stable.
Any change to baseline instructions or V1 packet shape is a contract violation, not calibration iteration.
```

### Candidate invariant

```text
tl01c-v1 is frozen for this slice.
Prompt iteration after a non-READY decision requires a successor slice (TL01D) with a new prompt version id.
```

### Mission falsification test

The mission has widened beyond prompt calibration if implementation requires:

* changing `TemporalEnvelopeV1` or TL00 kernel types;
* changing `TemporalAnnotationOverlayV1` or TL01 overlay contract;
* changing TL01B `compare_temporal_overlays` classifications or `EvaluationVerdict` enum;
* modifying grounding rules or evidence ownership validation;
* writing contributions or graph revisions;
* participant-role storage, projected occurrences, timeline queries, or UI.

Stop rather than absorbing those capabilities.

---

## §3 Mandatory first moves

Before coding or live proof:

1. Read:

```text
AGENTS.md
.cursor/rules/responses-api-structured-extraction.mdc
.cursor/rules/anti-oracle-leakage.mdc
.cursor/rules/corpus-pii-and-llm-payloads.mdc

Docs/Design/CONTRACT-temporal-shadow-extraction-v1.md
Docs/Design/CONTRACT-temporal-prompt-calibration-v1.md
Docs/Plans/HANDOFF-tl01b-model-shadow-temporal-extraction.md (structure reference only)
```

2. Record repository state:

```bash
git fetch origin
git status --short
git branch --show-current
git rev-parse HEAD
git rev-parse origin/main
```

3. Confirm the TL01B merge is in ancestry:

```bash
git merge-base --is-ancestor \
  6eeffe239c582f129f0c6bf167b0f6d6fc51f6c6 \
  origin/main
```

4. Inspect owning code:

```text
src/graph_memory/temporal_shadow_extraction.py
src/graph_memory/temporal_shadow_extraction_schema.py
evals/graph_memory_layer/temporal_shadow_prompt_calibration.py
evals/graph_memory_layer/examples/temporal_shadow_cohort/
evals/graph_memory_layer/examples/temporal_shadow_holdout/
evals/graph_memory_layer/examples/temporal_shadow_adversarial_v2/
```

5. Confirm there is no overlapping open temporal-calibration PR.

6. Preserve unrelated local and runtime state.

---

## §4 Runtime isolation

The TL01C calibration runner must not read from or write to:

```text
out/graph_memory/worlds/eldyrwild/
graph heads
revision stores
Firestore graph collections
Hermes
Timeline API or UI surfaces
```

Calibration artifacts belong under:

```text
evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/
```

Default aggregate path:

```text
<output-dir>/calibration/aggregate.json
```

---

## §5 Architecture decision

### Separation of concerns

| Layer | Responsibility |
| --- | --- |
| TL01B extraction runner | Single-case overlay production + gold comparison (unchanged) |
| TL01C calibration runner | Multi-cohort, multi-lane, multi-repetition orchestration + aggregate + decision |
| Prompt registry | Versioned instructions + packet renderer selection |
| Seal verification | Git-anchored fixture immutability for holdout and adversarial |

### Why a separate calibration runner

TL01B proves single-case extraction quality. TL01C proves **prompt-version quality** across:

* a **baseline control** (tl01b-v1 on development + holdout TL01B mirror case);
* a **candidate treatment** (tl01c-v1 on development mirror + holdout + adversarial);
* **repetition stability** (3 paired runs per required lane/cohort);
* **sealed holdout/adversarial** fixtures verified against git seal commits.

The calibration runner **reuses** `run_temporal_shadow_extraction` per repetition. It does not fork comparison logic.

---

## §6 Frozen dependencies

Do **not** change:

| Dependency | Location | Rule |
| --- | --- | --- |
| `TemporalEnvelopeV1` | TL00 kernel | No schema changes |
| `TemporalAnnotationOverlayV1` | TL01 overlay | No schema changes |
| `compare_temporal_overlays` | TL01B comparison | No classification changes |
| Grounding rules | TL01B extraction | No relaxation |
| Evidence ownership | TL01B extraction | No broadening |
| TL01B output publication | TL01B runner | Unchanged |
| `EvaluationVerdict` enum | TL01B schema | Do not extend for TL01C |

### Baseline freeze (non-tautological)

Baseline immutability is enforced by **hardcoded test fingerprints**, not by recomputing from live strings at test time:

| Artifact | Constant | SHA256 |
| --- | --- | --- |
| `TL01B_BASELINE_INSTRUCTIONS` | `FROZEN_TL01B_INSTRUCTIONS_SHA256` | `c036558b52b8a44e5358fb7f3062dbf9db5b7f5bf86cb7fa2d986e7fddd0ceec` |
| Baseline prompt bundle (`tl01b-v1`) | `FROZEN_TL01B_PROMPT_SHA256` | `c7606bb6a97f358dc275c5681f0c819e0db84da14d07e8f19ff56b870402bf51` |
| V1 rendered packet (sealed development case) | `FROZEN_TL01B_V1_PACKET_SHA256` | `9925e9fb65c124a560cd231707b174139c5911e3f2eaab5d7088b001f80f8430` |

`baseline_prompt_fingerprint()` returns `{prompt_version, instructions_sha256, packet_version}` for runtime diagnostics. Tests assert against the frozen constants above.

Any edit to `TL01B_BASELINE_INSTRUCTIONS`, `render_temporal_shadow_user_content_v1`, or the sealed development case that changes the V1 rendered packet **must** be treated as a baseline contract change — not a TL01C calibration tweak.

### Candidate freeze

`tl01c-v1` (`TL01C_SOURCE_AWARE_INSTRUCTIONS` + `tl01c-packet-v1` + `render_temporal_shadow_user_content_v2`) is frozen for this slice.

When calibration returns `ITERATE_PROMPT`, the successor is **TL01D** with a **new prompt version id** (e.g. `tl01d-v1`). Do not mutate `tl01c-v1` in place after the first live calibration attempt.

---

## §7 Prompt registry and packet V2

Registry: `graph_memory.temporal_shadow_extraction.TEMPORAL_PROMPT_SPECS`

| Version | Packet | Renderer | Role |
| --- | --- | --- | --- |
| `tl01b-v1` | `tl01b-packet-v1` | `render_temporal_shadow_user_content_v1` | Baseline (no `source_context`) |
| `tl01c-v1` | `tl01c-packet-v1` | `render_temporal_shadow_user_content_v2` | Candidate (includes `source_context`) |

Unknown `prompt_version` in a sealed case fails closed before provider invocation (`unsupported_prompt_version` → `BLOCKED_BY_CONTRACT` at aggregate level if it surfaces as a run failure).

### Packet V2 `source_context`

Built only via TL01 `derive_assertion_source_time`. Each assertion packet may include:

```json
{
  "source_time": { "...": "TemporalPointV1 transport or null" },
  "derivation": "single_session | ...",
  "semantic_authority": "provenance_only"
}
```

Rules enforced at build time and in instructions:

* `semantic_authority` is always `provenance_only`.
* Unsafe or skipped derivation fails closed at packet build time.
* V1 packets omit `source_context` entirely.

### Candidate decision sequence (per assertion)

TL01C instructions require this order:

1. Identify proposition from assertion metadata (`assertion_kind`, subject/target, predicate, label, `semantic_value`). Evidence events must not override proposition type.
2. Choose temporal lane: `occurrence_time`, `valid_time`, `not_applicable`, `ambiguous`, or `unresolved`.
3. Treat `source_context.source_time` as **provenance_only** — never auto-copy into occurrence/valid. Reuse only when source episode narrates the same event/state boundary and evidence does not establish different fiction time.
4. Normalize conservatively; preserve relative/textual incompleteness.
5. Ground per TL01B rules: `resolved` requires snippet-grounded payloads; owned evidence subsets; verbatim `source_phrase` when supplied.

### Few-shot contamination guard

TL01C synthetic few-shot examples use **invented campaigns only** (Arin, Nera, Mara, Veyra, Red Company, etc.).

They must **not** contain sealed cohort terms:

```text
Stafl, Caelynn, Lysandra, Maelthor, Hybrid, Copper and Quartz
```

Adversarial V2 fixtures must **not** reuse few-shot cast, predicates, or sentence templates. See §10.

---

## §8 Development cohort

**Path:** `evals/graph_memory_layer/examples/temporal_shadow_cohort/`

| Case file | Prompt | Purpose |
| --- | --- | --- |
| `temporal-case.json` | `tl01b-v1` | Baseline development lane |
| `temporal-case-tl01c.json` | `tl01c-v1` | Candidate development lane |

Both cases share the **same** `base-contribution.json`, `gold-overlay.json`, assertion IDs, and evidence registry. They differ only in `prompt_version` and packet rendering.

### Development matrix (6 assertions)

| # | Category | Gold |
| --- | --- | --- |
| 1 | Event (revive) | resolved occurrence session-7 |
| 2 | Valid-time start | resolved valid from session-13 |
| 3 | Event destroy | resolved occurrence session-24 |
| 4 | Scene framing | not_applicable |
| 5 | Negative provenance | not_applicable |
| 6 | Ambiguous mention | ambiguous |

Development is **sealed by design overlap** — baseline and candidate run on mirrored assertions to detect prompt-quality deltas without holdout leakage.

---

## §9 Holdout cohort

**Path:** `evals/graph_memory_layer/examples/temporal_shadow_holdout/`

| Case file | Prompt | Purpose |
| --- | --- | --- |
| `temporal-case-tl01b.json` | `tl01b-v1` | Baseline holdout lane |
| `temporal-case.json` | `tl01c-v1` | Candidate holdout lane |

Case ID: `tl01c-temporal-shadow-holdout-v1`

### Holdout matrix (7 assertions)

| # | Category | Gold |
| --- | --- | --- |
| 1 | Same-source event (portal) | resolved occurrence session-8 |
| 2 | Valid-time start (coordinates) | resolved valid start session-8 |
| 3 | Structural containment | not_applicable |
| 4 | Scene framing (inn) | not_applicable |
| 5 | Ambiguous name/identity | ambiguous |
| 6 | Relative/incomplete historical | textual occurrence |
| 7 | Same-source event (Mother) | resolved occurrence session-18 |

### Holdout independence rules

Holdout **must not overlap** development on:

* `selected_assertion_ids`
* `evidence_ref_ids` in the evidence registry

Tests enforce zero intersection. Holdout uses distinct corpus recap spans and assertion IDs.

### Holdout sealing

Holdout fixtures must be **git-sealed before the first candidate holdout live run**. After sealing, do not edit holdout case, base, gold, or evidence source files without a new seal commit and documented rationale.

Known holdout seal commit (reference for unit tests):

```text
2c3be373fdaf6a713c4cae9c5ab75f9ffad5bc1d
```

---

## §10 Adversarial cohort V2

**Path:** `evals/graph_memory_layer/examples/temporal_shadow_adversarial_v2/`

**Deprecated:** `evals/graph_memory_layer/examples/temporal_shadow_adversarial/` (V1) — contaminated by overlap with TL01C few-shot patterns. Retained for historical reference only. **Do not use for calibration.**

Case ID: `tl01c-temporal-shadow-adversarial-v2`

### V2 cast (independent of few-shots)

Synthetic markdown uses **Jorin / Pella / Tovin / Quill Harbor / frost seal / Ash Riders** with proposition shapes and wording distinct from TL01C few-shot examples.

V2 fixture payload files must **not** contain few-shot contamination terms:

```text
Arin, Nera, Mara, Veyra, Red Company, watch captain, shattered the beacon
```

### Patterns covered (5 assertions)

| Source file | Pattern |
| --- | --- |
| `sources/source-diff-occurrence.md` | Occurrence ≠ source session |
| `sources/source-diff-valid.md` | Valid-time start ≠ source session |
| `sources/valid-end.md` | Valid-time end in narrated episode |
| `sources/reattest.md` | Re-attestation → not_applicable |
| `sources/ambiguous-relative.md` | Ambiguous relative history |

### Adversarial lane rules

* **Candidate lane only** — no baseline/adversarial paired runs.
* Contributes to unsafe-over-resolution and source-leakage totals in the calibration decision.
* Does **not** merge into development/holdout exact-match READY numerators (decision still blocks on any adversarial unsafe/leakage).
* Must be **git-sealed before live adversarial runs**, same procedure as holdout (§12).

---

## §11 Cohort independence summary

| Cohort | Baseline lane | Candidate lane | Overlap with development |
| --- | --- | --- | --- |
| Development | `temporal-case.json` | `temporal-case-tl01c.json` | By design (same 6 assertions) |
| Holdout | `temporal-case-tl01b.json` | `temporal-case.json` | **None** (assertion + evidence IDs) |
| Adversarial V2 | — | `temporal-case.json` | **None** (synthetic, separate case) |

Oracle-leakage rule: adversarial and holdout gold terms must not appear in TL01C instructions few-shots. Development cohort terms must not appear in few-shots.

---

## §12 Sealing procedure

Sealing binds holdout and adversarial fixtures to a **git commit** so post-seal edits are detectable at calibration time.

### When to seal

1. After holdout fixtures are finalized and committed — **before any candidate holdout live run**.
2. After adversarial V2 fixtures are finalized and committed — **before any candidate adversarial live run**.

Record both seal commit SHAs in the calibration report and aggregate.

### Seal verification API

`verify_cohort_seal(case_path, seal_commit_sha, repo_root, execution_commit_sha)` in `temporal_shadow_prompt_calibration.py`.

Verification steps (fail closed → `CohortSealError`):

1. `seal_commit_sha` is non-empty.
2. Seal commit exists: `git cat-file -e <seal>^{commit}`.
3. Seal is ancestor of execution commit: `git merge-base --is-ancestor <seal> <execution>`.
4. Load case; verify `case.base_contribution_sha256` matches executed base file bytes.
5. Verify `case.gold_overlay_sha256` matches executed gold file bytes.
6. For each verified path (case JSON, base contribution, gold overlay, every `evidence_registry[].source_artifact_path`):
   * path exists in worktree;
   * worktree SHA256 equals blob SHA256 at seal commit: `git show <seal>:<path>`.

Returns `CohortSealRecord`:

```text
case_sha256, base_sha256, gold_sha256, seal_commit_sha, case_id, verified_paths
```

### Aggregate seal fields (separated — no single combined digest)

Top-level `TemporalPromptCalibrationAggregateV1` records:

| Field | Cohort |
| --- | --- |
| `holdout_case_sha256` | Holdout candidate case file |
| `holdout_base_sha256` | Holdout base contribution |
| `holdout_gold_sha256` | Holdout gold overlay |
| `holdout_seal_commit_sha` | Git seal commit |
| `adversarial_case_sha256` | Adversarial V2 case file |
| `adversarial_base_sha256` | Adversarial V2 base contribution |
| `adversarial_gold_sha256` | Adversarial V2 gold overlay |
| `adversarial_seal_commit_sha` | Git seal commit |

There is **no** `--holdout-seal-sha` arbitrary digest override. Seal integrity is commit-anchored only.

### CLI seal arguments

```bash
--holdout-seal-commit <sha>      # required for live runs
--adversarial-seal-commit <sha>  # required for live runs
--skip-seal-verification         # tests and --fake only
```

`--fake` implies skipped seal verification.

### Example sealing workflow

```bash
# 1. Finalize and commit holdout + adversarial V2 fixtures
git add evals/graph_memory_layer/examples/temporal_shadow_holdout/
git add evals/graph_memory_layer/examples/temporal_shadow_adversarial_v2/
git commit -m "Seal TL01C holdout and adversarial V2 cohort fixtures."

# 2. Record seal SHAs
HOLDOUT_SEAL=$(git rev-parse HEAD)
# (same commit if both sealed together, or separate commits if staged independently)
ADV_SEAL=$(git rev-parse HEAD)

# 3. Pass SHAs to live calibration (after development freeze confirmation)
uv run python evals/graph_memory_layer/temporal_shadow_prompt_calibration.py \
  --development-case evals/graph_memory_layer/examples/temporal_shadow_cohort/temporal-case.json \
  --candidate-development-case evals/graph_memory_layer/examples/temporal_shadow_cohort/temporal-case-tl01c.json \
  --holdout-case evals/graph_memory_layer/examples/temporal_shadow_holdout/temporal-case-tl01b.json \
  --candidate-holdout-case evals/graph_memory_layer/examples/temporal_shadow_holdout/temporal-case.json \
  --adversarial-case evals/graph_memory_layer/examples/temporal_shadow_adversarial_v2/temporal-case.json \
  --holdout-seal-commit "$HOLDOUT_SEAL" \
  --adversarial-seal-commit "$ADV_SEAL" \
  --model-id <resolved-from-MODEL_POLICY.json> \
  --repetitions 3 \
  --output-dir evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/
```

---

## §13 Repetition protocol

Default: **3 repetitions** per required lane/cohort pair (`--repetitions 3`).

### Run matrix (per repetition *n*)

| Lane | Cohort | Case |
| --- | --- | --- |
| baseline | development | `temporal_shadow_cohort/temporal-case.json` |
| baseline | holdout | `temporal_shadow_holdout/temporal-case-tl01b.json` |
| candidate | development | `temporal_shadow_cohort/temporal-case-tl01c.json` |
| candidate | holdout | `temporal_shadow_holdout/temporal-case.json` |
| candidate | adversarial | `temporal_shadow_adversarial_v2/temporal-case.json` |

Total runs per calibration: `5 × repetitions` (15 at default).

Each repetition invokes `run_temporal_shadow_extraction` with `overwrite=True`. Failed runs remain on disk with `failure-manifest.json`; they count in aggregates and can block READY.

---

## §14 Run layout on disk

```text
<output-dir>/
  calibration/
    baseline/
      development/
        run-01/ ... run-03/
      holdout/
        run-01/ ... run-03/
    candidate/
      development/
        run-01/ ... run-03/
      holdout/
        run-01/ ... run-03/
      adversarial/
        run-01/ ... run-03/
    aggregate.json
```

Per-run artifacts (from TL01B runner, unchanged):

```text
run-manifest.json
comparison.json          # on success
overlay.json             # on success
failure-manifest.json    # on failure
```

---

## §15 Calibration aggregate schema

Schema: `dmb_temporal_prompt_calibration_v1` (`TemporalPromptCalibrationAggregateV1`)

The aggregate is the **durable source of truth** for report regeneration. Every field below must be populated by the runner.

### Top-level aggregate fields

| Field | Description |
| --- | --- |
| `schema` | `dmb_temporal_prompt_calibration_v1` |
| `calibration_id` | Derived from prompt SHAs, seal SHAs, model, repetitions, repo SHA |
| `repository_sha` | Execution commit at calibration time |
| `holdout_case_sha256` | Candidate holdout case file digest |
| `holdout_base_sha256` | Holdout base contribution digest |
| `holdout_gold_sha256` | Holdout gold overlay digest |
| `holdout_seal_commit_sha` | Holdout git seal |
| `adversarial_case_sha256` | Adversarial V2 case file digest |
| `adversarial_base_sha256` | Adversarial V2 base digest |
| `adversarial_gold_sha256` | Adversarial V2 gold digest |
| `adversarial_seal_commit_sha` | Adversarial git seal |
| `baseline_prompt_sha256` | `compute_prompt_sha256("tl01b-v1")` |
| `candidate_prompt_sha256` | `compute_prompt_sha256("tl01c-v1")` |
| `model_id` | Provider model used |
| `repetitions` | Repetition count |
| `slices` | Baseline + candidate metric slices |
| `decision` | `CalibrationDecision` |
| `diagnostics` | Decision notes |

### Metrics slice (`TemporalPromptCalibrationMetricsSliceV1`) — per prompt lane

| Field | Description |
| --- | --- |
| `prompt_lane` | `baseline` or `candidate` |
| `prompt_version` | `tl01b-v1` or `tl01c-v1` |
| `prompt_sha256` | Version bundle digest |
| `case_ids` | **Populated** list of case IDs seen across cohorts and run records |
| `pass_count` | Cohorts passing slice heuristic |
| `partial_count` | Cohorts partial |
| `fail_count` | Cohorts failed (zero successes or unsafe) |
| `blocked_count` | **Provider failures only** (not total failure_count) |
| `cohort_aggregates` | Per-cohort aggregates (below) |

### Cohort aggregate (`CalibrationCohortAggregateV1`)

| Field | Description |
| --- | --- |
| `prompt_lane`, `cohort`, `case_id` | Identity |
| `run_count`, `success_count`, `failure_count` | Run totals |
| `exact_match` | min/median/max exact match counts across successes |
| `resolved_exact_match` | min/median/max resolved exact counts |
| `min_status_accuracy` | Minimum status accuracy across successes |
| `min_not_applicable_accuracy` | Minimum not_applicable accuracy across successes |
| `total_unsafe_over_resolution` | Summed across repetitions |
| `total_source_to_occurrence_false_positives` | Occurrence leakage split |
| `total_source_to_valid_time_false_positives` | Valid-time leakage split |
| `total_source_leakage_false_positives` | Sum of occurrence + valid leakage |
| `total_evidence_selection_mismatches` | Evidence ID mismatches (separate from case failures) |
| `total_evidence_or_case_failures` | `evidence_unresolved`, `digest_mismatch`, `invalid_case`, `invalid_gold_overlay` |
| `total_provider_failures` | Provider failure codes |
| `total_grounding_failures` | `grounding_failure` code |
| `total_invalid_payloads` | Contract failure codes |
| `total_wrong_temporal_value` | Classification tally |
| `total_wrong_temporal_lane` | Classification tally |
| `total_status_mismatch` | Status mismatch tally |
| `min_exact_match_ratio` | min(exact / total_gold) using per-run denominators |
| `min_resolved_exact_ratio` | min(resolved_exact / resolved_gold) using resolved gold rows |
| `assertion_stability` | Per-assertion repetition distributions |
| `run_records` | Per-repetition audit rows |
| `manifest_consistency_ok` | Cross-run manifest check |
| `manifest_diagnostics` | Inconsistency details |

### Assertion stability (`CalibrationAssertionStabilityV1`)

Per `base_assertion_id` across repetitions:

| Field | Content |
| --- | --- |
| `classification_counts` | Comparison classification histogram (includes `run_failed` on failures) |
| `status_counts` | Predicted interpretation status histogram |
| `occurrence_normalized_counts` | Canonical JSON normalized occurrence payloads |
| `valid_time_normalized_counts` | Canonical JSON normalized valid_time payloads |
| `failure_counts` | Failure codes attributed when runs fail |

Failed repetitions appear in assertion stability (second-pass attribution after all runs complete).

### Run record (`CalibrationRunRecordV1`)

Durable per-repetition row for report regeneration: lane, cohort, repetition, success flag, case/model/prompt/repo IDs, provider response ID, metric snapshots or failure code, manifest consistency flags.

---

## §16 Calibration decision

### Decision enum

```text
PROMPT_READY_FOR_BROADER_SHADOW
ITERATE_PROMPT
BLOCKED_BY_INPUT_REPRESENTATION
BLOCKED_BY_EVIDENCE
BLOCKED_BY_CONTRACT
PROVIDER_FAILURE
```

Do **not** modify TL01B `EvaluationVerdict`. Mapping:

| TL01B `EvaluationVerdict` | TL01C `CalibrationDecision` |
| --- | --- |
| `SAFE_FOR_NEXT_EXPERIMENT` | `PROMPT_READY_FOR_BROADER_SHADOW` |
| `ITERATE_PROMPT` | `ITERATE_PROMPT` |
| `BLOCKED_BY_EVIDENCE` | `BLOCKED_BY_EVIDENCE` (case/evidence seam) |
| `BLOCKED_BY_CONTRACT` | `BLOCKED_BY_CONTRACT` |
| `PROVIDER_FAILURE` | `PROVIDER_FAILURE` |
| — | `BLOCKED_BY_INPUT_REPRESENTATION` (TL01C-specific heuristic) |

### Exact priority order

Implemented in `compute_calibration_decision`. Evaluate **in this order**; first match wins:

| Priority | Decision | Condition |
| --- | --- | --- |
| 1 | `PROVIDER_FAILURE` | Any candidate cohort `total_provider_failures > 0` |
| 2 | `BLOCKED_BY_CONTRACT` | Any candidate cohort `total_invalid_payloads > 0` |
| 3 | `BLOCKED_BY_EVIDENCE` | Any candidate cohort `total_evidence_or_case_failures > 0` |
| 4 | `ITERATE_PROMPT` | Any candidate cohort `total_unsafe_over_resolution > 0` |
| 5 | `ITERATE_PROMPT` | Any candidate cohort `total_source_leakage_false_positives > 0` |
| 6 | `ITERATE_PROMPT` | Any candidate cohort `total_grounding_failures > 0` |
| 7 | `BLOCKED_BY_INPUT_REPRESENTATION` | `total_wrong_temporal_value >= 2` AND `total_wrong_temporal_lane == 0` AND `total_status_mismatch == 0` (correct status/lane, wrong payload) |
| 8 | `ITERATE_PROMPT` | Missing candidate holdout or development aggregate |
| 9 | `ITERATE_PROMPT` | Any candidate cohort `failure_count > 0` |
| 10 | `ITERATE_PROMPT` | Any cohort (baseline or candidate) `manifest_consistency_ok == false` |
| 10b | `ITERATE_PROMPT` | Live: `provider_run_repository_shas != [aggregate_build_sha]` |
| 11 | `PROMPT_READY_FOR_BROADER_SHADOW` | All READY thresholds met (below) |
| 12 | `ITERATE_PROMPT` | Default — quality insufficient |

**Critical distinctions:**

* **Grounding phrase failures** (`grounding_failure`) → `ITERATE_PROMPT`, not `BLOCKED_BY_EVIDENCE`.
* **Evidence/case seam failures** (`evidence_unresolved`, `digest_mismatch`, `invalid_case`, `invalid_gold_overlay`) → `BLOCKED_BY_EVIDENCE`.
* **Evidence selection mismatches** are tracked separately; they contribute to quality signals but follow the general `ITERATE_PROMPT` path unless masked by higher-priority blocks.
* **Unsafe and source-leakage** are evaluated **before** the input-representation heuristic.

### READY thresholds (code constants)

| Constant | Value | Meaning |
| --- | --- | --- |
| `READY_DEV_MEDIAN_EXACT_MATCHES` | 4 | Development median exact matches ≥ 4 of 6 gold rows |
| `READY_DEV_RESOLVED_EXACT_MATCHES` | 2 | Per-run threshold for a qualifying development run |
| `READY_DEV_RESOLVED_EXACT_RUNS` | 2 | At least 2 development runs with resolved exact ≥ 2 (not min-across-all) |
| `READY_MIN_HOLDOUT_STATUS_ACCURACY` | 0.80 | Holdout min status accuracy ≥ 0.80 |
| `READY_MIN_NOT_APPLICABLE_ACCURACY` | 1.0 | All candidate cohorts min not_applicable accuracy ≥ 1.0 |
| `READY_MIN_HOLDOUT_EXACT_OCCURRENCE` | 1 | Holdout `exact_occurrence_match.min` ≥ 1 |
| `READY_MIN_HOLDOUT_EXACT_VALID_TIME` | 1 | Holdout `exact_valid_time_match.min` ≥ 1 |

Additional READY requirements (enforced by priority order before step 11):

* `seals_verified=True` (skip-seal only allowed with `fake=True`; skipped seals cannot READY)
* Live runs require a clean git worktree via `git status --porcelain` **without** `-uno` (non-ignored untracked files block); ignored calibration artifacts stay excluded by pathspec. Development and baseline-mirror fixtures are verified against execution-commit blobs (`verify_fixtures_tracked_at_commit`). Aggregate records `aggregate_build_sha` and `provider_run_repository_shas`, which must be identical (`[aggregate_build_sha]`) for READY
* Zero unsafe / source leakage / grounding / failed runs
* Manifest consistency OK on **all** cohorts (baseline and candidate), including exact expected case ID per lane/cohort
* Every failure/success manifest must include `repository_sha`

* Zero candidate unsafe over-resolution **across all cohorts and repetitions**.
* Zero candidate source leakage false positives.
* Zero candidate failed runs (`failure_count == 0` everywhere).
* Manifest consistency OK on all cohorts.

**Non-negotiable:** one successful repetition cannot hide unsafe or lane-coverage failures in other repetitions (`exact_*_match.min`, not `.max`).

---

## §17 Stop conditions

Stop and report (do not absorb scope) when:

* TL01B baseline fingerprints drift without an explicit baseline contract amendment;
* holdout or adversarial fixtures were edited after sealing without a new seal commit;
* seal commit is not an ancestor of the execution commit;
* worktree fixture bytes differ from seal commit blobs;
* development and holdout assertion or evidence IDs overlap;
* adversarial V1 path is used instead of V2;
* adversarial V2 reuses few-shot contamination terms;
* TL01C few-shots contain sealed cohort terms;
* implementation requires TL00/TL01 schema changes;
* implementation requires graph writes or Timeline API/UI;
* an open PR already owns this capability.

Use:

```text
Stop condition:
Repository SHA:
Calibration ID:
Holdout seal commit:
Adversarial seal commit:
Affected cohort:
Exact failure:
Why TL01C cannot absorb it:
Required contract or evidence decision:
Suggested successor slice:
Operator decision required:
```

---

## §18 Required tests

### Baseline freeze tests (`tests/test_temporal_shadow_extraction_tl01c.py`)

* `test_baseline_instructions_fingerprint_stable`
* `test_baseline_v1_rendered_packet_fingerprint_stable`
* `test_v1_packet_lacks_source_context_v2_includes_provenance_only`
* `test_unknown_prompt_version_fails_before_provider`

### Prompt content tests

* `test_tl01c_instructions_contain_required_distinction_phrases`
* `test_tl01c_synthetic_examples_exclude_sealed_cohort_terms`
* `test_resolve_prompt_spec_tl01c_packet_version`

### Cohort independence tests

* `test_development_and_holdout_assertion_ids_do_not_overlap`
* `test_development_and_holdout_evidence_ids_do_not_overlap`
* `test_adversarial_v2_excludes_few_shot_contamination`

### Calibration runner tests (`tests/test_temporal_shadow_prompt_calibration.py`)

* `test_baseline_and_candidate_outputs_separated`
* `test_independent_run_directories_per_repetition`
* `test_failed_repetitions_remain_visible`
* `test_aggregate_counts_match_underlying_manifests`
* `test_mixed_safe_unsafe_set_cannot_receive_ready_verdict`
* `test_one_correct_run_cannot_hide_unsafe_repetitions`
* `test_holdout_seal_fields_recorded_in_aggregate`
* `test_verify_cohort_seal_rejects_unknown_commit`
* `test_verify_cohort_seal_accepts_known_holdout_seal`
* `test_input_representation_blocked_when_wrong_value_dominates`
* `test_unsafe_blocks_before_input_representation`
* `test_evidence_case_failure_is_blocked_by_evidence`
* `test_provider_failure_decision`
* `test_aggregate_splits_occurrence_and_valid_leakage`
* `test_failed_repetition_appears_in_assertion_stability`
* `test_case_ids_populated_in_metrics_slice`
* `test_run_prompt_calibration_writes_separate_lane_dirs`

### Regression suite

```bash
uv run pytest tests/test_temporal_shadow_extraction_tl01c.py -q
uv run pytest tests/test_temporal_shadow_prompt_calibration.py -q
uv run pytest tests/test_temporal_shadow_extraction.py -q
uv run pytest tests/test_temporal_shadow.py -q
git diff --check
```

Record exact commands and results in the PR.

---

## §19 Live proof procedure

Execute in order:

### Phase 0 — Preconditions

1. Confirm PR `#452` / merge `6eeffe239c582f129f0c6bf167b0f6d6fc51f6c6` in ancestry.
2. Confirm baseline freeze tests pass (§18).
3. Resolve model from `MODEL_POLICY.json`; bootstrap env via `load_dungeonmindbuddy_dotenv()`.

### Phase 1 — Seal holdout and adversarial V2

1. Commit finalized holdout + adversarial V2 fixtures.
2. Record `holdout_seal_commit_sha` and `adversarial_seal_commit_sha`.
3. Do not edit sealed files after this point without re-sealing.

### Phase 2 — Development paired runs (3×)

Run full calibration matrix or individual development repetitions. Confirm:

* baseline development uses `tl01b-v1`;
* candidate development uses `tl01c-v1` + packet V2;
* overlays and comparisons land under `calibration/baseline/development/` and `calibration/candidate/development/`.

### Phase 3 — Baseline freeze confirmation

Before holdout live runs:

* re-run baseline fingerprint tests;
* confirm `FROZEN_TL01B_*` constants still match;
* confirm no drift in `TL01B_BASELINE_INSTRUCTIONS` or V1 packet rendering.

### Phase 4 — Holdout paired runs (3×)

Run with `--holdout-seal-commit` (and adversarial seal if running full matrix). Seal verification must pass before provider calls.

### Phase 5 — Adversarial V2 runs (3×)

Candidate adversarial lane only. Seal verification required.

### Phase 6 — Aggregate and report

1. Confirm `calibration/aggregate.json` written.
2. Record `calibration_id`, all seal fields, `decision`, `diagnostics`.
3. Author `Docs/Reports/REPORT-tl01c-temporal-prompt-calibration.md` from aggregate (human review).

### Fake / CI path

```bash
uv run python evals/graph_memory_layer/temporal_shadow_prompt_calibration.py \
  ... \
  --fake \
  --skip-seal-verification
```

Fake path skips seal verification and uses placeholder model batches.

---

## §20 Expected changed paths

In scope for TL01C:

```text
src/graph_memory/temporal_shadow_extraction.py          # registry, packet V2, tl01c instructions
src/graph_memory/temporal_shadow_extraction_schema.py   # calibration aggregate models
evals/graph_memory_layer/temporal_shadow_prompt_calibration.py
evals/graph_memory_layer/examples/temporal_shadow_cohort/temporal-case-tl01c.json
evals/graph_memory_layer/examples/temporal_shadow_holdout/
evals/graph_memory_layer/examples/temporal_shadow_adversarial_v2/
tests/test_temporal_shadow_extraction_tl01c.py
tests/test_temporal_shadow_prompt_calibration.py
Docs/Design/CONTRACT-temporal-prompt-calibration-v1.md
Docs/Plans/HANDOFF-tl01c-source-aware-temporal-prompt-calibration.md
Docs/Reports/REPORT-tl01c-temporal-prompt-calibration.md
```

Out of scope:

```text
src/graph_memory/kernel/temporal.py
src/graph_memory/temporal_shadow.py
TL01B comparison / EvaluationVerdict
evals/graph_memory_layer/examples/temporal_shadow_adversarial/   # V1 deprecated
Timeline API / UI
graph writes
```

---

## §21 Documentation contract

Maintain:

```text
Docs/Design/CONTRACT-temporal-prompt-calibration-v1.md
Docs/Plans/HANDOFF-tl01c-source-aware-temporal-prompt-calibration.md
Docs/Reports/REPORT-tl01c-temporal-prompt-calibration.md
```

Report must cite aggregate `calibration_id`, seal commits, model ID, decision, and per-cohort stability — not paraphrase without artifact linkage.

---

## §22 Explicit non-goals

TL01C does not:

* publish temporal data to the graph;
* change TL00 temporal kernel types;
* change TL01 overlay or preview contracts;
* replace per-run TL01B comparison with calibration-only scoring;
* auto-promote `tl01c-v1` without human review;
* mutate `tl01c-v1` after first live attempt (use TL01D instead);
* use adversarial V1 fixtures;
* allow arbitrary seal digest overrides;
* add participant roles, projected occurrences, timeline queries, or UI.

---

## §23 Demolition declaration

If this slice is abandoned:

* Remove calibration runner and aggregate schema **only** after archiving final `aggregate.json` and report to `Docs/Reports/`.
* Preserve TL01B extraction runner and sealed development cohort.
* Do not delete holdout/adversarial fixtures without documenting gold rationale.
* Prompt registry entries may remain if used by tests; otherwise revert candidate version only.

---

## §24 Acceptance criteria

1. PR `#452` in ancestry; implementation rebased on containing `origin/main`.
2. Baseline byte-stable: frozen fingerprint tests pass.
3. Prompt registry fail-closed on unknown versions.
4. Packet V2 adds `source_context` with `semantic_authority: provenance_only`.
5. Holdout and adversarial V2 sealed before candidate live runs; seal verification passes.
6. Separate aggregate seal fields populated (case/base/gold/commit for each cohort).
7. Three repetitions per required lane/cohort; failed reps remain visible.
8. Aggregate reproducible from on-disk run artifacts.
9. Decision priority matches §16; grounding → `ITERATE_PROMPT`; evidence/case → `BLOCKED_BY_EVIDENCE`.
10. Adversarial V2 independent of few-shots; V1 not used.
11. All §18 tests pass; `git diff --check` clean.
12. Live proof completed or explicitly deferred with operator sign-off and fake-path tests green.

---

## §25 Required PR body

```markdown
## Mission

Add source-aware temporal prompt calibration (TL01C) comparing frozen TL01B baseline
to tl01c-v1 candidate across development, holdout, and adversarial V2 cohorts.

## Dependency

PR #452 / merge 6eeffe239c582f129f0c6bf167b0f6d6fc51f6c6

## Capability

Frozen baseline + tl01c-v1 candidate + packet V2 source_context
→ repeated paired runs → calibration aggregate → CalibrationDecision

## Existing behavior preserved

- TL01B extraction runner unchanged
- TL01B comparison classifications unchanged
- TL00/TL01 contracts unchanged
- graph authority untouched

## Live calibration result

<model_id, calibration_id, seal commits, decision, key metrics>

## Explicitly not implemented

- graph publication
- Timeline API/UI
- participant roles
- tl01c-v1 in-place mutation after live attempt

## Tests

<exact commands and results>

## Next decision

<PROMPT_READY_FOR_BROADER_SHADOW | ITERATE_PROMPT → TL01D | BLOCKED_* | PROVIDER_FAILURE>
```

---

## §26 Required handback

The coding-agent handback must include:

1. Actual base SHA and head SHA.
2. Branch name.
3. Confirmation PR `#452` is in ancestry.
4. Exact changed paths (or `git diff --stat` filtered to TL01C scope).
5. Baseline fingerprint confirmation (`FROZEN_TL01B_*` tests passed).
6. Candidate prompt SHA256 (`compute_prompt_sha256("tl01c-v1")`).
7. Holdout seal commit SHA and verification result.
8. Adversarial V2 seal commit SHA and verification result.
9. All aggregate seal field values from live or fake run.
10. Model ID and provider response IDs (live runs).
11. `calibration_id` and aggregate path.
12. Final `decision` and `diagnostics`.
13. Per-cohort min/median/max exact and resolved exact.
14. Unsafe, source-leakage, grounding, evidence/case failure totals.
15. Assertion stability highlights (unstable assertions).
16. Every test command and result.
17. Paths outside allowlist, or `none`.
18. Runtime graph state touched, expected `none`.
19. Confirmation TL00/TL01 unchanged.
20. Confirmation no graph writes.
21. Stop conditions encountered, or `none`.
22. Successor recommendation (§27).

---

## §27 Successor decision

Do not assume TL02 is automatically next. Choose based on `CalibrationDecision`.

### When decision is `PROMPT_READY_FOR_BROADER_SHADOW`

Proceed to **broader shadow extraction cohort** (beyond sealed development/holdout/adversarial) per threat-statblock roadmap. Human review of aggregate + artifacts required before promotion.

### When decision is `ITERATE_PROMPT`

Dispatch **TL01D — prompt iteration slice**:

* new prompt version id (e.g. `tl01d-v1`);
* revise instructions and/or packet representation;
* re-run calibration against **same holdout/adversarial seal commits** for comparability;
* do **not** change TL01B baseline or TL01 contracts.

Grounding misses, unsafe over-resolution, and source leakage land here — not `BLOCKED_BY_EVIDENCE`.

### When decision is `BLOCKED_BY_EVIDENCE`

Repair source-span or case/evidence seam (`evidence_unresolved`, digest mismatch, invalid case/gold). Do not compensate with broader corpus access.

### When decision is `BLOCKED_BY_CONTRACT`

Write a contract decision before coding. Invalid payloads and unsupported prompt versions land here.

### When decision is `BLOCKED_BY_INPUT_REPRESENTATION`

Revise packet V2 transport (source_context shape, normalization visibility) or evidence packet layout — not TL01B comparison rules. Wrong temporal value with correct status/lane suggests representation gap.

### When decision is `PROVIDER_FAILURE`

Treat provider availability or model compatibility as the next dependency. Do not replace live proof with fake-client results.

---

## §28 Final directive

Build the experiment that tells us whether **source-aware prompt calibration** is trustworthy enough for broader shadow rollout.

Do not build the Timeline yet.

The correct progression is:

```text
typed temporal contract (TL00)
→ shadow overlay (TL01)
→ evidence-bound extraction (TL01B)
→ prompt calibration with sealed holdout + adversarial (TL01C)
→ broader shadow cohort OR prompt iteration (TL01D)
→ participant roles (TL02)
→ projected occurrences
→ node timelines
→ product surface
```

Preserve uncertainty.

Keep source provenance separate from fiction time.

Let unsafe over-resolution and source leakage remain visible across every repetition.

The Timeline project should advance because the calibration evidence supports it, not because a single green run appeared in one cohort.
