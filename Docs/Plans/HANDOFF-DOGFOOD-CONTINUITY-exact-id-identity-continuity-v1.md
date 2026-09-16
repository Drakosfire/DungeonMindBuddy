# HANDOFF — DOGFOOD-CONTINUITY exact-id identity continuity v1

**Created:** 2026-09-15  
**Status:** ACTIVE — one implementation capability  
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-exact-id-identity-continuity-v1.md`  
**Flow / owner:** `DOGFOOD-CONTINUITY`  
**Design authority base:** `main@68577114b3c8ec7e06bc0b0a8d382143fdc570ec`  
**PR title:** `DOGFOOD-CONTINUITY: confirm existing objects by exact durable id`

## §1 Mission and merge-ready invariant

**Mission:** When a candidate reuses an exact same-kind durable object id already
present on the sealed parent head, identity resolution confirms that object
(`resolved_existing`) even if surface labels drifted or cross-kind aliases share
the label — so governed materialization does not CREATE_NEW into an occupied id.

**Merge-ready invariant:**

```text
proposed_node_id / candidate_id equals parent same-kind object_id
  → resolved_existing (before label match / cross-kind block)
label drift alone never invents CREATE_NEW for that durable id
wrong-kind exact id does not force confirm
```

## §4 Write lease

```text
apps/live_control_server/models/world_graph_mutation_context.py
tests/test_exact_id_identity_continuity.py
Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-exact-id-identity-continuity-v1.md
Docs/Reports/REPORT-DOGFOOD-CONTINUITY-exact-id-identity-continuity-v1.md
```


**Lease serialization with #726:** both slices touch
`apps/live_control_server/models/world_graph_mutation_context.py`. Steward
decision: **serialize** — merge this #725 object exact-id slice before #726
edge exact-id; #726 rebases onto the #725 head. No concurrent unserialized
dual-write to that file.

## §7 Evidence

```bash
uv run pytest tests/test_exact_id_identity_continuity.py tests/test_pc_identity_normalization.py tests/test_cutover_native_governed_write.py -q
uv run ruff check apps/live_control_server/models/world_graph_mutation_context.py tests/test_exact_id_identity_continuity.py
```

## Predecessor STOP

`longmont-c1/session-2` / `dungeonmind_write` /
`parent_binding_mismatch` / `object_id=loc:rivers-edge-pub`.
