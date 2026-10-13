# DOGFOOD: observable conversation context trace

Status: ACTIVE for Buddy observation producer/inspection UI. APP-STATE #1122 merged its accepted persistence contract as `6f54b152c506bc8cd356ad3e4cdb66a2c46babac`; DOGFOOD consumes it without editing persistence paths. Runtime activation remains behind SERVER's coordinated shared-schema rollout. The user's continuing Mirathorn goal authorizes design and implementation but does not transfer another lane's paths.
Base: `origin/main@a2b8db65fc69fa06b6e7e32bb16bcf4ecca5d6b8`, fetched and inspected 2026-10-13.
Branch: `codex/buddy-context-trace`.
Checkout: `/home/drakosfire/.codex/worktrees/buddy-context-trace/DungeonMindBuddy`.
Topology: serial; predecessor #1119 merged exact head `b0cd7045` as `a2b8db65`. This is the sole context-trace implementation slice. Open #1014, #869, #844, #826, #798, and the rules stack have no overlapping trace write lease.

## Capability

Persist observable execution and context-management evidence for each accepted policy Ask, including failed turns. Expose it through authenticated World history and an expandable Buddy trace. Capture actual graph tool arguments/results, source passages returned, source routes, context material before/after compaction, recorded keep/prune decisions, provider identity and actual usage when available, and exact safe failure codes. Distinguish conservative envelope accounting from provider-reported tokens. Historical turns without captured trace must say unavailable; never reconstruct a fictional trace.

This is the APP-STATE/Buddy contract: APP-STATE owns durable trace storage, attempt fencing and World/turn identity; Buddy owns the allowlisted observation producer and inspection UI. DungeonMind retains exclusive graph/source truth. A trace observation grants no citation, source admission, retry permission, turn completion or World mutation.

PRIME's accepted owner split: APP-STATE implements a per-attempt trace table/types/store/lifecycle/migration, capped at 1 MiB per attempt with explicit incomplete/unavailable capture states. Exact complete broker-validated passage snapshots bind to the source-read execution event and original scope/reference/revision/digest. Capture is write-ahead with the validated read event; terminal close is atomic and preserves failed/interrupted attempts. These snapshots are historical context, not a graph authority or source archive. No arbitrary tool payload, whole provider prompt, hidden reasoning or credentials are eligible. Buddy consumes APP-STATE's supplied typed contract; the initial proposal remains design evidence only.

Consumer query/result gap addressed in APP-STATE's current draft contract: typed search/object/neighborhood/support requests, observed limits, returned node labels and claim/relationship/evidence projections, explicit coverage/omission counts, and exact execution receipt hashes. The viewer and pure producer projection now consume that shape. Five producer variants validate against owner draft contract digest `bf26b81d7b0f3097bcaa61f262e9c9a68cbe5db21f9599fa3526abbbce6271de`; this is provisional compatibility evidence, not proof that the persistence contract has merged or that live capture works. Nine producer tests and eight viewer tests pass; app typecheck and Ruff pass.

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

SERVER's citation-identity repair #1121 merged as `ad555917179764c61dcbc3095f9d7fd5182709b2`; its shared-function lease is released. This lane must re-anchor before collector/history integration while preserving its packet/version semantics. Because 5202 now runs from this checkout, rebase/source adoption must occur in a stopped transition. This branch currently edits neither shared backend file. APP-STATE retains persistence ownership; its accepted implementation remains a separate integration dependency.

## Runtime and verification

The accepted source-context reference is `source_read_event_id` plus specific `source_reads` IDs/digests, referring to earlier exact passage snapshots in the same attempt. Viewer validation now covers exact, wrong-digest and future-capture cases: eleven cases pass plus app typecheck. Delivery repair #1124 owns the provider denial/membership functions until it settles; trace integration consumes that repair afterward. Message dedup #1123 is merged at `cfc788a9` and its matching temporary UI delta in the serving checkout is preserved until main is adopted.

5202 now serves this PR #1120 branch at `ec6bc77f` after the user requested removal of empty-conversation filler and the routine New Conversation confirmation notice. The trace viewer is still standalone and not wired. Its UI/API/Graph health checks passed; the browser shows neither removed line. The previous session directory and environment were preserved, and the separate stable-main services were untouched. Preserve the existing failed Ask, World facts, and Plan text. Live durable-trace rollout still requires the tested owning contract and verified migration/source-switch boundary. Disposable database tests use independent ports/data directories.

The requested text cleanup extends the targeted test write set to `apps/live-control-ui/src/agentInteraction/WorldAgentConversation.planPlay.integration.test.tsx`. Verification: 214 history/integration cases pass; both remaining Play reconciliation failures reproduce on unchanged predecessor code; TypeScript app typecheck passes.

Required evidence: strict trace privacy/shape tests; real PostgreSQL migration/readback/attempt-fencing tests; policy execution fake with graph success plus parent denial preserved on a running turn; authenticated history serialization; expandable UI showing actual usage vs estimates and present context vs routes; cumulative diff review; committed/pushed PR. Then run fresh acceptance queries without replaying the existing request. Full Mirathorn answers, compaction recovery, and synthesis remain requirements of the overarching goal, not claims of this trace slice.
