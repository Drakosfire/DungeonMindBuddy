# APP-STATE: bounded per-attempt context trace persistence

Status: MERGED. PR #1122 accepted head `8aaa27d37b72d0833662e9510bbaaaa125d4e4ef`, merge `6f54b152c506bc8cd356ad3e4cdb66a2c46babac`. Original base: `a2b8db65fc69fa06b6e7e32bb16bcf4ecca5d6b8`; final base: `ad555917179764c61dcbc3095f9d7fd5182709b2`. Historical-source extension authority is in [the successor handoff](HANDOFF-APP-STATE-historical-source-trace.md). This predecessor grants no active write lease or live migration authority.

APP-STATE owns the typed storage contract, migration, claim fencing, per-attempt retention, and atomic terminal closure. DOGFOOD owns the producer and UI. SERVER owns authenticated, explicit opt-in history routing. The existing `graph_context_execution` remains the authority for source admission, provider authorization, completion, retry, and World mutation; trace rows are supplemental history only.

## Contract

- Persist optional `dmb_turn_context_trace_v1` rows by `(turn_id, attempt)` in `agent.turn_context_trace`; preserve all attempts. No trace is synthesized for legacy rows.
- Trace payloads are strict typed observations with a 1 MiB serialized per-attempt ceiling. Keep complete validated source passages up to the existing maximum of eight reads and 96,000 aggregate characters per turn. Reject overflow and set an explicit safe capture-incomplete code; never truncate or silently discard.
- Recording reserves 4 KiB for safe capture-failure and terminal fields; incomplete open traces retain 2 KiB for terminal closure. Model sizing uses spaced, ASCII-escaped JSON as a conservative bound, and writes also check PostgreSQL's actual JSONB text byte length. Overflowing additional generic observations preserve existing observations and return explicit incomplete capture rather than blocking core turn finalization.
- Every passage binds to a validated source-read execution event, read call, World, graph/source revision, source and evidence IDs, passage boundaries, exact character count, and SHA-256 of the captured UTF-8 bytes. This snapshot proves what was returned; it grants no read, citation, admission, or write authority.
- Context snapshots distinguish visible model-context material from retrieval-only routes. A retrieval route never claims its body was present. Do not store hidden reasoning, provider prompts or raw provider requests, credentials, arbitrary exception strings, or untyped tool payloads.
- Present source material names its source-read event and specific `source_reads` passage IDs/digests. Each must match an earlier captured passage in this trace; supplied route pins must match that captured scope. Retrieval-only route handles carry no captured-source claims.
- Graph operation observations use a strict union for search, object, neighborhood, and support requests, with allowlisted query/target/seed IDs, scope/revision, and observed limits. Their bounded result projection stores stable node labels/kinds plus claim, relationship, and evidence IDs and exact returned/total counts. Limited projections name safe omission codes. APP-STATE binds both request/result packet hashes, projected IDs, revision, and coverage to one validated graph-operation ledger event; source passage bytes remain in their dedicated observation. A missing projection at terminal close marks capture incomplete.
- `begin`, append, and source-read capture require the running turn's exact World/conversation/attempt/revision and an unexpired DB-time claim. Trace-only writes do not advance turn revision. Identical duplicate observation retries are idempotent; changed duplicates and stale/out-of-order writes conflict.
- A source passage observation and its validated source-read ledger event commit in the same transaction before the server passes those bytes to a context/provider consumer. An active opted-in trace requires every content-bearing source receipt to have the exact matching passage snapshot.
- Completed, failed, and interrupted turn status and trace closure commit in one transaction. Preserve partial observations on interruption. Stale workers cannot append after expiry or close a newer attempt.
- Reads are World-scoped and return all attempts to the authenticated opt-in SERVER history route. Default history does not add trace. Trace write/read failure cannot cause automatic redispatch; failure is exposed as incomplete/unavailable.

## Write lease

- `src/application_state/agent_conversation/context_trace.py`
- `src/application_state/agent_conversation/context_trace_store.py`
- `src/application_state/agent_conversation/types.py`
- `src/application_state/agent_conversation/repository.py`
- `src/application_state/agent_conversation/service.py`
- `src/application_state/migrations/versions/20261013_0022_turn_context_trace.py` (down revision 0021 only while it remains current)
- `tests/test_agent_context_trace_types.py` and the source-read/terminal lifecycle case in `tests/application_state/test_agent_conversation_postgres.py`
- `tests/application_state/test_agent_conversation_context_trace_postgres.py` for near-cap terminal/overflow and fabricated-source regressions
- `tests/application_state/test_agent_conversation_postgres.py` and `test_agent_conversation_service.py` only for migration-head assertions and terminal lifecycle behavior
- this handoff

No SERVER, DOGFOOD producer/UI, Graph/source implementation, retained database, provider, runtime, or corpus paths are leased. Migration activation against retained data is a separate rollout decision.

## Required owning proof

- Strict schema, privacy, World identity, source digest/character binding, 8-read/96,000-character, and 1 MiB bound witnesses.
- Disposable PostgreSQL migration and fresh-service readback for all attempts.
- Exact source receipt plus passage commits atomically; source event cannot be used without matching captured passage when tracing is active.
- Stale revision, wrong attempt, expired claim, post-terminal append, and changed duplicate are rejected; identical duplicate is idempotent.
- Completed, failed, live-interrupted, and expired-claim interrupted transitions close trace with the terminal row atomically, including rollback witness.
- Partial attempts survive retry, and World-scoped history returns all attempts without altering default projections.

No live migration or provider call is part of this slice.
