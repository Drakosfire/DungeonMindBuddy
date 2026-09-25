# STEWARD'S ANCHOR — CON-READY

**Status:** ACTIVE — MANDATORY PICKUP DOCUMENT
**Line of work:** `CON-READY / DOGFOOD-CONTINUITY`
**Updated:** 2026-09-25
**Repository:** `Drakosfire/DungeonMindBuddy`
**Re-anchor:** `main@08e4c39967e63bc3b60791748129ca3eaa42f161`
**Authority reconciliation:** PR #745 — no implementation lease
**Current frontier:** **Buddy consumer migration — NEXT / NOT YET IMPLEMENTED**
**Active legacy V2-2 implementation:** **NONE**
**V2-3 derived gold:** **NOT AUTHORIZED**

> Repository truth supersedes chat reconstruction. WorldKeeper extraction and
> DungeonMind V5.4 are complete. Reconcile Buddy authority in #745, then design
> one bounded consumer-migration handoff. Do not dispatch from historical
> handoffs.

## Mandatory pickup order

1. this anchor;
2. `Docs/Design/DESIGN-source-to-world-authoring-interaction-contract.md`;
3. `Docs/Plans/PLAN-CON-READY-authoring-v2-derived-gold-ablation-loop-v1.md`;
4. `Docs/Plans/HANDOFF-CON-READY-worldkeeper-sidequest-v1.md` as completed
   ancestry;
5. `Docs/Plans/HANDOFF-CON-READY-source-to-world-transaction-semantics-v1.md`
   as historical migration evidence;
6. `Docs/Plans/HANDOFF-v6-1-dungeonbuddy-vnext-domain-runtime-foundation.md`
   for the current runtime/cutover boundary.

## Current state

```text
V2-0 contract census                     COMPLETE / PASS
V2-1 published-recap local proposal      MERGED — #738
V2-1A working projection / UI dogfood    MERGED — #741
V2-2 governed World commit               MERGED / HISTORICAL — #742
WorldKeeper extraction WK-1..WK-5        COMPLETE
WorldKeeper PR #7                        MERGED
DungeonMind V5.4                         COMPLETE
WorldKeeper WK-5 consumer seam           COMPLETE / AVAILABLE
PR #745                                  AUTHORITY RECONCILIATION
Buddy consumer migration                 NEXT — NOT YET IMPLEMENTED
V2-3 derived gold                        NOT AUTHORIZED
```

No old V2-2 implementation is active. #745 is documentation/authority
reconciliation, not an ACTIVE implementation handoff and not a production
switch.

## Accepted ownership boundary

### DungeonBuddy

- interaction and reversible drafts;
- source selection/presentation;
- explicit create-new versus use-existing choice;
- similarity presentation;
- prepared-change review and verified-result UX.

### WorldKeeper

- `WorldChangeIntent`;
- semantic interpretation;
- same-transaction dependency resolution;
- `PreparedWorldChange`;
- confirmation coordination;
- verified-result reshaping.

### DungeonMind

- durable object and relationship IDs;
- source and provenance authority;
- profile, scope, and admission policy;
- immutable revisions and atomic publication;
- durable publication outcome/recovery;
- general World reads.

WorldKeeper is a thin coordinator. It does not own source admission, durable-ID
allocation/prediction, general reads, or durable recovery.

## Prospective-reference decision

```text
Buddy:       client_op_id
WorldKeeper: result_of(client_op_id)
             resolves semantic dependency
             never predicts durable identity
DungeonMind: atomically allocates durable IDs
             substitutes through dependent operations
             publishes one child
             returns client-operation → durable-result mappings
```

The prior Buddy prospective-durable-ID mechanism is historical evidence, not
the destination.

## PR #745 disposition

#745 lands:

- the accepted Buddy interaction authority;
- the completed WorldKeeper extraction record;
- retirement of the old transaction-semantics handoff;
- current Authoring v2 sequencing;
- this anchor and its exact design-agent mirror.

It does not land WorldKeeper runtime integration, production write switching,
bridge-genesis migration, or any other implementation. V6.1 explicitly leaves
those to later vNext/cutover work.

## Next action gate

After #745 merges and repository authority is synchronized, the steward may
design and land one fresh handoff for a bounded Buddy consumer migration. That
handoff must:

- re-anchor current `main`;
- be ACTIVE before dispatch;
- declare PR topology;
- name its exact lease and runtime ownership;
- consume the WorldKeeper WK-5 seam;
- preserve Buddy interaction ownership and DungeonMind durable authority;
- keep later production switching/runtime/bridge-genesis work out of scope.

No implementation is authorized by this anchor alone.

## Holds

Still held:

- V2-3 derived gold;
- extraction/model ablation;
- Agent-assisted authoring;
- identity reconciliation;
- generic graph-editor work;
- legacy classifier repair as the target architecture;
- implementation changes hidden in #745.

```text
AUTHORING V2                      RE-ANCHORED
WORLDKEEPER SIDE QUEST           COMPLETE / HISTORICAL
TRANSACTION-SEMANTICS HANDOFF    RETIRED / HISTORICAL
PR #745                          AUTHORITY RECONCILIATION
BUDDY CONSUMER MIGRATION         NEXT / NOT YET IMPLEMENTED
V2-3 DERIVED GOLD                NOT AUTHORIZED
```
