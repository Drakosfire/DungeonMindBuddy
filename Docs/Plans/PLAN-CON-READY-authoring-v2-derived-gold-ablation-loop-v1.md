# PLAN — CON-READY: Authoring v2 → derived gold → extraction ablation loop

**Updated:** 2026-09-25
**Status:** ACTIVE SEQUENCING AUTHORITY — PLAY consumer migration next; V2-3 not authorized
**Repository:** `Drakosfire/DungeonMindBuddy`
**Re-anchor:** `main@e696b20e5f5e34f0fb7cf2c8fb04dc48c1706ea4`

## Current sequence

```text
V2-0 contract census                     COMPLETE / PASS
V2-1 published-recap local proposal      MERGED — #738
V2-1A working projection / UI dogfood    MERGED — #741
V2-2 governed World commit               MERGED / HISTORICAL — #742

WorldKeeper extraction                    COMPLETE
Buddy ownership reconciliation            MERGED — #745
WorldKeeper V3 compatibility              MERGED — #8
Buddy custom predicate profile V3         MERGED — #754
PLAY custom-predicate amendment           MERGED — #752

PLAY-0 thread activation                  CURRENT
PLAY-1 Buddy → WorldKeeper proof          NEXT
PLAY-2 persistent isolated authority      BLOCKED
PLAY-3 browser dogfood vertical           BLOCKED

V2-3 derived gold                        NOT AUTHORIZED
V2-4 extraction/model ablation           PARKED
V2-5 Agent-assisted authoring            PARKED
```

## Product mission

```text
read source
→ inspect governed World truth
→ stage reversible intent
→ review one PreparedWorldChange
→ explicitly confirm
→ inspect VerifiedCommittedChange
→ continue from source or World
```

The ownership split is settled:

```text
Buddy       interaction + application intent
WorldKeeper semantic transaction interpretation/coordination
DungeonMind durable governed truth
```

## Immediate next capability

PLAY-1 is the sole next implementation lane.

It proves:

```text
Buddy object + relationship proposals
→ WorldChangeIntent
→ WorldKeeper #8
→ isolated in-memory vNext authority
→ PreparedWorldChange
→ VerifiedCommittedChange
```

The canonical relationship uses an exact GM-authored custom predicate:

```text
dungeonbuddy.custom:works_at
```

and a second previously unknown valid custom predicate proves the namespace is
open by contract rather than special-cased.

The isolated parent uses Buddy semantic profile revision 2 from:

`dungeonbuddy_dnd5e_custom_predicate_profile()`.

No existing V2-pinned World is migrated.

Canonical handoff:

`Docs/Plans/HANDOFF-CON-READY-PLAY-worldkeeper-consumer-proof-v1.md`

## V2-3 gate

V2-3 remains unauthorized until at least:

1. PLAY-1 consumer semantics are accepted;
2. PLAY-2 proves persistent isolated authority and restart/reopen durability;
3. PLAY-3 demonstrates a coherent browser source → prepare → confirm → inspect loop;
4. Steward explicitly activates V2-3.

## Durable holds

- no automatic dedupe or implicit identity authority;
- no privileged Agent write route;
- no generic graph editor;
- no source-markdown mutation as World authoring;
- no object-first / relationship-repair publication;
- no prospective durable-ID prediction in Buddy or WorldKeeper;
- no occurrence/mention binding inferred from evidence;
- no production authority switch hidden inside PLAY;
- no implementation from historical/retired handoffs.
