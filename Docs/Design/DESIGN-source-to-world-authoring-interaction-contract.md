# Design — Source-to-World authoring interaction contract

**Status:** ACCEPTED BUDDY INTERACTION AUTHORITY — implementation is partial and path-specific
**Date:** 2026-09-25
**Workstream:** `CON-READY / DOGFOOD-CONTINUITY`
**Authority re-anchor:** `main@08e4c39967e63bc3b60791748129ca3eaa42f161`
**Authority reconciliation PR:** #745
**Completed side quest:** `Docs/Plans/HANDOFF-CON-READY-worldkeeper-sidequest-v1.md`
**Custom-predicate amendment:** PR #752, rebased on Buddy `main@7addcd05b20c894eb4d50b9d63e5ebdee4bc2cc7`

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

The WorldKeeper consumer boundary below remains the accepted ownership model.
Implementation has progressed since this decision: the accepted
[PLAY-1 consumer proof](../Reports/REPORT-CON-READY-PLAY-worldkeeper-consumer-proof-v1.md)
covered a bounded proposal-to-prepare/commit seam, without changing production
routes or proving all operations in this design. The current
[native Graph service](../../apps/live_control_server/services/native_graph_explorer.py)
also uses WorldKeeper to prepare and commit supported create/connect intents;
its [request models](../../apps/live_control_server/models/native_graph_explorer.py)
and [owning tests](../../tests/test_native_graph_explorer.py) show the bounded
operations and review/confirmation behavior. This is evidence of specific
implemented paths, not blanket completion of this design or proof of hosted
deployment or availability. Check the current routes and release evidence for
the environment in question.

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

Buddy-side semantic translation remains a consumer responsibility, not ownership
of WorldKeeper semantics. PR #745 established this authority; the later PLAY-1
proof and native Graph path provide bounded implementation evidence. Neither
establishes that every operation or surface described here has migrated.

## Durable reference versus source occurrence

A durable object reference identifies one object at one World revision. A
source occurrence identifies words in a source artifact. They are related only
by an explicit mention/link assertion or a truthful projection rule.

- Clicking an unambiguous durable recap pill opens exact object inspection.
- Creating an object does not itself promise a new recap pill.
- Source selection remains explicit input to authoring, not durable identity.
- DungeonMind remains the authority for source identity and provenance.
- Evidence grounding does not imply occurrence or mention binding. That
  binding awaits a distinct DungeonMind write contract.

## Explicit operations and identity choice

Object creation and relationship creation are distinct current operations.
Source-occurrence linking is a distinct future semantic operation; the WK-5 v0
consumer seam supports `create_object`, `use_existing`, and
`create_relationship`. Relationship authoring may visibly seed an endpoint
from the current source/object context, but must not inherit hidden state.

Similarity is advice, not identity authority. Buddy must present an explicit
choice between using an existing governed object, creating a distinct object,
or later entering an explicit identity-reconciliation operation. Only the last
operation changes canonical identity.

## Human-authored relationship predicates

A GM may craft a relationship predicate instead of choosing a preset. This is
an accepted product capability, not an optional vocabulary-polish feature.
Buddy preserves the operator's chosen meaning and maps a valid custom local
term, such as `works_at`, to `dungeonbuddy.custom:works_at`. It must not
substitute `located_in`, `allied_with`, or another approximate predicate.

The selected World semantic profile must explicitly admit that custom
namespace for `entity_ref` assertions at both publication and read time.
Buddy owns the lexical product mapping and review UX; DungeonMind owns
qualified-term and value-kind admission. WorldKeeper carries and binds the
exact predicate without adding a vocabulary of its own. A custom relationship
does not imply identity equivalence, aliasing, merging, or a source-occurrence
link.

If a World is pinned to a profile without this capability, Buddy must report
that the predicate is not publishable under the current authority. It may not
silently change the profile, publish under a different term, or claim that a
staged-only custom relationship became durable. Profile transition for an
existing World is a separate authority decision.

The opt-in V3-backed Buddy profile revision 2 is merged in PR #754, following
DungeonMind #77/#78 and WorldKeeper #8. That satisfies the custom-predicate
capability prerequisite for a World explicitly pinned to that profile; it does
not transition a V2-pinned World. PR #752's companion plan file is a PLAY-1
design amendment, not an independent adapter implementation handoff.

## Same-transaction references

Buddy assigns each result-producing semantic item (`CreateObject`, `CreateFact`,
and `CreateRelationship`) a non-empty, transaction-unique `client_op_id`.
`UseExisting` instead names an exact `durable_object_id`. A dependent
relationship endpoint refers to a `CreateObject` result in the same intent as
`result_of(client_op_id)`, regardless of operation order.

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

Missing, duplicate, wrong-kind, out-of-transaction, or otherwise
unresolvable operation references fail closed before confirmation. There is no
object-first publication, placeholder relationship, second repair publication,
or prospective durable-ID algorithm in Buddy or WorldKeeper.

## Prepare, confirm, and result

1. Buddy selects product source context and constructs one complete
   `WorldChangeIntent`, using already admitted evidence references in operation
   metadata. The WK-5 service receives `prepare_change(intent)`; it does not
   accept a separate raw source-context argument or admit a source.
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

The original next step, the PLAY-1 consumer proof, is complete; its
[accepted historical report](../Reports/REPORT-CON-READY-PLAY-worldkeeper-consumer-proof-v1.md)
records its exact scope and limits. The proof used an injected service and an
in-memory repository; it did not itself switch production routes.

This document describes interaction authority, not a current implementation
lease. Re-anchor on the current repository policy and an explicitly authorized
handoff before undertaking further work. The historical V2-3 derived-gold
ablation remains separately parked in the transferred plan.

## Reconciliation with prior authorities

- `DESIGN-graph-object-authoring-surface.md` is historical product evidence.
- `HANDOFF-CON-READY-source-to-world-transaction-semantics-v1.md` is historical
  migration evidence; its prospective-ID mechanism is not the destination.
- `HANDOFF-CON-READY-worldkeeper-sidequest-v1.md` is complete/historical.
- `ARCHITECTURE-campaign-supergraph.md` continues to own durable World
  architecture.
- [`PLAN-CON-READY-authoring-v2-derived-gold-ablation-loop-v1.md`](../Plans/PLAN-CON-READY-authoring-v2-derived-gold-ablation-loop-v1.md)
  is historical execution authority; V2-3 remains separately parked.
