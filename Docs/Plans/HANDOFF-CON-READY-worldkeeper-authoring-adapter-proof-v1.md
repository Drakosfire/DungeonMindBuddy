# AMENDMENT — CON-READY custom predicates for PLAY-1

**Status:** DESIGN AMENDMENT / PREREQUISITE — NO INDEPENDENT IMPLEMENTATION LEASE

**Repository:** `Drakosfire/DungeonMindBuddy`

**Workstream:** `CON-READY / PLAY`

**Re-anchor:** Buddy `main@7addcd05b20c894eb4d50b9d63e5ebdee4bc2cc7` (PR #754 merge)

**Product authority:** `Docs/Design/DESIGN-source-to-world-authoring-interaction-contract.md`

**Implementation authority:** one PLAY-1 handoff, proposed in PLAY-0 PR #753; reconcile that handoff before dispatch

**V2-3 and production switching:** NOT AUTHORIZED

This document retains its historical filename so links from PR #752 remain
resolvable. It replaces the former independent, 984-line adapter implementation
handoff. **Do not dispatch an adapter implementation from this document.**
PR #752 supplies the custom-predicate product contract to PLAY-1; it is not a
second implementation lane or a stacked code PR lease.

## Accepted prerequisite record

The following are accepted prerequisites, not proposals awaiting implementation:

- DungeonMind #77: V3 open-predicate runtime, reviewed head
  `0f709d76fdc53bac9c9258d1751463ae2c76ca71`, merge
  `a9051f02dfd95e051a83c1d74b26bb04a2b3e5bf`.
- DungeonMind #78: final authority disposition
  `SEMANTIC_PROFILE_V3_OPEN_PREDICATE_NAMESPACES_ACCEPTED`, reviewed head
  `19cf798d9b8ed9c63eb41d585b5e6ad46d99f5a0`, merge
  `54a419f99057d96e0c4e7620d8bd8ccc6816fb62`.
- WorldKeeper #8: V3-compatible prepare/compile/commit, accepted head
  `49a8620f066ce7ef8972a699020c012f50af9158`, merge
  `a0a70db275cf6c5f3876fe7b4d2a557de12388f5`.
- Buddy #754: opt-in V3-backed `dungeonbuddy.dnd5e` profile revision 2,
  accepted head `acf2e5cb286cf7c5040e9c6a51f4ba2978ec0731`, merge/current
  re-anchor `7addcd05b20c894eb4d50b9d63e5ebdee4bc2cc7`.

WorldKeeper's pre-V3 WK-5 merge `8a5efb96b69dc9ca136288ecc80f67c1ed027bd1`
is historical ancestry, **not** the compatible dependency pin for authored
custom predicates. The PLAY-1 handoff must replace that pin with the accepted
#8 authority above. Buddy #754 already pins the reviewed DungeonMind #77
runtime head. These accepted facts do not authorize an implicit V2-to-V3
transition for an existing World.

## Product requirement carried into PLAY-1

A GM may author a new relationship term. Buddy must preserve the selected
meaning exactly: valid local term `works_at` maps to
`dungeonbuddy.custom:works_at`, never approximately to `located_in`,
`allied_with`, or another fixed predicate. Buddy owns lexical/product mapping
and review UX. DungeonMind's selected profile owns namespace and value-kind
admission at publication and read time; the opt-in custom namespace accepts
`entity_ref`, not arbitrary literal facts. WorldKeeper carries the exact
qualified predicate through the prepared and committed transaction without
inventing a vocabulary or durable ID.

PLAY-1 must prove the open namespace, not special-case one string:

1. Stage an object for **The Wizard's Tower Brewing Co** and a relationship
   from an exact existing durable Pippa ref via `works_at` to that object. The
   relationship target is the same-transaction `result_of` the brewery's
   `CreateObject.client_op_id`; no Buddy or Keeper code predicts its `ent:*`
   identity.
2. Stage and publish a second, previously unknown valid local predicate
   (for example `mentors`) under `dungeonbuddy.custom`, also as `entity_ref`.
   Assert exact qualified predicates and endpoints in the committed child.
3. Fail closed for an unscoped term, unsupported value kind, invalid local
   term, unresolved local object reference, stale authority, or a World still
   pinned to the V2 profile. No silent profile migration or predicate fallback.

`link_existing` remains occurrence/mention semantics, not WorldKeeper
`UseExisting`; merge/reconciliation and source-occurrence binding remain out of
scope. Evidence grounding is explicit and does not imply a mention binding.

## One consumer-proof composition

PLAY-1 owns the sole implementation and its exact path/verification lease.
The isolated proof should use this composition:

```text
Buddy staged proposals
→ Buddy-owned mapper
→ injected WorldChangeService
→ DungeonMindWorldKeeperRuntime
→ InMemoryKnowledgeRevisionRepository (test authority)
→ prepared change / explicit test confirmation / verified committed child
```

The injected service is the Buddy seam; the DungeonMind-backed runtime and
in-memory repository are the test composition. Buddy currently has **no
existing production vNext `KnowledgeRevisionRepository` factory** to reuse.
PLAY-1 must not create one, change live authoring routes, or absorb
bridge-genesis, persistence, source admission, production read/write switching,
publication, allocation, recovery, or exact-child verification logic.
Those responsibilities stay with their accepted owners or later cutover work.

## Sequencing and disposition

1. PR #754 is merged in the re-anchor above; this PR #752 is a design
   prerequisite, not an implementation dispatch.
2. Reconcile PLAY-0 / PR #753 against this amendment and current Buddy main:
   replace the pre-V3 WorldKeeper pin, include custom predicates in the bounded
   subset and canonical witness, and retain one PLAY-1 implementation handoff.
3. Dispatch PLAY-1 only after its own activation conditions are met. Review
   this amendment and PLAY-0 independently. Neither PR #752 nor this document
   merges a PR or activates production routes.

The former independent `CON-READY: prove WorldKeeper authoring adapter` PR,
its branch instructions, and its separate acceptance token are retired. The
next implementation disposition belongs to **PLAY-1**, once that single
handoff is reconciled and activated.
