# DEMO: Build Agent conversation adoption

## Status

**BLOCKED.** This handoff defines a bounded first Build Agent slice: truthful World, Build surface, active document, and committed-revision context for a conversational Agent turn. It grants no implementation lease, runtime authority, or write permission.

Steward: DEMO. Implementation owner: DungeonMindBuddy. Content-aware source retrieval is a separate future capability and is outside this handoff.

## Pinned baseline and topology

- Re-anchored to Buddy main `61f76f567bce672bf88248bd17e5bb44feb77ba2` (2026-10-02).
- PR #836 merged at `6de8d831ab82308086677fb3038122936ab9a756`; PR #839 merged at `47f9955fd054017a1739dfa8129df65dd61d6bcd`; PR #842 merged at `672d18b059eaeceff20555374170ec2679f79082`. Those gates are settled.
- PR #781 covers the shared Build projection-action helper and tests only; it does not own the Build page or controller.
- The current serial prerequisites ahead of later surface adoption are recovery → AGENT-INTERACTION runtime acceptance (#865) → Plan action projection (#859) → Plan conversation consumer (#857) → the Elderwyld Plan Graph usefulness path. Play follows that path. PRIME retains sequencing authority among later Play, Build, and Ingest adoption; this handoff assigns Build no slot.
- Build remains **BLOCKED** pending the Buddy exact-document/committed-registry-revision state-sync/admission implementation and a separate exact Build resolver/request lease. No Build implementation, provider, database, or runtime lease is active. At any future activation, re-anchor main, inspect open PRs and leases, and confirm shared Agent and server-route ownership.

## Current evidence

At the pinned main:

- `BuildSurfacePage` mounts `BuildSurfaceContext` and `BuildReferenceCapability`; it does not mount a conversational Ask plugin.
- `buildBuildSurfaceInteractionPublication` publishes graph-reference tools and document actions with `agentContext: null` for both active and empty publication paths.
- No Build surface file calls `usePublishAgentSurfaceContext`. The app mounts the shared `AgentInteractionChrome`, which renders only when an Ask plugin registers presence in `AskPluginSlot`.
- The shared Agent request model accepts surface `build` and primary-work kind `build`, but `apps/live_control_server/routes/agent.py` currently rejects every primary-work kind other than `plan`. Schema acceptance is not a Build resolver.
- The older `/api/live/query` SurfaceContext V1 is campaign/document/session-shaped and its resolver does not accept Build; it is not a fallback conversation path. Use the shared `/api/live/agent/turn` contract with explicit World owner scope and a server-verified Build resolver.
- The current `usePublishAgentSurfaceContext` compatibility helper fills a missing campaign ID with the surface ID (so Build could become campaign `build`), and the shared ambient/thread scope is campaign-shaped. A managed-World Build publisher must avoid that fallback; any browser-local thread namespace must remain separate from the wire owner and carry an explicit World owner identity.
- The roadmap and Architecture ruling require the exact admitted Build document and current committed registry revision; campaign/World ID equality does not prove ownership. The server must derive owner scope from the admitted workspace record.
- The UI API currently exposes Index and World Plan turn wrappers only; the future Build path needs a typed client wrapper after the server resolver is accepted.
- Build metadata and draft state are available in the Build controller/editor. They are not proof of server-side World ownership or committed-revision authority.

These are source findings, not a live browser or provider witness.

## Bounded first-slice contract

1. Reuse the app-scoped `AgentInteractionChrome` and `AskPluginSlot`. Build contributes a Build-specific Ask plugin and current Build context; do not create a second chat shell or change the shared host without a new ownership review.
2. Offer this path only when the current selection is a managed World and the active Build document is eligible. World scope comes from the managed World selection. A legacy Build campaign ID or display label must never be promoted, translated, or guessed as a World ID.
3. The turn context may contain only the verified World identity, surface identity (`build`), active document identity/title, the exact current committed object revision, and whether unsaved edits exist. The user’s question is sent as the message. Set `graph_request` to `none`.
4. Do not send Markdown, source excerpts, browser/editor draft bytes, graph payloads, or other document content in this slice. UI and prompt wording must say that the Agent has not read the document; for a dirty document, say that draft edits are excluded. Show the identity/revision disclosure before dispatch.
5. Keep the visible conversation identity World-scoped. Record the verified Build document and committed revision as each turn’s historical basis, and scope provider continuation to that basis. A document or revision change starts a fresh provider segment; it does not replace the World conversation or invalidate the durable turn. Bind completion to its originating turn and frozen basis, so a late result remains in World history under the original document/revision and is never presented as an answer for the newly selected document.
6. If managed World ownership, active document identity, or committed revision cannot be verified, disable or fail the turn before provider dispatch. Do not fall back to campaign scope, Graph context, Plan resolution, or client-provided content.

## Required server admission

The Build surface/document editor supplies explicit `document_id` and expected committed registry revision as locators to validate; the server must not infer a unique document from the World. Before model dispatch, Buddy resolves the admitted workspace record, verifies its World association and current committed registry revision, and derives owner scope only from that authoritative record. The response and trace report the server-resolved document and revision.

A missing, foreign, stale, ambiguous, legacy-only, or unavailable document/revision fails closed with no provider call. Never synthesize revision identity from a title, campaign label, draft hash, or client state. This accepted owner boundary requires no new cross-repository contract; the remaining gate is implementation of Buddy's exact-document/revision state-sync and admission path, followed by its separately leased Build resolver/request work. Do not add source reading to solve this gap. Confirm the existing request authentication/selection boundary during activation; this slice does not create a new authentication system.

## Verification required at activation

The future ACTIVE handoff must pin an exact base/head, enumerate an exclusive expected-path allowlist, name the verification environment and PR topology, and identify any mutable authority documents needing synchronization after the state-sync/admission prerequisite settles. Candidate file boundaries below are investigative hints only; they are not a lease.

At minimum, verify at the owning boundaries:

- A mounted Build + shared Agent host test proves Ask presence and context for an eligible managed World/document, plus unavailable behavior for empty, loading, error, legacy, foreign, or unresolved documents.
- The captured client request contains the honest World/Build/document/revision identity, the question, the accurate dirty-state flag, and `graph_request: none`; it contains no Markdown or draft bytes.
- Backend tests prove exact World/document/revision resolution and reject missing, foreign, stale, or unsupported identity before runtime/provider dispatch. An accepted mocked turn reports the server-resolved context and sends no source body.
- Owning-boundary switch witness: submit a Build turn for document A/revision 1, switch to document B/revision 2 while A is pending, then complete A. Prove A remains on its originating durable turn in the same World history with A/revision 1 provenance, is never presented as B’s answer, and B starts a fresh provider segment without A’s hidden provider context.
- Review the cumulative base-to-head diff and run the relevant Build UI, Agent-turn route/service, and type checks. Record inherited failures separately. A live managed-World witness is still required before product acceptance; tests alone do not claim it.

Candidate implementation boundaries to recheck after re-anchoring:

- Build page/context/publication, a Build Ask plugin, and mounted Build/Agent tests under `apps/live-control-ui/src/buildSurface`.
- The existing Agent turn resolver/route and its owning tests under `apps/live_control_server`.
- Add or change shared Agent/API paths only if the design review proves they are needed and their leases are clear.

## Explicit exclusions

No source-aware Q&A, committed Markdown read, content disclosure contract, truncation or budgeting policy, Graph query, graph citations, ingestion/admission, draft bytes, Plan behavior, campaign-to-World mapping, shared chat-shell redesign, authentication-system change, provider call, database/runtime action, or implementation PR is authorized by this BLOCKED handoff.

If source-aware Q&A is later requested, it needs a separate Content/APP-STATE-owned committed-read contract and a new handoff. Do not add it to the identity-only Build slice.
