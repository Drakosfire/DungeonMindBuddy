# REPORT — DOGFOOD-CONTINUITY current-corpus admission acceptance v1

**Status:** HOLD — progressive dogfood; latest STOP at longmont-c1/session-6  
**Handoff:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-current-corpus-admission-acceptance-v1.md`  
**Harness PR:** #722  
**Repair PRs:** #723 · #724 · #725  
**Latest rerun head:** `5e4368e5` (`dogfood-continuity/acceptance-rerun-after-exact-id`)

## Cleared STOP classes

| Failure | Repair |
|---|---|
| `endpoint_kind_not_admitted` at write | #723 admission eligibility |
| `duplicate_node_id` (blocked cross-class shared ids) | #724 |
| `parent_binding_mismatch` same-kind exact id / label drift | #725 |
| `parent_binding_mismatch` wrong-kind exact id CREATE_NEW | #725 follow-up (`blocked_collision`) |

## Best depth so far

`execute-2026-09-15T225036Z-86661d42` sealed **C1 sessions 1–8** before
`parent_binding_mismatch` on `node:city_council` (wrong-kind; now blocked in #725).

## Latest execute (stochastic)

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

## Immediate successor

Narrow repair for **edge durable-id continuity**: when a candidate reuses an
exact `edge_id` already present on the parent head, do not CREATE_NEW that
relationship id (mirror node exact-id continuity; expect confirm-existing or
eligibility reject). Then fresh pristine `--execute`.
