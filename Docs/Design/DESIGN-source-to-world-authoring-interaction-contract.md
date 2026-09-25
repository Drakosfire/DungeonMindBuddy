# Design — Source-to-World authoring interaction contract

**Status:** ACCEPTED BUDDY INTERACTION AUTHORITY — consumer migration not yet implemented
**Date:** 2026-09-25
**Workstream:** `CON-READY / DOGFOOD-CONTINUITY`
**Authority re-anchor:** `main@08e4c39967e63bc3b60791748129ca3eaa42f161`
**Authority reconciliation PR:** #745
**Completed side quest:** `Docs/Plans/HANDOFF-CON-READY-worldkeeper-sidequest-v1.md`

## Decision

Graph authoring is a continuous interaction between a source occurrence and the
governed World. It is not an Author Node wizard whose tab sequence is the
product state machine.

```text
read source
→ inspect durable World truth
→ choose an explicit authoring operation
→ stage reversible intent
→ preview its working interpretation
→ review one exact prepared World change
→ explicitly confirm
→ inspect the verified durable result
→ continue from source or World
```

The existing Buddy controls and governed-write path remain historical
implementation evidence. The accepted destination is the WorldKeeper consumer
boundary described here.

## Accepted ownership boundary

```text
DungeonBuddy
  interaction
  reversible drafts
  source selection and presentation
  explicit create-new versus use-existing choice
  similarity presentation
  review and result UX

WorldKeeper
  WorldChangeIntent
  semantic interpretation
  same-transaction dependency resolution
  PreparedWorldChange
  confirmation coordination
  verified-result reshaping

DungeonMind
  durable object and relationship IDs
  source and provenance authority
  profile, scope, and admission policy
  immutable revisions
  atomic publication
  durable publication outcome and recovery
  general World reads
```

WorldKeeper is deliberately a thin coordinator. It does not own source
admission, durable-ID allocation or prediction, a general application read
layer, or durable publication recovery. It coordinates the semantic change
lifecycle through DungeonMind's authority.

Current Buddy-side semantic translation is migration evidence, not permanent
product ownership. PR #745 establishes authority only; it does not perform the
consumer migration.

## Durable reference versus source occurrence

A durable object reference identifies one object at one World revision. A
source occurrence identifies words in a source artifact. They are related only
by an explicit mention/link assertion or a truthful projection rule.

- Clicking an unambiguous durable recap pill opens exact object inspection.
- Creating an object does not itself promise a new recap pill.
- Source selection remains explicit input to authoring, not durable identity.
- DungeonMind remains the authority for source identity and provenance.

## Explicit operations and identity choice

Object creation, source-occurrence linking, and relationship creation are
distinct operations. Relationship authoring may visibly seed an endpoint from
the current source/object context, but must not inherit hidden state.

Similarity is advice, not identity authority. Buddy must present an explicit
choice between using an existing governed object, creating a distinct object,
or later entering an explicit identity-reconciliation operation. Only the last
operation changes canonical identity.

## Same-transaction references

Buddy assigns every staged operation a non-empty, transaction-unique
`client_op_id`. A dependent operation refers to an earlier result as
`result_of(client_op_id)`.

```text
Buddy WorldChangeIntent
  create(client_op_id="brewery")
  relate(existing Pippa, works_at, result_of("brewery"))
        ↓
WorldKeeper
  validates and resolves the semantic dependency
  prepares one coherent change
  does not predict a durable ID
        ↓
DungeonMind V5.4
  atomically allocates durable IDs
  substitutes those IDs through dependent operations
  publishes one immutable child or none
  returns client-operation → durable-result mappings
        ↓
WorldKeeper
  verifies and reshapes the result for Buddy
```

Missing, duplicate, wrong-kind, forward/out-of-transaction, or otherwise
unresolvable operation references fail closed before confirmation. There is no
object-first publication, placeholder relationship, second repair publication,
or prospective durable-ID algorithm in Buddy or WorldKeeper.

## Prepare, confirm, and result

1. Buddy submits exact source context, exact World context, and one complete
   `WorldChangeIntent`.
2. WorldKeeper interprets semantic dependencies and returns a
   `PreparedWorldChange` without durable mutation.
3. Buddy presents that exact prepared change and collects explicit confirmation.
4. WorldKeeper coordinates confirmation of that exact preparation.
5. DungeonMind performs authority checks, durable-ID allocation, substitution,
   and atomic publication.
6. DungeonMind owns durable outcome/recovery and returns operation-result
   mappings.
7. WorldKeeper verifies/reshapes the result; Buddy presents it and may use
   ordinary DungeonMind-backed World reads to inspect the child.

Stale authority fails closed. A successful durable publication remains success
even if a later UI refresh fails.

## Sequencing boundary

Completed prerequisites:

- V2-2 governed write path (historical Buddy path);
- WorldKeeper WK-1 through WK-5 and PR #7;
- DungeonMind V5.4 atomic operation-result semantics;
- WorldKeeper WK-5 consumer seam.

Next, but **not authorized by this document**:

> one bounded DungeonBuddy consumer-migration handoff using the accepted
> WorldKeeper seam.

Still not authorized: V2-3 derived gold, extraction/model ablation,
Agent-assisted authoring, identity reconciliation, generic graph-editor work,
or production write switching/runtime/bridge-genesis migration hidden inside
#745. The latter work remains in later vNext/cutover slices, consistent with
the V6.1 foundation boundary.

## Reconciliation with prior authorities

- `DESIGN-graph-object-authoring-surface.md` is historical product evidence.
- `HANDOFF-CON-READY-source-to-world-transaction-semantics-v1.md` is historical
  migration evidence; its prospective-ID mechanism is not the destination.
- `HANDOFF-CON-READY-worldkeeper-sidequest-v1.md` is complete/historical.
- `ARCHITECTURE-campaign-supergraph.md` continues to own durable World
  architecture.
- `PLAN-CON-READY-authoring-v2-derived-gold-ablation-loop-v1.md` owns current
  sequencing and keeps V2-3 unauthorized.
