# Contract — Graph Kernel Public Boundary

**Status:** ACTIVE AUTHORITY (boundary contract for PR003+)  
**Date:** 2026-07-10  
**Architecture:** [`ARCHITECTURE-campaign-supergraph.md`](./ARCHITECTURE-campaign-supergraph.md)  
**Tracker:** [`PR-TRACKER-campaign-supergraph.md`](../Plans/PR-TRACKER-campaign-supergraph.md) (PR003)

## Legal import surface

Application and runtime code outside `src/graph_memory` should import durable
graph operations from:

```text
graph_memory.kernel
```

Do **not** import these as application API:

```text
graph_memory.world_supergraph.storage
graph_memory.world_supergraph.paths
graph_memory.world_supergraph.integrity
graph_memory.world_supergraph.model
graph_memory.world_supergraph.contribution_store
graph_memory.union_supergraph.load
graph_memory.union_supergraph.validate
graph_memory.union_supergraph.preview_import
graph_memory.union_supergraph.preview_run_materialize
```

Legacy preview adapters may retain those Python imports only with an explicit
`PR003_LEGACY_GRAPH_PREVIEW_EXEMPTION` comment tied to PR006–PR008 deletion.

TypeScript preview/latest-ingest selectors are gated by an **exact file + selector
allowlist** in `tests/test_graph_kernel_boundaries.py` (`TS_LEGACY_SELECTOR_ALLOWLIST`).
A file-level exemption comment does **not** bypass the TypeScript guard.

## Available in PR003

World SuperGraph head/revision operations re-exported from PR002 storage:

- `open_world_graph_head` / `open_current_world_graph`
- `load_current_world_graph` / `load_world_graph_revision`
- `publish_world_graph_revision` / `publish_world_revision`
- `rollback_world_graph_head`
- `build_world_graph_integrity_report` / `build_world_integrity_report`

## Available in PR004 — identity

Exported from `graph_memory.kernel` (implemented; not reserved):

- `resolve_identity` / `classify_identity_outcome` (pure classifiers; no silent mutation)
- `record_identity_decision`
- `merge_identity` / `split_identity` / `unmerge_identity`
- Models: `IdentityCandidate`, `IdentityResolution`, `IdentityDecisionRecord`,
  `IdentityResolutionPolicy`

## Available in PR005 — contribution / merge

Exported from `graph_memory.kernel` (implemented; not reserved):

- `create_graph_contribution` / `build_assertion` / deterministic ID helpers
- `merge_contribution_to_revision`
- `supersede_graph_contribution` / `retract_graph_contribution`
- `rebuild_from_contributions`
- `build_contribution_integrity_report`
- Models: `GraphContribution`, `GraphContributionAssertion`,
  `DurableAssertionSupport`, `ContributionMergeResult`,
  `ContributionIntegrityReport`

Contribution ledger storage lives under `world_supergraph/contribution_store.py`
and is **not** a legal app import — use the Kernel APIs above.

## Reserved (not complete)

Placeholders live in `src/graph_memory/kernel/contracts.py` and raise
`NotImplementedError`. They are **not** exported from `graph_memory.kernel`.

### PR007 — projection

`project_world_graph`, `build_projection_payload`,
`resolve_projection_admissibility`

## Enforcement

CI tests:

- `tests/test_graph_kernel_public_api.py`
- `tests/test_graph_kernel_boundaries.py`
