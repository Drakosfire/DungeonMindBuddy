---
title: Managed-World Plan selected-card body Compose, Review and Apply
document_class: implementation_handoff
status: SETTLED
created_at: "2026-10-04"
workstream: DEMO
design_authority: "../Design/DESIGN-world-plan-card-edit-target.md"
design_base: "Buddy main 60e1f672441c509f45561f717611af767ece20a1"
pr_topology: serial
implementation_branch: codex/demo-selected-card-body-edit
implementation_pr: "#913 merged"
---

# HANDOFF — Compose and Apply an edit to one Plan Playable body

## PRIME settlement — 2026-10-04

**Status: SETTLED; exclusive implementation write lease closed.** PR #913 merged at `f971931ebade4bc7e4550b6fc2f659276afb30d1` from reviewed head `110440433e6d350a0508fd99f554974f09ad3a36`, base `768dc85ca93b05d438c9f92d85a781c07f699ce4`. PRIME reviewed four distinct submitted heads; final SERVER and APP-STATE acceptance covers unchanged production code at `9414772e`, and independent UI review accepts the final test-only head. Final review: https://github.com/Drakosfire/DungeonMindBuddy/pull/913#issuecomment-5982512061.

Independent owning evidence: 227/227 UI tests, then 14/14 affected mounted tests, then the final 1/1 same-card supersession witness; 86/86 SERVER/isolated PostgreSQL tests, then 56/56 affected tests including v1 Option typed receipt/proposal and fresh-service readback. Author final suites passed 283 UI and 88 SERVER/APP-STATE tests. Cumulative diff passed whitespace review. TypeScript still reports only the inherited unchanged `ThreatPublicationPanel.tsx:553` JSX namespace error. No required GitHub check was configured.

The implemented flow selects a current v1/v2 card body, Compose→Review→explicit Apply to the draft, then ordinary Save and fresh reopen. It preserves marker identity, edges, siblings and protected references; mismatched, stale and late same-card responses fail without mutation. Ordinary HTTPS links unsupported by the mounted editor remain unavailable; supported typed references retain identity and label. Migration 0015 was verified only against isolated fixtures; the fixture is stopped. No operator runtime/database migration, provider/corpus call, Graph conversation, full prototype presentation adoption or J1–J6 acceptance is claimed.

The activation and allowlist below are historical execution authority, not a continuing write lease. Projection fidelity repair and Graph-backed conversation require their own newly pinned bounded activation.

## PRIME activation — 2026-10-04

**Historical activation (now SETTLED).** PRIME activated one selected-card body Compose/Review/Apply implementation PR from fresh Buddy remote main `de82370d1a33ada648e22ec087b6eb02aa28532a` (design #912 merge, reviewed head `44acb1420ee8edadef4201e6f510a29718df172b`). SERVER, APP-STATE and ARCHITECTURE accepted that exact design. This activation is pinned by the commit publishing this handoff; fetch and start from that commit before implementation.

**Owner/path contract:** DEMO is the sole writer for the exact §5 allowlist, including its co-owned SERVER and APP-STATE work. SERVER independently reviews canonical body/admission/fingerprint/response/race evidence. APP-STATE independently reviews nullable target storage, migration compatibility, constraints and fresh-service history. ARCHITECTURE retains the range/codec contract. PRIME independently reviews the cumulative diff and owning-boundary evidence before merge. No competing write lease is assigned to the reviewers.

**Fresh census:** PRIME fetched remote main, checked all eleven open PRs and their changed paths (#887/#869/#844/#826/#798/#781/#765/#764/#763/#761/#760), and found no overlap with §5. #887 is prototype-only. #911 is merged and SETTLED. Graph adapter #905 and Graph conversation remain BLOCKED and acquire no paths or migration lane here.

**Migration:** current code chain ends at `20261003_0014`; APP-STATE accepted one nullable typed receipt on the existing action row. This lease authorizes exactly `20261004_0015_plan_action_playable_target.py`, parent `20261003_0014`, plus the named codec/constraints/history changes and two migration-head test assertions. Do not edit historical migrations, add tables, change conversation behavior, upgrade dependencies or run this migration against operator/shared data. Verify upgrade of populated 0014 fixtures preserves legacy no-target actions and their IDs/history, as well as fresh target persistence and malformed receipt rejection.

**Topology/resources:** one serial implementation PR on `codex/demo-selected-card-body-edit`. Reuse the clean closed-Ask checkout `/tmp/dmb-demo-card-ask-02fa1188` after fetching this activation and switching to that branch. Provider fakes/synthetic fixtures only. Approved isolated PostgreSQL fixture: `/tmp/dmb-demo-appstate-pg`, loopback `127.0.0.1:55461`, per-test UUID databases, tests own migration state; coordinate its start/stop with PRIME. It is currently stopped. No operator 5202/8000/5203 or application database lease, live provider/corpus call, credential change or restart. Shared codec vectors live only in the exact fixture path in §5; test logs/output stay under `/tmp`.

The parity/protected-structure/retry/race/migration and mounted Apply→Save→fresh-reopen evidence below is required before the implementation merges. Activation permits the code needed to produce that evidence. Stop for any extra path, new capability, schema head collision or inability to preserve canonical body/protected structure.

## PRIME narrow history amendment — 2026-10-04

PRIME adds only the two §5 local-history paths needed for the existing proposal persistence contract to recognize `replace_playable_body`. DEMO remains the sole writer in PR #913. Preserve existing payload limits, sanitization, privacy, and recovery behavior; do not mislabel card edits as selection/caret edits, broaden durable conversation state, change storage authority, or make a reloaded proposal actionable without existing fresh target/basis checks. Prove correct target-kind persistence and reload in the focused test. PRIME fetched remote main `a21da688c1a63907519607675453350b35216bf2` and inspected all twelve open PR file sets; neither added path overlaps another PR. This amendment is pinned by its publication commit and does not change the active implementation base or other leases.

## 1. User action and invariant

In the existing managed-World Plan Cards view, the user selects one current
Playable card, composes an edit for only its authored body, reviews the proposal,
explicitly Applies through WorldPlanEditBridge, then uses ordinary Save and a
fresh reopen.

The edit targets the exact selected identity in the exact submitted current
draft and verified saved World/Plan base. It never targets matching display
text, a sibling card, an entire heading section, marker/title, edge, relationship
or another draft. Apply changes the mounted draft only. It does not Save,
commit, write Graph state or change a Run.

Existing text-selection and complete heading-section proposal behavior remains
unchanged and has no Playable target field. Card-target mode must fail closed;
it cannot fall back to those generic target modes.

## 2. Authority and current seam

Design contract: [DESIGN-world-plan-card-edit-target.md](../Design/DESIGN-world-plan-card-edit-target.md).

At the base above:

- WorldPlanCardProjection derives display bodies through
  slicePlayableBodies. It retains kind/ID and flattened text but no editable
  source range.
- playableStructureIndex validates versioned structure and records hierarchy
  and edges but has no editor positions.
- WorldPlanEditBridge captures current selection or a generic root-heading
  section. It already fences World, document, saved base, full draft, selection
  and Agent binding. The new mode must extend this authority without changing
  its existing document-selection behavior.
- Current World proposal API types, server models and action receipt do not
  carry Playable identity, grammar or body digest. APP-STATE action records
  persist draft/basis and selected-text hash, not the card.
- The existing section-targeting contract intentionally rejects a
  round-trip-unsafe parent Beat. No serializer, Run parser, marker grammar or
  relationship behavior is leased here.

The range matrix and failure behavior are in the design. Key semantics: v1
Scene/Beat/Choice/Option are marked headings; v2 Beat/Scene/Choice are marked
headings and Option is a marked top-level list item. Heading targets exclude
marker and title and stop at the next Playable heading or unmarked root H1/H2.
v2 Beat means its direct body only. A non-contiguous Choice body split by
marked Options is unavailable in this first slice. A v2 Option keeps its
marker, list wrapper, edges and siblings.

## 3. Proposed contract and recovery

The exact proposed card-mode request fields are `target_kind:
"replace_playable_body"`, `playable_target: { kind, id }` where `kind` is one
of `scene|beat|choice|option`, `body_serialization_version:
"plan-playable-body-markdown-v1"`, `target_body_markdown`, and
`target_body_sha256`. The target ID matches
`^(scene|beat|choice|option):[a-z0-9][a-z0-9._-]{0,127}$` and its prefix must
equal `kind`. The body string is non-empty and limited to 8,000 Unicode scalar
values; its digest is exactly 64 lowercase hex characters. Reuse current exact
World/document/saved-base and full-draft fields. Do not send editor offsets,
root indexes or claimed marker grammar; do not overload `selected_text`. The
client declares the codec version it used; SERVER rejects unsupported versions
and independently derives the body. Existing no-target fields and fingerprint
behavior stay unchanged.

`plan-playable-body-markdown-v1` serializes exactly the resolved body-node
fragment as a synthetic Tiptap doc with the existing
`tiptapJsonToSemanticMarkdown` contract. It includes that serializer's single
terminal LF, is UTF-8 without BOM, is not trimmed again, and preserves Unicode
code points. A heading target serializes its authored root body blocks. A v2
Option serializes the marked top-level list item's child blocks, excluding the
outer item, marker and edge attributes while retaining nested child blocks.
`target_body_sha256` is lowercase-hex SHA-256 over exactly those UTF-8 bytes.
The server parses the exact submitted draft, independently derives and
serializes the same body, and requires exact string plus digest equality. Its
full-draft SHA remains over the exact UTF-8 encoding of the submitted
`draft_markdown` string with current behavior.
Round-trip warnings, unsupported nodes, or UI/server byte mismatch disable
that target; do not broaden the parser to make it pass. Any serializer change
needs a new version.

UI and SERVER must run the same golden vectors (or equivalent parity tests)
for the exact submitted draft, target, canonical body string and digest. Cover
LF/CRLF/CR, heading boundaries and unmarked nested headings, escaping, links,
inline marks, code, hard breaks, and v2 Option inline, multi-paragraph and
nested-list bodies. Unsupported/non-round-tripping fragments remain out of
scope. `range_semantics_version` is exactly
`"plan-playable-ranges-v1"`; response `body_scope` is one of
`heading_body|beat_direct_body|option_item_content`, with server-derived
`marker_grammar_version` `v1|v2`.

Card responses use
`schema_version: "dmb_world_plan_document_edit_proposal_v2"` and bind the
existing `action_id` plus the exact request `idempotency_key`, target, grammar,
body scope, range and serialization versions, body digest, saved basis and
full-draft digest. The UI accepts it only for the exact in-flight request and
capture/conversation binding; it verifies echoed idempotency key and all
request/target/base/draft/body/version fields before Review and Apply. A
non-empty `action_id` is associated only with that correlated response. A late
same-target response cannot attach to a newer capture.

SERVER constructs the canonical action fingerprint and owns
`_matches_world_action_receipt` semantics. Fingerprint target-mode input
includes exact saved basis and raw-draft digest, target kind and typed
Playable kind/ID, server-derived marker grammar, body scope, range and
serialization versions, target-body digest and instruction; mutable
conversation history remains excluded. Keep the existing no-target fingerprint
algorithm for historic/document-selection actions. Check complete typed target
both at early existing-receipt lookup and concurrent-reservation-race readback
before any provider dispatch. Same-key/different-ID requests conflict even
when body and draft digests match.

APP-STATE's design ruling on the original packet accepts one nullable,
versioned target receipt on the existing `plan_action.action` record. The
proposed nullable JSONB field is named `playable_target_receipt`; it is the
only new durable semantic field. It contains exactly:

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

The action's `target_kind` is `replace_playable_body`; its existing
`selected_text_sha256` remains null. Constraint/codec changes must require one
valid nullable receipt for this target kind and keep a null receipt plus
current digest rules for historical/current no-target modes. The existing
`request_fingerprint` stores the SERVER-computed fingerprint. The allowlisted
`PlanActionProjection` includes a nullable receipt, with historic no-target
rows decoding and projecting null. A fresh-service read must expose the
original target and both versions. Do not create a new table or change Agent
conversation storage/behavior. Do not persist editor offsets, root indexes,
raw body bytes or marker bytes; do not reuse selected-text digest as card ID.

APP-STATE accepts one candidate migration only at the current chain head:
`src/application_state/migrations/versions/20261004_0015_plan_action_playable_target.py`
with `down_revision = "20261003_0014"`. Fresh activation must confirm main
still ends at 0014; if not, stop and return to PRIME. The migration adds only
the nullable target receipt and constraints needed for the new target mode.
It does not add conversation behavior, another table or unrelated storage.

The existing service does not replay a completed proposal payload. Preserve
that behavior: a pending same-key action is not dispatched again; completed
same-key requests do not promise payload replay; a different card under the
same key conflicts; failed or indeterminate outcomes need a visible explicit
recovery action and a new key. A lost response must not be shown as Applied or
cause an automatic second provider call.

APP-STATE accepts the one nullable `playable_target_receipt` extension and the
candidate `0015` migration stated above, conditional on a fresh activation
re-anchor confirming the migration head is still `20261003_0014`. The exact implementation and isolated-test migration lease is active under PRIME activation above. No Agent-conversation schema or
behavior change is part of this Plan-action receipt.

## 4. Owner boundaries

- **DEMO:** Plan card action, mounted-draft position mapping and canonical body
  bytes, exact in-flight response/conversation correlation, target-aware
  capture/review, WorldPlanEditBridge Apply and Save/reopen proof.
- **Buddy SERVER:** exact-draft identity/body validation, canonical body codec,
  server-derived grammar/scope, canonical action-fingerprint construction,
  `_matches_world_action_receipt`, action/idempotency response binding and
  same-key checks at existing-receipt and reservation-race readback boundaries.
- **APP-STATE:** accepted one nullable typed receipt on the existing action
  row; owns its durable storage/codec, target projection, historic no-target
  compatibility, and conditional migration. SERVER constructs and matches the
  canonical fingerprint.
- **ARCHITECTURE:** cross-boundary contract acceptance.
- **PRIME:** active path arbitration, cross-owner sequencing, final lease and
  PR topology.

APP-STATE accepted the storage shape on original packet head
`8f023095ef3a6b26ddf35f831a0282b31f8edbbc`; SERVER reviewed head
`649b87df28ea209bca9cb23e54a6a4bf437e28e2`. SERVER, APP-STATE and ARCHITECTURE accepted the exact final amendment; PRIME activation above governs the sole implementation lane.

## 5. Settled implementation write allowlist (closed)

Only these paths are leased. New helpers/tests are limited to the named body-target contract; no directory-wide write authority is granted.

**DEMO / UI**

- apps/live-control-ui/src/planSurface/components/WorldPlanCardProjection.tsx
- apps/live-control-ui/src/planSurface/PlanSurfacePage.tsx
- apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx
- apps/live-control-ui/src/planSurface/components/agentInteractionHistory.ts — only preserve/reload the existing proposal payload with the truthful `replace_playable_body` target kind
- apps/live-control-ui/src/planSurface/components/agentInteractionHistory.test.ts — focused persistence/reload coverage for that target kind
- apps/live-control-ui/src/planSurface/agentEdit/planAgentEditProposal.ts
- apps/live-control-ui/src/planSurface/agentEdit/planPlayableBodyTarget.ts
- apps/live-control-ui/src/planSurface/agentEdit/planPlayableBodyTarget.test.ts
- apps/live-control-ui/src/planSurface/agentEdit/planSectionTarget.ts
- apps/live-control-ui/src/api/types.ts
- apps/live-control-ui/src/api/liveApi.ts
- apps/live-control-ui/src/planSurface/PlanSurfacePage.test.tsx
- apps/live-control-ui/src/planSurface/WorldPlanCardProjection.integration.test.tsx
- apps/live-control-ui/src/planSurface/WorldPlanAgentReviewedEdit.integration.test.tsx
- apps/live-control-ui/src/planSurface/agentEdit/planAgentEditProposal.test.ts
- apps/live-control-ui/src/api/liveApi.test.ts

**Buddy SERVER**

- apps/live_control_server/models/plan_document_edit_proposal.py
- apps/live_control_server/services/plan_document_edit_proposal.py
- apps/live_control_server/services/plan_playable_body_target.py
- tests/test_plan_playable_body_target.py
- tests/test_world_plan_edit_proposal.py
- tests/test_plan_document_edit_proposal.py
- tests/fixtures/plan_playable_body_codec_v1.json — shared UI/SERVER golden vectors

**APP-STATE**

- src/application_state/plan_action_dialogue/types.py
- src/application_state/plan_action_dialogue/service.py
- src/application_state/plan_action_dialogue/repository.py
- tests/application_state/test_plan_action_dialogue_postgres.py
- src/application_state/migrations/versions/20261004_0015_plan_action_playable_target.py — exact accepted additive migration, parent 0014
- tests/application_state/test_agent_conversation_postgres.py:146, update only
  its migration-head assertion for 0015
- tests/application_state/test_agent_conversation_service.py:781-782, update
  only its migration-head assertion for 0015

The migration and two head-assertion changes above are now included in the exclusive lease. No historical migration or conversation behavior change is authorized. A new remote schema head or competing migration requires re-sequencing with PRIME.

**Mutable authority paths for activation and settlement**

These authority paths are included for truthful contract and post-merge settlement:

- Docs/Design/DESIGN-world-plan-card-edit-target.md
- Docs/Plans/HANDOFF-DEMO-plan-card-edit-target.md
- Docs/Roadmaps/ROADMAP-demo.md

Do not mark the in-flight slice complete early. Record actual reviewed head,
merge commit, owner decisions and evidence only after they exist.

The 2026-10-04 PR census found #887 limited to prototypes/plan-play-cards/**;
#869 to statblock editor/workbench; #844 to an Ingest handoff; #826 to
World-space binding; #781 to semantic-action projection; #764 to PlanSurface
configuration/projection registration; #765/#763 to Rules work; and remaining
open PRs to backlog or UI/Rules documentation. No path overlapped this
candidate list at that census. Recheck live paths, active handoffs and leases
at activation; this is not a standing collision clearance.

## 6. Required owning-boundary evidence after activation

1. **UI range/codec tests:** prove every v1/v2 range in the design matrix,
   sibling headings, unmarked nested notes, unmarked root boundaries, v2 Beat
   direct body, v2 list-item Options, duplicates, malformed/mixed grammar,
   empty bodies and non-contiguous Choice bodies. Run golden body-codec vectors
   shared with SERVER and assert exact UTF-8 bytes/digests, including Option
   inline, multi-paragraph and nested-list cases.
2. **SERVER tests:** validate target membership, canonical body bytes and
   digest against the exact request draft; reject duplicate/missing/wrong-kind/
   stale inputs; bind action_id, idempotency_key, exact in-flight target/base/
   draft/body/versions; conflict on same-key/different-ID targets with
   identical body/draft digests both at existing receipt lookup—before any
   current Plan read or provider call—and concurrent-reservation-race readback
   before dispatch. Prove no provider redispatch.
3. **APP-STATE tests:** read old no-target actions unchanged; persist target and
   server-computed fingerprint values with exact basis/draft; fresh-service
   readback exposes the exact nullable receipt; prove same-key/different-ID
   conflict when body/draft digests match, plus pending/completed/failed/
   indeterminate behavior. A completed lost proposal payload remains explicitly
   non-replayable.
4. **Mounted UI witness:** select a current card, Compose, inspect exact target
   identity/body/basis, Review, then deliver a late same-target response to a
   newer request/capture and make a stale draft/range/target or conversation
   change; prove correlation or Apply refuses without editor mutation. Repeat
   with fresh capture and Apply only the intended body.
5. Prove Apply did not Save. Use ordinary Save, unmount, freshly reopen, and
   verify intended body plus unchanged sibling content, marker identity, option
   edges and protected links. Keep existing document-selection proposal tests
   passing unchanged.

Use deterministic provider fakes. APP-STATE PostgreSQL tests use its approved
isolated test DSN. No live provider, operator runtime, shared service or
persistent demo database is authorized by this design.

## 7. Exclusions and stop conditions

No Graph reads/writes, Run creation/admission, marker or relationship authoring,
generic parser redesign, new conversation model, changed document-selection
semantics, source-patching framework, automatic Apply/Save, unrelated action
history work, or new storage role/table unless APP-STATE requires and PRIME
explicitly approves. No second implementation PR.

Stop and return to PRIME if target validation requires Run readiness/admission,
the range model cannot preserve adjacent Plan content, the proposal API needs a
broader context contract, APP-STATE cannot preserve existing fingerprint
compatibility, or SERVER/APP-STATE requests a different scope. Any additional schema or migration change requires a revised owner-approved contract and PRIME lease.

## 8. Runtime/state lane

The activation block owns the exact isolated checkout/test database/output lane. No live Plan, operator service, Graph, provider credentials, prototype import or shared database is leased. Per-test database migrations and deterministic fixtures are authorized; no operator migration/deployment is implied.

## 9. Completion and settlement

This design packet closes no roadmap milestone or J1–J6 gate. Owner contract acceptance and the exact ACTIVE path lease are recorded above. After implementation merges, record the exact reviewed
head, merge commit, owner reviews, test provenance, any accepted migration and
remaining live/operator evidence in this handoff and ROADMAP-demo.md. Keep the
connected DEMO journey unaccepted until its required rehearsal and operator
gate pass.
