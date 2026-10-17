# AGENT — saved Build section admission

SETTLED — #1280 merged at 9f0dabf32031f0b6c972956c505d4ae75fa55695.
Successor: [provider/answer inclusion](HANDOFF-AGENT-build-section-provider-inclusion.md).

Serial producer. PRIME implements solo; ARCHITECTURE reviews. Base
04f9f09bbf94ab42e894ecb5e86ae5914adac96b; branch
codex/build-saved-section-admission; non-serving /tmp/prime-recap-mention-boundaries.
Current open Ingest/UI leases are disjoint. #1279 is merged; no implementation
agent delegation or serving lease. This source capability precedes writer inclusion.

One capability: explicit Build-only section authorization and validated receipt in
the existing V3 conversation execution ledger. Context trace remains observational.
Pin exact receipt-owned managed World/document/registry revision/content hash/
visibility, unique read ID, canonical 1-based inclusive line range and conservative
saved-authored-source/not-played class. Authorize before slicing/exposing an
already resolved immutable body; earlier work resolution did load the whole body.
APP independently hashes the COMPLETE transient source proof against its frozen
receipt and computes/verifies the exact UTF-8 slice before persisting a receipt.
No native Graph artifact/anchor identity is manufactured. Retain only the passage,
its digest and source basis for historical readback, not another full source copy.

Validate pairing/cardinality/hash/range/phase and exact receipt basis on fresh
readback. A resolved controller response must precede acquisition; pending/unknown,
post-writer, stale claim, unavailable/mismatched body, malformed or oversized range
cannot expose a validated passage. Unresolved section authorization prevents
later provider authorization. Preserve existing event/storage and per-read text
size bounds; no new authorization call cap. Saved Build passages are a distinct
source category and do not consume native-anchor max_source_read_chars settlement
accounting; the actual frozen per-read maximum and aggregate execution storage
bound still apply. Preserve Unicode and CRLF with
splitlines(keepends=True); no normalization or latest-workspace fallback.

Exclusive writes: this handoff; predecessor
Docs/Plans/HANDOFF-AGENT-build-jev-single-writer.md; Docs/Roadmaps/ROADMAP-demo.md;
src/application_state/agent_conversation/types.py;
src/application_state/agent_conversation/service.py;
src/application_state/agent_conversation/build_section.py;
apps/live_control_server/services/agent_turn_service.py;
tests/test_agent_build_saved_sections.py.
No dependency/migration/UI/provider/runtime selection/serving/corpus/retained data
writes. Existing SQL V3 ledger CHECK constrains envelope/events count/size rather
than per-event kind; prove real PostgreSQL acceptance without a migration.

Tests: real first SDK controller → parent authorize → exact source slice → APP
receipt → fresh service/model reload; Unicode/CRLF, source drift, wrong World/
visibility/revision/digest, forged snippet with valid self-hash, duplicate/missing
pair, pending/unknown/post-writer, stale and concurrent CAS, unavailable trace,
no provider exposure for pending receipt. Existing Graph/source/controller/writer
regressions. Synthetic HTTP and unique disposable PostgreSQL only. Exact cumulative
review required. Writer source inclusion, qualified citations/open targets, Jev
planner, ordinary runtime and full-pilot parity are separate successor work.
