# DEMO: Build Agent conversation adoption

## Status

**BLOCKED.** This handoff defines a bounded first Build Agent slice: truthful World, Build surface, active document, and committed-revision context for a conversational Agent turn. It grants no implementation lease, runtime authority, or write permission.

Steward: DEMO. Implementation owner: DungeonMindBuddy. Content-aware source retrieval is a separate future capability and is outside this handoff.

## Pinned baseline and topology

- Buddy main at design: `3608663a950cde7472ea942628170f083e533b14` (2026-10-02).
- At re-anchor, PR #836 (managed World → native Graph binding) and #839 (Plan source-bundle diagnostics) were open. PRIME owns their review and merge.
- PR #842 is the BLOCKED Play Agent adoption handoff. PRIME owns its activation and the serial slot decision.
- PR #781 only changes the shared Build projection-action helper and tests; it does not own the Build page or controller.
- Default topology is **serial**. Do not activate or dispatch this Build implementation while #836/#839 or the Play #842 slot decision is unresolved. At activation, fetch current main, inspect open PRs and leases, and confirm shared Agent and server-route ownership again.

## Current evidence

At the pinned main:

- `BuildSurfacePage` mounts `BuildSurfaceContext` and `BuildReferenceCapability`; it does not mount a conversational Ask plugin.
- `buildBuildSurfaceInteractionPublication` publishes graph-reference tools and document actions with `agentContext: null` for both active and empty publication paths.
- No Build surface file calls `usePublishAgentSurfaceContext`. The app mounts the shared `AgentInteractionChrome`, which renders only when an Ask plugin registers presence in `AskPluginSlot`.
- The shared Agent request model accepts surface `build` and primary-work kind `build`, but `apps/live_control_server/routes/agent.py` currently rejects every primary-work kind other than `plan`. Schema acceptance is not a Build resolver.
- Build metadata and draft state are available in the Build controller/editor. They are not proof of server-side World ownership or committed-revision authority.

These are source findings, not a live browser or provider witness.

## Bounded first-slice contract

1. Reuse the app-scoped `AgentInteractionChrome` and `AskPluginSlot`. Build contributes a Build-specific Ask plugin and current Build context; do not create a second chat shell or change the shared host without a new ownership review.
2. Offer this path only when the current selection is a managed World and the active Build document is eligible. World scope comes from the managed World selection. A legacy Build campaign ID or display label must never be promoted, translated, or guessed as a World ID.
3. The turn context may contain only the verified World identity, surface identity (`build`), active document identity/title, the exact current committed object revision, and whether unsaved edits exist. The user’s question is sent as the message. Set `graph_request` to `none`.
4. Do not send Markdown, source excerpts, browser/editor draft bytes, graph payloads, or other document content in this slice. UI and prompt wording must say that the Agent has not read the document; for a dirty document, say that draft edits are excluded. Show the identity/revision disclosure before dispatch.
5. Bind the conversation and each response to the verified World + Build document + committed revision. A document or revision change invalidates the pending turn and any incompatible saved thread continuity. Never display a late response under a different document.
6. If managed World ownership, active document identity, or committed revision cannot be verified, disable or fail the turn before provider dispatch. Do not fall back to campaign scope, Graph context, Plan resolution, or client-provided content.

## Required server admission

The client’s World/document locators and expected revision are claims to check, not authority. Before model dispatch, Buddy must independently resolve the selected managed World and the active Build document through an owning server-side authority, prove that the document belongs to that World, load its current committed revision, and compare it with the expected revision. The response and trace must report the resolved identity/revision.

A mismatch, foreign or missing document, legacy-only selection, unresolved World mapping, or unavailable revision must fail closed with no provider call. Use the native Build revision identity; do not synthesize a revision from a title, campaign label, draft hash, or client state. If Buddy has no server authority that can prove World-to-Build-document ownership and the committed revision, stop before dispatch and return to the relevant work-authority owner for a contract. Do not add source reading to solve this gap. Confirm the existing request authentication/selection boundary during activation; this slice does not create a new authentication system.

## Verification required at activation

The future ACTIVE handoff must pin an exact base/head, enumerate an exclusive expected-path allowlist, name the verification environment and PR topology, and include mutable authority documents that need a truthful sync after #836 settles. Candidate file boundaries below are investigative hints only; they are not a lease.

At minimum, verify at the owning boundaries:

- A mounted Build + shared Agent host test proves Ask presence and context for an eligible managed World/document, plus unavailable behavior for empty, loading, error, legacy, foreign, or unresolved documents.
- The captured client request contains the honest World/Build/document/revision identity, the question, the accurate dirty-state flag, and `graph_request: none`; it contains no Markdown or draft bytes.
- Backend tests prove exact World/document/revision resolution and reject missing, foreign, stale, or unsupported identity before runtime/provider dispatch. An accepted mocked turn reports the server-resolved context and sends no source body.
- A document/revision switch while a turn is pending cannot display the old answer or continue an incompatible thread under the new identity.
- Review the cumulative base-to-head diff and run the relevant Build UI, Agent-turn route/service, and type checks. Record inherited failures separately. A live managed-World witness is still required before product acceptance; tests alone do not claim it.

Candidate implementation boundaries to recheck after re-anchoring:

- Build page/context/publication, a Build Ask plugin, and mounted Build/Agent tests under `apps/live-control-ui/src/buildSurface`.
- The existing Agent turn resolver/route and its owning tests under `apps/live_control_server`.
- Add or change shared Agent/API paths only if the design review proves they are needed and their leases are clear.

## Explicit exclusions

No source-aware Q&A, committed Markdown read, content disclosure contract, truncation or budgeting policy, Graph query, graph citations, ingestion/admission, draft bytes, Plan behavior, campaign-to-World mapping, shared chat-shell redesign, authentication-system change, provider call, database/runtime action, or implementation PR is authorized by this BLOCKED handoff.

If source-aware Q&A is later requested, it needs a separate Content/APP-STATE-owned committed-read contract and a new handoff. Do not add it to the identity-only Build slice.
