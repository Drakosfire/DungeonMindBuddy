# A10m durable identity dogfood — Session 23 Lysandra

**Validated:** 2026-07-08  
**Harness:** `tests/test_a10m_lysandra_durable_identity_dogfood.py`

## What was validated

- Authored `merge_objects` assertion (`assert-merge-lysandra`) with GM-chosen survivor `party:captain_lysandra_ironveil`
- `plan_authored_merge_reconciliation` → `apply_union_supergraph_merge_plan` → `build_recap_graph_projection`
- Durable redirect `node:lysandra` → `party:captain_lysandra_ironveil`
- Merged-away node hidden from normal projection; survivor carries aliases, evidence, adjacency, merge provenance
- `dmb-node:node:lysandra` rewrites to survivor in projection markdown
- Overlay merge skipped when assertion already materialized (`union_identity_overlay_merge_skipped_durable`)

## Result

All acceptance assertions pass in the dogfood test module.

## Follow-ups (queued in Backlog.md)

- Union projection diagnostics — count alias mention redirects (non-blocking; dmb-node rewrites counted, alias-backed mentions not)
- A10n selected-object durable identity polish — present merge provenance in GM-facing card without raw scores by default
