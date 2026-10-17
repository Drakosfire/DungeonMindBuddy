# Agent — Compose into the saved Build page

IMPLEMENTATION MERGED — Buddy#1288 atbabdf1fe78cde23f5954414a675e487a606f0a03; exact-head ARCHITECTURE review passed. UI/editor/persistence capability is implemented, but it is not yet deployed. The operator then required guarded strict schema adoption before rollout; HANDOFF-AGENT-build-strict-schema.md now owns the consumer/runtime successor. Original bounded contract follows.

Explicit operator dogfood priority: ask for NPCs/jobs and put a table on the page. PRIME implements solo; ARCHITECTURE independently reviews; DOGFOOD remains on Ingest. Base origin/main@119043228c60142e670bbad61d2cd73ed96426ba. Branch codex/build-compose-insertion, /tmp/prime-recap-mention-boundaries. Parallel-independent of DOGFOOD's managed-run projection; no unmerged dependency. #1285 selected-source inclusion is merged at210c174f; #1286 evidence-read auth is merged at11904322 and deployed. Do not wait on source-navigation or automatic Jev acquisition before delivering creative Compose.

## Complete user outcome

On a saved Build worldbuilding document: ask “Create six NPCs for Edge, with jobs and a distinguishing detail, and add them as a table.” Generate one inert Markdown/table proposal, show it inline in the same World conversation, insert into the exact mounted editor after review, manually edit, explicitly Save and reopen. Existing Ask remains Graph-backed conversation. Creative proposals are proposed authored lore, not retrieved facts or admitted Graph identities. No automatic Save or publication, cross-document routing, unsaved-document creation, selection replacement or whole-document rewrite in this first slice.

## Owner contract (ARCHITECTURE reviewed before activation)

- Expose an explicit typed Build Compose capability/bridge beside Ask through the shared conversation publication. Route conversational write intent to Compose without adding another competing writing field. Do not reuse PlanActionBasis with fake Plan UUIDs/revisions/consultation. Plan historical models and serialized data stay unchanged.
- A narrow APP-owned Build proposal reservation/result store carries the genuine managed World, conversation, workspace document ID/registry revision/content hash, draft hash, caret and draft/selection generations, idempotency key/fingerprint and provider lifecycle. Use existing unit-of-work/fencing patterns, not a new provider framework. Concurrent/repeated/uncertain requests cannot cause unacknowledged provider replay. List/reopen receipts in their exact World conversation; capture their position relative to existing turns rather than inventing Plan actions.
- Verify active World/source ownership, source kind worldbuilding_source, committed revision/hash and frozen visibility before generating. Current draft is operator-provided source data, not admitted Graph or higher-priority instructions. Model returns inert Markdown and assumptions, never target IDs or write authority. Use the existing configured OpenAI GPT-6 Luna route and protected GenerationEngine prepared-text dispatch/lifecycle; one tool-free generation, no automatic retry/fallback. Standing worldbuilding/model approvals apply. No fixed authorization cap is introduced.
- Freeze the editor instance, managed World/document, committed revision/hash, draft/selection generation and insertion position. Only insert at a captured caret; reject a nonempty selection clearly. Host validates supported Markdown/table import/export and simulated insertion, preserving surrounding content and protected existing identities. Reuse/extract surface-neutral editor helpers where applicable; no Plan authority impersonation.
- Review/insert uses the current bridge and exact frozen editor/draft binding. Navigation, draft edits, moved caret, save/base drift, stale response, duplicate Apply and action ambiguity cannot overwrite another document. Apply is one editor transaction and means unsaved draft insertion, not durable Save. Existing MarkdownCanvasSession Save/CAS owns persistence.
- Preserve the operator's full-prompt inspection requirement for the new Compose call: private exact prepared-envelope capture before dispatch when enabled; metadata tied to this Build proposal's durable provider authorization; authenticated exact proposal/prompt read; reusable component/full-request inspector without fabricating an APP Graph trace. Credentials/headers stay outside capture. Ordinary history remains body-free apart from the deliberate proposal result. Reuse agent_prompt_evidence storage.

## Exclusive expected writes

- this handoff
- Docs/Plans/HANDOFF-AGENT-evidence-read-auth.md (truthful predecessor settlement only)
- Docs/Roadmaps/ROADMAP-demo.md (current Build Compose acceptance/gates only)
- src/application_state/build_proposal/__init__.py (new)
- src/application_state/build_proposal/types.py (new)
- src/application_state/build_proposal/service.py (new)
- src/application_state/migrations/versions/20261016_0026_build_proposals.py (new additive store)
- apps/live_control_server/models/build_document_proposal.py (new)
- apps/live_control_server/services/build_document_proposal.py (new)
- apps/live_control_server/routes/agent.py (Build proposal/create/status/list/prompt routes only)
- apps/live-control-ui/src/api/buildDocumentProposalApi.ts (new; own types/transport wrapper)
- apps/live-control-ui/src/api/liveApi.evidenceReads.test.ts (Build proposal endpoint transport cases only; predecessor lease settled)
- apps/live-control-ui/src/api/liveApi.ts (requiresNativeGraphAuthorization/canRetryLocalSessionRequest only; explicit function-level split from DOGFOOD's getHistoricalRecapWorldProjection)
- apps/live-control-ui/src/documentEditing/markdownInsertion.ts (new shared pure insertion/admission helpers)
- apps/live-control-ui/src/documentEditing/markdownInsertion.test.ts (new)
- apps/live-control-ui/src/planSurface/agentEdit/planAgentEditProposal.ts and .test.ts (only necessary pure helper extraction/reuse, no Plan contract change)
- apps/live-control-ui/src/buildSurface/buildComposeBridge.ts (new)
- apps/live-control-ui/src/buildSurface/BuildSurfaceShell.tsx (publish Compose bridge)
- apps/live-control-ui/src/buildSurface/BuildSurfaceShell.test.tsx
- apps/live-control-ui/src/agentInteraction/WorldAgentConversation.tsx (typed Build capability)
- apps/live-control-ui/src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx (mock the new independent proposal-list read; existing invariants unchanged)
- apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx and .css (Build intent routing/inline receipts only)
- apps/live-control-ui/src/planSurface/components/BuildComposeProposal.tsx and .test.tsx (new)
- apps/live-control-ui/src/planSurface/components/BuildComposeProposal.css (new)
- apps/live-control-ui/src/planSurface/components/PreparedRequestInspector.tsx (new reusable body renderer)
- apps/live-control-ui/src/planSurface/components/BuddyPromptInspector.tsx and .test.tsx (pure viewer extraction preserving existing behavior)
- tests/application_state/test_build_proposal_postgres.py (new)
- tests/test_build_document_proposal.py (new owning route/service/SDK tests)
- apps/live-control-ui/src/buildSurface/BuildCompose.integration.test.tsx (new mounted insertion/Save/reopen)

No IngestionModule/historical projection/types.ts/global Build campaign map, Graph knowledge mutation, dependency upgrades or runtime model change. Batch concrete extra-path needs once before editing. GenerationEngine/Core stay pinned and unchanged.

## Verification, evidence and deployment

Use synthetic source and mock SDK/HTTP plus disposable APP54329 first. Cover typed ownership/hash, idempotency/concurrency, durable authorization before SDK, known-not-sent vs uncertain outcomes, no replay, invalid Markdown/HTML/Graph-token rejection, exact request capture, source navigation/stale generation/draft/CAS, duplicate Apply and editor Undo. Prove a table through mounted Build editor + manual change + existing Save + fresh reopen; render desktop and narrow widths. Then one authorized live synthetic Compose witness with actual cost/latency/token usage recorded; no private corpus or new provider required.

Preserve beginning/end refs, exact requests/responses and evidence for the research/local-agent task dataset. Source receipt binding is not semantic accuracy or Graph publication proof. Request exact-head independent ARCHITECTURE review promptly, merge under PRIME authority after gates, and settle the handoff. Apply the additive APP migration only after backup/restore verification against current data; preserve source files/history and operator draft. An active provider request is a runtime collision to wait out, not an operator approval gate.

Keep 5202/8000 available to the operator until matched reviewed rollout. Any test servers use verified-free loopback ports, explicit isolated proxy/storage roots, reject live API destinations and finally-cleanup; verify owned listeners are gone. DOGFOOD alone owns its5206/8006 fixture lane; do not collide. Operator inspection remains a separate human acceptance gate; a passing synthetic witness alone does not close the full Mirathorn goal.
