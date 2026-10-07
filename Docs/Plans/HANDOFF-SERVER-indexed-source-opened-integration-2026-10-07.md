# HANDOFF — SERVER: indexed source opened completion witness

**Status:** REVIEW READY under PRIME's bounded integration lease. **Exact base:** Buddy `main@2305bf9c3c99f3a25df63046e58fc589ad65a359` (#1015 and #1016 merged). **Code head:** `43077d5a0dd7cb555d922cccf35571d625281fa4`; the final PR head adds this handoff only. PRIME owns independent review and merge. This branch is separate from draft operational rollout #1014 and grants no live runtime, provider, or data lease.

## Primary question and lease

Can one saved-Plan/World turn use a source discovered only through the complete bounded native index, independently admit its exact Graph target/ref through a later operation, open the frozen anchor in its active retrieval session, and persist a producing attempt whose Graph and source-read events justify `source_opened=true`?

Write lease: the directly owning route/service tests and this handoff. Existing SERVER production paths (`integrations/dungeonmind/world_graph_reads.py`, `routes/agent.py`, `services/agent_turn_service.py`) were inspected but needed no change. No APP-STATE types/migration, Core, schema, provider prompt, UI, or generic framework change is in scope.

## Witness

The route test now uses a pinned in-memory native Graph and a digest-pinned local Markdown sign source, plus disposable PostgreSQL application state. Its saved Plan selects an unrelated tavern scene, so `ev:sign` is absent from initial retrieval and the first provider packet, but present in the complete index's frozen source scope. The parent Graph search for Crossroads Sign admits `rel:sign-watchtower` with `ev:sign` into the active retrieval session. The parent then authorizes and executes the real source reader for the exact indexed anchor; the excerpt says the sign points toward the old watchtower. The second producing provider envelope includes both exact tool outputs. The stored attempt includes the validated Graph event and validated source-read event; the persisted APP-STATE completion and response citation derive `source_opened=true` with the read receipt ID. No external provider or live corpus was used.

The adjacent offline host fixture previously produced a Graph citation for out-of-dispatch evidence after expansion alone. #1015 now correctly rejects that answer, so its fake final answer is a Plan-only response while retaining the host expansion, authorization, HTTP, history, and replay checks. The V1 service fixture similarly seeds `ev:one` into its legitimate initial dispatched packet before testing later Graph-operation binding, preserving its V1 lifecycle and completion coverage. Neither fixture grants index membership alone as evidence.

## Verification and limits

- Focused route, turn-service, and source-admission suites: **110 passed** on disposable PostgreSQL 16 after the code change. Ruff on both changed test files, `uv lock --check`, and `git diff --check` passed.
- The exact code paths, dependency lock, migration files, and changed tests are byte-identical across the #1016 rebase; #1016 changed only PlanSurfacePage UI and its test. The single owning route witness is rerun against the final code head after this handoff is committed.
- The first baseline attempt could not connect to the expected disposable PostgreSQL port; an isolated `postgres:16-alpine` container supplied the test fixture. The unmodified baseline route test then failed at its old out-of-dispatch citation, as expected under #1015; the two old V1 service variants failed for the same now-invalid support assumption. Those fixture assumptions were corrected, not production behavior.
- This proves the synthetic/public contract path, not a live provider answer, content truth of the current corpus, or UI delivery timing. Existing live Graph adoption and manual history-refresh issues remain separate.

**Acceptance proposed:** `SERVER_INDEXED_SOURCE_OPENED_INTEGRATION_ACCEPTED`, subject to PRIME exact-head review. No live deployment or merge is authorized by this handoff.
