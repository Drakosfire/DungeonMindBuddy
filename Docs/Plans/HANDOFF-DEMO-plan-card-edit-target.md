---
title: Managed-World Plan selected-card body Compose, Review and Apply
document_class: implementation_handoff
status: BLOCKED
created_at: "2026-10-04"
workstream: DEMO
design_authority: "../Design/DESIGN-world-plan-card-edit-target.md"
design_base: "Buddy main 60e1f672441c509f45561f717611af767ece20a1"
pr_topology: serial
implementation_branch: not_assigned
implementation_pr: not_authorized
---

# HANDOFF — Compose and Apply an edit to one Plan Playable body

> This is a BLOCKED design packet. It grants no code, storage, migration,
> runtime or implementation lease.

## Status and activation gate

**Status: BLOCKED.** Buddy main 60e1f672441c509f45561f717611af767ece20a1 is
the fresh design base. PR #911 is merged and its implementation handoff is
SETTLED. The roadmap names selected-card Compose/Review/Apply as a serial
successor, but the current World Plan proposal action receipt does not store a
Playable target.

ARCHITECTURE determined that selected identity must bind proposal request,
response, Apply and durable action history. The current fingerprint binds exact
saved basis, draft digest, target kind and selected-text digest only. Two cards
with identical bodies in the same draft therefore alias unless identity is
added to request fingerprint and durable target provenance. PRIME expanded this
design packet to name that one APP-STATE-owned target contract, but did not
authorize its implementation or migration.

Before activation, PRIME must receive SERVER and APP-STATE acceptance of the
target request/response and durable action identity, including legacy
no-target compatibility and pending/completed/uncertain behavior; approve the
exact path allowlist and any version/migration; and re-anchor main, open PRs,
active leases and test/runtime state. PRIME may then publish a fresh ACTIVE
handoff. Until then, no implementation branch, code PR or migration is
authorized under this document.

The intended topology after all gates resolve is **serial**, with one
implementation PR for the selected-card edit capability. It is not stacked on
an unmerged behavior PR. This topology is proposed only; PRIME records the
final activation order and exact active lane.

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

For targeted mode, the client submits canonical kind/ID with existing exact
World/document/saved-base and current-draft fields. It sends no editor offsets
or claimed grammar version. SERVER independently resolves identity and body
from that exact submitted draft, validates uniqueness and digest, derives the
grammar version, and returns a response bound to target, server-derived body
scope, range-semantics version, body digest, draft digest and saved basis.

APP-STATE must fingerprint the target identity and server-derived grammar,
body scope, range semantics and body fingerprint with its exact basis and
current draft digest, and make the semantic target visible in the durable
action record and allowlisted history projection. This distinguishes same-body
cards for same-key conflict detection and fresh-service readback. Historic no-target document-selection actions retain current
compatibility. Do not reuse the selected-text digest as a card ID.

The existing service does not replay a completed proposal payload. Preserve
that behavior: a pending same-key action is not dispatched again; completed
same-key requests do not promise payload replay; a different card under the
same key conflicts; failed or indeterminate outcomes need a visible explicit
recovery action and a new key. A lost response must not be shown as Applied or
cause an automatic second provider call.

The exact field codec, schema version and migration necessity belong to
APP-STATE. The current repository's latest migration is
20261003_0014_plan_action_dialogue.py. A new sequential migration under
src/application_state/migrations/versions is a candidate only if APP-STATE
chooses a schema change after re-anchoring. Do not edit migration 0014 or
assume a new column, table or storage role before owner approval.

## 4. Owner boundaries

- **DEMO:** Plan card action, mounted-draft position mapping, target-aware
  capture/review, WorldPlanEditBridge Apply, stale-state behavior and
  Save/reopen mounted proof.
- **Buddy SERVER:** exact-draft identity/body validation, server-derived grammar
  and request/response binding.
- **APP-STATE:** durable identity codec, idempotency fingerprint and action
  history, historic row compatibility, status/recovery semantics, any migration.
- **ARCHITECTURE:** cross-boundary contract acceptance.
- **PRIME:** active path arbitration, cross-owner sequencing, final lease and
  PR topology.

SERVER and APP-STATE acceptance is not recorded in this BLOCKED packet. No
owner may treat this design proposal as authority to implement its component.

## 5. Candidate implementation paths for PRIME review

These are candidates, not a write lease. PRIME must re-check every path and
active PR before activation and narrow or amend the list with each owner.

**DEMO / UI**

- apps/live-control-ui/src/planSurface/components/WorldPlanCardProjection.tsx
- apps/live-control-ui/src/planSurface/PlanSurfacePage.tsx
- apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx
- apps/live-control-ui/src/planSurface/agentEdit/planAgentEditProposal.ts
- apps/live-control-ui/src/planSurface/agentEdit/planSectionTarget.ts, or a
  new narrowly scoped Playable-body range helper if review prefers it
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
- a minimal identity-only resolver under apps/live_control_server/services if
  current parsing cannot prove unique membership without importing Run
  admission/readiness
- tests/test_world_plan_edit_proposal.py
- tests/test_plan_document_edit_proposal.py

**APP-STATE**

- src/application_state/plan_action_dialogue/types.py
- src/application_state/plan_action_dialogue/service.py
- src/application_state/plan_action_dialogue/repository.py
- tests/application_state/test_plan_action_dialogue_postgres.py
- src/application_state/migrations/versions/20261004_0015_plan_action_playable_target.py,
  only if APP-STATE approves a migration and fresh main still ends at revision 0014

No exact APP-STATE schema or migration has been accepted. The path list is
provisional and must become an exact exclusive lease before any write. Do not
touch migration 0014 or add a new one before that decision.

The 2026-10-04 PR census found #887 limited to prototypes/plan-play-cards/**;
#869 to statblock editor/workbench; #844 to an Ingest handoff; #826 to
World-space binding; #781 to semantic-action projection; #764 to PlanSurface
configuration/projection registration; #765/#763 to Rules work; and remaining
open PRs to backlog or UI/Rules documentation. No path overlapped this
candidate list at that census. Recheck live paths, active handoffs and leases
at activation; this is not a standing collision clearance.

## 6. Required owning-boundary evidence after activation

1. **UI range tests:** prove every v1/v2 range in the design matrix, sibling
   headings, unmarked nested notes, unmarked root boundaries, v2 Beat direct
   body, v2 list-item Options, duplicates, malformed/mixed grammar, empty
   bodies and non-contiguous Choice bodies.
2. **SERVER tests:** validate target membership and body digest against the
   exact request draft, reject duplicate/missing/wrong-kind/stale inputs, bind
   target/base/draft/body in the response, conflict when the same idempotency
   key switches between two same-body card IDs, and prove no provider
   redispatch.
3. **APP-STATE tests:** read old no-target actions unchanged; persist and
   freshly reload the new semantic target and exact basis/draft; prove
   target-sensitive fingerprints, same-key conflict and pending/completed/
   failed/indeterminate behavior. A completed lost proposal payload remains
   explicitly non-replayable.
4. **Mounted UI witness:** select a current card, Compose, inspect exact target
   identity/body/basis, Review, then make a stale draft/range/target or
   conversation change and prove Apply refuses without editor mutation. Repeat
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
compatibility, or SERVER/APP-STATE requests a different scope. Any schema or
migration change remains blocked until APP-STATE accepts the contract and PRIME
activates the exact path.

## 8. Runtime/state lane

No ports, service process, live Plan, Graph, provider credentials or database
are part of this blocked design lane. Future deterministic UI/server tests use
fakes; APP-STATE database tests use its isolated test target only. At
activation, name branch/base, checkout, services, ports, database, schema,
output directories and runtime owner. Do not use the operator's 5202/8000/5203
session or the prototype in #887.

## 9. Completion and settlement

This design packet closes no roadmap milestone or J1–J6 gate. After owner
contract acceptance, PRIME must publish a fresh ACTIVE handoff with an exact
path lease and PR order. After implementation merges, record the exact reviewed
head, merge commit, owner reviews, test provenance, any accepted migration and
remaining live/operator evidence in this handoff and ROADMAP-demo.md. Keep the
connected DEMO journey unaccepted until its required rehearsal and operator
gate pass.
