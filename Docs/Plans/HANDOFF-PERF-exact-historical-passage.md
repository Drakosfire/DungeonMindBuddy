# Exact historical passage acquisition

**Status:** ACTIVE; PRIME activates the bounded contract after Architecture design critique.
**Base:** e4ab29157d98684bc1e1ad9362ce220dc499e03a; branch codex/exact-historical-passage, existing buddy-context-loop checkout.
**Topology:** serial after accepted1491; no overlapping backend/trace acquisition lease in inspected open PRs. One backend/UI read capability, no schema migration. Owned API8000/5202 paired delivery, existing retained data and dependencies; no new environment/source export.

## Invariant and critique

Opening one earlier source passage currently downloads the full all-attempt trace. Resolve the exact historical World/conversation/turn/attempt/trace/event/source-read/hash tuple on the server, with GM and verified World gates, and return only its exact captured passage. Never grant current-turn Graph/citation authority, infer latest, or include other observations/prompts. Keep existing full-trace Debug API unchanged. Capture is append-only for passage bytes; response is an observed exact passage, not a claim that its enclosing trace is immutable or current.

Strict canonical UUIDs/positive attempt/digest/128-character read ID; reject missing/duplicate/unknown selectors before storage. Query read ID supports encoded slashes/reserved characters. Join World+conversation+turn+attempt+trace, fetch at most one bounded1MiB trace using SQL CASE before transferring payload. Validate stored model/bindings/digest/character count and exactly one matching event/read/hash, fail closed on corruption/missing/mismatch. Serialize only response schema/reference/passage, cap64KiB UTF8 bytes (12k Unicode characters alone are not a byte bound), no silent truncation. No migration, rawprompt read, latest fallback or filesystem paths.

Client exact URL/query and pending-only coalescing retain transport access/body/cancellation fences. Local reader uses exact tuple+read-wave key, hides already visible bytes synchronously on access/mutation wave, cancels abandoned reads and fences late body/digest completions/World-conversation ABA. Verify actual UTF8 SHA256 and codepoint character count before inert plain-text display. Bounded local observation may survive collapse within the same reference/wave; no global settled cache/TTL or fulltrace memoization. Errors remain unavailable with explicit read-only retry.

## Exclusive write lease

- This contract and accepted1491 HANDOFF-PERF-agent-launcher-delivery.md settlement.
- APP src/application_state/agent_conversation/context_trace_store.py and service.py: exact bounded DB read; context_trace.py only if response contract belongs there.
- apps/live_control_server/models/agent_turn.py and routes/agent.py: typed response/strict authenticated endpoint.
- tests/test_agent_context_trace_route.py or new exact-passage route test; tests/application_state/test_agent_conversation_context_trace_postgres.py owner tests.
- UI src/api/buddyContextTraceTypes.ts, liveApi.ts, liveApi.worldConversation.test.ts and liveApi.evidenceReads.test.ts; existing inFlightReads implementation unchanged, extend its tests only if required by new route.
- UI src/planSurface/components/BuddyHistoricalSourcePassage.tsx and its test, plus current World history integration test only for affected current API fixtures.
- Existing private API bootstrap source binding and owned5202 index/assets only after exact-head independent approval/merge; preserve prior bootstrap/index for rollback, data/env/service identity unchanged.

Verify real disposable PostgreSQL exact join/provenance/hash corruption/missing/oversize and one-trace selection; route authentication before store, canonical selectors and duplicates, typed response64KiB Unicode bound/no extra observations; API encoded reserved read ID, pending-only identity/cancel/access body fence; UI true digest/provenance/visible-wave retirement/ABA/latehash/retry/no fulltrace/provider calls. Focused owner suites, tsc/build and cumulative diff; exact-head independent review, merge, paired API/UI delivery, native read reduction and protected17state unchanged. If storage/schema change emerges, stop/split. Full goal remains open: other list/graph bounds, heavy controller loading, user+Agent Rules lookup, native Combat. Rule-graph experiments wait for all objectives.

## Author verification before independent review

Real disposable PostgreSQL/route cohort36passes: exact one-attemptload including a deliberately invalid other attempt, all eight changed provenancepins, stored hash/count/World/duplicate corruption, authbeforeselectors/storage, canonical/duplicate/unknown/missingselectors, reserved/Unicode read ID, response Unicode/control-character serialized bounds, unchanged fulltrace API. Actual schema already enforces1MiB pertrace; SQL CASE additionally bounds transferbefore Pythonmodel parsing. No migration. Client7-filecohort154passes, including21historicalreader cases and pending exactidentity/partialcancel/accessstreamfences; defaultreader makes one exactpassageGET, no fulltrace/providerprompt. RealWorldhistoryDebug/Prompt integration passes; TypeScript/build/diffcheck pass. An author test found and corrected a wave-retirement duplicatefetch causedby saved-state dependency; no held artifact was adopted. No blanket all-repository green claim; known unrelated predecessor baseline failures remain outofscope. API/UI/runtime acceptance awaits exact-head review and merge.
