# PLAN — CON-READY: Authoring v2 → derived gold → extraction ablation loop

**Created:** 2026-09-18
**Updated:** 2026-09-25
**Status:** ACTIVE SEQUENCING AUTHORITY — WorldKeeper extraction complete; Buddy consumer migration next; V2-3 not authorized
**Canonical path:** `Docs/Plans/PLAN-CON-READY-authoring-v2-derived-gold-ablation-loop-v1.md`
**Workstream:** `CON-READY / DOGFOOD-CONTINUITY / campaign memory authoring`
**Re-anchor:** `main@08e4c39967e63bc3b60791748129ca3eaa42f161`
**Authority reconciliation:** PR #745

## Current sequence

```text
V2-0 contract census                     COMPLETE / PASS
V2-1 published-recap local proposal      MERGED — #738
V2-1A working projection / UI dogfood    MERGED — #741
V2-2 governed World commit               MERGED / HISTORICAL — #742
WorldKeeper extraction WK-1..WK-5        COMPLETE
DungeonMind V5.4                         COMPLETE
WorldKeeper WK-5 consumer seam           COMPLETE
source-to-World authority reconciliation CURRENT — #745
Buddy consumer migration                 NEXT — NOT YET IMPLEMENTED
V2-3 derived gold                        STILL NOT AUTHORIZED
V2-4 extraction/model ablation           PARKED
V2-5 Agent-assisted authoring            PARKED
```

The WorldKeeper side quest has returned. The old question—whether same-batch
references belong in a repaired Buddy classifier or in the extracted
boundary—is settled. WorldKeeper owns semantic dependency resolution;
DungeonMind V5.4 owns durable-ID allocation/substitution and atomic publication.

## Product mission

The product loop remains:

```text
read source
→ inspect governed World truth
→ stage reversible intent
→ review one PreparedWorldChange
→ explicitly confirm
→ inspect the verified durable result
→ continue from source or World
```

The accepted ownership split is defined by
`DESIGN-source-to-world-authoring-interaction-contract.md`.

## Current decision

PR #745 is authority reconciliation only. It must land the missing Buddy design
ancestry, record the completed WorldKeeper extraction, retire the legacy
transaction-semantics handoff, and establish the next gate.

PR #745 must not implement:

- a WorldKeeper runtime/client integration;
- production write switching;
- bridge-genesis migration;
- a legacy classifier repair;
- V2-3 or later authoring capabilities.

Those runtime and cutover concerns remain outside the V6.1 foundation slice and
belong to separately designed later work.

## Next bounded capability

After #745 merges and state authority is synchronized, the steward may design a
fresh Buddy consumer-migration slice. It must use:

```text
Buddy
  client_op_id + reversible interaction intent
        ↓
WorldKeeper WK-5
  WorldChangeIntent
  result_of(client_op_id)
  PreparedWorldChange
  confirmation coordination
  verified-result reshaping
        ↓
DungeonMind V5.4
  source/provenance/admission authority
  durable-ID allocation + dependency substitution
  atomic publication + durable recovery
```

The new handoff must re-anchor current `main`, declare PR topology, identify
its write/runtime lease, and choose one independently useful consumer path. No
old handoff activates automatically.

## V2-3 gate

V2-3 derived gold remains unauthorized until:

1. #745 merges and the CON-READY authorities agree;
2. a bounded Buddy consumer migration is explicitly designed, implemented,
   reviewed, merged, and dogfooded;
3. the source → prepared change → confirmed durable result loop is coherent
   enough that exported examples represent the intended product;
4. the steward explicitly activates a new V2-3 handoff.

## Durable holds

- No automatic dedupe or implicit identity authority.
- No privileged Agent write route.
- No generic graph editor.
- No source-markdown mutation disguised as World authoring.
- No partial object-then-relationship publication.
- No prospective durable-ID prediction in Buddy or WorldKeeper.
- No implementation lane from a COMPLETE/HISTORICAL handoff.

## Authority map

- interaction authority:
  `Docs/Design/DESIGN-source-to-world-authoring-interaction-contract.md`
- current pickup:
  `Docs/Plans/STEWARDS-ANCHOR-con-ready.md`
- completed side quest:
  `Docs/Plans/HANDOFF-CON-READY-worldkeeper-sidequest-v1.md`
- retired migration evidence:
  `Docs/Plans/HANDOFF-CON-READY-source-to-world-transaction-semantics-v1.md`
- durable World architecture:
  `Docs/Design/ARCHITECTURE-campaign-supergraph.md`
- vNext foundation boundary:
  `Docs/Plans/HANDOFF-v6-1-dungeonbuddy-vnext-domain-runtime-foundation.md`
