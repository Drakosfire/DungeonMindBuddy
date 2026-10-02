# HANDOFF — DEMO: ask from saved Plan content

**Status:** #833 consumer implementation COMPLETE — merged at
`5a7abdfdf0be13c11b0ce849be433e03a6cb662d` from reviewed head
`86c1ea2552a6f035f4b172ce83a694f57628f9b1`. Its configured-provider witness
below passed one saved-content Plan turn and reload, but did not prove World-wide
conversation continuity. Expanded canonical runtime acceptance remains PENDING
after APP-STATE #867 recovery and resumed/re-anchored AGENT-INTERACTION #865,
before #857 Plan cutover acceptance. This status correction grants no new
runtime or Plan implementation lease.

**Historical activation base:** `origin/main@c48abb9fa5857df90af0b086ab78294445fd252a`
after APP-STATE PRs #831, #832, and #827 merged.

**Steward:** DEMO task `01a0efc8-f3a8-7be2-a556-33eb338338e8`

**Historical design base:** Buddy `main@a0b1462080c1eefd0d3e92f397b640cb2c174d2b`,
refreshed after PR #830 merged. The latest DEMO status is in
[ROADMAP-demo.md](../Roadmaps/ROADMAP-demo.md).

**Completed Buddy PR:** #833 — `DEMO: ask from saved Plan content`

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

The #833 per-turn receipt extended the existing browser-local Plan conversation
summary and was sanitized by the existing conversation-history persistence
path. The configured-provider witness below confirms that local history survives
reload with the complete basis tuple and without Plan Markdown in the receipt.
Browser-local history is not an authoritative server-side retry receipt. This
implementation did not change PR #827’s APP-STATE conversation contract or add
conversation schema.

The atomic current-World-Plan read completed under APP-STATE ownership in
PRs #831 and #832. DEMO did not edit Content service code or tests. The merged
Buddy #833 consumer called the Content operation with the full World,
object-revision, WorkRevision-number, and SHA pins. #833 was one serial consumer
PR and is complete.

## 4. Completed #833 evidence and later runtime acceptance

### #833 consumer acceptance — complete

Buddy #833 merged at `5a7abdfdf0be13c11b0ce849be433e03a6cb662d` from reviewed
head `86c1ea2552a6f035f4b172ce83a694f57628f9b1`. The consumer pins and reads
the current committed Plan body before Agent dispatch, excludes a divergent
editor draft, forces `graph_request.mode=none`, and persists a compact
source-free basis receipt.

**Configured-provider witness — PASS (2026-10-01):** in synthetic World
`demo-saved-plan-ask-witness-2026-10-01`, Plan
`d901c4ad-5d74-4430-ab6e-45f622086b0e`, committed WorkRevision
`65352d85-0871-483f-8e59-e145f7e86791` (revision 1, SHA
`3277078c8b2778896805bc7165aec43942c9da25ae74d97c481839356c56ddad`), one
bounded question used the saved seven-rings-at-dusk fact and excluded an
unsaved nine-rings-at-dawn editor draft. Reload restored the turn and exact
basis tuple. Trace `agent-trace-a66bdf5dd035` recorded OpenAI
`gpt-6-luna`, one model call, no tools or graph, 611 input / 48 output / 13
reasoning tokens and trace-estimated USD 0.0000851. The provider request ID was
not separately surfaced, and the estimate is not a billing receipt. This
witness closes only the connected saved-Plan Ask gate; it does not prove
World-wide conversation continuity or full J2/J1–J6 acceptance.

### Expanded canonical runtime acceptance — pending

PRIME's serial follow-up is APP-STATE #867 recovery → resumed/re-anchored
AGENT-INTERACTION #865 canonical runtime acceptance → Plan action-dialogue
projection #859 → #857 Plan conversation cutover acceptance. Capture the
already-merged #833 semantic proof as a distinct phase inside the canonical
runtime acceptance. This schedules broader evidence; it does not retroactively
change #833's contract or make #867/#865 prerequisites to the completed #833
consumer or its historical witness.

- Repeat the #833 semantic phase with a distinctive committed Plan fact and a
  dirty-draft decoy; prove the draft is excluded, `graph_request.mode=none`
  reaches the Agent, graph resolution is zero, and the exact source-free basis
  tuple survives durable conversation reload without Plan Markdown.
- Separately prove canonical server-side reload, receipt-first same-intent retry
  after both Plan-head and conversation-pointer advance returning the original
  receipt/provenance with no second provider dispatch, changed-intent conflict,
  and pinned-context recovery.
- Keep this within the one canonical runtime acceptance coordinated by PRIME;
  do not start a Plan-specific or second isolated runtime. The #859 migration
  still requires APP-STATE review, and #859/#857 require their own exact
  activation and acceptance gates.

## 5. Historical #833 path leases and collision census

The path lists below record the single consumer PR's write lease. All #833
UI/test and server consumer leases ended when #833 merged; none is active under
this handoff.

### APP-STATE predecessor — complete

- PR #831 merged as `5b7721c580e1478f5d00008bf9512252fd35d1b6`.
- PR #832 merged as `d75df0949c67dc7cf336df3886dc4159e70e59da`.
- PR #827 merged as `c48abb9fa5857df90af0b086ab78294445fd252a`, completing World-wide Agent conversation receipts. Its migration and tests are settled on `main`.
- The Content operation is `read_current_world_plan_revision(document_id, *, expected_world_id, expected_revision, expected_revision_n, expected_content_sha256)`. It validates World ownership, active `kind=plan`, WorkObject `object_revision`, current WorkRevision number, and full SHA in one transaction.
- Its result contains exact committed Markdown and `(world_id, document_id, object_revision, work_revision_id, revision_n, content_sha256, committed_status, has_divergent_working_copy)`. Never persist the Markdown in the receipt.

### Historical DEMO UI/test allowlist — released at #833 merge

- `apps/live-control-ui/src/api/types.ts`
- `apps/live-control-ui/src/planSurface/PlanSurfacePage.tsx`
- `apps/live-control-ui/src/planSurface/PlanSurfacePage.test.tsx`
- `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx`
- `apps/live-control-ui/src/planSurface/components/agentInteractionHistory.ts`
- `apps/live-control-ui/src/planSurface/components/agentInteractionHistory.test.ts`

During #833, this UI/test sublease implemented early current-revision pinning,
request/receipt typing, strict response validation, and local receipt
persistence. It did not send editor draft text or persist saved Plan Markdown. The lease ended at merge, and the consumer was delivered in one PR.

### Historical DEMO server consumer allowlist — released at #833 merge

The #833 server consumer's historical write allowlist was:

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

During #833, PRIME transferred the four overlapping paths below to DEMO's
isolated `codex/demo-saved-plan-ask-consumer` lane for the saved-content Ask
slice:

- `apps/live_control_server/routes/agent.py`
- `apps/live_control_server/services/agent_turn_service.py`
- `tests/test_agent_turn_route.py`
- `tests/test_agent_turn_service.py`

Those server path leases ended at #833 merge. The test
`tests/application_state/test_agent_conversation_postgres.py` was explicitly
excluded from that consumer.

At the original #833 activation, the suspended worktree
`/home/drakosfire/.codex/worktrees/agent-world-conversation-backend/DungeonMindBuddy`,
branch `codex/agent-world-conversation-backend`, was preserved at `0e49c4d7`
with its dirty diff intact. That preservation note is historical; this handoff
does not reopen that checkout or allocate paths to a successor runtime lane.

The merged #833 server consumer performs the atomic Content read before
provider dispatch, rejects stale or foreign pins before the model call, injects
only the committed body into the existing Plan turn, keeps
`graph_request.mode=none`, and returns the exact basis receipt.

### Historical collision census at #833 activation

- By the original activation, PR #827's
  `src/application_state/agent_conversation/{repository,service,types}.py`,
  migration, and tests had merged at
  `c48abb9fa5857df90af0b086ab78294445fd252a`.
- At original activation, open PR #826 covered World-space provisioning/binding,
  its tests, and dependency files. It did not overlap this graph:none slice.
- At original activation, open PRs #798, #781, #765, #764, #763, #761, and
  #760 were checked; none overlapped either #833 sublease. #763's dependency
  paths remained excluded.

At original activation, topology was serial: APP-STATE #831/#832 and #827 were
settled predecessors, followed by one Buddy consumer PR. #833 completed that
topology. PRIME retains review and merge coordination.

## 6. Historical activation and current successor gates

The operator authorized this saved-content consumer as DEMO's next user-visible
capability. DEMO originally re-anchored at
`origin/main@c48abb9fa5857df90af0b086ab78294445fd252a` after APP-STATE
#831/#832 and #827 settled. PRIME transferred the four overlapping paths to
the isolated DEMO consumer lane; Buddy #833 then merged at
`5a7abdfdf0be13c11b0ce849be433e03a6cb662d` from reviewed head
`86c1ea2552a6f035f4b172ce83a694f57628f9b1`. The UI/test and server consumer
leases ended at that merge. This activation record is historical and grants no
current implementation or runtime lease.

The planned serial follow-up is #867 recovery → resumed/re-anchored #865
canonical runtime acceptance → #859 Plan action-dialogue projection after
APP-STATE migration review and PRIME's exact lease → #857 Plan conversation
cutover acceptance. The expanded canonical witness includes the #833 semantic
phase described in §4; that scheduling does not retroactively alter the #833
contract or its passed turn-and-reload witness. The completed J2 Apply witness
and graph/retrieval, recap-ingestion, and full J1–J6 acceptance remain separate
roadmap outcomes. PRIME retains review and merge authority.
