# REPORT — PR #697 DungeonMind selected-object read-contract stop

**Recorded:** 2026-09-08
**Buddy PR:** #697 — `DOGFOOD-CONTINUITY: project complete World objects across surfaces`
**Buddy branch:** `dogfood-continuity/surface-neutral-full-world-object-projection-v1`
**Canonical design handoff:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-surface-neutral-full-world-object-projection-v2.md`
**State:** **DESIGN HOLD — CODE NOT STARTED**

---

## Stop condition

DungeonMind cannot currently provide a complete selected-node one-hop neighborhood as an object-centric read. DungeonMindBuddy must not fake completeness.

## Owning boundary

DungeonMind:

```text
dungeonmind.application.world_graph_retrieval.RetrievalBounds
WorldGraphRetrievalService.get_object
WorldGraphRetrievalService.get_neighborhood
```

Buddy adaptation boundary:

```text
apps/live_control_server/integrations/dungeonmind/world_graph_reads.py
```

## Observed capability

DungeonMind already owns exact object and neighborhood reads over one coherent scoped/admissible World projection. These reads are intentionally bounded.

The current transport-neutral retrieval implementation enforces hard ceilings:

```text
objects         12
relationships   24
assertions      32
anchors         32
```

Normal defaults are lower. Truncation is reported honestly through `coverage.truncated_fields`.

Therefore these operations provide a trustworthy **bounded/partial retrieval**, not the v2 requirement for a complete selected object.

DungeonMind can also project the broader admitted graph, but asking Buddy to request the whole World/campaign projection and slice one object locally is explicitly forbidden by the v2 handoff. It would move graph selection/reconstruction into the product client and make selected-object latency/payload scale with the whole World.

## Missing contract

DungeonMind needs one object-centric operation which, at a pinned/current World revision and ordinary scope/admissibility context, can return:

- the exact selected node;
- every admitted incoming one-hop relationship;
- every admitted outgoing one-hop relationship;
- every related endpoint required by those relationships;
- selected-node admitted attributes/assertions required by the retrieval contract;
- all supporting evidence/source-anchor metadata exposed by authority;
- lossless assertion/temporal metadata already carried by authority;
- explicit `complete | partial` semantics;
- no silent dependence on the existing 12/24/32/32 product result caps.

A result labeled complete must actually be complete for the selected-object contract.

## Why Buddy cannot safely compensate

Buddy must not:

- union bounded `get_object`, search, or neighborhood fragments to reconstruct graph truth;
- paginate arbitrary retrieval fragments and declare the union authoritative;
- call `project_world_graph`, receive the entire admitted graph on each click, and locally slice it;
- raise/guess DungeonMind caps and call the result complete;
- hide `coverage.truncated_fields`;
- omit high-degree relationships for presentation convenience.

All of those violate the authority split established by DungeonMind cutover and the #697 v2 completeness invariant.

## DungeonMind successor

Created in `Drakosfire/DungeonMind`:

```text
branch:
  retrieval/complete-selected-object-one-hop-v1

base:
  e82e790e011773369f07b1b431482d5026d4dd3e

handoff:
  Docs/Handoffs/HANDOFF-complete-selected-object-one-hop-read.md

handoff commit:
  6ed0e82227c2a6a419ab71ce7bbd16fb8d478e7a
```

Mission:

> Add one DungeonMind-native complete selected-object read over the existing coherent read/projection authority, with all admitted one-hop relationships/endpoints and explicit completeness semantics, while preserving scope/admissibility/provenance/temporal behavior and leaving existing bounded retrieval intact.

## Buddy state authority

Until the DungeonMind successor is implemented, reviewed, and accepted:

```text
PR #697                     DRAFT
#697 design                 ACTIVE / accepted direction
#697 implementation         NOT STARTED
#697 state                  DESIGN HOLD
Buddy completeness workaround FORBIDDEN
Stage 4                     NOT STARTED by this lane
```

After the DungeonMind successor lands, #697 resumes from the same v2 handoff. The product design does not need to be weakened or re-scoped merely because the current authority contract is bounded.

## Unblock evidence required from DungeonMind

DungeonMind must hand back at least:

```text
exact accepted head
selected-object operation/result contract
one object with >24 admitted touching relationships
all relationships returned
all opposite endpoints returned
completeness = complete
required truncated_fields = []
World-cross-campaign request witness
GM/PLAYER fail-closed witness
temporal/assertion metadata preservation witness
read timing/count observability
World head unchanged
```

Only then may Buddy #697 begin CODE.

---

## What remains false

- Buddy still cannot truthfully project a complete selected World object.
- Cross-surface semantic parity is not implemented.
- Cross-source APP-STATE provenance hydration for the complete object is not implemented.
- Agent selected-object parity is not implemented.
- No performance acceptance witness exists for the complete object contract.
- Stage 4 presentation remains intentionally downstream.
