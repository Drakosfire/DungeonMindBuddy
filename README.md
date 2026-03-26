# DungeonMindBuddy

DungeonMindBuddy is a narrative knowledge graph and canon-reduction project for TTRPG campaign material. It converts source documents into schema-validated evidence and fact records, then derives campaign-specific projections with deterministic conflict handling.

## Current implemented scope

- Versioned schema contracts in `schemas/v0.1/`
- Canon layering model:
  - world layer (`canon_layer=world`, `campaign_id=null`)
  - campaign layer (`canon_layer=campaign`, `campaign_id=<id>`)
- Deterministic reducer and benchmark harness:
  - `src/reducer/canon_projection.py`
  - `evals/canon_layering/`
- Remote corpus inventory + normalization tooling:
  - `evals/corpus_remote/build_remote_inventory.py`
  - `evals/corpus_remote/validate_remote_artifacts.py`
  - `evals/corpus_remote/run_remote_snapshot_pipeline.py`
  - `scripts/run_remote_snapshot_from_env.sh`

## Project structure

- `schemas/v0.1/` - normative JSON schema contracts and examples
- `src/contracts/` - schema validation helpers
- `src/reducer/` - deterministic projection logic
- `tests/` - contract, reducer, benchmark, and remote-ingestion tests
- `evals/canon_layering/` - hard-gated benchmark scenarios and runner
- `evals/corpus_remote/` - remote corpus inventory and validation pipeline
- `out/` - generated artifacts (gitignored)

## Setup

This repository uses `uv` for Python dependency and environment management.

```bash
uv sync
```

## Verification commands

```bash
uv run ruff check .
uv run pytest tests/ --maxfail=1
uv run python evals/canon_layering/run_benchmarks.py
```

## Remote snapshot pipeline

### Environment file

Create `.env.ssh` in repo root:

```bash
SSH_PRIVATE_KEY=<ssh_password_or_secret>
SSH_HOST=<host_or_tailscale_ip>
SSH_ALIAS=<ssh_username>
```

### One-command run

```bash
scripts/run_remote_snapshot_from_env.sh
```

Optional arguments:

```bash
scripts/run_remote_snapshot_from_env.sh "<remote_docs_root>" <sample_size>
```

Default remote docs root:

`/media/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy/Docs/Eldyrwild and Campaign Context`

### Output artifacts

- `out/evals/corpus_remote/remote_inventory.json`
- `out/evals/corpus_remote/normalization_manifest.json`
- `out/evals/corpus_remote/reproducibility_report.json`

## Notes and limitations

- Current normalization sampling is deterministic by sorted path and may bias toward world documents unless stratified sampling is enabled.
- Source classification (`source_class`) still uses heuristic inference and should be hardened with path policy rules.
- This project is pipeline-first; no API or UI layer is implemented in this repository.
