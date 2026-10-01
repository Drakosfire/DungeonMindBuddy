# HANDOFF — DEMO: ask from saved Plan content

**Status:** BLOCKED — the operator selected this as DEMO’s next capability and
ARCHITECTURE has ruled the contract. The read requires an APP-STATE-owned
Content service path; no implementation lease is active until the owner approves
that path or delivers it as a serial prerequisite.

**Steward:** DEMO task `01a0efc8-f3a8-7be2-a556-33eb338338e8`

**Design base:** Buddy `main@a0b1462080c1eefd0d3e92f397b640cb2c174d2b`,
refreshed after PR #830 merged. The latest DEMO status is in
[ROADMAP-demo.md](../Roadmaps/ROADMAP-demo.md).

**Proposed Buddy PR title after activation:** `DEMO: answer from saved Plan content`

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

The request binds the managed World ID, active Plan document ID, expected
**current** committed revision number, full SHA-256, question, and thread. It
sends no Markdown and no draft. Buddy first validates the exact managed World
record and passes its stable ID to Content. Content then resolves the active
World-owned `kind=plan` WorkObject and its current immutable WorkRevision in
one Content transaction. It verifies the stored World owner, Plan kind, active
status, current-head revision number, and full digest before returning bytes.

A stale or mismatched pin, wrong World, wrong kind/status, missing current
commit, missing historical bytes, or digest mismatch fails before any model
call. The selected saved Plan body is the only Plan prose injected. Force
`graph_request.mode=none` and do not invoke a graph resolver. The mounted
surface discloses that the saved Plan text and question go to the configured
model. A divergent editor working copy is disclosed but never used.

Each successful response returns and persists the exact context basis:
`(world_id, document_id, work_revision_id, revision_n, content_sha256,
committed_status, has_divergent_working_copy)`. Never copy the Plan body into
the receipt. A body that cannot fit the supported request budget fails
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

The atomic current-World-Plan read is a separate APP-STATE-owned prerequisite.
ARCHITECTURE confirmed that
`apps/live_control_server/services/workspace_document_registry.py::get_committed_playable_revision`
is insufficient: it reads the WorkObject and current/historical revision in
separate Content calls, does not validate current-head plus expected digest as
one operation, and is not called with the route’s complete pin. The new narrow
Content operation belongs in `src/application_state/content/service.py`. It
must return the immutable body and tuple from one Content transaction and add
no schema or migration.

The APP-STATE owner must approve/lease that Content path or deliver the
prerequisite on a serial APP-STATE PR. Until then, DEMO does not edit Content
service code or tests. DEMO’s Buddy consumer follows that prerequisite as a
separate serial PR.

## 4. Acceptance witness and owning-boundary checks

After both path leases are active:

- In disposable APP-STATE state, create an active World-owned Plan, commit a
  distinctive body, and capture its current revision number and SHA.
- Prove the Content operation returns exactly that current immutable body and
  tuple. Prove wrong World/kind/status, missing current commit, stale revision,
  wrong digest, and a later revision fail closed. Verify the current read reports
  a divergent working copy without returning it.
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

## 5. Proposed serial leases and exact paths

### APP-STATE prerequisite (owner approval required)

- `src/application_state/content/service.py`
- `tests/application_state/test_plan_work_object_postgres.py`

The prerequisite adds only the atomic active World-owned current Plan read and
its owning-boundary tests. No migration, schema, route, conversation-storage,
or provider path is proposed. If the owner identifies additional paths, return
them for a lease update before editing.

### Buddy consumer (depends on the APP-STATE prerequisite)

- `apps/live_control_server/models/agent_turn.py`
- `apps/live_control_server/routes/agent.py`
- `apps/live_control_server/services/agent_turn_service.py`
- `apps/live_control_server/services/workspace_document_registry.py`
- `apps/live_control_server/services/agent_runtime.py`
- `apps/live_control_server/services/pydantic_ai_agent_runtime.py`
- `apps/live-control-ui/src/api/types.ts`
- `apps/live-control-ui/src/planSurface/PlanSurfacePage.tsx`
- `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx`
- `apps/live-control-ui/src/planSurface/components/agentInteractionHistory.ts`
- `apps/live-control-ui/src/planSurface/components/agentInteractionHistory.test.ts`
- `tests/test_workspace_document_registry.py`
- `tests/test_agent_turn_route.py`
- `tests/test_agent_turn_service.py`
- `tests/test_agent_runtime.py`
- `tests/test_pydantic_ai_agent_runtime.py`
- `apps/live-control-ui/src/planSurface/PlanSurfacePage.test.tsx`

The Buddy consumer may only pass the client’s expected revision/digest to the
Content operation, validate the returned World/document/pin before model
invocation, inject the server-read bytes into the existing Plan turn, and
return/render/persist the bounded receipt. It must preserve current Ask/edit
behavior, exclude draft text, keep graph mode off, and use the existing Agent
runtime. Do not add graph, Plan writes, proposals, Apply, new storage, migration,
a new provider, or a new shared runtime.

### Collision census at `origin/main@a0b1462080c1eefd0d3e92f397b640cb2c174d2b`

- PR #826, head `4fa28e586783f0e63edb85fa664afa53521367f6`, owns World-space
  provisioning/binding, its tests, and dependency files. It does not overlap
  this graph:none slice.
- PR #827, head `1f3b8a3ff386c592f9251172d13352c70f1e0d51`, owns
  `src/application_state/agent_conversation/{repository,service,types}.py`, its
  migration, and tests. It does not overlap the Content prerequisite. Its
  conversation schema is not needed because the exact basis is persisted in
  Buddy’s existing local Plan thread summary.
- Open PRs #798, #781, #765, #764, #763, #761, and #760 were also inspected.
  They do not overlap the Buddy consumer paths; #763 owns dependency files and
  they remain excluded.
- Inspected Buddy worktrees show no Plan Ask implementation lane. Recheck remote
  refs, open PRs, and owner leases before each serial PR begins.

Topology is **serial**: APP-STATE atomic-read prerequisite first, then one Buddy
consumer PR. No stacked or parallel behavioral dependency. PRIME owns review
and merge coordination; DEMO owns Buddy integration and final verification.

## 6. Activation boundary

The operator authorized this as DEMO’s next user-visible capability. This
handoff remains BLOCKED only on APP-STATE approval or delivery of its prerequisite
path. The candidate Buddy allowlist becomes an exclusive write lease only after
that boundary is resolved and the handoff is pinned ACTIVE. Keep the J2 Apply
witness, native V6 graph binding, Sessions 26/27/28 evidence, and Session 28
recap ingestion as separate roadmap gates.
