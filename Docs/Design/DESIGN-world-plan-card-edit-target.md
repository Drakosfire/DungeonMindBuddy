---
title: Selected Playable-card body editing in a managed-World Plan
document_class: design
status: accepted
created_at: "2026-10-04"
workstream: DEMO
design_base: "Buddy main 60e1f672441c509f45561f717611af767ece20a1"
pr_topology: serial
---

# DESIGN — Selected Playable-card body editing

**Status: accepted.** #912 reviewed head `44acb1420ee8edadef4201e6f510a29718df172b` merged at `de82370d1a33ada648e22ec087b6eb02aa28532a`, with final SERVER, APP-STATE and ARCHITECTURE acceptance. Execution authority and exact path/resource lease live in the companion implementation handoff. Required parity/protected-structure/race and migration evidence is a pre-implementation-merge gate; this design claims no implemented capability or operator acceptance.

Implementation #913 merged at `f971931ebade4bc7e4550b6fc2f659276afb30d1` from reviewed head `110440433e6d350a0508fd99f554974f09ad3a36`. The companion handoff records owning evidence and closes its lease; this does not establish operator runtime adoption or full shared card-interface acceptance.

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

Proposed exact field and enum contract for card-target mode:

- Preserve current no-target request/response fields and fingerprint behavior.
  Card mode adds request `target_kind: "replace_playable_body"` and
  `playable_target: { kind, id }`, with `kind` exactly one of `scene`, `beat`,
  `choice`, or `option`; `id` matches
  `^(scene|beat|choice|option):[a-z0-9][a-z0-9._-]{0,127}$` and its prefix
  equals `kind`. It does not accept client Tiptap offsets, root indexes,
  marker-grammar claims, identity paths or raw edge data as authority.
- Keep the exact World/document/saved-base fields, complete current draft and
  existing raw-draft digest. Card mode adds
  `body_serialization_version: "plan-playable-body-markdown-v1"`,
  non-empty `target_body_markdown` of at most 8,000 Unicode scalar values, and
  lowercase-hex 64-character `target_body_sha256`. The client declares only
  the codec version it used; SERVER rejects an unsupported version and still
  derives the target body independently. It does not overload `selected_text`.
- SERVER resolves marker grammar from the exact submitted draft, validates
  that the typed identity is canonical and unique, independently resolves and
  serializes the body under this section's contract, then requires exact
  submitted/server body-string and digest equality.
- Card responses use
  `schema_version: "dmb_world_plan_document_edit_proposal_v2"` and return
  existing `action_id` and `idempotency_key`, plus `playable_target`,
  server-derived `marker_grammar_version` (`v1` or `v2`), `body_scope`
  (`heading_body`, `beat_direct_body`, or `option_item_content`),
  `range_semantics_version: "plan-playable-ranges-v1"`, body serialization
  version and digest, and the exact saved base and full-draft digest. Existing
  document-selection responses remain v1.

### Canonical target-body bytes

The body is a semantic Markdown fragment, not raw source lines or a Tiptap JSON
digest. Define codec `plan-playable-body-markdown-v1` as follows:

1. On the UI, take exactly the resolved body nodes. For a heading target these
   are authored root blocks. For a v2 Option these are the child blocks of
   that one top-level list item, excluding its list-item wrapper, identity and
   edge attributes while retaining descendant blocks such as nested lists.
2. Build `{ type: "doc", content: bodyNodes }` and serialize it with the
   existing `tiptapJsonToSemanticMarkdown` contract. Its exact output,
   including its one terminal LF, is `target_body_markdown`. Do not trim it
   again, prepend a marker, include a heading/list wrapper, or normalize
   Unicode. Markdown import normalizes CRLF and CR to LF; the serialized value
   is UTF-8 text without a BOM.
3. `target_body_sha256` is lowercase hex SHA-256 over exactly
   `UTF8(target_body_markdown)`. The server independently derives the same
   body from the exact submitted draft and runs the equivalent canonical
   semantic serializer. It requires exact string and digest equality; a
   client digest alone is not authority. Preserve existing full-draft
   `draft_sha256` semantics: SHA-256 over the exact UTF-8 encoding of the
   submitted `draft_markdown` string, without new newline, Unicode,
   frontmatter or BOM normalization.
4. Require serialize → Markdown import → serialize stability and semantic
   structure equality for the selected fragment. A warning, unsupported node,
   unrepresentable fragment, or UI/server codec mismatch makes that target
   unavailable. Serializer behavior changes require a new serialization
   version and fixtures; stored fingerprints must not silently change meaning.

The UI and SERVER must consume the same checked-in golden vectors (or
equivalent cross-boundary parity tests) containing exact draft, target,
canonical body string and digest. Cover LF/CRLF/CR source lines, heading
boundaries and unmarked nested headings, escaping, links, inline marks, code,
hard breaks, and v2 Option single/multiple paragraphs, nested lists and inline
content. Vectors must prove that a target marker, outer list wrapper, sibling
items and edges are excluded from body bytes but unchanged in the full-document
protected inventory. Unsupported or non-round-tripping forms stay unavailable;
do not broaden parser admission to make a vector pass.

SERVER owns canonical action-fingerprint construction and server-side receipt
matching. Its target-aware fingerprint input includes the existing saved
basis, exact raw-draft digest, `target_kind`, typed Playable kind/ID,
server-derived marker grammar, body scope, range-semantics version,
body-serialization version, target-body digest and instruction. Mutable
conversation history is excluded. Preserve the existing no-target fingerprint
algorithm for historic and current document-selection actions. Both the early
existing-receipt lookup and concurrent-reservation-race readback must compare
the complete typed target before any provider dispatch; same-key/different-ID
requests conflict even when body and draft digests are identical.

APP-STATE's storage ruling on original packet head
`8f023095ef3a6b26ddf35f831a0282b31f8edbbc` accepts one nullable, versioned
target receipt on the existing `plan_action.action` record. SERVER reviewed
head `649b87df28ea209bca9cb23e54a6a4bf437e28e2`; the exact field list below
also persists the new body-serialization version required by that review. The
proposed exact field is `playable_target_receipt JSONB NULL`; do not create a
new table or change Agent conversation storage/behavior. Its non-null v1 value
has exactly these fields:

```text
schema_version: "dmb_plan_playable_target_receipt_v1"
kind: "scene" | "beat" | "choice" | "option"
id: canonical kind-prefixed Playable ID
marker_grammar_version: "v1" | "v2"
body_scope: "heading_body" | "beat_direct_body" | "option_item_content"
range_semantics_version: "plan-playable-ranges-v1"
body_serialization_version: "plan-playable-body-markdown-v1"
target_body_sha256: lowercase hex SHA-256
```

The `target_kind` header value for this mode is `replace_playable_body`;
`selected_text_sha256` remains null. Storage constraints require this mode to
have exactly one valid target receipt, while existing `replace_selection` and
`insert_at_caret` rows require a null receipt and retain their current
selection-digest rules. The existing `request_fingerprint` field stores the
SERVER-computed fingerprint. The allowlisted `PlanActionProjection` exposes a
nullable `playable_target_receipt`; historic no-target rows decode/project it
as null. A fresh-service read must show the original target and both version
fields.

The current main migration head is `20261003_0014`. A single candidate
migration is `src/application_state/migrations/versions/20261004_0015_plan_action_playable_target.py`,
with `down_revision = "20261003_0014"`; it is allowed only if a fresh main
re-anchor at activation still ends at 0014 and PRIME includes it in the exact
lease. If the head moved, stop and re-sequence. This migration adds only the
nullable typed receipt and the constraints needed for its target mode; no
conversation schema/behavior, second table, or unrelated storage is in scope.
Persist no editor offsets, root indexes, raw body bytes or marker bytes.

The UI accepts a response only for the exact in-flight capture and conversation
binding that issued it. It checks echoed `idempotency_key`, request/capture
identity, World/document/saved base/full-draft digest, typed target, body digest,
range/serialization versions and Agent conversation binding before Review and
again before Apply. `action_id` is generated by the server; the UI requires a
non-empty ID and associates it only with that matching in-flight response. A
late same-target response cannot attach to a newer capture or conversation.

This is a public and durable contract change. The accepted APP-STATE storage
shape is one nullable `playable_target_receipt` value and its allowlisted
projection; no second table or Agent-conversation change. Historic
document-selection actions have no Playable target and must continue to decode
and match under current no-target fingerprint behavior. Do not reinterpret old
selected-text digests as Playable identity.

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

- **DEMO / Plan UI:** card selection, Tiptap range resolution and canonical
  body serialization, exact in-flight response and conversation binding,
  Review display, WorldPlanEditBridge Apply fences, mounted parity tests and
  ordinary Save/reopen proof.
- **Buddy SERVER:** exact-draft identity/body resolution, canonical body codec,
  server-derived grammar/scope, canonical action-fingerprint construction,
  receipt matching, action/idempotency response binding and request-boundary
  tests. Do not change Run admission or use Run readiness as an edit gate.
- **APP-STATE:** accepted one nullable versioned target receipt on the existing
  action row; owns durable storage/codec, target history projection, legacy
  row compatibility, and the candidate migration conditional on main still
  ending at 0014. SERVER constructs and matches the canonical fingerprint.
- **ARCHITECTURE:** accepts the cross-boundary identity and range contract.
- **PRIME:** chooses topology, resolves cross-owner sequencing and activates a
  finalized write lease after re-anchoring.

APP-STATE accepted the storage shape on original packet head
`8f023095ef3a6b26ddf35f831a0282b31f8edbbc`; SERVER reviewed head
`649b87df28ea209bca9cb23e54a6a4bf437e28e2`. SERVER, APP-STATE and ARCHITECTURE accepted the exact final amendment. PRIME separately activated the bounded implementation and isolated-test migration under the companion handoff; no operator/shared-database migration is authorized. If an owner requires
marker/relationship mutation, Run/parser admission changes, new Graph behavior,
unrelated persistence or a second user capability, stop and return to PRIME
for a scope decision.

## 7. Acceptance evidence required after activation

1. Pure range tests for every v1/v2 row, sibling headings, unmarked nested
   notes, unmarked root H1/H2 boundaries, v2 Beat direct body, v2 Option list
   items, duplicate/mixed identities, empty bodies and non-contiguous Choice
   bodies.
2. Shared codec vectors run at both UI and SERVER boundaries and compare exact
   canonical bytes/digests for each supported fixture. SERVER tests validate
   the exact submitted draft, resolve one canonical target, reject
   missing/duplicate/wrong-kind/mismatched-body targets, bind response to
   `action_id`, `idempotency_key`, the in-flight request/conversation,
   target/base/draft/body and versions, and reject same-key/different-ID
   requests on both existing-receipt lookup and concurrent-reservation-race
   readback before any current-Plan read or provider dispatch, including when
   the two targets have identical body and full-draft digests.
3. APP-STATE tests cover old no-target row compatibility, typed target and
   server-computed fingerprint persistence, same-key/different-ID conflict for
   identical body/draft digests, fresh-service target readback and action-history
   projection, pending and
   uncertain/lost-response behavior, and no provider redispatch.
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
