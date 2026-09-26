# STEWARD'S ANCHOR — CON-READY

**Status:** ACTIVE — MANDATORY PICKUP DOCUMENT
**Line of work:** `CON-READY / PLAY / DOGFOOD-CONTINUITY`
**Updated:** 2026-09-25
**Repository:** `Drakosfire/DungeonMindBuddy`
**Re-anchor:** `main@e696b20e5f5e34f0fb7cf2c8fb04dc48c1706ea4`
**Current frontier:** **PLAY-0 activation → PLAY-1 Buddy → WorldKeeper consumer proof**
**V2-3 derived gold:** **NOT AUTHORIZED**

> Repository truth supersedes chat reconstruction. The WorldKeeper extraction,
> V3 custom-predicate compatibility, and Buddy V3 profile are complete. PLAY-1
> is the sole next CON-READY implementation candidate. Its handoff remains
> BLOCKED until PLAY-0 merges, predecessor state is synchronized, and the
> steward re-anchors and activates the handoff on `main`.

## Mandatory pickup order

1. this anchor;
2. `Docs/Plans/PLAN-CON-READY-PLAY-dogfood-thread-v1.md`;
3. `Docs/Plans/HANDOFF-CON-READY-PLAY-worldkeeper-consumer-proof-v1.md`;
4. `Docs/Design/DESIGN-source-to-world-authoring-interaction-contract.md`;
5. `Docs/Plans/HANDOFF-CON-READY-worldkeeper-authoring-adapter-proof-v1.md`
   as the merged custom-predicate amendment only;
6. `Docs/Plans/HANDOFF-v6-1-dungeonbuddy-vnext-domain-runtime-foundation.md`
   for Buddy vNext domain runtime authority.

Historical V2-2 and the old transaction-semantics handoff are evidence only.

## Current accepted state

```text
V2-0 contract census                         COMPLETE
V2-1 published-recap local proposal          MERGED — #738
V2-1A working projection                     MERGED — #741
V2-2 governed World commit                   HISTORICAL — #742

PR #745 ownership reconciliation             MERGED
DungeonMind V5.4                             ACCEPTED
DungeonMind semantic-profile V3              ACCEPTED — #77/#78
WorldKeeper WK-5 consumer seam               ACCEPTED — #7
WorldKeeper V3 compatibility                 ACCEPTED / MERGED — #8
Buddy V6.1 domain runtime                    ACCEPTED — #749
Buddy custom-predicate profile V3            MERGED — #754
Buddy PLAY custom-predicate amendment        MERGED — #752

PLAY-0                                       CURRENT PR
PLAY-1 consumer proof                        NEXT / BLOCKED
PLAY-2 persistent isolated authority         BLOCKED
PLAY-3 browser dogfood                       BLOCKED
production authority migration               SEPARATELY GOVERNED
V2-3 derived gold                            NOT AUTHORIZED
```

## Ownership

### DungeonBuddy

Interaction, reversible drafts, exact create-new/use-existing choice, GM-authored
relationship term selection, prepared-change review, and result UX.

### WorldKeeper

`WorldChangeIntent`, semantic preparation, same-transaction dependency
resolution, `PreparedWorldChange`, confirmation coordination, and verified-result
reshaping.

### DungeonMind

Durable identities, semantic-profile/provenance/admission authority, immutable
revisions, atomic publication, and durable replay/recovery.

## PLAY-1 decision

PLAY-1 proves a bounded backend consumer against isolated in-memory vNext
authority.

Canonical transaction:

```text
existing Pippa
+ create The Wizard's Tower Brewing Co
+ Pippa dungeonbuddy.custom:works_at local:brewery
→ Buddy mapper
→ WorldChangeIntent
→ WorldKeeper
→ one verified DungeonMind child
```

A second previously unknown valid term such as
`dungeonbuddy.custom:mentors` must use the same generic mapping branch.

Buddy must not replace authored custom terms with fixed predicates.

Existing V2-pinned Worlds are not migrated by PLAY-1.

## Holds

PLAY-1 does not authorize:

- production Graph Authoring route switching;
- persistent/PostgreSQL PLAY authority;
- source admission;
- occurrence/mention binding or `link_existing`;
- merge/reconciliation;
- bridge-genesis or legacy→vNext migration;
- live Eldyrwild mutation;
- Agent authoring;
- V2-3.

## Dispatch

After PLAY-0 merges:

1. synchronize PLAY-0 predecessor state and re-anchor fresh `main`;
2. record the merged base and current dependencies, then activate the PLAY-1
   handoff on `main`;
3. create `codex/con-ready-play-1-worldkeeper-consumer-proof`;
4. execute only the ACTIVE PLAY-1 handoff;
5. open exactly one serial implementation PR;
6. do not merge without Steward review.
