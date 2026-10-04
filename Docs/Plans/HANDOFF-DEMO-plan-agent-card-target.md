---
title: Managed-World Plan Agent committed Playable-card Ask target
document_class: implementation_handoff
status: BLOCKED
created_at: "2026-10-04"
workstream: DEMO
design_authority: "../Design/DESIGN-world-plan-agent-playable-target.md"
design_base: "Buddy main 5b1322d9719b4ee2bf64c28c2ee22ce071cee43f"
pr_topology: serial
implementation_branch: not_assigned
implementation_pr: not_authorized
---

# HANDOFF — Ask about one committed Playable card in a World Plan

> This is durable design authority only. It is BLOCKED and holds no
> implementation write lease.

## Status and activation gate

**Status: BLOCKED.** This handoff is proposed with the companion design at
Buddy main `5b1322d9719b4ee2bf64c28c2ee22ce071cee43f`. No implementation lane,
branch, PR, or schema change is authorized.

Activation requires all of the following to be recorded by PRIME after
re-anchoring:

1. The companion design is accepted at its exact reviewed head. That acceptance
   confirms the first capability is committed-card Ask only; Compose/Review/
   Apply remain a serial successor.
2. APP-STATE approves how the selected Playable reference enters
   `SubmittedTurnIntentV1` and durable `TurnProvenance` (or demonstrates an
   existing typed receipt with equivalent semantics). The decision must cover
   intent fingerprints, durable history/replay identity, compatibility for
   no-target turns, and any storage/migration paths. Current `selected_object`
   is Graph selection and may not be reused. No schema change is authorized by
   this handoff while the owner decision is pending.
3. Buddy's Agent/server owner approves the typed request field/version and the
   exact committed-Plan membership resolver. The request carries only
   `{kind, id}` plus the target-envelope schema version; the server selects
   v1/v2 marker parsing from the exact pinned WorkRevision. Client-supplied
   marker grammar versions or unknown envelope versions are rejected. The
   owner also approves duplicate, malformed, dangling, and wrong-kind
   membership behavior and proves validation does not invoke Run
   admission/readiness or mutate Run behavior.
4. DEMO accepts the mounted Cards selection affordance and the dirty-editor
   behavior: same `{kind, id}` means Ask against the pinned committed Plan with
   explicit disclosure; draft-only, missing, changed-kind, ambiguous, or
   otherwise unprovable target/basis fails closed.
5. PRIME fetches current `main`, inspects open PRs and active leases again,
   records the final Buddy and APP-STATE path owners, and confirms the complete
   future path allowlist and runtime/state ownership. PR #887 was prototype-only
   at the design snapshot and is not a production dependency; its status still
   must be rechecked.
6. The future implementation PR is explicitly authorized as one serial DEMO
   PR after this handoff becomes ACTIVE. No APP-STATE migration or additional
   successor PR is implied.

If any answer changes the one-turn invariant or needs proposal/Apply behavior,
stop and re-review the design. Do not activate by metadata-only edits while a
contract owner or path is unresolved.

## §1 Mission and merge-ready invariant

Add one committed Playable-card target to the canonical managed-World Plan Ask
without replacing the current server-owned World conversation, changing the
existing committed Plan provider context, or enabling Graph.

For every accepted targeted turn, Buddy must validate exactly one canonical
Playable `{kind, id}` against the same exact server-resolved committed Plan
WorkRevision the Ask uses. The selected identity, exact primary-work basis,
and existing turn/conversation identity must form one immutable submitted
intent and durable receipt. Same-turn retries with a different target conflict;
same-target replay returns the original receipt/answer without provider
redispatch or silent re-resolution against a newer Plan revision.

Non-targeted Plan Ask remains unchanged. The feature must fail closed rather
than substitute a card, document, World, or revision.

## §2 Design authority and owning boundaries

Re-read after activation:

1. `Docs/Design/DESIGN-world-plan-agent-playable-target.md`.
2. `Docs/Roadmaps/ROADMAP-demo.md` at the current re-anchored main; the
   design-time sequencing decision is Ask first, selected-card proposal/Apply
   serially later.
3. `apps/live-control-ui/src/tiptap/playable/playableElementIdentity.ts` and
   the current mounted Plan Cards projection.
4. `apps/live-control-ui/src/api/types.ts::WorldPlanAgentTurnRequestV1` and
   `apps/live_control_server/models/agent_turn.py::AgentTurnRequest`.
5. `apps/live_control_server/routes/agent.py::_work_resolver` and
   `apps/live_control_server/services/agent_turn_service.py`, including
   `_submitted_turn_intent`, `_conversation_provenance`, and `_plan_message`.
6. APP-STATE's approved `SubmittedTurnIntentV1` / `TurnProvenance` contract,
   current `request_fingerprint` compatibility rules, and exact turn replay
   behavior. These are an activation dependency, not a design assumption.

Design-time facts at main `5b1322d9719b4ee2bf64c28c2ee22ce071cee43f`:

- Buddy PR #909 merged at
  `79611f775c98eadc6695fda0314f057f71801eb2`. The Cards view projects the same
  mounted document/draft and ordinary Save path. Its element `id`/`kind` are
  available for a selection affordance, but the projection currently does not
  publish a selected Playable target.
- `PlanSurfacePage.tsx` publishes `agentContext: null`; its
  `selectionGeneration` measures Tiptap selection updates, not card identity.
  The separate ambient World Plan context in
  `WorldPlanAgentConversation.tsx` does not contain the selected element.
- `WorldPlanAgentTurnRequestV1` has no selected target; strict server
  `AgentTurnRequest` rejects unknown fields. The generic bounded
  `AgentSurfaceContextRequestV1` pointer belongs to a different path, and
  `tests/test_agent_surface_context.py::test_non_empty_plan_pointers_reject_surface`
  proves non-empty Plan pointers are rejected there. Do not treat a local
  publication pointer as a server contract.
- Current canonical Plan Ask resolves the exact managed-World committed Plan
  and supplies its server-resolved Markdown through `_plan_message`. Preserve
  that authorized committed Plan context. The new request carries no client
  card/source/draft bytes and no additional card excerpt. The target identity
  is focus metadata, not a citation or Graph reference.
- `SubmittedTurnIntentV1` currently binds the Plan kind/document/object
  revision/expected `revision_n`/content SHA but not target identity.
  `TurnProvenance.primary_work` contains the server-resolved WorkRevision ID,
  `revision_n`, and SHA; `selected_object` is Graph selection. A request-only
  target cannot make a different-target retry conflict or identify the target
  in durable history.
- The existing Play Run parser in
  `apps/live_control_server/services/play_run_reference_manifest.py` is useful
  marker-grammar evidence but belongs to Run reference admission. Reuse it only
  if target membership can be derived without importing Run creation/readiness
  semantics; otherwise stop and return the parser seam to PRIME. Do not change
  Run admission for this Ask capability.
- Open PR #887 was `DOGFOOD: prototype connected Plan and Play cards`, head
  `4b91c09d8a50188dfb1c9ce795358b32d17c02d7`, with changed paths only under
  `prototypes/plan-play-cards/**`. It is prototype evidence, not a runtime
  dependency or production source. Recheck its live state and all leases before
  activation.

Owner boundaries:

- **DEMO UI** owns card selection, local selection clearing/fencing, and clear
  committed-basis disclosure.
- **Buddy Agent/server** owns request admission, exact target membership
  validation, and server-side committed context assembly.
- **APP-STATE** owns durable submitted intent, receipt/history, and idempotent
  replay identity for the target. It approves its path/schema changes.
- **PRIME** owns design acceptance, activation, path/PR arbitration, and
  cross-owner sequencing.
- **WorldPlanEditBridge** owns proposal Apply but is explicitly outside this
  Ask slice.

## §3 Observable contract and required evidence

| Sequence | Required result |
| --- | --- |
| Clean Plan; user selects one canonical card in the mounted Cards view | The UI publishes only the versioned `{kind, id}` identity and captures the existing World/document/editor/request fences. It does not use `selectedCardViewIdentity` or Tiptap `selectionGeneration` as the Playable identity. |
| Targeted Ask submitted | Canonical `/api/live/agent/turn` request retains existing World owner, Plan object revision, expected WorkRevision `revision_n` and content SHA, client thread/turn identity, `graph_request=none`, and `graph_selection=null`, with one typed target and no client source bytes. |
| Server admission | Server independently resolves the exact current committed World Plan and actual WorkRevision ID, validates one matching canonical target in that same source, and only then forms the runtime request with existing committed Plan content and the normalized target focus. No Graph resolver runs. |
| Same-ID body/title changed in a dirty editor; target kind/ID still exactly matches committed basis | Ask may proceed only with explicit UI disclosure that the answer uses the committed revision, not unsaved edits. The durable result reports that actual basis. |
| New/draft-only target, target absent from pinned committed basis, duplicate/malformed marker, wrong kind, stale basis, or UI cannot prove correspondence | Fail closed before provider dispatch; visible unavailable/stale-target state; never fall forward, use another card, or treat the request as an un-targeted success. |
| Retry same World/turn ID, exact target and exact submitted Plan basis | Return the original completed receipt and answer; do not call the provider again or re-resolve a newer current target/basis. |
| Retry same World/turn ID and same other fields but changed target | Durable idempotency conflict before provider dispatch. The target must participate in submitted-intent fingerprint and resolved provenance/replay identity. |
| Ordinary un-targeted Plan Ask | Existing request, committed context, conversation identity, and behavior remain unchanged. |
| Any targeted Plan Ask | Graph stays `none`, Graph selection stays null, no Graph retrieval/citation/auth path is invoked, and no Graph write occurs. |

Required owning-boundary proof after activation:

- A mounted `PlanSurfacePage` / `WorldPlanCardProjection` /
  `WorldPlanAgentConversation` test selects a real v1 and v2 card identity and
  proves that exact identity and current Plan basis reach the typed turn
  request while no card/source Markdown is in the request.
- Buddy server tests prove exact membership against the committed
  `get_current_world_plan_revision` result; v1/v2 canonical grammar is selected
  from that pinned source; wrong kind, duplicate, absent, draft-only,
  malformed, dangling, stale, foreign, and unmatched identities fail before
  runtime dispatch. Unknown envelope versions and client-supplied marker
  grammar versions are rejected rather than ignored. Existing committed Plan
  context is preserved; Graph resolution is not called.
- APP-STATE tests prove the target participates in submitted-intent matching,
  persists as non-Graph provenance tied to exact primary WorkRevision, rejects
  same-key/different-target replay, replays exact target/answer without
  provider dispatch, and preserves the historic no-target fingerprint.
- UI tests prove target state clears/fails closed on World/document/revision
  replacement, Card projection basis loss, target deletion/type change, and
  selection invalidation; a dirty matching target is labeled as committed
  basis, never draft grounding.
- Existing no-target Ask, conversation continuity/history, and current
  document-selection proposal suites still pass. These tests do not prove
  selected-card Compose/Review/Apply; that belongs to the serial successor.

## §4 Candidate implementation paths — not a write lease

This BLOCKED handoff reserves no paths. The following is the candidate Buddy
write set to revalidate and finalize at activation:

**Buddy UI and public request**

- `apps/live-control-ui/src/planSurface/PlanSurfacePage.tsx`
- `apps/live-control-ui/src/planSurface/components/WorldPlanCardProjection.tsx`
- `apps/live-control-ui/src/planSurface/components/WorldPlanCardProjection.css`
- `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx`
- `apps/live-control-ui/src/api/types.ts`
- `apps/live-control-ui/src/planSurface/PlanSurfacePage.test.tsx`
- `apps/live-control-ui/src/planSurface/WorldPlanCardProjection.integration.test.tsx`
- `apps/live-control-ui/src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx`
- `apps/live-control-ui/src/api/liveApi.test.ts`

**Buddy server request and target admission**

- `apps/live_control_server/models/agent_turn.py`
- `apps/live_control_server/routes/agent.py`
- `apps/live_control_server/services/agent_turn_service.py`
- new `apps/live_control_server/services/agent_plan_playable_target.py` only if
  the accepted parser seam needs an identity-only resolver separate from Run
  admission;
- `tests/test_agent_turn_route.py`
- `tests/test_agent_turn_service.py`
- new `tests/test_agent_plan_playable_target.py` only if the new resolver file
  is needed.

**APP-STATE paths — conditional and unapproved**

The following paths may be required only after APP-STATE names and approves the
storage contract; none is currently leased:

- `src/application_state/agent_conversation/types.py`
- `src/application_state/agent_conversation/service.py`
- `src/application_state/agent_conversation/repository.py`
- `tests/application_state/test_agent_conversation_service.py`
- `tests/application_state/test_agent_conversation_postgres.py`
- `tests/application_state/test_agent_conversation_provenance_migration.py`
- any migration path explicitly named by APP-STATE before activation.

If APP-STATE requires additional paths, a different schema version, a separate
co-owned PR, or a changed identity model, stop and return to PRIME. Do not
implement from this candidate list as if it were an active lease.

## §5 Explicit exclusions

- No selected-card Compose, proposal generation, Review, Apply, `WorldPlanEditBridge`
  changes, or ordinary Save/reopen proof in this first slice.
- No change to existing document-selection proposal behavior.
- No Graph retrieval, selected Graph node, citation, source-anchor read,
  DungeonMind binding, or Graph write.
- No client card/source/draft Markdown, excerpt, title, or body text added to
  the selected-target field or request. Preserve the current server-resolved
  committed Plan context only.
- No Run/Playable admission or readiness change, Run schema, database change,
  marker authoring or mutation, GenerationEngine/provider behavior, credentials,
  dependency, lockfile, or prototype import.
- No generic `/api/live/query` pointer route, `AgentSurfaceContextRequestV1`
  widening, or reuse of Graph `graph_selection`/`selected_object` for a Plan
  element.
- No branch, implementation PR, or active write lease while this handoff is
  BLOCKED.

## §6 Topology and runtime/state ownership

**PR topology: serial.** Once ACTIVE, this handoff may authorize exactly one
implementation PR: `DEMO: selected committed-card Ask target`. No proposal,
Apply, Graph, or cleanup PR is authorized here. The selected-card
Compose/Review/Apply successor waits until this Ask slice merges, its state
sync completes, and PRIME re-anchors.

The future implementation should use deterministic provider/runtime fakes.
Do not use or restart the operator UI/API sessions, #887 prototype, external
provider credentials, or a shared live conversation. APP-STATE database tests
must use the repository's isolated test DSN and approved APP-STATE-owned
fixtures. No live provider acceptance is claimed by this slice.

## §7 Verification plan after activation

Run the focused owning-boundary suites independently and report each result by
provenance (author-local, independently rerun, CI):

1. Buddy server: `uv run pytest tests/test_agent_plan_playable_target.py tests/test_agent_turn_service.py tests/test_agent_turn_route.py tests/test_agent_surface_context.py`
2. APP-STATE: `uv run pytest tests/application_state/test_agent_conversation_service.py tests/application_state/test_agent_conversation_postgres.py tests/application_state/test_agent_conversation_provenance_migration.py`
3. Mounted UI: `npm --prefix apps/live-control-ui run test -- src/planSurface/PlanSurfacePage.test.tsx src/planSurface/WorldPlanCardProjection.integration.test.tsx src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx src/api/liveApi.test.ts`
4. UI typecheck: `npm --prefix apps/live-control-ui run typecheck`
5. Inspect the complete base-to-head diff against the re-anchored main and verify the changed-path set against the final ACTIVE §4 lease.

At design time, the current roadmap records an existing UI typecheck diagnostic
in `ThreatPublicationPanel.tsx` (`TS2503: Cannot find namespace JSX`). Compare
base/head if it remains; do not rename an inherited failure as a regression or
a pass. Do not use live credentials, external providers, or operator runtimes
to satisfy this deterministic acceptance contract.

## §8 State-authority sync set after merge

The future implementation PR's backward-looking sync set is:

- this handoff: record exact implementation PR/head/merge SHA, review-cycle
  count, accepted APP-STATE contract, and mark the current Ask capability
  merged;
- `Docs/Roadmaps/ROADMAP-demo.md`: record committed-card Ask completion and
  keep selected-card Compose/Review/Apply as a serial successor, not completed
  or automatically active;
- the accepted APP-STATE contract/reference, only if its owner publishes or
  changes one as part of the approved co-owned receipt work.

The design document is stable authority and changes only if the accepted
contract changes. No routine documentation-only PR is authorized for this
future status sync; attach it to the next dependent implementation PR or use a
guarded steward sync after re-anchoring if no successor exists.

## §9 Acceptance rubric and stop conditions

The implementation is merge-ready only when all are true:

- UI selection is derived from a current marker-backed card, not the Cards view
  identity or a generic Tiptap selection-generation counter.
- The canonical request uses an explicit versioned selected-Playable reference
  and exact existing World/Plan pins. The server resolves actual WorkRevision
  ID, `revision_n`, and digest; registry `loaded_revision` is never substituted.
- Server target membership is unique, canonical, kind-matching, and checked
  using the marker grammar of the exact committed Plan basis used for Ask. The
  target does not claim marker grammar version; unknown target-schema versions
  and extra version fields fail closed. Validation does not change Run
  admission or silently use draft text.
- Dirty-basis behavior is visible and truthful; draft-only, deleted from the
  committed basis, mismatched-kind, duplicate, stale, unknown, or unresolved
  target states fail closed before runtime dispatch.
- Same-key/different-target replay conflicts; same-key/same-target replay
  returns the immutable original target and basis without provider redispatch.
  APP-STATE has approved the storage/fingerprint compatibility contract.
- The same server-owned World conversation identity and existing committed
  Plan provider context remain intact. Graph stays off and no new source bytes
  cross the request boundary.
- Existing non-targeted Plan Ask and document-selection proposals remain
  unchanged; the selected-card proposal successor is named, not implemented.

Stop and return to PRIME before editing if the work needs a Graph read, a new
source-text contract, proposal/Apply targeting, a Run/parser behavior change,
an unapproved APP-STATE path/schema, or any path outside the finalized ACTIVE
lease. The handoff remains BLOCKED until every activation gate is satisfied.
