# INGEST — native review context V2

ACTIVE — PRIME explicitly allocated this first read-only-context implementation after independent approval of OverMind PR65 head bada8450c0a5c68e39e7872625fcc103fdc6c203, merged b301121601560fd91f0906c5f0121afa10fe87c4. Design: `DungeonOverMind/Docs/Plans/HANDOFF-INGEST-native-review-context-caller.md` at that merge. No standing identity publication, reviewed-choice producer, WK bridge, runtime cutover or full-clone lease follows.

## Lane and invariant

Serial, one implementation PR. Existing checkout `/home/drakosfire/Projects/.codex/249d/DungeonMindBuddy`; branch `codex/native-review-context-v2`; fetched base `1447a1fde55932fe8395dd99a88124d02f212d08`. Open1853/1855/1868 inspected; PRIME explicitly transferred only the selection-context/selected-knowledge portions below, with no overlap with their current paths. Core remains accepted4ccd; no package/lock or environment changes.

The authenticated existing selection-context HTTP route and agent selected-knowledge consumer receive one tagged native-review V2 packet. Frozen candidate/source proposals remain separate from admitted native assertions. Server derives exact native World, campaign, session, GM role, established/provisional standing and immutable revision. Use existing Core vNext queries and coherent source views, not another policy/ranker/facade. An identity-only hit, unavailable support, absent or ambiguous alternative is never an accepted PC choice. A shared World source body cannot widen campaign assertion admission.

Concrete source spelling: the approved design's semantic session recap means existing product `source_domain="recap"` for ExtractionRun/source SQL. Require that literal plus exact nonblank agreeing run/source campaign/session. No new domain value/profile or generic/worldbuilding fallback.

Authenticate/owner/intent/reconcile first. A completed durable turn replays the original result before ANY current run/native/source validation. Only new/unfinished execution rebuilds V2 and checks hash/drift/size/provenance before provider authorization. Null-selector submitted intent fingerprint semantics stay unchanged.

## Exclusive write lease

- This handoff.
- `src/graph_memory/ingestion/selection_context.py`.
- `apps/live_control_server/models/ingest_selection_context.py`.
- `apps/live_control_server/routes/extract_promote.py`: only `post_ingest_selection_context` and necessary selection-context imports.
- `apps/live_control_server/services/ingest_selection_context.py`.
- New `apps/live_control_server/integrations/dungeonmind/vnext_review_context.py`.
- `apps/live_control_server/models/agent_turn.py`, `src/application_state/agent_conversation/types.py`: only selected-knowledge V2 parsing/persistence contracts.
- `apps/live_control_server/services/agent_turn_service.py`: only selected-knowledge reconstruction/hash/size/provenance; preserve existing completed replay ordering.
- `tests/test_ingest_selection_context.py`, `tests/test_agent_selected_knowledge_context.py`, new `tests/test_native_ingest_review_context.py`.

No other Build/Plan/Play intent/routing/media paths, Core/WK code, pin/lock, schema, native graph writes, identity producer/writer or alternate provenance authority. Return expanded path/contract or new design issue before editing.

## State and preflight

Evidence root `/home/drakosfire/Projects/.codex/historical-graph-repair/cache/native-review-context-v2`. Pre-code primary APP54331 read-only repeatable-read inventory `pre-code-selector-inventory.json` at2026-10-29T01:06:02.644670Z (Oct28 local):43JSONcolumns,0nonnull selectors,0Ingestturns,0selection provenance references. Controls true/true/false; retained turns Build228/Plan155/Play11. This satisfies the repeated inventory gate for code transition, not deployment. No permanent dual V1/V2 live APIs; preserve historical bytes and null-selector fingerprints. If new actual V1 data appears, stop for its preservation case.

Native test state is `InMemoryNativeSourceEvidenceRepository`/existing governed domain fixtures only. APP tests use existing `tests.application_state.conftest.application_state_dsn`: localhost54329 admin, unique `dungeonbuddy_app_state_test_<12hex>` database per fixture, normal upgrade and fixture-owned teardown. Record instantiated fixture identities in test evidence where available. No primary native54330/APP54331 writes, no corpus writes, no new full clone/worktree/environment, no provider calls. Test temporary files stay under this task's cache with a dedicated pytest basetemp. Do not point truncating fixtures or cleanup at primary/baseline databases.

No change to running API8000/UI5202 is allocated. Before eventual delivery, repeat the selector inventory. PRIME must briefly stop/deny only new Ingest selected-knowledge submissions, let accepted requests reconcile, inventory again, switch route+agent consumers together, then reopen Ingest. Other surfaces remain available. If a nonnull V1 selector appeared, stop rather than convert it. These barrier mechanics are a delivery proposal, not permission to activate them here.

## Proof and handback

Exercise actual authenticated HTTP and agent reconstruction/provenance consumers, cross-campaign assertions sharing one source, exact frozen scope, absent/unsupported/ambiguous outcomes, source/head/binding drift, integrity errors, hash/size and completed replay without current reads/provider. Assert read-only native/file conservation and preserve existing null-selector fingerprints. Synthetic positives are component-only; actual6PC acceptance remains unavailable before lawful standing publication. Full-system ingestion stays0/15.

Implement, verify owning boundaries, inspect cumulative base-to-head diff, commit/push/open this one PR. PRIME owns independent exact-head review, merge and delivery. Author checks do not self-accept benchmark results. Preserve original captures/harness expectations and return exact head, fixture/conservation evidence and outstanding holds.

## Implementation evidence and remaining gates

The existing HTTP and agent contracts now require explicit V2 tags. The resolver requires literal recap plus exact agreeing nonblank campaign/session and an active managed World. Its native adapter uses Core's public source-access context (verified immutable revision plus coherent source view), Buddy's existing campaign read-context constructor and Core entity/search/evidence services. It records projection inputs, revision/head, source epoch, descriptor refs, existing search limits/completeness and alternatives. Exact ID hits without admitted assertions remain insufficient support; multiple alternatives remain ambiguous. No search result approves identity. Evidence previews contain exact admitted span text rather than the shared source body. Core admission/provenance is explicitly distinguished from unverified semantic entailment. Head/binding/run drift refuses and the entire packet is hashed.

Author boundary checks: **64/64 passing** across selection HTTP/source tests37, durable selected-knowledge tests16 and native component/HTTP/agent tests11. Additional unchanged binding/replay checks:9passed,1inherited failure. Combined74checks:73passed,1failed. The inherited `test_managed_world_graph_projection.py::test_unresolvable_or_unverified_binding_fails_before_native_read[unbound]` expects `native_graph_binding_missing`, while current main returns `native_graph_provisioning_pending`. It reproduces alone; its test and owning binding/World-registry code have no diff from base1447a1f. Both outcomes refuse before native reads. Do not silently repair this outside the lease or call the combined run green.

Evidence: `test-results-final.xml` in the task cache. Actual recorded integration APP fixture `dungeonbuddy_app_state_test_16fcfaaf2079` on localhost54329; fixture teardown verified absent afterward. Native tests use only an in-memory repository and explicitly seeded component witnesses, never standing publication evidence. The source/candidate file conservation test and native repository-state conservation test pass. Completed durable replay forbids all current run/source/native/binding access and dispatches no additional provider. The existing null-selector fingerprint check passes. The V1 unbound/worldbuilding acceptance tests were deliberately replaced with V2 recap-only refusal expectations under the approved contract; no historical benchmark score or capture changed.

Test interpreter is reused `/home/drakosfire/Projects/buddy-benchmark-worktree/.venv/bin/python`: accepted Core4ccd39a, cryptography46.0.7, pytest9.0.2 and FastAPI0.136.3. This is not a claim of full product-lock environment equivalence. No dependency/environment changes, primary writes, provider calls, graph publication or running-service switch occurred. Initial sandbox execution could not write the designated cache; authorized execution outside that filesystem restriction succeeded. Intermediate fixture-authoring failures are not product acceptance evidence.

Independent review, merge and coordinated runtime cutover remain PRIME-owned. Repeat the selector inventory under the proposed short Ingest-only admission barrier before delivery; this PR does not activate the barrier. Real6PC acceptance remains unavailable and full-system ingestion stays **0/15 verified**. The next separately allocated capability must establish lawful standing/reviewed choices before the retained recap can be published and ordinarily read back; this read capability does not satisfy that milestone.
