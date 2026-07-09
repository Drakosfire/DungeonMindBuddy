# Graph Review A10 Archive

This index preserves the implementation and dogfood trail for the July 2026 Graph Review authored-memory spike.

The current architecture and restart point are:

- `Docs/Reports/SPIKE-CLOSEOUT-graph-review-authored-memory-2026-07.md`
- `Docs/Design/DESIGN-graph-object-authoring-surface.md`
- `Docs/Plans/ROADMAP-graph-object-authoring-surface.md`

## Why these documents remain

The A10 series contains useful evidence: early dogfood findings, decisions that changed during implementation, and the original A10m reconciliation plan. They are historical records, not authoritative descriptions of the current write path.

In particular, the original A10m handoff describes reconciliation as a separate explicit pass. PR #305 changed the operator path: a committed merge materializes automatically when a live `previewUnionStorePath` is selected, after overlay and event-log success. The closeout report describes that current behavior.

## Historical categories

| Category | Documents |
| --- | --- |
| Initial dogfood | `Docs/Reports/DOGFOOD-graph-object-authoring-a10-user-stories.md` |
| A10 hardening notes | `Docs/Plans/NOTE-a10b-authored-alias-prose-grounding.md`, `NOTE-a10c-node-detail-hierarchy.md`, `NOTE-a10d-authoring-form-clarity.md`, `NOTE-a10e-authoring-layout-quiet-source.md` |
| Durable merge design | `Docs/Plans/HANDOFF-a10m-union-supergraph-merge-reconciliation.md` |
| Durable merge dogfood | `evals/lysandra_vertical_slice/A10O-DURABLE-MERGE-MATERIALIZATION-BRIDGE.md` |

The documents remain at their original paths to preserve existing links. Each is marked with a historical-status banner rather than moved.
