# PR006 — Eldyrwild C2 World Materialization Report

**Verdict:** PASS — acceptance corpus materialized to durable world graph head with provenance, integrity, and rebuild equivalence.

**Generated:** from `artifacts/graph_memory/pr006/eldyrwild-c2-materialization-report.json`

## Head revisions

| Field | Value |
|---|---|
| Baseline revision | `rev:304b0b388299f13510c2b3fcfa8fcdea` (`op:pr006-baseline`) |
| Final head revision | `rev:e8693f31816f9424d73718247880d3fb` |
| Parent at materialize start | baseline revision above |

## Inventory summary

| Metric | Count |
|---|---|
| Requested sources | 79 |
| Accepted sources | 79 |
| Skipped | 0 |
| Failed required | 0 |
| Recaps (sessions 1–23) | 23 |
| PC hubs | 6 |
| Worldbuilding (Mirathorn + Mireward) | 46 |
| Campaign hub sources | 2 |
| Mechanical statblocks | 2 |

## Graph counts

| Metric | Value |
|---|---|
| Nodes | 36 |
| Edges | 143 |
| Contributions merged | 79 |
| Accepted assertions | 223 |
| Assertions with source artifact linkage | 223 |

## Identity diagnostics

- Unresolved mentions: 0
- Rejected assertions: 0

## Integrity

- World integrity: valid
- Contribution integrity: valid
- Rebuild equivalent to head: yes
- Duplicate graph state created on idempotent replay: no

## Required hubs

- Mirathorn (`loc_mirathorn`): present
- Mireward (`loc_mireward`): present

## Examples (stable node IDs)

| Entity | Node ID | Source domain |
|---|---|---|
| PC Caelynn | `pc_caelynn` | worldbuilding (PC hub) |
| Captain Lysandra Ironveil | `npc_lysandra_ironveil` | npc_note (campaign hub) |
| Mirathorn | `loc_mirathorn` | worldbuilding |
| Mireward | `loc_mireward` | worldbuilding |
| Session 23 event | `event_session_23` | recap |
| Cross-session edge | `pc_*` → `event_session_N` (`participated_in`) | recap |

Session 23 additionally links `event_session_23` → `loc_mireward` (`occurred_at`, gate battle).

## Plan trust

**Plan can trust:**

- Persistent `eldyrwild` world graph head for `longmont-c2`
- Session 1–23 recap inventory with sha256 provenance
- Mirathorn + Mireward location nodes in merged head
- Six C2 PC hub nodes with kernel domain mapping
- Kernel merge + rebuild equivalence
- Source artifact linkage on every accepted assertion

**Plan cannot trust:**

- Revision-pinned projection slices (PR007)
- Latest-ingest / preview graph selection (PR008)
- Graph Review preview union as durable authority
- Autonomous agent writes without governed confirm (PR011)

## Unsupported PR007 requirements

- Revision-pinned Projection Engine
- Plan latest-ingest / preview selection migration
- Focus-session overlay semantics beyond read-model baseline
- Production retrieval over graph head without projection contract

## Retained temporarily

```
Retained temporarily:
- Graph-preview route parameters and preview projection adapters.
- Plan latest-ingest / preview selection consumers.

Reason:
- PR006 establishes persistent runtime graph availability but does not implement the revision-pinned Projection Engine or migrate Plan.

Remaining consumer:
- Existing Graph Review preview views.
- Existing Plan graph-preview/dogfood views.

Required deletion PR:
- PR007 removes production projection selectors.
- PR008 removes Plan latest-ingest / preview selection.
- PR012 catches only named leftovers.
```

## Bundle generation

```bash
uv run python -c 'from pathlib import Path; import json; from graph_memory.materialization.acceptance_manifest import load_acceptance_manifest; from graph_memory.materialization.candidate_bundle import build_deterministic_acceptance_bundle; repo=Path("."); mp=repo/"config/graph_memory/eldyrwild_c2_acceptance_manifest.json"; m=load_acceptance_manifest(mp); b=build_deterministic_acceptance_bundle(repo,m,manifest_path=mp); print(len(b["sources"]))'
```

## Operator CLI

```bash
uv run python scripts/materialize_eldyrwild_c2_world_graph.py inventory \
  --repo-root . \
  --manifest config/graph_memory/eldyrwild_c2_acceptance_manifest.json

uv run python scripts/materialize_eldyrwild_c2_world_graph.py materialize \
  --repo-root . \
  --manifest config/graph_memory/eldyrwild_c2_acceptance_manifest.json \
  --bundle artifacts/graph_memory/pr006/eldyrwild-c2-source-candidate-bundle.json \
  --store-root /tmp/dmb-pr006-world \
  --fresh-root \
  --report artifacts/graph_memory/pr006/eldyrwild-c2-materialization-report.json
```
