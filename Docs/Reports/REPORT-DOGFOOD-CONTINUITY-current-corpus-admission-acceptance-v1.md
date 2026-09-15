# REPORT — DOGFOOD-CONTINUITY current-corpus admission acceptance v1

**Status:** HOLD — progressive dogfood; stopped at longmont-c1/session-9 after clearing earlier STOPs  
**Handoff:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-current-corpus-admission-acceptance-v1.md`  
**Harness PR:** #722  
**Repair stack on rerun head `b34eafc6`:** #723 endpoint-kind eligibility · #724 blocked cross-class id disambiguation · #725 exact-id identity continuity (+ wrong-kind occupied-id block)  
**World / DB:** `dogfood-current-corpus-acceptance-v1` / `dmb_current_corpus_acceptance_v1` @ `127.0.0.1:54329`

## Latest execute

```text
run: execute-2026-09-15T225036Z-86661d42
STRUCTURAL ACCEPTANCE: HOLD
sealed sessions: longmont-c1 session-1 .. session-8 (8)
last good head: rev:8d76f3ede8b137a694a136eda81a1435
STOP: longmont-c1 / session-9
boundary: dungeonmind_write
details: parent_binding_mismatch object_id=node:city_council
  (parent kind=party; candidate claimed location + CREATE_NEW into occupied id)
model_calls: 9
```

## Cleared STOPs (same dogfood series)

| Session | Prior failure | Repair |
|---|---|---|
| c1/s1 | endpoint kinds not admitted | #723 |
| c1/s2 | duplicate_node_id glowkindle | #724 |
| c1/s2 | parent_binding_mismatch loc:rivers-edge-pub | #725 same-kind exact id |
| c1/s9 | parent_binding_mismatch node:city_council | #725 follow-up wrong-kind occupied-id block (pending fresh rerun) |

## Next

Fresh pristine `--execute` with `b34eafc6` (includes wrong-kind occupied-id block).
