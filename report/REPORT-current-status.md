# DungeonMindBuddy Status Report

Date: 2026-03-26

## 1) Current Status

The project is in an executable checkpoint state with deterministic benchmarking, schema validation, reducer logic, and remote corpus snapshot tooling implemented and verified.

Most recent functional checkpoint commits:

- `c7f27d0` - canon-layer benchmark and remote ingestion harness
- `c4ba3df` - one-command remote snapshot wrapper script

## 2) Working Functionality

### 2.1 Canon layering in schema contracts

Implemented and wired through:

- `schemas/v0.1/common.schema.json` (`canonLayer`)
- `schemas/v0.1/evidence_unit.schema.json` (`canon_layer`, `campaign_id`, campaign-layer conditional)
- `schemas/v0.1/canon_decision.schema.json` (`campaign_id` scoping)

### 2.2 Deterministic reducer and benchmark harness

Implemented:

- Reducer: `src/reducer/canon_projection.py`
- Schema validator: `src/contracts/schema_validation.py`
- 6 deterministic scenarios: `evals/canon_layering/scenarios/`
- Benchmark runner: `evals/canon_layering/run_benchmarks.py`
- Hard thresholds: `evals/canon_layering/thresholds.json`

Generated outputs:

- `out/evals/canon_layering/results.json`
- `out/evals/canon_layering/report.md`
- `out/evals/canon_layering/determinism_hash_report.json`

### 2.3 Test coverage and quality gates

Implemented test suites:

- contract tests
- reducer golden-output tests
- provenance/isolation/determinism tests
- remote inventory/validator/runner tests

Verification commands currently passing:

- `uv run ruff check .`
- `uv run pytest tests/ --maxfail=1`
- `uv run python evals/canon_layering/run_benchmarks.py`

### 2.4 Remote corpus ingestion preparation

Implemented:

- Inventory generator: `evals/corpus_remote/build_remote_inventory.py`
- Artifact validator: `evals/corpus_remote/validate_remote_artifacts.py`
- Pipeline wrapper: `evals/corpus_remote/run_remote_snapshot_pipeline.py`
- Convenience shell wrapper: `scripts/run_remote_snapshot_from_env.sh`

Output artifacts:

- `out/evals/corpus_remote/remote_inventory.json`
- `out/evals/corpus_remote/normalization_manifest.json`
- `out/evals/corpus_remote/reproducibility_report.json`

## 3) Current Observations and Issues

### 3.1 Sampling bias in manifest selection

Current sampled manifest generation takes deterministic sorted-path prefix (`N` docs). This can over-represent world documents and under-represent campaign documents depending on path ordering.

Observed example:

- For sample size 100, manifest became entirely world-layer while campaign documents existed in full inventory.

### 3.2 Source class inference is heuristic

`source_class` inference currently relies on path-name pattern matching. This is useful for bootstrap but brittle for long-term correctness.

### 3.3 Remote operational assumptions

Remote path and corpus presence must be validated each run. Initial runs succeeded technically with zero-document inventory when path did not exist; this is now detectable through artifact inspection but should be hardened with explicit minimum-document gating.

## 4) Proposed Next Steps

### Priority 1: Stratified deterministic sampling

Replace prefix sampling with deterministic stratified sampling by:

- `canon_layer`
- `campaign_id`
- optional `source_class`

Target: guaranteed campaign-layer coverage in every sample (for example, minimum quota per detected campaign group).

### Priority 2: Add hard minimum-content gates

Fail remote pipeline if:

- `total_documents == 0`
- sample has zero campaign docs when campaign docs exist in inventory
- required source-class quotas are not met

### Priority 3: Path policy configuration

Introduce explicit mapping config (JSON/YAML) for:

- path-prefix -> `source_class`
- path-prefix -> `canon_layer`
- path-prefix -> `campaign_id`

Use this to replace fragile heuristics over time.

### Priority 4: Reducer parity on real extracted records

Next vertical expansion should connect:

- real ingestion/extraction output
- reducer benchmark projections
- conflict-resolution and canon-decision replay tests

## 5) Recommended Immediate Action

Implement stratified manifest sampling with hard gates before scaling benchmark size further. This will prevent false confidence from world-heavy sample slices and align benchmark coverage with the core goal: world vs campaign canon behavior under conflict and override conditions.
