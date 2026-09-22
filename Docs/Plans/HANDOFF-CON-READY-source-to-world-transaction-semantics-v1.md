# HANDOFF — CON-READY: source-to-World transaction semantics

**Created:** 2026-09-22  
**Status:** PARKED MIGRATION EVIDENCE — DO NOT DISPATCH IN DUNGEONBUDDY  
**Canonical handoff path:** `Docs/Plans/HANDOFF-CON-READY-source-to-world-transaction-semantics-v1.md`  
**Flow / owner:** `CON-READY`  
**Design authority:** `Docs/Design/DESIGN-source-to-world-authoring-interaction-contract.md`  
**Pause authority:** `Docs/Plans/HANDOFF-CON-READY-worldkeeper-sidequest-v1.md`  
**Original design base:** `main@c6730c94cbdce97ce1b6bd7999fc4685d61f9c69`

## §1 Why this handoff is parked

This handoff identifies a real defect in the current DungeonBuddy authoring
implementation:

`classify_graph_review_expressibility()` rejects a same-batch relationship
endpoint unless it already has a durable `nodeId`, while the existing
contribution translator already knows how to resolve a transaction-local object
proposal to its deterministic prospective authored object identity.

Originally this was going to be the next bounded Buddy implementation.

That dispatch is now paused.

The World Keeper side quest is establishing a cleaner ownership boundary in
which semantic transaction interpretation—including expressibility and
transaction-local reference resolution—should not remain a growing
DungeonBuddy responsibility.

Keep this document as exact current-implementation evidence and as a candidate
migration acceptance test. Do not reserve the old write lease or open an
implementation PR from it.

## §2 Preserved capability requirement

The product requirement remains:

> One proposed transaction may create an object and create a relationship whose
> endpoint is that same transaction-local object. One explicit confirmation
> must produce either one coherent immutable child with durable endpoints or no
> publication.

Example:

```text
Create local:brewery
existing Pippa → works_at → local:brewery

→ prepare exact interpretation without World mutation
→ explicit confirm
→ exactly one child revision
→ created object has one durable identity
→ relationship endpoint is that same durable identity
→ exact child read-back proves both
```

This requirement belongs in the future World Keeper transaction contract even
if a temporary Buddy bridge is later required.

## §3 Transaction-local integrity invariants

Within one prepared proposal/intent set:

- every local proposal/reference ID is non-empty;
- every local proposal/reference ID is unique;
- a `local_proposal` object endpoint resolves to exactly one object proposal
  in that same set;
- missing references fail closed;
- references to a non-object proposal fail closed;
- references outside the prepared set fail closed;
- invalid durable endpoints fail closed;
- a changed proposal set cannot reuse a prior confirmation binding;
- stale World parent fails closed.

The duplicate-local-ID case is required negative coverage. Current dictionary
construction can otherwise collapse duplicate keys and silently choose one
prospective object identity.

## §4 Accepted current implementation evidence

Current Buddy translation already does the important semantic work
conceptually:

```text
all object assertions
→ deterministically compute prospective authored object identity
→ build local proposal ID → prospective durable object ID map
→ resolve relationship local endpoints through that map
→ build one exact contribution containing object + edge
→ seal contribution digest during prepare
→ confirm reconstructs/proves the same contribution
→ DungeonMind atomically validates/publishes that contribution
```

The present mismatch is earlier classification, not missing object/edge
materialization machinery.

A future implementation must not invent a two-publication object-then-edge
workflow.

## §5 Historical candidate Buddy write lease — NOT ACTIVE

The original candidate lease was:

- `apps/live_control_server/services/graph_object_authoring_prepare.py`
- `tests/test_graph_object_authoring_prepare.py`
- `tests/test_graph_object_authoring_published_recap_write.py`
- this handoff;
- a focused report.

That list is retained only to make the old bounded repair reconstructable.

**It is not an active write lease.**

Any Buddy implementation now requires a fresh post-World-Keeper handoff.

## §6 Migration decision required before implementation

After World Keeper design is accepted, re-read current Buddy `main` and
choose explicitly among:

### A. Minimal temporary Buddy bridge

Repair only the classifier/referential validator so dogfood can continue while
the World Keeper client migration is prepared.

Use this only if product continuity requires it.

### B. Direct World Keeper implementation

Implement the transaction semantics in World Keeper and migrate Buddy's
authoring call boundary without adding more semantic compiler ownership to
Buddy.

This is preferred if the service boundary is ready.

### C. Re-design

If the accepted World Keeper contract changes the meaning of prepare,
prospective durable identity, or source binding, stop and write a new bounded
design. Do not force this historical handoff onto the new architecture.

## §7 Evidence that must eventually survive

Wherever the capability lands, require:

- valid durable → local object relationship passes semantic preparation;
- valid local object → durable relationship if supported passes likewise;
- duplicate local reference IDs fail closed;
- missing local reference fails closed;
- non-object local reference fails closed;
- out-of-transaction local reference fails closed;
- invalid durable endpoint fails closed;
- prepare performs no durable World mutation;
- one confirm produces one immutable child;
- exact child contains the created object and durable edge;
- retry/recovery produces no second child;
- changed/stale prepared intent fails closed;
- existing durable-to-durable relationship behavior remains green.

## §8 Relationship result identity remains open

Do not require a Buddy-specific `created_relationship_ids` response merely to
close this handoff.

The future World Keeper committed-change contract must decide whether:

```text
local relationship operation ID → durable relationship ID
```

is returned explicitly, or whether exact relationship navigation is resolved
from exact child read-back.

The correctness witness only requires proof of the exact durable edge in the
published child.

## §9 Explicit holds

This parked handoff does not authorize:

- Author Node redesign;
- inspection routing;
- mention/pill projection policy;
- identity merge/reconciliation;
- automatic dedupe;
- extraction/model changes;
- V2-3;
- DungeonMind schema changes;
- live World mutation.

## §10 Resume gate

Do not reactivate this handoff.

After World Keeper design/bootstrap is accepted, create a **new** fresh-main
DungeonBuddy handoff that cites this document as evidence and states which
repository owns the implementation.

Until then:

```text
STATUS = PARKED
BUDDY IMPLEMENTATION = NONE
V2-3 = NOT AUTHORIZED
```
