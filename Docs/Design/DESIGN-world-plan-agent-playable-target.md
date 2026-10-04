---
title: Selected committed Playable-card target for managed-World Plan Ask
document_class: design
status: proposed_for_review
version: 0.1
created_at: "2026-10-04"
workstream: DEMO
design_base: "Buddy main 5b1322d9719b4ee2bf64c28c2ee22ce071cee43f"
roadmap_authority: "../Roadmaps/ROADMAP-demo.md@5b1322d9719b4ee2bf64c28c2ee22ce071cee43f"
implementation_handoff: "../Plans/HANDOFF-DEMO-plan-agent-card-target.md"
---

# Selected committed Playable-card target for World Plan Ask

## Decision

The first capability is **selected committed-card Ask** on the existing
managed-World Plan conversation. A selected Playable element focuses one
ordinary Plan Ask; it does not create a new conversation, a card store, a Graph
read, or an edit workflow.

One merge-ready invariant governs the slice:

> Every accepted targeted Plan Ask binds one canonical Playable `{kind, id}`
> to the exact server-resolved committed Plan WorkRevision used for that turn;
> the same target and basis are part of the immutable submitted-turn/replay
> identity. A retry cannot silently change the target or fall forward to a
> different revision.

The request carries only an identity target, never card/source Markdown. Buddy
re-resolves the exact World-owned Plan basis, validates that the identity
occurs exactly once with that kind in the committed source, and records the
resolved target with the turn's existing WorkObject/WorkRevision provenance.
The provider continues receiving the already-authorized server-resolved
committed Plan context. This design adds the selected identity as focus only;
it does not add a card excerpt, a second Plan context path, or a Graph payload.

Non-targeted Plan Ask remains unchanged. Selected-card Compose, Review, Apply,
and Save are a **serial successor**, not part of this slice. Existing
document-selection proposals remain unchanged.

## Current authority and evidence

This design is based on Buddy main
`5b1322d9719b4ee2bf64c28c2ee22ce071cee43f`. The DEMO roadmap at that exact
revision splits committed-card Ask from selected-card proposal/Apply. PR #909
merged at `79611f775c98eadc6695fda0314f057f71801eb2`; the saved Plan Cards view
is a read-only lens over the same editor draft and ordinary Save/reopen path.

Open PR #887 (`4b91c09d8a50188dfb1c9ce795358b32d17c02d7`) is prototype-only
under `prototypes/plan-play-cards/**`. It neither owns production Plan Agent
paths nor supplies production data/evidence for this contract. The remaining
open-PR inventory was checked at design time; recheck it before implementation
activation.

The current code leaves these seams separate:

- `apps/live-control-ui/src/planSurface/PlanSurfacePage.tsx` publishes
  `SurfaceInteractionPublication.agentContext: null`. Its
  `selectionGeneration` is incremented by Tiptap selection updates; it is not
  a selected Playable-element identity. `selectedCardViewIdentity` identifies
  the Cards view instance, not a selected card.
- `apps/live-control-ui/src/planSurface/components/WorldPlanCardProjection.tsx`
  builds marker-backed card nodes with `id` and `kind`, but renders them as a
  read-only projection without a selection callback. Its rendered body text is
  not a turn target or request payload.
- `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx`
  publishes ambient World/document context without card identity and posts
  `WorldPlanAgentTurnRequestV1` to `/api/live/agent/turn` with the existing
  managed World, Plan basis, `graph_request: {mode: "none"}`, and
  `graph_selection: null`.
- `apps/live-control-ui/src/tiptap/playable/playableElementIdentity.ts`
  defines the marker-backed `PlayableElementIdentity` (`kind`, `id`, marker
  version, and v2-only attributes). The target contract intentionally carries
  only the canonical `kind` and `id`; the server derives marker version and
  membership from the pinned source.
- `apps/live-control-ui/src/surfaceInteraction/types.ts` and
  `agentInteraction/agentSurfaceContextRequest.ts` define bounded generic
  `{kind, value}` pointers from the lease-guarded surface publication. That
  local publication is not the canonical World Plan Agent request. The
  separate generic Plan surface-context resolver rejects non-empty pointers;
  `tests/test_agent_surface_context.py::test_non_empty_plan_pointers_reject_surface`
  protects that boundary. Do not route this capability through
  `/api/live/query`, overload `graph_selection`, or change Graph pointer
  semantics.
- `apps/live_control_server/models/agent_turn.py::AgentTurnRequest` is strict
  (`extra="forbid"`) and has no Playable target field. The canonical request
  therefore needs an explicit typed extension; a UI-only generic pointer
  cannot affect server admission or the provider prompt.
- `apps/live_control_server/routes/agent.py::_work_resolver` resolves the
  selected World and the exact committed Plan, including object revision,
  WorkRevision ID, revision number, SHA-256, and divergent-working-copy state.
  `agent_turn_service.py::_plan_message` supplies the already-authorized
  server-resolved committed Plan Markdown and user question to the runtime.
  Preserve this current committed-content behavior. Do not send client card,
  source, or draft Markdown. The older merged
  `HANDOFF-DEMO-plan-agent-conversation.md` describes a metadata-only intent;
  the current implementation and the 5b roadmap correction are the execution
  authority for this design. This PR does not edit that historical handoff.
- `src/application_state/agent_conversation/types.py` has
  `SubmittedTurnIntentV1` and `TurnProvenance`. Submitted intent currently
  binds the Plan locator and expected content basis but has no Playable target;
  `TurnProvenance.selected_object` is the Graph-selection reference and must
  not be reused for a Plan element. The durable provenance and intent
  fingerprint need an APP-STATE-approved target reference.

Existing owning evidence includes:

- `apps/live-control-ui/src/planSurface/PlanSurfacePage.test.tsx`, especially
  “pins Ask to the exact committed World Plan revision and excludes editor
  text”;
- `apps/live-control-ui/src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx`
  for server conversation continuity and durable replay;
- `tests/test_agent_turn_route.py` and `tests/test_agent_turn_service.py` for
  exact committed Plan resolution, provider context, and graph-disabled turn
  behavior;
- `tests/application_state/test_agent_conversation_service.py`,
  `test_agent_conversation_postgres.py`, and
  `test_agent_conversation_provenance_migration.py` for APP-STATE intent,
  receipt, and fingerprint behavior;
- `apps/live-control-ui/src/planSurface/WorldPlanCardProjection.integration.test.tsx`
  for mounted Cards/Document/save/reopen behavior. It is not yet a card
  selection-to-Agent witness.

## Target and basis contract

The proposed canonical turn field is a nullable, versioned identity reference:

    selected_playable_target: null | {
      schema: "dmb_selected_playable_target_v1",
      kind: "scene" | "beat" | "choice" | "option",
      id: canonical kind-prefixed PlayableElementId
    }

The envelope is a contract version, not the marker grammar version. The server
derives whether the marker is v1 or v2 from the exact committed Plan. The
canonical ID grammar and equality rules are owned by
`playableElementIdentity.ts` plus the server-side committed-source validator:
`id` must be canonical, its prefix must match `kind`, and the exact pinned Plan
must contain one and only one identity with that pair. No title, body, source
span, excerpt, or Graph reference belongs in the target object.

The target is meaningful only alongside the request's existing primary-work
pin:

| Identity | Submitted expectation | Server-resolved receipt |
| --- | --- | --- |
| Managed World | `owner_scope.world_id` | verified canonical World ID |
| Plan WorkObject | `primary_work.object_id` | exact active World-owned Plan ID |
| Registry object revision | `primary_work.expected_revision` | actual object revision |
| WorkRevision content | `expected_revision_n` + content SHA-256 | actual WorkRevision ID + revision number + digest |
| Selected target | versioned `{kind, id}` only | validated target identity + exact `primary_work` basis |
| Turn/conversation | existing client thread and turn IDs | existing server-owned conversation and durable turn receipt |

`expected_revision` is the registry/object revision. It is not
`revision_n`, and neither is a substitute for the server-resolved WorkRevision
ID. The request keeps the current World Plan request shape and graph-disabled
semantics; this design does not use `loaded_revision` as content identity.

On a non-targeted turn, the target is absent/null and behavior is unchanged. On
a targeted turn, server admission resolves the same committed Plan basis as
today, then validates target membership against that exact source. A missing,
malformed, duplicate, wrong-kind, foreign, or absent target fails closed before
provider dispatch. A newer revision is never substituted for a stale expected
basis.

## Dirty editor behavior

The Cards lens reflects the mounted editor draft, while canonical Ask uses the
server-resolved committed Plan. The selected-target contract must not erase
that distinction:

- A dirty editor may still submit a target only when the UI can establish that
  the current selected `{kind, id}` corresponds to exactly one element in the
  committed revision being requested. The server independently verifies
  membership against that exact committed source.
- If a draft edits the body/title but preserves the same canonical target, Ask
  is still about the committed Plan. The visible result must disclose the
  committed WorkRevision used and that unsaved changes were not used.
- A draft-only/new target, a target deleted from the committed basis, a
  kind/ID mismatch, duplicate identity, uncertain saved basis, or inability to
  establish correspondence must not fall back to an adjacent card or the
  current latest revision. Do not send a targeted Ask; show a stale/unavailable
  target state instead.
- A response is immutably about the target submitted with its turn. Later UI
  selection changes do not rewrite the turn's target or server history. A
  later new turn captures a new target and current exact Plan basis.

The server's full existing committed Plan context remains authorized and
unchanged. The selected identity tells the runtime which existing element the
question focuses on; it does not authorize a new selected-card excerpt, source
read, or draft-content path.

## Replay and APP-STATE ownership

Current code has no existing safe binding for the target:

1. `AgentTurnRequest` has no selected Plan-element field.
2. `agent_turn_service._submitted_turn_intent()` constructs
   `SubmittedTurnIntentV1` from the message, surface, client work state,
   primary-work pin, graph request, and Graph selection only.
3. APP-STATE fingerprints the submitted intent and uses the World + turn ID
   idempotency key. Two otherwise-equal requests with different Playable
   targets are currently indistinguishable to that intent fingerprint.
4. `TurnProvenance.primary_work` stores the exact Plan basis, but
   `selected_object` represents Graph selection. There is no independent
   durable Plan-target reference for the completed transcript/replay receipt.

Therefore the slice requires APP-STATE to co-own a versioned logical
selected-Playable reference in both submitted intent and durable turn
provenance (or to identify an existing typed receipt that provides identical
semantics; current code evidence shows none). The target is bound to the
same-record `primary_work` WorkRevision. This does not prescribe a SQL column,
migration, or field name before APP-STATE approval.

Required semantics:

- The submitted-intent fingerprint includes a non-null selected target. Reuse
  of the same world/turn ID with a different target conflicts before provider
  dispatch.
- The durable receipt preserves the server-resolved target and exact primary
  WorkRevision for history display and completed replay. Do not overload the
  Graph-selected-object slot.
- A replay of the same turn, target, and original basis returns the original
  answer/receipt without provider redispatch or target re-resolution against a
  newer current revision. A distinct new turn resolves its own current pinned
  basis.
- APP-STATE decides storage shape, request/turn fingerprint compatibility, and
  any migration. In particular, adding nullable fields must preserve the
  repository's historical fingerprint compatibility behavior for turns with
  no selected target.

Until APP-STATE confirms this contract, implementation remains BLOCKED. A
request-only UI addition is not an acceptable substitute for durable replay
identity.

## Ownership and exclusions

- **DEMO UI** owns the explicit Cards selection affordance, deriving identity
  from the current marker-backed projection, clearing/fencing it on World,
  document, revision, and draft changes, and disclosing committed-basis
  behavior.
- **Buddy Agent/server** owns typed per-turn admission, canonical target
  validation against the exact server-resolved Plan, provider-context assembly,
  and fail-closed errors.
- **APP-STATE** owns the durable submitted-intent/provenance/replay contract and
  any storage/migration it requires. Approval is a pre-activation gate, not an
  implied schema change.
- **PRIME** owns cross-owner sequencing, re-anchor, path collision review, and
  explicit handoff activation.
- **WorldPlanEditBridge** remains the owner of mounted-editor proposal Apply,
  but it is not changed or invoked by this Ask slice.

This design does not authorize Graph retrieval, citation, source-anchor reads,
card/source Markdown in the request, new provider behavior, proposal targeting,
Review/Apply, Run/Play changes, marker mutation, credentials, or a new durable
card store. Graph-backed Plan Ask remains a separate blocked design with its
own APP-STATE receipt, managed-binding, and DungeonMind source-evidence gates.

## Named successor and design-review disposition

The named serial successor is selected-card Compose/Review/Apply. That later
slice must define exact v1/v2 Scene, Choice, and Option body-range mapping,
dirty-draft targeting, and `WorldPlanEditBridge` target fences. Ask-target
admission does not authorize or imply proposal target/Apply behavior. Existing
document-selection proposals remain unchanged.

This design is submitted for explicit DEMO/PRIME and APP-STATE review. The
companion implementation handoff is BLOCKED on APP-STATE's target receipt and
fingerprint approval, the server's committed-target membership rule, and the
dirty-draft correspondence rule. Acceptance of this design PR alone does not
activate code or allocate a write lease.
