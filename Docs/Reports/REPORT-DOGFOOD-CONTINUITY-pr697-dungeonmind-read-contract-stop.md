# REPORT — PR #697 DungeonMind selected-object read-contract stop

**Recorded:** 2026-09-08
**Closed:** 2026-09-09
**Buddy PR:** #697 — `DOGFOOD-CONTINUITY: project complete World objects across surfaces`
**Buddy branch:** `dogfood-continuity/surface-neutral-full-world-object-projection-v1`
**Canonical design handoff:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-surface-neutral-full-world-object-projection-v2.md`
**State:** **HOLD CLOSED — CODE RESUMED**

---

## Stop condition (resolved)

DungeonMind previously could not provide a complete selected-node one-hop neighborhood as an object-centric read. That contract now exists.

## Owning boundary

DungeonMind:

```text
dungeonmind.application.world_graph_retrieval.WorldGraphRetrievalService.get_complete_object
CompleteObjectLookupResult
```

Buddy adaptation boundary:

```text
apps/live_control_server/integrations/dungeonmind/world_graph_reads.py
apps/live_control_server/services/world_graph_object_projection.py
```

## Unblock evidence accepted from DungeonMind

DungeonMind PR #52 merged on `main` as `d8f7a9f0d6b256f5cf4588987520bf286f1eade3`.

Review Cycle 3 PASS / MERGE-READY on exact head:

```text
bd0423da7ba917cb4010f173eeda2a3903430233
review 5149817087
```

Accepted contract:

- `get_complete_object()` returns the complete selected-object assertion ledger (existence, alias, summary, property, aspect) with evidence and temporal/assertion metadata.
- Those assertion IDs participate in provenance anchors; observability counts the widened ledger.
- >24 touching relationships and >32 distinct anchors without truncation.
- explicit `complete | partial` plus named partial reason.
- GM/PLAYER and cross-campaign behavior.
- temporal semantics preserved.
- Eldyrwild ~534ms cold / ~327ms warm.
- World head unchanged.

Non-blocking documented smell: `CompleteObjectLookupResult.property_assertions` means the full ledger on the complete result.

Inherited hosted CI `benchmark-smoke` failure (`WorldGraphProjectionService` without `reviewed_world_initializations`) is not a #52/#697 blocker.

## Buddy state authority

```text
PR #697                     DRAFT
#697 design                 ACTIVE / accepted direction (v2)
#697 implementation         CODE using WorldGraphRetrievalService.get_complete_object
#697 state                  HOLD CLOSED
Buddy completeness workaround FORBIDDEN
Stage 4                     NOT STARTED by this lane
```

## What remains before review

- focused/full automated evidence for the Buddy product join and cross-surface consumers
- §13 live Eldyrwild witnesses (Karsemine, unrelated node, high-degree node)
- human STOP after merge
- Stage 4 remains NOT DONE
