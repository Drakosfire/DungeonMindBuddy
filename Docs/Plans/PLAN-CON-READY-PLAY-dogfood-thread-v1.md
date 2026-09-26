# PLAN — CON-READY PLAY: play-like World authoring dogfood thread

**Updated:** 2026-09-25
**Status:** ACTIVE SEQUENCING DESIGN — PLAY-0 activation
**Repository:** `Drakosfire/DungeonMindBuddy`
**Re-anchor:** `main@e696b20e5f5e34f0fb7cf2c8fb04dc48c1706ea4`
**WorldKeeper authority:** #8 merge `a0a70db275cf6c5f3876fe7b4d2a557de12388f5`
**DungeonMind runtime authority:** `0f709d76fdc53bac9c9258d1751463ae2c76ca71`
**Buddy custom profile authority:** #754 merge `7addcd05b20c894eb4d50b9d63e5ebdee4bc2cc7`
**V2-3:** NOT AUTHORIZED

## Goal

Make the source-to-World authoring loop usable enough to dogfood in a play-like
GM workflow without hiding the vNext/production authority boundary.

Target moment:

```text
source/session material
→ stage object + relationship
→ review exact PreparedWorldChange
→ explicitly confirm
→ receive VerifiedCommittedChange
→ inspect exact durable result
→ reopen and continue
```

## Sequence

```text
PLAY-0  thread design + truthful PLAY-1 handoff        CURRENT PR
PLAY-1  Buddy → WorldKeeper in-memory consumer proof   NEXT
PLAY-2  persistent isolated vNext PostgreSQL authority
PLAY-3  browser play-like dogfood vertical
PLAY-4  production-authority migration                 separately governed
```

## PLAY-1

PLAY-1 proves only the application boundary:

```text
Buddy staged proposals
→ Buddy-owned mapper
→ WorldChangeIntent
→ WorldChangeService
→ DungeonMindWorldKeeperRuntime
→ in-memory vNext authority
→ PreparedWorldChange
→ explicit commit
→ VerifiedCommittedChange
```

The canonical proof creates **The Wizard's Tower Brewing Co** and relates exact
existing **Pippa** to it with:

```text
dungeonbuddy.custom:works_at
```

A second previously unknown valid predicate, such as:

```text
dungeonbuddy.custom:mentors
```

must pass through the same generic branch. This proves the accepted open
predicate namespace rather than a special-case vocabulary mapping.

PLAY-1 uses Buddy semantic profile revision 2 from
`dungeonbuddy_dnd5e_custom_predicate_profile()`.

It does not migrate existing V2-pinned Worlds.

## Persistent holds

Across PLAY:

- Buddy never predicts durable IDs.
- WorldKeeper remains the semantic transaction coordinator.
- DungeonMind owns publication and durable authority.
- Evidence support does not imply occurrence binding.
- `link_existing` remains deferred occurrence/mention semantics.
- No automatic dedupe/merge.
- No object-first / relationship-repair publication.
- No hidden production route switch.
- No live Eldyrwild mutation before separately governed cutover.

## Current status

```text
PR #745 ownership reconciliation                  MERGED
DungeonMind semantic-profile V3                  ACCEPTED
WorldKeeper #8 V3 compatibility                  MERGED
Buddy #754 custom predicate profile              MERGED
Buddy #752 custom-predicate PLAY amendment       MERGED
PLAY-0                                           CURRENT PR
PLAY-1                                           BLOCKED — activate after PLAY-0 merge, sync, and re-anchor
PLAY-2                                           BLOCKED ON PLAY-1
PLAY-3                                           BLOCKED ON PLAY-2
production cutover                               SEPARATELY GOVERNED
V2-3                                             NOT AUTHORIZED
```

Canonical PLAY-1 handoff (write lease begins only after activation):

`Docs/Plans/HANDOFF-CON-READY-PLAY-worldkeeper-consumer-proof-v1.md`
