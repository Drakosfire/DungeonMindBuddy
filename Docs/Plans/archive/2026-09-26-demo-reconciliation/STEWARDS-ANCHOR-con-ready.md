# STEWARD'S ANCHOR — CON-READY

**Status:** ACTIVE — MANDATORY PICKUP DOCUMENT
**Line of work:** `CON-READY / PLAY / DOGFOOD-CONTINUITY`
**Updated:** 2026-09-25
**Repository:** `Drakosfire/DungeonMindBuddy`
**Re-anchor:** `main@f30b4c906bb179b25f00207c40cb38c0debdc264`
**Current frontier:** **PLAY-1 active — in-memory WorldKeeper consumer proof**
**V2-3 derived gold:** **NOT AUTHORIZED**

> Repository truth supersedes chat reconstruction. PLAY-0 / PR #753 is merged and accepted. PR #767 merged at `f30b4c906bb179b25f00207c40cb38c0debdc264`, releasing `pyproject.toml`. PLAY-1 is the sole ACTIVE CON-READY implementation slice; this guarded Steward sync places its authority on `main` before redispatch.

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

PLAY-0                                       COMPLETE / MERGED — #753
  accepted head                              25197d1b9f2dbf96752e453c34456830d5a99d1a
  final review                               5324695932
  merge                                      6e92bec11df22b4b4243cb58c1bbcbe43b109ff6
PLAY-1 consumer proof                        ACTIVE — #767 MERGED
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

PR #767 merged; its `pyproject.toml` collision is resolved. Dispatch is
authorized only for the bounded PLAY-1 handoff:

1. fetch fresh `main`;
2. verify no open PR owns `pyproject.toml`, `uv.lock`, or
   `apps/live_control_server/integrations/worldkeeper/**`;
3. re-verify WorldKeeper, DungeonMind, and Buddy V3 profile pins;
4. land the ACTIVE handoff on `main` through the guarded Steward sync;
5. rebase and use `codex/con-ready-play-1-worldkeeper-consumer-proof`;
6. execute only that ACTIVE handoff;
7. open exactly one serial implementation PR;
8. do not merge without Steward review.
