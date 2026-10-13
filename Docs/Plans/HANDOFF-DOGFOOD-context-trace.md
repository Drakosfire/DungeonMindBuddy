# DOGFOOD: observable conversation context trace

Status: ACTIVE for Buddy observation producer/inspection UI; APP-STATE retains implementation ownership of persistence. Integration is BLOCKED pending its accepted payload and persistence contract. The user's continuing Mirathorn goal authorizes design and implementation but does not transfer another lane's paths.
Base: `origin/main@a2b8db65fc69fa06b6e7e32bb16bcf4ecca5d6b8`, fetched and inspected 2026-10-13.
Branch: `codex/buddy-context-trace`.
Checkout: `/home/drakosfire/.codex/worktrees/buddy-context-trace/DungeonMindBuddy`.
Topology: serial; predecessor #1119 merged exact head `b0cd7045` as `a2b8db65`. This is the sole context-trace implementation slice. Open #1014, #869, #844, #826, #798, and the rules stack have no overlapping trace write lease.

## Capability

Persist observable execution and context-management evidence for each accepted policy Ask, including failed turns. Expose it through authenticated World history and an expandable Buddy trace. Capture actual graph tool arguments/results, source passages returned, source routes, context material before/after compaction, recorded keep/prune decisions, provider identity and actual usage when available, and exact safe failure codes. Distinguish conservative envelope accounting from provider-reported tokens. Historical turns without captured trace must say unavailable; never reconstruct a fictional trace.

This is the APP-STATE/Buddy contract: APP-STATE owns durable trace storage, attempt fencing and World/turn identity; Buddy owns the allowlisted observation producer and inspection UI. DungeonMind retains exclusive graph/source truth. A trace observation grants no citation, source admission, retry permission, turn completion or World mutation.

PRIME's accepted owner split: APP-STATE implements a per-attempt trace table/types/store/lifecycle/migration, capped at 1 MiB per attempt with explicit incomplete/unavailable capture states. Exact complete broker-validated passage snapshots bind to the source-read execution event and original scope/reference/revision/digest. Capture is write-ahead with the validated read event; terminal close is atomic and preserves failed/interrupted attempts. These snapshots are historical context, not a graph authority or source archive. No arbitrary tool payload, whole provider prompt, hidden reasoning or credentials are eligible. Buddy consumes APP-STATE's supplied typed contract; the initial proposal remains design evidence only.

Consumer contract gap identified 2026-10-13: the current draft `TraceGraphTool` carries only event IDs/outcome/result code. Existing validated execution events carry request/result hashes, IDs and coverage but not actual query/selectors or returned graph facts. References to that ledger alone cannot satisfy the user's searches/tool-calls/results requirement. The accepted producer/persistence interface must include an allowlisted, broker-validated query/result projection (not arbitrary provider payload), or an exact immutable retrievable observation artifact. Until then the viewer must explicitly report unavailable query details; this requirement remains open and must not be reduced to event hashes.

## Invariant critique

- A response can arrive before a later authorization is denied. Persist the later failure without changing an earlier provider outcome to unknown or replaying the Ask.
- Parent-rejected tool outputs are observations, not admitted evidence. Preserve their exact safe codes so the next repair can distinguish coverage/admission errors from transcript validation.
- A stale attempt must not overwrite or append to a newer attempt's trace. Trace writes must not advance the turn's execution revision or lifecycle.
- Never persist provider reasoning, system instructions, credentials, arbitrary exception text, or complete provider request bodies. Only allowlisted parent tools and visible conversation/context material are eligible.
- No silent truncation: reject an invalid/oversized observation explicitly and record capture failure. Existing tool/source policy quotas bound eligible output; route handles remain separate from material present in model context.
- A trace write/read failure must be visible as missing evidence and must never authorize automatic redispatch.

## Exclusive expected write set

- This handoff; predecessor `Docs/Plans/HANDOFF-DOGFOOD-mirathorn-context-loop.md`; `Docs/Reports/REPORT-DOGFOOD-mirathorn-context-loop.md`.
- NOT LEASED TO DOGFOOD: APP-STATE trace types/store, repository/service trace methods, migration and targeted persistence tests. APP-STATE retains their implementation ownership. Draft proposal files are preserved in `/tmp/buddy-context-trace-contract-proposal`; the proposed type contract passed eight focused tests before being removed from this implementation checkout. Consume the accepted owning contract when supplied.
- Buddy trace collector module; `agent_turn_service.py`, `agent_conversation_context.py`, `agent_runtime.py`, `hermes_graph_agent.py`, `hermes_graph_agent_host.py` and targeted tests for observable telemetry.
- `apps/live_control_server/routes/agent.py`, `models/agent_turn.py`; UI API types/client and `WorldPlanAgentConversation` component/style/history tests; a dedicated trace component and its tests.

No dependency pin/lockfile, graph write, ingestion publication, arbitrary corpus fallback, background summary/edge loop, or stable-main runtime is leased.

PRIME's current dispatch reserves the initial provider-packet/receipt/reclaimed-packet functions in `routes/agent.py` and `agent_turn_service.py` to SERVER's citation-identity repair. Trace collector/history integration in both files is PARKED until that repair merges and this lane re-anchors. This branch currently edits neither file. Viewer and proposed API-type work can continue independently; APP-STATE separately settles the persistence lease.

## Runtime and verification

5202 now serves this PR #1120 branch at `ec6bc77f` after the user requested removal of empty-conversation filler and the routine New Conversation confirmation notice. The trace viewer is still standalone and not wired. Its UI/API/Graph health checks passed; the browser shows neither removed line. The previous session directory and environment were preserved, and the separate stable-main services were untouched. Preserve the existing failed Ask, World facts, and Plan text. Live durable-trace rollout still requires the tested owning contract and verified migration/source-switch boundary. Disposable database tests use independent ports/data directories.

The requested text cleanup extends the targeted test write set to `apps/live-control-ui/src/agentInteraction/WorldAgentConversation.planPlay.integration.test.tsx`. Verification: 214 history/integration cases pass; both remaining Play reconciliation failures reproduce on unchanged predecessor code; TypeScript app typecheck passes.

Required evidence: strict trace privacy/shape tests; real PostgreSQL migration/readback/attempt-fencing tests; policy execution fake with graph success plus parent denial preserved on a running turn; authenticated history serialization; expandable UI showing actual usage vs estimates and present context vs routes; cumulative diff review; committed/pushed PR. Then run fresh acceptance queries without replaying the existing request. Full Mirathorn answers, compaction recovery, and synthesis remain requirements of the overarching goal, not claims of this trace slice.
