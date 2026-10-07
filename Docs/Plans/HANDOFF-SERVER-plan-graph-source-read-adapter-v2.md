# HANDOFF — SERVER: saved-Plan source-read adapter V2

**Status:** ACTIVE under PRIME's single bounded adapter lease. **Base:** Buddy `main@dae1a57f4be64ce3809aa1bf8c9a87fd642d51fb`; predecessors #1003 `81a105ecd00c0f18fe0665537866ad4edec8bcb3` and #1004 `22c3690310037b092665dbc808feb1cdf321048c` are merged. Draft #917 is a held prototype without production lease. PRIME owns independent review and merge.

**Primary question:** Can a saved-Plan turn open only source anchors admitted in its frozen retrieval session, durably authorize and validate each read under APP-STATE V2 budgets, and derive per-evidence citation `source_opened` only from successful reads included in the final producing provider envelope?

## Lease and boundaries

Expected source paths: `apps/live_control_server/services/agent_turn_service.py`, `apps/live_control_server/services/hermes_agent_runtime.py`, and `src/graph_memory/hermes_graph_plugin.py`. Owning tests: `tests/test_agent_turn_service.py`, `tests/test_hermes_graph_agent_contract.py`, and `tests/test_hermes_graph_agent_host.py`, plus this handoff. Keep V1 metadata-only rows and replay unchanged. Reuse trusted internal `receipt_version=2` and accepted APP-STATE V2 types/service; freeze read-call, anchor, character, and provider/completion budgets. The parent broker supplies session and Graph scope, persists authorization before external read and validated result before tool reply, and fails closed on uncertain persistence or stale/foreign input. No model-authored source-opened flag governs admission. Preserve exactly-once provider-attempt and recovery fences.

Do not add ingestion/discovery, a new reader/framework/dependency, provider calls, a live database migration, runtime deployment, or UI changes. Verify the actual AgentTurn V2 wire and ordinary UI consumer guard; if a new DTO/UI path is required, name it and stop for PRIME's bounded extension rather than silently editing outside this lease. The source-quality and broad-corpus gates remain separate.

## Stop and acceptance

Stop on missing typed V2 append/validation support, inability to bind a read to the producing envelope, a needed path outside the lease, or a changed remote base/file collision. Acceptance requires owning service/host tests for admitted and denied anchors, strict pre-read authorization/result persistence, budgets, failed/partial/truncated reads, forged citation flags, final envelope inclusion, V1 replay, and response-wire/UI compatibility. Run focused and relevant repository gates, inspect exact cumulative diff, commit/push one PR, and hand PRIME exact head/evidence. Do not merge or deploy.

**Implementation head/evidence:** pending.
