# Temporal Prompt Calibration V2 (generalized runner)

**Status:** Implemented (evaluation seam extension)  
**Authority modules:** `evals/graph_memory_layer/temporal_shadow_prompt_calibration.py`, `src/graph_memory/temporal_shadow_extraction_schema.py`  
**Supersedes (partially):** `CONTRACT-temporal-prompt-calibration-v1.md` — v1 remains authoritative for TL01C historical semantics; v2 documents runner generalization only.

## What changed from v1

### Control vs candidate versions derived from cases

Before any provider call, the runner loads control cases (`development_case`, `holdout_case`, optional `baseline_adversarial_case`) and candidate cases (`candidate_development_case`, `candidate_holdout_case`, `adversarial_case`).

- Every control case must share one `prompt_version` (baseline/control lane).
- Every candidate case must share one `prompt_version` (candidate lane).
- Control and candidate versions must differ.
- Mixed versions fail closed with `PromptVersionMismatchError` before provider invocation.

Derived versions populate: expected manifest checks, `compute_prompt_sha256`, `calibration_id`, metrics slices, and aggregate `baseline_prompt_version` / `candidate_prompt_version` fields (alongside existing sha fields).

Hardcoded `tl01c-v1` / `TEMPORAL_SHADOW_PROMPT_VERSION` literals are no longer used in the runner.

### Optional control adversarial lane

CLI: `--baseline-adversarial-case` (optional).

| `baseline_adversarial_case` | Run matrix per repetition |
| --- | --- |
| absent (default) | 5 lanes — historical TL01C matrix unchanged |
| present | 6 lanes — adds `baseline/adversarial` |

When set: paired equivalence is validated against `adversarial_case`; fixtures are verified tracked at the execution commit (same as development/baseline-mirror inputs).

### Calibration identity

`calibration_id` payload includes both control and candidate prompt versions and sha256 hashes so changing either prompt changes the id. Keys (baseline adversarial omitted when not run):

```text
baseline_prompt_version, candidate_prompt_version,
baseline_prompt_sha256, candidate_prompt_sha256,
holdout_case_sha256, holdout_seal_commit_sha,
adversarial_case_sha256, adversarial_seal_commit_sha,
model_id, repetitions, repository_sha, aggregate_build_sha,
provider_run_repository_shas
```

### Artifact paths (TL01D)

Regression and promotion aggregates are separated under:

```text
evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01d/regression/calibration/aggregate.json
evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/tl01d/promotion/calibration/aggregate.json
```

TL01C live aggregate remains at `live/calibration/aggregate.json` (frozen).

## Unchanged from v1

- `compute_calibration_decision` priority order and READY threshold constants
- Failure code routing buckets
- Seal verification semantics (`verify_cohort_seal`, `--holdout-seal-commit`, `--adversarial-seal-commit`)
- Clean worktree checks for live runs
- Paired baseline/candidate fixture equivalence rules (contribution, gold, assertions, evidence)

## TL01D invocation profile

| Lane | Prompt version | Fixture role |
| --- | --- | --- |
| Control (baseline) | `tl01c-v1` (frozen TL01C candidate becomes TL01D control) | development + holdout mirrors |
| Candidate | `tl01d-v1` | candidate mirrors + adversarial V2 |

Exact case paths are chosen at CLI invocation; the runner derives versions from those files rather than assuming TL01C ids.
