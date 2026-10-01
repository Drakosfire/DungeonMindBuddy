# HANDOFF — DEMO: ask from saved Plan content

**Status:** ACTIVE — one serial Buddy consumer PR. The UI/test preparation
and server consumer subleases are active on the exact paths below.

**Activation base:** `origin/main@c48abb9fa5857df90af0b086ab78294445fd252a`
after APP-STATE PRs #831, #832, and #827 merged.

**Steward:** DEMO task `01a0efc8-f3a8-7be2-a556-33eb338338e8`

**Design base:** Buddy `main@a0b1462080c1eefd0d3e92f397b640cb2c174d2b`,
refreshed after PR #830 merged. The latest DEMO status is in
[ROADMAP-demo.md](../Roadmaps/ROADMAP-demo.md).

**Buddy PR title:** `DEMO: ask from saved Plan content`

## 1. One user-visible capability

On a saved managed-World Plan, the GM can ask the existing Plan Agent a question
whose answer may use the exact committed Plan revision selected by the surface.
This is a read-only conversation turn. Each successful turn names the World,
Plan, WorkRevision, revision number, digest, committed state, and whether the
editor had a divergent working copy.

This excludes unsaved draft text, graph retrieval or citations, Plan edits,
Apply, writes, recap ingestion, and new server-side conversation storage. It
does not close full J2 or any connected J1–J6 acceptance gate.

## 2. ARCHITECTURE’s settled contract

The request binds the managed World ID and active Plan document ID, keeps the
existing `expected_revision` field as the WorkObject `object_revision` freshness
pin, and adds `expected_revision_n` plus full `expected_content_sha256` for the
committed WorkRevision body. The UI can fetch the existing
`getWorldOwnedPlanCommittedRevision(documentId)` result to obtain the latter
pin; it checks the returned World/document/status for early feedback. The client
sends no Markdown and no draft. Buddy validates the active managed World record
and passes its stable ID to Content. Content resolves the active World-owned
`kind=plan` WorkObject and its current immutable WorkRevision in one Content
transaction. It verifies expected object revision, stored World owner, Plan
kind/status, current-head revision number, and full digest before returning
bytes. The server repeats every check; the client check is not authority.

A stale or mismatched object revision, revision number, or digest, wrong World,
wrong kind/status, or missing current commit fails before any model call. The
selected saved Plan body is the only Plan prose injected. Force
`graph_request.mode=none` and do not invoke a graph resolver. The mounted
surface discloses that the saved Plan text and question go to the configured
model. A divergent editor working copy is disclosed but never used.

Each successful response returns and persists the exact context basis:
`(world_id, document_id, object_revision, work_revision_id, revision_n,
content_sha256, committed_status, has_divergent_working_copy)`. Never copy the
Plan body into the receipt. A body that cannot fit the supported request budget fails
visibly before a model call; never silently truncate it and claim the entire
Plan was read. No Plan, graph, or other saved work changes.

The managed World record and Content WorkObject live under separate owners;
this is intentionally not a cross-store transaction. Buddy validates the
managed World record, while Content independently verifies
`WorkObject.world_id == expected_world_id` in its transaction. If World
remapping or deactivation must revoke in-flight reads, add a binding/version
pin or a pre-dispatch recheck; do not claim the two checks are atomic.

## 3. Persistence and owner boundary

The per-turn receipt will extend the existing browser-local Plan conversation
summary and be sanitized by the existing conversation-history persistence path.
That path already survives reload; tests must prove the complete basis tuple
survives reload without saving Plan Markdown in the receipt. This does not
change PR #827’s APP-STATE conversation contract or add conversation schema.

The atomic current-World-Plan read is complete under APP-STATE ownership in
PRs #831 and #832. DEMO does not edit Content service code or tests. The Buddy
consumer calls the merged Content operation with the full World, object-revision,
WorkRevision-number, and SHA pins. It remains one serial consumer PR.

## 4. Acceptance witness and owning-boundary checks

With the UI and server path leases active:

- In disposable APP-STATE state, create an active World-owned Plan, commit a
  distinctive body, and capture its current revision number and SHA.
- Prove the Content operation returns exactly that current immutable body and
  tuple. Prove wrong World/kind/status, missing current commit, mismatched
  object revision, stale revision_n, wrong digest, and a later revision fail
  closed. Verify the current read reports a divergent working copy without
  returning it.
- Ask an ordinary Plan question requiring the distinctive fact. Verify only
  those returned Content bytes reach the configured Agent call, with
  `graph_request.mode=none` and zero graph resolution.
- Verify a dirty editor draft is disclosed but excluded. Save/reload the existing
  conversation and verify the exact context-basis tuple remains attached to the
  turn.
- Verify invalid World/document/pin and an over-budget body make no model call;
  the Plan and other saved work remain unchanged.
- Run the Content service test against a disposable APP-STATE database, Buddy
  registry/Agent route/service and runtime tests, mounted Plan Ask regression,
  and focused history-sanitization/reload tests. Do not use a shared database or
  start a shared runtime. A later configured-provider live witness stays under
  the existing DEMO provider mandate and PRIME’s runtime coordination.

## 5. Serial leases and exact paths

### APP-STATE predecessor — complete

- PR #831 merged as `5b7721c580e1478f5d00008bf9512252fd35d1b6`.
- PR #832 merged as `d75df0949c67dc7cf336df3886dc4159e70e59da`.
- PR #827 merged as `c48abb9fa5857df90af0b086ab78294445fd252a`, completing World-wide Agent conversation receipts. Its migration and tests are settled on `main`.
- The Content operation is `read_current_world_plan_revision(document_id, *, expected_world_id, expected_revision, expected_revision_n, expected_content_sha256)`. It validates World ownership, active `kind=plan`, WorkObject `object_revision`, current WorkRevision number, and full SHA in one transaction.
- Its result contains exact committed Markdown and `(world_id, document_id, object_revision, work_revision_id, revision_n, content_sha256, committed_status, has_divergent_working_copy)`. Never persist the Markdown in the receipt.

### Current DEMO UI/test sublease — exclusive write allowlist

- `apps/live-control-ui/src/api/types.ts`
- `apps/live-control-ui/src/planSurface/PlanSurfacePage.tsx`
- `apps/live-control-ui/src/planSurface/PlanSurfacePage.test.tsx`
- `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx`
- `apps/live-control-ui/src/planSurface/components/agentInteractionHistory.ts`
- `apps/live-control-ui/src/planSurface/components/agentInteractionHistory.test.ts`

This sublease implements early current-revision pinning, request/receipt typing, strict response validation, and local receipt persistence. It must not send editor draft text or persist saved Plan Markdown. The whole Buddy consumer remains one PR; do not open a UI-only PR.

### Current DEMO server consumer sublease — active

The server consumer's exclusive write allowlist is:

- `apps/live_control_server/models/agent_turn.py`
- `apps/live_control_server/routes/agent.py`
- `apps/live_control_server/services/agent_turn_service.py`
- `apps/live_control_server/services/workspace_document_registry.py`
- `apps/live_control_server/services/agent_runtime.py`
- `apps/live_control_server/services/pydantic_ai_agent_runtime.py`
- `tests/test_workspace_document_registry.py`
- `tests/test_agent_turn_route.py`
- `tests/test_agent_turn_service.py`
- `tests/test_agent_runtime.py`
- `tests/test_pydantic_ai_agent_runtime.py`

PRIME explicitly transfers the four overlapping paths below to DEMO's isolated `codex/demo-saved-plan-ask-consumer` lane for this saved-content Ask slice:

- `apps/live_control_server/routes/agent.py`
- `apps/live_control_server/services/agent_turn_service.py`
- `tests/test_agent_turn_route.py`
- `tests/test_agent_turn_service.py`

The other paths in the server allowlist are active for this consumer. `tests/application_state/test_agent_conversation_postgres.py` is explicitly excluded and must remain untouched.

The suspended, recoverable worktree `/home/drakosfire/.codex/worktrees/agent-world-conversation-backend/DungeonMindBuddy`, branch `codex/agent-world-conversation-backend`, is preserved at `0e49c4d7` with its dirty diff intact. PRIME and ARCHITECTURE found no live owner task. Do not edit, transplant, or delete that checkout or its uncommitted work. The paused AGENT-INTERACTION lane must not resume edits to transferred paths until this DEMO consumer PR merges; afterward it must re-anchor and reconcile against #827 and the DEMO merge before resuming its separate conversation-persistence work.

The server must perform the atomic Content read before provider dispatch, reject stale or foreign pins before the model call, inject only the committed body into the existing Plan turn, keep `graph_request.mode=none`, and return the exact basis receipt.

### Current collision census

- PR #827's `src/application_state/agent_conversation/{repository,service,types}.py`, migration, and tests are merged at `c48abb9fa5857df90af0b086ab78294445fd252a`.
- Open PR #826 owns World-space provisioning/binding, its tests, and dependency files. It does not overlap this graph:none slice.
- Open PRs #798, #781, #765, #764, #763, #761, and #760 were checked; none overlaps either active sublease. #763's dependency paths remain excluded.

Topology is serial: APP-STATE #831/#832 and #827 are settled predecessors, followed by one Buddy consumer PR. PRIME owns review and merge coordination; DEMO owns Buddy integration and final verification.

## 6. Activation boundary

The operator authorized this as DEMO's next user-visible capability. DEMO re-anchored at `origin/main@c48abb9fa5857df90af0b086ab78294445fd252a` after fetching current `origin/main`. The UI/test and server consumer subleases are ACTIVE on the allowlist in §5 following PRIME's explicit transfer of four overlapping paths. The suspended AGENT-INTERACTION checkout remains intact and must not be resumed until after the DEMO consumer PR merges and that lane re-anchors and reconciles its recoverable work.

This is one serial consumer PR; do not split or publish a partial UI PR. Keep the J2 Apply witness, native V6 graph binding, Sessions 26/27/28 evidence, and Session 28 recap ingestion as separate roadmap gates.
