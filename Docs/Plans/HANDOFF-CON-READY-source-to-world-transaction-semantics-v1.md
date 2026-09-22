# HANDOFF — CON-READY: source-to-World transaction semantics

**Created:** 2026-09-22
**Status:** BLOCKED — design re-anchor must be accepted and re-anchored before dispatch
**Canonical handoff path:** `Docs/Plans/HANDOFF-CON-READY-source-to-world-transaction-semantics-v1.md`
**Flow / owner:** `CON-READY`
**PR topology:** `serial`
**Design authority:** `Docs/Design/DESIGN-source-to-world-authoring-interaction-contract.md`
**Design base:** `main@c6730c94cbdce97ce1b6bd7999fc4685d61f9c69`

## §1 Mission and merge-ready invariant

Make a staged create-object plus relationship transaction publishable when a
relationship endpoint is a valid `local_proposal` reference to an object created
in that same transaction.

> A prepared contribution may contain durable and transaction-local endpoints.
> On one explicit confirm it either publishes one child World revision whose
> relationships resolve to the emitted durable IDs, or publishes nothing. The
> receipt maps each committed local object proposal to its durable node ID.

This is transaction semantics only. It does not redesign the Author Node,
change durable-reference click behavior, add automatic duplicate resolution, or
claim recap mention linkage.

## §2 Activation gate

Do not dispatch or reserve §4 paths until all are true:

1. the source-to-World interaction contract is accepted and landed on `main`;
2. a fresh re-anchor records the then-current `main`, open CON-READY PRs, and
   actual implementation base;
3. no active serial CON-READY implementation PR owns these paths; and
4. the steward confirms that the current authority still has the
   `local_proposal → authored object node ID` translation seam and that the
   failure remains at prepare classification rather than an authority change.

Activation may fill in the authorized branch/PR title and backward-looking
state-authority sync. It must not enlarge this mission without a new design
review.

## §3 Required behavior

```text
Create local:brewery
existing node:pippa → works_at → local:brewery
→ prepare succeeds without a World mutation
→ explicit confirm
→ exactly one child revision
→ relationship target is the durable ID emitted for local:brewery
→ receipt exposes local:brewery → node:* mapping
```

The following remain fail-closed: a missing local proposal, a local reference
to a non-object proposal, a reference outside the prepared proposal set, an
invalid durable endpoint, a stale parent, or a changed prepared proposal.

## §4 Files in scope — write lease after activation

- `apps/live_control_server/services/graph_object_authoring_prepare.py`
- `tests/test_graph_object_authoring_prepare.py`
- `tests/test_graph_object_authoring_published_recap_write.py`
- `Docs/Plans/HANDOFF-CON-READY-source-to-world-transaction-semantics-v1.md`
- `Docs/Reports/REPORT-CON-READY-source-to-world-transaction-semantics-v1.md`

One additional focused test path may be added only if the existing published
recap integration fixture cannot own the real prepare/confirm/read-back proof.
Any production path outside this list is a STOP and re-brief.

## §5 Out of scope

- UI composition, tabs, resize behavior, hover/click interaction, and load UX;
- durable-reference inspection routing;
- relationship-form redesign beyond correcting a proven transaction payload;
- recap occurrence/pill creation or mention-link policy;
- identity reconciliation, merge, automatic dedupe, or extraction candidates;
- DungeonMind schema/dependency changes, raw SQL, and live World mutation;
- V2-3 derived gold and all later work.

## §6 Implementation contract

The prepare classifier must recognize the same canonical endpoint rule used by
contribution translation:

```text
existing_graph_node → exact governed durable node ID
local_proposal(object in this prepared set) → deterministic authored node ID
```

It must not reject a valid local endpoint merely because it has no already
published `nodeId`. Translation must continue to materialize the object and
rewrite dependent edges in the single contribution; confirm/idempotency behavior
must remain unchanged.

Operator-facing inexpressible errors must name the invalid endpoint class rather
than report the unrelated identity-merge limitation.

## §7 Evidence required to merge

- focused unit coverage proves valid object-local endpoints pass classification;
- negative coverage proves each invalid local-reference class fails closed;
- an owning real-authority integration test proves before-confirm head stability;
- the same test proves one confirmed child, emitted object ID, exact durable
  edge endpoint, and receipt mapping after fresh read-back;
- retry proves no second child revision;
- existing durable-to-durable relationship coverage stays green;
- `git diff --check`, focused backend tests, and applicable type/build checks
  pass at the reviewed head.

No live mutation is required for this implementation slice. Live dogfood occurs
only after review acceptance and an explicit operator action under the existing
governed publication protocol.

## §8 Required review handback

Record exact base/head, changed paths versus §4, classification/translation
contract, integration authority used, parent/child/receipt evidence, retry
result, baseline failures, and confirmation that V2-3 remains unauthorized.

## §9 Acceptance rubric

- [ ] Same-batch local object + relationship is expressible.
- [ ] Invalid local references fail closed with truthful diagnostics.
- [ ] One confirm produces one immutable child with fully durable endpoints.
- [ ] Receipt and read-back expose local-to-durable identity mapping.
- [ ] No unrelated Authoring UX, identity, mention-linking, or World-authority
  capability was added.
