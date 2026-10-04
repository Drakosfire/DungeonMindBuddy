---
title: Selected Playable-card body editing in a managed-World Plan
document_class: design
status: BLOCKED
created_at: "2026-10-04"
workstream: DEMO
design_base: "Buddy main 60e1f672441c509f45561f717611af767ece20a1"
pr_topology: serial
---

# DESIGN — Selected Playable-card body editing

> **Status: BLOCKED.** The current proposal action receipt does not identify a
> selected Playable card. Correct replay and durable history require typed target
> identity in the request, response, fingerprint and action record. SERVER and
> APP-STATE contract reviews, exact path lease and activation are outstanding.
> This document authorizes no implementation or migration.

## 1. User outcome

From the existing managed-World Plan Cards view, select one Playable card,
compose an edit for only its authored body, inspect the returned proposal,
explicitly Apply it to the mounted Plan draft, then use ordinary Save and a fresh
reopen to verify the result.

The feature targets exactly one current card body. It does not replace card
identity, heading/title, option relationships, a sibling card, the rest of the
Plan, or accepted World state. Applying changes only the mounted draft. Saving
remains a separate operator action.

Existing document-selection and heading-section Compose/Review/Apply behavior
must remain unchanged. Card targeting is a separate explicit mode; it must
never fall back to generic text selection or a heading section.

## 2. Current evidence at the pinned base

At Buddy main 60e1f672441c509f45561f717611af767ece20a1:

- PR #909 projects cards from the mounted Plan document. WorldPlanCardProjection
  retains kind and ID and shows flattened body text. It calls
  slicePlayableBodies, which returns identity and body text but no source range.
- playableStructureIndex validates versioned structure and records hierarchy
  and v2 option edges. It does not return Tiptap positions.
- WorldPlanEditBridge captures a current text selection or a generic complete
  root-heading section. Its fences cover editor, World, document, saved base,
  current draft, selection and Agent binding. It has no selected-card identity
  or body-range target.
- planSectionTarget is heading-oriented. Its ranges can include child cards or
  exclude portions of a projected card body.
- Buddy #890 proves that section replacement must fail closed when a semantic
  or Markdown round trip cannot preserve its captured structure. The Session 29
  parent Beat remains unavailable because adjacent list blocks merge on round
  trip. This design does not broaden that serializer repair.
- PR #911 added committed-card Ask. It does not add proposal targeting or Apply
  authority. Its selected-target and saved-basis rules remain specific to Ask.
- The current proposal request binds World/document/base, full submitted draft
  and digest, target kind, selected text and selected-text digest. Durable Plan
  action identity fingerprints the saved basis, draft, target kind,
  selected-text digest and instruction. Neither request nor receipt stores a
  Playable identity or marker grammar. A completed action's proposal payload is
  not replayable.

## 3. Range semantics

The UI derives target positions from the current mounted Tiptap structure. It
must not find a range by matching flattened card text, heading labels or
display titles. The card display projection remains read-only evidence, not an
edit-range authority.

A heading target is the contiguous sequence of authored root blocks after the
marked heading and before the next marked Playable heading of any kind or an
ordinary unmarked root H1/H2. The heading node, marker identity and title are
excluded. Ordinary unmarked root H3/H4 notes remain in the current projected
body. A following Playable heading is always a boundary, even when the
hierarchy makes it a child card. Apply the existing disjoint-body projection
rule to Tiptap positions rather than flattened text.

| Grammar | Card kind and authored placement | Editable body |
| --- | --- | --- |
| v1 | Scene H2 | Root blocks after the marked Scene heading to the next Playable heading or ordinary unmarked root H1/H2. |
| v1 | Beat H3 under a Scene | Root blocks after the marked Beat heading to the next Playable heading or ordinary unmarked root H1/H2. |
| v1 | Choice H3 under a Scene | Root blocks after the marked Choice heading to the next Playable heading or ordinary unmarked root H1/H2. |
| v1 | Option H4 under a Choice | Root blocks after the marked Option heading to the next Playable heading or ordinary unmarked root H1/H2. |
| v2 | Beat H2 | Only direct Beat prose after the marked Beat heading and before the first marked Scene/Choice heading or other boundary. Child cards are excluded. An empty direct body is untargetable. |
| v2 | Scene H3 under a Beat | Root blocks after the marked Scene heading to the next Playable heading or ordinary unmarked root H1/H2. |
| v2 | Choice H3 under a Beat | Root blocks after the marked Choice heading to the next Playable heading or ordinary unmarked root H1/H2, but only when the projected body maps to one contiguous structural range. |
| v2 | Option | Body content of exactly one marked top-level list item. Keep its identity marker, list wrapper, authored activation/suppression edges and all sibling items outside the replaceable body. |

A marked v2 Option is removed from its parent heading's projected body;
unmarked items in a list containing marked Options remain in that parent body.
That can make a Choice body structurally non-contiguous. The first card-edit
slice disables such a Choice target before proposal submission. It must not
delete, move, reparent or absorb any Option to manufacture a contiguous range.
Any other body that cannot be represented as one exact range is unavailable.

For every target, marker/identity attributes, heading title, option edge
attributes, links to other card identities, list wrappers, sibling list items,
frontmatter and all content outside the body are protected. A proposal that
changes this protected inventory or its order is rejected before the mounted
draft changes. Canonical serialization may normalize Markdown bytes; acceptance
compares semantic editor structure and ordinary Save/reopen rather than
claiming byte-for-byte source preservation.

## 4. Draft basis and stale-target policy

A safe current mounted draft is the proposal input, whether clean or dirty. A
draft-only card may be targeted if it is valid and unique in that exact draft.
The UI discloses that the proposal uses unsaved draft content. Keep the verified
saved World/Plan base revision and digest pinned; do not replace a draft target
with a saved-baseline target.

At card selection and Compose, capture the versioned identity and current
draft. Before Review and again before Apply, re-resolve the same identity in
that exact current draft and require the same grammar, semantic parent/path,
contiguous structural range, target-body digest, full draft digest, saved base
and mounted editor. Any change after capture, including a range shift, requires
a new Compose. Do not relocate a stale range or bind to a same-ID neighbor.

Maintain a card-target selection generation distinct from Tiptap's
selectionGeneration. That editor field is not Playable identity. Existing
editor, World/document, saved-base, draft, selection and Agent-thread fences
remain in force as applicable. A changed card target, editor draft, target
topology, saved revision, document, World or Agent binding invalidates Review
and Apply. No stale Review may mutate the editor.

If a target is missing, duplicated, malformed, unsupported, empty, split across
non-contiguous blocks, over the existing proposal cap, or unsafe to serialize
and reload, disable Compose with an actionable reason. Recovery is to correct
the current Plan if necessary, select the card again and Compose a fresh
proposal. Never use a generic selection fallback.

## 5. Proposal, durable action identity and replay

The current digest fields do not distinguish two cards with identical body
text in the same draft. The selected card must therefore be explicit typed
intent in the proposal request and durable action identity. This is required
even when selected-text and draft digests are present.

Proposed request contract for card-target mode:

- Add a typed Playable target containing canonical kind and ID. Do not accept
  client Tiptap offsets, root indexes, marker-grammar claims, identity paths or
  raw edge data as authority.
- Reuse the exact World/document/saved-base fields, complete current draft and
  its digest, and selected-text field for the canonical body fragment. Add no
  source bytes beyond the existing full-draft proposal input and targeted
  fragment.
- SERVER resolves marker grammar from the exact submitted draft, validates
  that the typed identity is canonical and unique in that draft, independently
  resolves the body under the range rules above, and checks the submitted
  selected-body digest against the resolved body.
- The proposal response echoes the typed identity and server-derived grammar
  version, body scope and range-semantics version, and binds the exact saved
  base, whole-draft digest and resolved target-body digest. The UI accepts it
  only when every field matches the captured target.

APP-STATE owns durable Plan action reservation, fingerprint, receipt and
history-projection compatibility. A target-aware action record and its
allowlisted projection must durably distinguish the typed identity,
server-derived marker grammar version, body scope, range-semantics version and
target-body digest, bound to the existing saved basis and draft digest. The
history row must display the semantic target after a fresh service read. The
request fingerprint includes those semantic values so a same-key retry for a
different card conflicts even when the cards have identical body text. Persist
semantic identity, body scope, range-semantics version and fingerprints only;
do not persist editor offsets, root indexes, raw body bytes or marker bytes.

This is a public and durable contract change. APP-STATE must choose the
backward-compatible record codec and whether a new nullable field or migration
is needed. Historic document-selection actions have no Playable target and
must continue to decode and match under current no-target fingerprint behavior.
Do not reinterpret old selected-text digests as Playable identity.

Recovery reflects existing durable action behavior. A pending action must not
dispatch again. A completed action's proposal payload is currently not
replayable; a retry with the same key must not redispatch or promise to return
that payload. Same-key/same-target completed requests report the existing
completed/unavailable outcome with the original typed target visible in durable
action history. Same-key/different-target requests conflict. Failed or
indeterminate actions require an explicit new action key and visible recovery
action; an uncertain response is not successful Apply. Future proposal-payload
replay is outside this design.

## 6. Owner boundaries and unresolved activation gate

- **DEMO / Plan UI:** card selection, Tiptap range resolution, target-aware
  capture, Review display, WorldPlanEditBridge Apply fences, mounted tests and
  ordinary Save/reopen proof.
- **Buddy SERVER:** request validation against the exact submitted draft,
  server-derived grammar/body identity, response binding and request-boundary
  tests. Do not change Run admission or use Run readiness as an edit gate.
- **APP-STATE:** request fingerprint compatibility, durable target identity,
  action-history projection, pending/failure/replay semantics and any schema
  or migration decision. No storage path or migration is approved yet.
- **ARCHITECTURE:** accepts the cross-boundary identity and range contract.
- **PRIME:** chooses topology, resolves cross-owner sequencing and activates a
  finalized write lease after re-anchoring.

The exact typed action receipt is not approved. PRIME authorized this bounded
design to name the APP-STATE contract, but not its implementation or migration.
SERVER and APP-STATE acceptance is required before activation. If either owner
requires marker/relationship mutation, Run/parser admission changes, new Graph
behavior, unrelated persistence or a second user capability, stop and return to
PRIME for a scope decision.

## 7. Acceptance evidence required after activation

1. Pure range tests for every v1/v2 row, sibling headings, unmarked nested
   notes, unmarked root H1/H2 boundaries, v2 Beat direct body, v2 Option list
   items, duplicate/mixed identities, empty bodies and non-contiguous Choice
   bodies.
2. SERVER tests validate the exact submitted draft, resolve one canonical
   target, reject missing/duplicate/wrong-kind/mismatched-body targets, bind
   response to target/base/draft/body, reject a same-key different-ID retry
   when body and draft digests are identical, and prove no provider redispatch.
3. APP-STATE tests cover old no-target row compatibility, typed target
   persistence, fingerprint mismatch conflict, fresh-service target readback and action-history projection,
   pending and uncertain/lost-response behavior, and no provider redispatch.
4. Mounted UI witness selects a card from the current draft; submits the typed
   target and exact body; Reviews; proves stale identity/range/body/basis or
   conversation binding blocks Apply; Applies only the target body and does not
   Save; then performs ordinary Save and a fresh reopen to prove only the
   intended body changed and protected identity/edge/sibling content remains.
5. Existing document-selection proposals still pass unchanged. Deterministic
   boundary tests need no live provider or operator runtime. APP-STATE
   PostgreSQL tests use its designated isolated test DSN.

A clean technical result is not operator acceptance of the complete DEMO
journey. ROADMAP-demo.md remains the sole current milestone ledger, and J1–J6
remain unaccepted until connected rehearsal and the human gate pass.
