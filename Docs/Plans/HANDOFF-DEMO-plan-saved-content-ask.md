# HANDOFF — DEMO: ask from saved Plan content

**Status:** BLOCKED — ARCHITECTURE has resolved the read contract. This proposal
still has no implementation write lease. Await PRIME's explicit activation and
disposition of the per-turn context-basis persistence seam below.

**Steward:** DEMO task `01a0efc8-f3a8-7be2-a556-33eb338338e8`

**Design base:** Buddy `main@a0b1462080c1eefd0d3e92f397b640cb2c174d2b`,
refreshed after PR #830 merged. The latest DEMO status is in
[ROADMAP-demo.md](../Roadmaps/ROADMAP-demo.md).

**Proposed PR title after activation:** `DEMO: answer from saved Plan content`

## 1. One proposed capability

On a saved managed-World Plan, the GM can ask the existing Plan Agent a question
whose answer may use the exact committed Plan revision selected by the surface.
This is a read-only conversation turn. The result identifies the World, Plan,
committed revision, and full content digest it used.

This excludes unsaved draft text, graph retrieval or citations, Plan edits,
Apply, writes, recap ingestion, and new conversation storage. It does not close
full J2 or any connected J1–J6 acceptance gate.

## 2. Settled read contract

ARCHITECTURE ruled that the request binds the managed World ID, active Plan
document ID, expected committed revision, full SHA-256, question, and thread.
The client sends no Markdown and no draft. Before any model call, the
Content-owned server read resolves the active World-owned `kind=plan` document
and returns the exact immutable committed bytes and digest. Wrong World, wrong
kind or status, missing commit, stale revision, or digest mismatch fails before
the model call.

Only those server-read bytes may be injected into the turn. Force
`graph_request.mode=none` and do not invoke a graph resolver. Return and persist
the exact `(world_id, document_id, revision, sha256)` context-basis tuple for
each turn; do not copy the Plan body into the receipt. A divergent editor
working copy is disclosed but never used. The Plan, graph, and other saved work
remain unchanged.

The mounted Plan surface must disclose that the selected saved Plan text and
question are sent to the configured model. If the whole exact body cannot fit
the supported request budget, fail visibly before the model call; never silently
truncate it and claim the entire Plan was read.

## 3. Activation gate: where the per-turn basis is persisted

The ruling requires the context-basis tuple to survive save/reload. The current
Plan UI already keeps safe turn summaries with its local conversation history;
adding the receipt there may satisfy this without new conversation storage or a
schema change. PR #827 separately adds APP-STATE World turn receipts whose
`TurnProvenance.primary_work` can carry kind, document ID, revision, and digest,
but that PR owns the APP-STATE repository/service/types/migration paths and is
not yet integrated into the current Plan Ask route.

**PRIME must choose the persistence seam before activation:** either accept the
existing Plan conversation's per-turn summary as the persistence surface, or
sequence/transfer the required APP-STATE receipt integration with APP-STATE.
This candidate lease does not edit PR #827 paths or change its contract.

## 4. Proposed acceptance witness

After PRIME activates a bounded path lease:

- Use a disposable managed World with a saved Plan containing a distinctive
  fact and a known committed revision and digest.
- Ask an ordinary Plan question requiring that fact. Verify the Content-owned
  read supplied precisely those bytes, and the returned and persisted receipt
  names the exact World, Plan, revision, and SHA-256.
- Reload the existing conversation and verify the context-basis tuple remains
  attached to its turn. Verify a divergent editor draft is disclosed and never
  sent.
- Verify wrong World/document/kind/status, missing commit, stale revision,
  digest mismatch, and over-budget body fail before a model call.
- Verify `graph_request.mode=none` results in no graph resolver/tool call and
  that the Plan, graph, and other saved work remain unchanged.
- Run the exact Content service read against a disposable APP-STATE database,
  the Buddy document-registry and Agent route/service tests, the mounted Plan Ask
  regression, and focused runtime prompt tests. A later configured-provider
  witness requires its own PRIME runtime lease.

## 5. Proposed Buddy write lease and exact path inventory

If PRIME accepts the existing Plan conversation as the receipt persistence
surface, the proposed serial Buddy implementation lease is limited to:

- `apps/live_control_server/models/agent_turn.py`
- `apps/live_control_server/routes/agent.py`
- `apps/live_control_server/services/agent_turn_service.py`
- `apps/live_control_server/services/workspace_document_registry.py` — use or
  extend the existing exact committed-revision adapter for the Content-owned
  read, without adding a second authority.
- `apps/live_control_server/services/agent_runtime.py`
- `apps/live_control_server/services/pydantic_ai_agent_runtime.py`
- `apps/live-control-ui/src/api/types.ts`
- `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx`
- `tests/application_state/test_plan_work_object_postgres.py` — prove the
  existing exact Content committed-revision read at its owning boundary.
- `tests/test_workspace_document_registry.py`
- `tests/test_agent_turn_route.py`
- `tests/test_agent_turn_service.py`
- `tests/test_agent_runtime.py`
- `tests/test_pydantic_ai_agent_runtime.py`
- `apps/live-control-ui/src/planSurface/PlanSurfacePage.test.tsx`

The runtime files may change only to pass the server-read Plan bytes into the
existing Plan turn. Keep graph mode disabled. Do not add a graph resolver, Plan
write, proposal, Apply path, new storage, migration, or provider-use surface.
If exact content reading requires paths outside this allowlist, stop and return
the precise owner/path/contract need to PRIME before editing.

### Collision census at `origin/main@a0b1462080c1eefd0d3e92f397b640cb2c174d2b`

- PR #826, head `4fa28e586783f0e63edb85fa664afa53521367f6`, owns World-space
  provisioning/binding, its tests, and dependency files. It does not overlap
  this graph:none slice.
- PR #827, head `1f3b8a3ff386c592f9251172d13352c70f1e0d51`, owns
  `src/application_state/agent_conversation/{repository,service,types}.py`, its
  migration, and tests. There is no exact path collision with the proposed
  lease, but it is a possible persistence dependency; resolve it before
  activation as stated above.
- Open PRs #798, #781, #765, #764, #763, #761, and #760 were also inspected.
  Their path sets do not overlap the proposed code paths; #763 owns dependency
  files and they remain excluded.
- The DEMO Plan Ask paths have no active implementation lane in the inspected
  Buddy worktrees. Recheck remote refs, open PRs, and leases immediately before
  activation.

PR #826 and #827 are separate active PRs, so this proposal uses **serial**
topology and introduces no stacked or parallel behavioral dependency. The
handoff path list is only a proposed allowlist; it becomes an exclusive lease
only when PRIME activates it.

## 6. Activation boundary

This BLOCKED handoff records the settled read contract, remaining persistence
decision, candidate allowlist, and collision census. It does not authorize code
edits, a shared runtime, a database, or provider use. Once PRIME chooses the
persistence seam and activates the exact path lease, DEMO will recheck the
remote base/PR census and implement only this capability. Keep the J2 Apply
witness, native V6 graph binding, Sessions 26/27/28 evidence, and Session 28
recap ingestion as separate roadmap gates.
