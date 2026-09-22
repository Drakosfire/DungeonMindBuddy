# Design — Source-to-World authoring interaction contract

**Status:** PROPOSED DESIGN RE-ANCHOR — DungeonBuddy implementation paused for World Keeper boundary extraction  
**Date:** 2026-09-22  
**Workstream:** `CON-READY / DOGFOOD-CONTINUITY`  
**Authority base:** `main@c6730c94cbdce97ce1b6bd7999fc4685d61f9c69` (PR #742 merged)  
**Current design PR:** #745  
**Side-quest handoff:** `Docs/Plans/HANDOFF-CON-READY-worldkeeper-sidequest-v1.md`  
**Evidence:** the 2026-09-22 C1/S1 governed-authoring dogfood report, the 2026-09-22 Graph Authoring audit, and PR #745 review `5279631534`.

## Decision

Graph authoring is a continuous interaction between a source occurrence and the
governed World. It is not an Author Node wizard whose tab sequence is the
product state machine.

```text
read source
→ inspect durable World truth
→ choose an explicit authoring operation
→ stage one local transaction
→ preview its working interpretation
→ review one exact governed change
→ explicitly publish
→ inspect the exact published result
→ continue from source or World
```

The existing Author Node controls, proposal store, working projection, and
prepare/confirm machinery remain useful implementation evidence. Their current
linear rail does not define the user model.

## Ownership re-anchor — World Keeper

PR #745 began as a DungeonBuddy interaction re-anchor. Review exposed a deeper
ownership boundary.

DungeonBuddy should own the interaction and application intent. It should not
permanently own the semantic compiler that turns those intentions into
DungeonMind contribution/evidence/publication machinery.

The emerging target is:

```text
DungeonBuddy
  source selection + product interaction + application intent
        ↓
World Keeper
  semantic interpretation + governed transaction lifecycle
        ↓
DungeonMind
  durable governed World knowledge + revisions + provenance + persistence
```

Therefore:

- this document remains DungeonBuddy product interaction authority;
- current Buddy-side semantic translation is migration evidence, not permanent
  product ownership;
- the next Buddy authoring implementation is paused while World Keeper defines
  the application/service boundary;
- no parked handoff activates automatically after this design lands.

See `HANDOFF-CON-READY-worldkeeper-sidequest-v1.md`.

## Terms and invariants

### Durable reference versus source occurrence

A durable object reference identifies one object at one World revision. A
source occurrence identifies words in a source artifact. They are related only
by an explicit mention/link assertion or by a truthful projection rule; neither
silently substitutes for the other.

Consequences:

- Clicking an unambiguous durable recap pill opens the exact object inspection
  view at the active revision. It does not re-enter duplicate resolution.
- Inspection exposes object prose, evidence, relationships, and explicit
  actions such as **Edit**, **Add relationship**, **Add alias/link mention**,
  and **Correct identity**.
- Creating an object does not itself promise a new recap pill. A pill appears
  only when committed World state truthfully links the relevant occurrence.

### Explicit operations, not a selected-node wizard

Object authoring, source-occurrence linking, and relationship authoring are
distinct operations.

Opening relationship authoring must start with independently owned
source/predicate/target state. It may intentionally seed one endpoint from an
inspected object or highlighted phrase, but that seed must be visible and must
never be inherited accidentally from a previous authoring operation.

### Transaction-local references

A staged transaction may refer to objects created by that same transaction:

```text
local:brewery = Create "The Wizard's Tower Brewing Co"
existing Pippa → works_at → local:brewery
```

A transaction-local reference is real transaction identity, not a missing
durable ID.

Within one proposed transaction:

```text
every local operation/reference ID is non-empty and unique

a local object reference resolves to exactly one object operation
in that same transaction
```

Missing, duplicate, wrong-kind, or out-of-transaction local references fail
closed before a prepared change is confirmable.

The accepted current Buddy implementation demonstrates the stronger safety
shape:

```text
transaction-local object
→ deterministic prospective durable identity during prepare translation
→ dependent relationship resolves to that prospective identity
→ exact object + relationship contribution is sealed
→ confirm reconstructs/proves the same contribution
→ DungeonMind atomically publishes it
```

Do **not** reinterpret the contract as:

```text
publish object
→ receive ID
→ rewrite/publish relationship
```

World Keeper's eventual public contract should preserve the safety guarantee
without exposing Buddy's current ID algorithm or DungeonMind's contribution
schema.

No partial publish, placeholder edge, follow-up repair, or fabricated durable
endpoint is acceptable.

### Identity advice is not identity authority

Duplicate matching is advisory. The operator has three conceptually separate
choices:

- use an existing governed durable object;
- create a distinct object despite a similar label; or
- enter an explicit identity-reconciliation operation.

Only the third changes canonical identity.

An extracted or fuzzy candidate may inform the decision. It does not establish
durable identity authority.

### Publication is a transition, not a terminal receipt

After successful or idempotently recovered publication, the product must retain
the parent/child revision and enough durable result identity to continue from
the changed World.

Required now:

- exact created durable objects can be opened/read back;
- exact committed relationships can be proven in the published child;
- the child revision can be inspected;
- publication success remains success if a later refresh fails.

**Not yet contracted:** how a client receives the exact durable relationship
handle for direct "Open relationship" navigation. That may become an additive
committed-change receipt mapping or be resolved from exact child read-back.
World Keeper design should decide this rather than freezing a Buddy-specific
answer here.

## Interaction contract

1. **Read.** Source remains primary. Campaign/session source context and the
   governed World lens stay independently explicit.
2. **Inspect.** A durable reference opens the exact World object. A plain text
   selection opens source context and an operation chooser.
3. **Author.** The operator selects an explicit operation; controls collect only
   that operation's inputs.
4. **Stage.** The local transaction may contain durable and transaction-local
   references. Working state is visibly uncommitted.
5. **Preview working interpretation.** The product shows how the staged intent
   changes the working view without claiming publication.
6. **Prepare/review.** The semantic transaction owner interprets the complete
   intent against exact World/source authority and returns one exact reviewable
   prepared change.
7. **Publish.** Explicit confirmation is bound to that exact prepared
   interpretation. Stale authority fails closed; retry/recovery is idempotent.
8. **Reconcile.** Durable result identity replaces committed local identity only
   after successful publication.
9. **Inspect result.** The exact child is readable, then the active governed
   projection may refresh independently. Mention navigation remains a
   separately truthful projection outcome.

## Boundary between product flow and semantic write machinery

The interaction contract intentionally does not require DungeonBuddy to own
the implementation behind steps 6–8.

Long term, DungeonBuddy should be able to express application intent roughly as:

```text
source context
+ Create object
+ Link occurrence
+ Create relationship
```

and receive:

```text
Prepared World change
→ explicit confirmation
→ Committed World result
```

World Keeper is being created to own that semantic transaction boundary.

DungeonMind remains the durable governed knowledge authority underneath it.

## Boundaries and sequencing

This re-anchor does not authorize:

- V2-3 derived gold;
- extraction/model ablation;
- Agent-assisted authoring;
- automatic dedupe;
- identity reconciliation implementation;
- resolver exceptions;
- raw graph edits;
- source-markdown mutation;
- a generic graph editor.

The previously proposed immediate Buddy transaction-semantics implementation is
now **PARKED** while World Keeper establishes the ownership boundary.

`Docs/Plans/HANDOFF-CON-READY-source-to-world-transaction-semantics-v1.md`
remains useful implementation/migration evidence, including its same-batch
object+relationship case. It is not an active write lease.

Resume sequencing only after the World Keeper bootstrap/design is accepted and
a fresh DungeonBuddy re-anchor explicitly decides the next migration step.

## Reconciliation with prior authorities

- `DESIGN-graph-object-authoring-surface.md` remains useful historical product
  intent: source-first authoring, staged human intent, and explicit
  review/confirm survive. Its wizard/overlay-era sequencing is not current
  interaction authority.
- `ARCHITECTURE-campaign-supergraph.md` remains the canonical durable World
  ownership model: one World graph, campaign-scoped assertions,
  revision-pinned projections, and separate read/write systems.
- DungeonMind remains the durable knowledge/kernel authority. World Keeper must
  not recreate graph storage, revision authority, provenance persistence, or
  identity ledger ownership.
- The Authoring v2 plan records V2-2 as merged and V2-3 as unauthorized.
- `HANDOFF-CON-READY-worldkeeper-sidequest-v1.md` owns the current pause and
  return gate.
