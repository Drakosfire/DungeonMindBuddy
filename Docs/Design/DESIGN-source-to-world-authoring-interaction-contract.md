# Design — Source-to-World authoring interaction contract

**Status:** PROPOSED DESIGN RE-ANCHOR — implementation remains blocked pending review/activation
**Date:** 2026-09-22
**Workstream:** `CON-READY / DOGFOOD-CONTINUITY`
**Authority base:** `main@c6730c94cbdce97ce1b6bd7999fc4685d61f9c69` (PR #742 merged)
**Evidence:** the 2026-09-22 C1/S1 governed-authoring dogfood report in the dogfood lane; the 2026-09-22 Graph Authoring audit.

## Decision

Graph authoring is a continuous interaction between a recap occurrence and the
governed World. It is not an Author Node wizard whose tab sequence is the
product state machine.

```text
read source
→ inspect durable World truth
→ choose an explicit authoring operation
→ stage one local transaction
→ preview its overlay
→ prepare and explicitly publish
→ reconcile local references to durable IDs
→ inspect the exact published result
→ continue from source or World
```

The existing Author Node controls, proposal store, working projection, and
prepare/confirm authority remain useful implementation pieces. Their current
linear rail does not define the user model.

## Terms and invariants

### Durable reference versus recap occurrence

A durable object reference identifies one object at one World revision. A recap
occurrence identifies words in a source artifact. They are related only by an
explicit mention/link assertion or by a truthful projection rule; neither one
silently substitutes for the other.

Consequences:

- Clicking an unambiguous durable recap pill opens the exact object inspection
  view at the active revision. It does not re-enter duplicate resolution.
- Inspection exposes object prose, evidence, relationships, and explicit
  actions such as **Edit**, **Add relationship**, **Add alias/link mention**,
  and **Correct identity**.
- Creating an object does not promise a new recap pill. A pill appears only
  when the committed World state truthfully links the relevant occurrence.

### Explicit operations, not a selected-node wizard

Object authoring, link/alias authoring, and relationship authoring are distinct
operations. Opening relationship authoring must start with independently
selected source, predicate, and target. It may intentionally seed one endpoint
from an inspected object or highlighted phrase, but it must show that seed and
must never inherit a stale node from a previous authoring session.

### Transaction-local references

A staged transaction may refer to objects that will be created by that same
transaction:

```text
local:brewery = Create “The Wizard's Tower Brewing Co”
node:pippa → works_at → local:brewery
```

`local:*` is an explicit transaction-local identity, not a missing durable ID.
At publish the authority materializes all new nodes, rewrites every dependent
assertion to the emitted durable IDs, validates the full contribution, and
advances one immutable child revision atomically. The receipt returns the
`local:* → node:*` mapping and the client replaces committed local references.

No partial publish, placeholder edge, follow-up repair, or fabricated durable
endpoint is acceptable.

### Identity advice is not identity authority

Duplicate matching is advisory. The operator has three separate choices:

- use an existing governed durable object;
- create a distinct object despite a similar label; or
- enter an explicit identity-reconciliation operation.

Only the third changes canonical identity. A candidate from extracted recap
memory remains useful context but is not a governed existing target until its
canonical ID is admitted in the exact World projection.

### Publication is a transition, not a terminal receipt

After a successful or idempotently recovered commit, the surface must expose
the parent and child revision, durable IDs, and exact result actions: open each
created object, open each published relationship, inspect the child revision,
or continue authoring. A refresh failure may not turn a successful write into a
failed write. Refresh is read-only and must report its own outcome.

## Interaction contract

1. **Read.** The recap remains primary. Its selected campaign/session and the
   governed World lens stay independently explicit.
2. **Inspect.** A durable reference opens the exact World object. A plain text
   selection opens source context and an operation chooser.
3. **Author.** The operator selects an operation; controls collect only that
   operation's inputs.
4. **Stage.** The local transaction can contain durable and transaction-local
   endpoints. The working projection labels local state as uncommitted.
5. **Preview.** The preview describes the proposed World contribution and its
   local-to-durable dependencies without claiming that it is published.
6. **Publish.** Existing server-resolved recap source authority, signed prepare,
   explicit confirm, stale-parent protection, and idempotent recovery remain
   the only durable write protocol.
7. **Reconcile.** The commit receipt binds local proposal IDs and local object
   references to immutable child-revision IDs; only committed drafts clear.
8. **Inspect result.** The result is readable at the exact child revision and
   then through the active governed projection. Mention navigation is a
   separately truthful projection outcome.

## Boundaries and sequencing

This re-anchor does not authorize V2-3 derived gold, extraction ablation,
automatic dedupe, resolver exceptions, raw graph edits, source-markdown
mutation, or a generic graph editor.

The next implementation capability is transaction semantics: accept valid
same-batch local-reference dependencies at the prepare boundary and prove their
atomic materialization. It is specified by the blocked successor handoff
`Docs/Plans/HANDOFF-CON-READY-source-to-world-transaction-semantics-v1.md`.

Only after that capability is accepted should successor work address
inspection/publish continuity, then the broader Authoring composition and
surface-navigation observations. This preserves the audit's order:

```text
transaction semantics
→ inspect/publish continuity
→ authoring composition
```

## Reconciliation with prior authorities

- `DESIGN-graph-object-authoring-surface.md` remains valuable historical
  product intent: source-first authoring, staged human intent, and explicit
  review/confirm survive. Its wizard/overlay-era sequencing is not current
  interaction authority.
- `ARCHITECTURE-campaign-supergraph.md` remains the canonical ownership model:
  one World graph, campaign-scoped assertions, revision-pinned projections, and
  separate read/write systems. This contract specifies the user interaction at
  that boundary.
- The Authoring v2 plan records V2-2 as merged but leaves V2-3 unauthorized.
  This contract pauses successor dispatch until the transaction-semantics
  handoff is activated from a fresh `main` re-anchor.
