# REPORT — DOGFOOD-CONTINUITY current-corpus admission acceptance v1

**Status:** HOLD — progressive dogfood; edge repair landed; pristine rerun in flight  
**Handoff:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-current-corpus-admission-acceptance-v1.md`  
**Harness PR:** #722  
**Repair PRs:** #723 · #724 · #725 · #726  
**Latest combined head:** `d3315694` (`dogfood-continuity/acceptance-rerun-after-exact-edge`)

## Cleared STOP classes (code; dogfood proof pending fresh execute)

| Failure | Repair |
|---|---|
| `endpoint_kind_not_admitted` at write | #723 admission eligibility |
| `duplicate_node_id` (blocked cross-class shared ids) | #724 |
| `parent_binding_mismatch` same-kind exact id / label drift | #725 |
| `parent_binding_mismatch` wrong-kind exact id CREATE_NEW | #725 follow-up (`blocked_collision`) |
| `relationship_id_collision` occupied compatible edge | #726 exact edge-id continuity |

## Best depth so far (handback; not yet superseded by this head)

`execute-2026-09-15T225036Z-86661d42` sealed **C1 sessions 1–8** before
`parent_binding_mismatch` on `node:city_council` (wrong-kind; blocked in #725).

## Prior execute that motivated #726 (handback)

```text
run: execute-2026-09-15T230452Z-857c2c0f
sealed: longmont-c1 session-1 .. session-5
last good head: rev:55c131aa12c9295476660abce3cbb46e
STOP: longmont-c1 / session-6
boundary: dungeonmind_write
reason: relationship_id_collision
relationship_id: edge:node:torbin:located_in:loc:hempholm
model_calls: 6
```

## Immediate next

Pristine full `--execute` on this combined head. No resume from session-6.
Structural acceptance remains HOLD until one uninterrupted run clears the
frozen current corpus.
