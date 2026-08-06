# HANDOFF — OPT01 serve one verified World Graph revision resident

**Created:** 2026-08-06.
**Status:** ACTIVE — dispatch exactly one implementation capability.
**Canonical handoff path:** `Docs/Plans/HANDOFF-opt01-resident-verified-world-revision.md`
**Conversation name:** `Optimization — Resident World Runtime Kickoff`
**Flow / agent:** `OPTIMIZATION`
**Handoff direction:** `DESIGN → CODE`
**Design agent:** `Optimization Designing Agent`
**Code agent:** `Optimization Coding Agent`
**PR title:** `OPTIMIZATION: serve verified resident World Graph revision`
**Suggested branch:** `opt/opt01-resident-verified-world-revision`
**Base revision:** `b6d1df07fae7b28760994509dcf2ae9bd8fb74c7`

> **Dispatch gate:** This is the kickoff PR for the Optimization line. It may run in parallel with Build and Statblock only because it operates below their public projection and hydration contracts. If implementation requires a surface contract, route schema, publication protocol, durable storage format, or contribution-merge change, stop and return to the Optimization Designing Agent.
>
> This checked-in handoff is the complete authority. Do not compress, replace, or reinterpret it before implementation. The PR description is only a transport pointer.

## §0 Optimization line charter

The Optimization line exists to make the World Graph feel continuously present without reopening graph authority, projection meaning, or surface design.

The line proceeds in this order:

```text
OPT01  verified resident revision read runtime          ← this handoff
OPT02  revision-ready notification and post-commit prewarm
OPT03  bounded serving recipes / surface bootstrap
OPT04  delta-aware publication and materialization
```

Only OPT01 is authorized here.

### Why this slice is parallel-safe

Current Build and Statblock work may continue changing how their surfaces present, request, and compose graph-derived objects. OPT01 must not decide those questions. It changes only how the Graph Kernel obtains the exact immutable revision and contribution authority used by existing projection code.

```text
existing Plan / Build / Statblock / Hermes callers
                  │
                  ▼
existing request and response contracts
                  │
                  ▼
existing projection semantics
                  │
                  ▼
NEW: verified resident revision read context
                  │
                  ▼
current file-backed World Supergraph
```

The public behavior above the new seam remains unchanged. The hot-path durable I/O below the seam changes deliberately.

### The problem this PR owns

The current warm projection cache still performs graph-scale work before a cache hit:

* it reads and hashes `head.json`;
* it reads and hashes the selected revision manifest and graph payload;
* for pinned requests, it also hashes the current head revision payload;
* it reads and hashes the contribution index and every contribution JSON;
* query requests bypass the response cache;
* a cold projection reloads and verifies the revision, then repeatedly reloads contribution records while reconstructing active assertion authority;
* source-span paragraph indexes may also be reread during projection construction.

The result is that a “warm” request can still scale with total graph and ledger bytes, and different request recipes reconstruct the same verified revision independently.

OPT01 replaces that behavior with one process-local, exact-revision read runtime. It does not optimize the durable write path.

## Shared vocabulary

| Term                        | Definition                                                                                                                                                                                                         |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Resident revision**       | One exact immutable World Graph revision whose manifest, canonical graph bytes, parsed store, active contribution records, and required read indexes were loaded and verified once for the current server process. |
| **Resident generation**     | A process-local opaque generation assigned to one successful cold load. It is never serialized or treated as durable identity.                                                                                     |
| **Head observation**        | A small per-request read and validation of `head.json`, yielding one exact `head_revision_id`. It is not a graph-payload verification.                                                                             |
| **Projection read context** | The selected resident revision plus the verified resident revision named by the current head observation, together with exact revision IDs and process-local generations.                                          |
| **Cold load**               | Durable reading, parsing, and integrity verification required to create a resident revision generation.                                                                                                            |
| **Resident hit**            | Resolution of an already verified resident generation without rereading or rehashing its revision payload, contribution ledger, contribution records, or source-span indexes.                                      |
| **Coalesced load**          | Multiple concurrent callers for the same `(root, world_id, revision_id)` sharing one cold load result.                                                                                                             |
| **Backing health**          | Process-local knowledge about whether an explicit scrub found the durable files still match a resident revision. It does not replace revision identity.                                                            |
| **Projection cache**        | A secondary process-local cache of completed projection payloads keyed only after a projection read context has been resolved. It is never authority.                                                              |

## Agent flow and nano-commit contract

`OPTIMIZATION` is a new parallel operating flow. Do not modify the shared handoff template merely to add the name in this implementation PR.

Use nano commits. A suitable sequence is:

1. characterize and prove current durable-read behavior;
2. introduce resident revision loading and lifecycle tests;
3. route projection authority reconstruction through the resident context;
4. replace fingerprint-before-cache behavior with context-keyed payload caching;
5. add structured timing/counter evidence and adversarial regressions;
6. complete handback evidence only after all owning tests are rerun.

The implementation may choose a different nano-commit decomposition, but every commit must tell one discrete implementation or proof story.

## §1 Mission and merge-ready invariant

**Mission:** Projection callers can reuse one exact verified World Graph revision so that repeated reads of that revision do not reread or rehash immutable graph, contribution, or admitted source-index files.

**Merge-ready invariant:** Every projection response is still derived from the exact world, selected revision, current observed head revision, campaign scope, focus, admissibility, and query named by the existing request contract, while each resident generation is admitted only after one complete fail-closed verification, concurrent callers share that generation, completed projection caches cannot outlive it, and later out-of-band backing mutation can neither poison nor silently replace the already verified in-memory authority.

### Pre-dispatch critique

| Question                                                     | Answer                                                                                                                                                                                                                                                   |
| ------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Can one invariant govern every claimed observable path?      | Yes. Every path is an exact projection read whose durable authority is either admitted into one resident generation or rejected before residency.                                                                                                        |
| What adversarial sequence is most likely to falsify it?      | Head revision A begins a cold load → head advances to B → B becomes resident first → A finishes later → an implementation-global “current” pointer or payload cache incorrectly replaces B with A.                                                       |
| Would the proposed §7 evidence actually detect that failure? | Yes. The ordered head-advance/interleaving test requires B to remain the head-following context, while A may exist only as an exact pinned resident revision.                                                                                            |
| Which owning boundary is easiest to under-test?              | Contribution authority reconstruction. A projection can appear correct while still rereading contribution files or reusing a payload cache that bypasses a failed resident load. Deterministic read counters and a different-query request are required. |
| What fact would force this slice to stop or split?           | Any requirement to change the projection request/response schemas, Build/Statblock callers, publication/commit paths, contribution merge semantics, or durable World Graph layout.                                                                       |

## §2 Context, authority, and boundaries

| Field                | Required content                                                                                                                                                                                                                                                                                                                 |
| -------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Parent authority     | `Docs/Design/ARCHITECTURE-campaign-supergraph.md`; `Docs/Roadmaps/ROADMAP-campaign-supergraph.md`; `Docs/Plans/PR-TRACKER-campaign-supergraph.md`; `Docs/Design/ARCHITECTURE-surface-interaction-layer.md`                                                                                                                       |
| Repository rules     | One World Supergraph per world; immutable revisions; atomic head advancement; exact revision-pinned projections; graph-first reads; no latest-ingest or preview fallback; surfaces do not own graph state; Graph Kernel is the legal runtime boundary.                                                                           |
| Base revision        | `b6d1df07fae7b28760994509dcf2ae9bd8fb74c7` as observed on `main` on 2026-08-06. Re-resolve before implementation.                                                                                                                                                                                                                |
| Predecessor contract | PR #440 process-local World Graph projection cache; current `WorldGraphProjectionRequest` / `WorldGraphProjection`; current `graph_memory.kernel.project_world_graph`; current exact Threat projection and Build graph-reference consumers.                                                                                      |
| Exact input consumed | `WorldGraphProjectionRequest`, validated `head.json`, immutable `revision.json` + canonical `graph.json`, active contribution records referenced by revision support, and current best-effort source-span index files admitted by the revision.                                                                                  |
| Named successor      | `OPT02 — revision-ready notification and post-commit prewarm`, after the human/Statblock publication protocol settles.                                                                                                                                                                                                           |
| What remains false   | A newly committed revision is not loaded in the background; writes still rebuild and serialize whole-world state; projection responses may still be broad and expensive to construct/serialize; browser callers may still request too much data.                                                                                 |
| Explicit non-goals   | New projection endpoints; bounded search/object/adjacency APIs; Build or Statblock UI changes; Threat progressive hydration; Play migration; graph write optimization; publication events; PostgreSQL or DungeonMind cutover; filesystem watcher; scheduled background scrub; cache-management route/panel; benchmark dashboard. |

### Authority read order

Read these in order before changing code:

1. `Docs/Design/ARCHITECTURE-campaign-supergraph.md`
2. `Docs/Plans/PR-TRACKER-campaign-supergraph.md`
3. `Docs/Roadmaps/ROADMAP-campaign-supergraph.md`
4. `Docs/Design/ARCHITECTURE-surface-interaction-layer.md`
5. `apps/live_control_server/services/world_graph_projection.py`
6. `src/graph_memory/world_projection_cache.py`
7. `src/graph_memory/kernel/world_projection.py`
8. `src/graph_memory/kernel/__init__.py`
9. `tests/test_world_graph_projection_service.py`
10. `tests/test_graph_kernel_world_projection.py`
11. `tests/test_graph_kernel_boundaries.py`

If the base moved, rebase before implementation. If merged Build or Statblock work changed only callers above the projection contract, continue. If it changed an allowlisted kernel/service path or the exact projection contract, stop and report the collision.

### Current implementation facts this handoff depends on

1. `apps/live_control_server/services/world_graph_projection.py` computes a full source fingerprint before looking up the process projection cache and computes it again before insertion.
2. `src/graph_memory/world_projection_cache.py` hashes the contribution index, every contribution file, `head.json`, the selected revision graph/manifest, and—when different—the head revision graph/manifest.
3. Requests with `query_text` bypass the service projection cache.
4. `src/graph_memory/kernel/world_projection.py` loads and verifies the current head target for pinned and unpinned requests, then separately loads a pinned selected revision when required.
5. Projection authority reconstruction loads contribution records from durable storage while resolving active support and aliases.
6. Existing projection responses already name exact selected and head revisions. OPT01 must preserve those schemas and meanings.

### Parallel-work collision rule

PR #508 currently touches `src/graph_memory/kernel/contribution_merge.py` and publication paths. Those paths are explicitly outside OPT01. If OPT01 appears to need them, the slice has crossed into publication and must stop.

No TypeScript or React path is authorized. Build and Statblock should be able to merge or rebase independently of OPT01.

## §3 Observable-path and adversarial-sequence inventory

| Path                                                    | Current behavior                                                                               | Required behavior                                                                                                                                                                          | Same invariant as §1? | Owning boundary                                    |
| ------------------------------------------------------- | ---------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------: | -------------------------------------------------- |
| First unpinned projection for a world/revision          | Reads/verifies head target, revision payload, contributions, source indexes; builds projection | Performs one cold load, admits one resident generation, builds unchanged projection                                                                                                        |                   Yes | Graph Kernel resident runtime + projection builder |
| Repeated unpinned projection, same head                 | Rehashes all cache inputs before a possible payload-cache hit                                  | Reads/validates only `head.json`; performs zero additional graph/revision/contribution/source-index reads or hashes                                                                        |                   Yes | Resident runtime + service cache boundary          |
| Query projection                                        | Bypasses process payload cache and reconstructs the revision                                   | Resolves the same resident generation; query text may use a context-keyed payload cache or rebuild only projection CPU work, never durable revision I/O                                    |                   Yes | Kernel projection entrypoint                       |
| Exact pinned historical projection                      | Verifies current head target and pinned selected revision on every cold path                   | Reuses resident head and selected revisions; response still names both exact IDs and correct `is_head`                                                                                     |                   Yes | Resident context resolver                          |
| First projection after head advance                     | Cold-loads new head revision                                                                   | Observes new head ID, coalesces one cold load for it, retains old revision for pinned reads                                                                                                |                   Yes | Head resolver + resident registry                  |
| Simultaneous first requests                             | Each can repeat expensive loading                                                              | Exactly one cold load per exact resident key; waiters receive the same ready generation or same failure                                                                                    |                   Yes | In-flight load coordinator                         |
| Cold-load integrity failure                             | Fails projection                                                                               | Fails closed with existing stable projection error mapping; no ready resident or payload-cache entry is created                                                                            |                   Yes | Cold loader + service mapper                       |
| Out-of-band graph/contribution mutation after residency | Current cache intentionally misses and ordinary request rediscovers corruption                 | Ordinary reads continue from the already verified resident generation without rereading mutated bytes; explicit scrub marks backing unhealthy; runtime clear/restart re-verifies and fails |                   Yes | Resident trust boundary + scrub                    |
| Malformed or mismatched `head.json` after residency     | Cache fingerprint forces miss and kernel fails                                                 | Every request still reads/validates `head.json` and fails closed; no old head is silently substituted                                                                                      |                   Yes | Head observation boundary                          |
| Browser hard refresh with server still running          | Client cache is lost; server repeats fingerprint work                                          | Server resident generation survives and is reused                                                                                                                                          |                   Yes | Server process runtime                             |
| Server restart / explicit runtime clear                 | Cache lost                                                                                     | No resident authority survives; next request performs complete verification again                                                                                                          |                   Yes | Runtime lifecycle                                  |
| Existing projection route/service error                 | Stable service envelope                                                                        | Same status/code/diagnostics unless this handoff explicitly names a changed trust case                                                                                                     |                   Yes | Service error mapper                               |

### Ordered adversarial sequences

| Sequence                                                                                                                             | Required safe outcome                                                                                                                              | Owning proof |
| ------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------- | ------------ |
| Two threads request the same cold revision → loader is blocked → both continue                                                       | One durable load; both receive the same resident generation; no duplicate contribution/source-index reads                                          | E2           |
| Head A observed → A load blocks → head advances to B → B loads and serves → A completes                                              | B remains the head-following result; A may be retained only as an exact resident/pinned revision; no global pointer or cache regresses to A        | E5           |
| Revision A becomes resident → `graph.json` and one active contribution are corrupted on disk → same and different-query requests run | Both requests continue to return data from resident A with zero additional durable revision reads; no mutated bytes enter memory                   | E6           |
| Previous sequence → explicit scrub A                                                                                                 | Scrub reports/records unhealthy backing without replacing or mutating resident A                                                                   | E6           |
| Previous sequence → runtime clear simulates restart → request A                                                                      | Complete verification reruns and fails with `projection_integrity_error`; no old payload cache can answer                                          | E6           |
| Cold load fails halfway after manifest/graph read → waiter exists → files repaired → retry                                           | First caller and waiter receive failure; no partial resident exists; next request performs a new load and can succeed                              | E3           |
| Valid resident A exists → `head.json` world ID or revision ID is malformed                                                           | Request fails closed even though A is resident; no fallback to cached head metadata                                                                | E4           |
| Payload cache contains projection for resident generation G1 → runtime clear → same revision reloads as G2                           | G1 payload cannot be returned under G2; cache key/lifecycle binds completed projections to exact resident generations                              | E7           |
| Pinned A request resolves current head B → A and B resident → head advances C                                                        | New unpinned request uses C; a later pinned A response names head C and selected A; no stale `head_revision_id` is smuggled from a cached response | E5/E7        |

## §4 Files in scope (allowlist)

| Action | Path                                                           | Purpose: how this establishes or proves §1                                                                                                                                                                  |
| ------ | -------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Create | `Docs/Plans/HANDOFF-opt01-resident-verified-world-revision.md` | Checked-in authority and final §8 handback.                                                                                                                                                                 |
| Create | `src/graph_memory/kernel/world_read_runtime.py`                | Own resident generations, cold-load verification, contribution/source-index admission, coalescing, lifecycle, health inspection, and deterministic counters/timings.                                        |
| Modify | `src/graph_memory/kernel/world_projection.py`                  | Resolve one projection read context and reconstruct projection authority from resident data rather than durable contribution/source-index reads. Preserve public projection schemas and semantics.          |
| Modify | `src/graph_memory/kernel/__init__.py`                          | Export only the minimal Kernel-owned runtime lifecycle/inspection symbols required by service/tests; do not expose storage internals to surfaces.                                                           |
| Modify | `src/graph_memory/world_projection_cache.py`                   | Replace file-fingerprint cache keys with exact resident-generation context keys; remove graph-scale fingerprinting from the request path; preserve tiny process-local LRU/TTL semantics where still useful. |
| Modify | `apps/live_control_server/services/world_graph_projection.py`  | Stop pre-request/post-request source hashing; call the Kernel boundary; emit structured optimization timing/counter observations; preserve error envelope behavior.                                         |
| Create | `tests/test_graph_kernel_world_read_runtime.py`                | Own cold admission, coalescing, retry, head interleaving, scrub, clear/restart, and deterministic durable-read-count proofs.                                                                                |
| Modify | `tests/test_world_graph_projection_service.py`                 | Replace per-request tamper-discovery cache tests with the explicit resident trust contract; prove service payload caching cannot bypass context resolution.                                                 |
| Modify | `tests/test_graph_kernel_world_projection.py`                  | Prove cold and warm projections are contract-equivalent and resident contribution reconstruction preserves exact authority behavior.                                                                        |

**Bounded discovery exception:**

```text
Directory: tests/fixtures/world_graph_runtime/
Maximum additional paths: 3
Allowed path kinds: small JSON fixture files only
Decision rule for including one: only when a deterministic concurrent/tamper test cannot be expressed by the existing world-initialization helpers without copying a large corpus fixture.
```

Prefer existing initialization helpers. Do not use this exception for snapshots of broad projection payloads or benchmark output.

If another production path is required, stop. Do not silently add routes, storage modules, publication modules, or frontend files.

## §5 Files and capabilities explicitly out of scope

| Path, layer, or capability                                              | Why this slice must not touch or claim it                                                                                                                               |
| ----------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `apps/live-control-ui/**`                                               | Build, Plan, Statblock, and Play consumer behavior is settling independently. No caller or UI contract change is required.                                              |
| `apps/live_control_server/routes/**`                                    | Existing route schemas/status mapping are sufficient. A route or response-header change would be a second API capability.                                               |
| `src/graph_memory/projection/**`                                        | Projection DTO/schema meaning is not being redesigned. Change only if a concrete existing-contract defect makes the resident seam impossible; that is a stop condition. |
| `src/graph_memory/world_supergraph/**`                                  | Durable format, path layout, integrity algorithms, and publication storage are predecessor authority, not optimization targets in OPT01.                                |
| `src/graph_memory/kernel/contribution_merge.py`                         | Statblock publication work currently owns this path; write optimization is a later slice.                                                                               |
| `src/graph_memory/kernel/contribution_models.py` and `contributions.py` | Contribution durable semantics are unchanged. Read them, do not alter them.                                                                                             |
| Threat publication / mechanics hydration services                       | Statblock line owns publication and read-composition semantics.                                                                                                         |
| Build graph-reference components                                        | Build line owns graph interaction and surface leases.                                                                                                                   |
| New cache-management endpoint, CLI, panel, or admin API                 | Runtime inspection is internal/test/log evidence only in OPT01.                                                                                                         |
| Background worker, filesystem watcher, scheduled scrub                  | Named successor or operational follow-up.                                                                                                                               |
| PostgreSQL, Neo4j, Materialize, Datomic, or DungeonMind integration     | Storage/runtime cutover is intentionally deferred.                                                                                                                      |
| Whole-world write optimization                                          | OPT04. A commit may still trigger one cold read on the first following projection.                                                                                      |
| Bounded object/search/adjacency projection recipes                      | OPT03 after current surface contracts settle and OPT01 measurements identify remaining cost.                                                                            |

## §6 Implementation contract and conditional matrices

```text
Input:
  Existing WorldGraphProjectionRequest plus the current file-backed World Graph
  head/revision/contribution/source-index artifacts already consumed by the
  projection Kernel.

Output:
  The same WorldGraphProjection or WorldGraphProjectionServiceError contract
  currently observed by callers, derived through a process-local verified
  projection read context.

Invariant:
  Every projection response is still derived from the exact world, selected
  revision, current observed head revision, campaign scope, focus,
  admissibility, and query named by the existing request contract, while each
  resident generation is admitted only after one complete fail-closed
  verification, concurrent callers share that generation, completed projection
  caches cannot outlive it, and later out-of-band backing mutation can neither
  poison nor silently replace the already verified in-memory authority.

Failure behavior:
  invalid request → existing invalid_request behavior
  missing world/head → existing world_graph_unavailable behavior
  malformed head → projection_integrity_error; do not use resident fallback
  cold revision/manifest/payload/contribution integrity failure →
    projection_integrity_error; no ready generation or completed payload cache
  cold I/O/internal failure → existing mapped failure; no partial residency
  coalesced loader failure → all waiters receive the same failed outcome
  explicit scrub mismatch → resident backing marked unhealthy; resident object
    remains unchanged; ordinary reads continue from known-good memory
  runtime clear/restart after backing mismatch → next request re-verifies and fails

Replay / idempotency:
  same exact resident key → same ready generation until eviction/clear/restart
  same exact projection context + request → equivalent payload; secondary cache
    may return the same process object
  different query/focus/campaign/scope → separate projection payload key but the
    same resident selected revision where applicable
  failed cold load → not cached as ready; next request may retry
  clear/restart → all process-local generations and payload cache entries vanish

Trust boundary:
  Verifies on cold admission:
    exact world/revision path safety; revision manifest; canonical graph payload
    hash; graph schema; recomputed content-addressed revision ID; parsed store;
    active contribution identity/world/assertion integrity; required resident
    indexes; current source-index parsing on the same best-effort terms as the
    existing projection path.
  Verifies on each projection request:
    request model; head.json syntax/world identity/safe head revision ID; exact
    selected/head resident context identity.
  Trusts without reproving on each warm request:
    graph.json, revision.json, contribution index/records, and admitted
    source-index bytes already verified/read into the resident generation.
```

### 6.1 Resident key and lifecycle

The durable identity key is exactly:

```text
(resolved_root, world_id, revision_id)
```

Rules:

1. `resolved_root` must be canonicalized before lookup.
2. `world_id` and `revision_id` use existing safety validation; no normalized, alias, path-derived, or first-win identity is permitted.
3. A successful cold load receives a new monotonic or otherwise collision-free process-local resident generation.
4. Resident generation is not persisted, serialized, written into graph data, or returned to UI clients.
5. Default ready-entry capacity is **8 resident revisions** across roots/worlds. Make it configurable only through a process environment setting with a documented default. Capacity must never be less than 2.
6. LRU eviction removes registry ownership only. A projection already holding a read-context reference remains valid because the resident object is immutable by ownership.
7. Loading entries are not exposed as ready and are not evicted. Temporary overflow while concurrent loads finish is preferable to cancelling or duplicating a load.
8. Runtime clear must atomically make all resident generations and completed projection payload entries unreachable to future requests.

### 6.2 Cold admission

One cold load must:

1. load and validate the exact revision manifest;
2. load/parse the exact revision store;
3. read the canonical graph payload bytes;
4. verify `graph_payload_sha256`;
5. verify world ID, revision ID, graph path, graph schema, and recomputed revision ID;
6. enumerate the active contribution IDs required by revision assertion support;
7. load and validate each required contribution record exactly once;
8. build immutable/read-only lookup structures sufficient to ensure warm projection never calls `load_contribution_record`;
9. build a graph-object → active-support index so warm projection does not rescan every support for every object;
10. admit source-span paragraph text used by current projection behavior once per resident generation, preserving current best-effort absence behavior;
11. build any identity context or other deterministic revision-only index that current projection recomputes and that can be reused without changing semantics;
12. publish the resident generation to waiters only after every required step succeeds.

A partially loaded object is never visible as ready.

The runtime must not validate every file merely present in the contributions directory. It validates the exact contribution records required by the selected revision’s durable support. Directory-wide hashing is prohibited on the hot path.

### 6.3 Projection read-context resolution

For every request:

1. Validate the request before storage state so existing invalid-input precedence remains truthful.
2. Read and validate `head.json`. This small head observation is intentionally permitted on every request in OPT01.
3. Resolve the head target to a verified resident generation. Pinned requests must still have a verified head target because response metadata trusts `head_revision_id` and `is_head`.
4. Resolve the selected revision:

   * unpinned → the same generation as the observed head target;
   * pinned → exact pinned resident generation, separately from the head target when IDs differ.
5. Build one projection read context containing exact selected/head IDs and exact resident generations.
6. Only after this resolution may a completed projection cache be consulted.
7. Projection construction must consume the selected resident store, contribution map, support indexes, identity context, and source-index data. It must not fall back to durable loaders.

A head can advance after the context is resolved. The response remains a truthful point-in-time projection because it names the exact head observation used. The implementation must not mix a cache key from one head observation with a projection built from another.

### 6.4 In-flight coalescing

* Coalescing key is the exact resident key.
* Exactly one loader owns durable reads for a missing key.
* Waiters block on that exact outcome; they do not start fallback loads.
* On success, every waiter receives the same resident generation object.
* On failure, every waiter receives the same safe failure class/diagnostics; no ready entry remains.
* A later request may retry after durable repair.
* Completion order must not create or overwrite a global “current revision” pointer. Head following is always resolved from the request’s head observation.

### 6.5 Secondary completed-projection cache

The existing process-local projection cache may remain, but its authority changes:

1. It is consulted only after a projection read context exists.
2. Its key must include:

   * resolved root;
   * world ID;
   * campaign ID;
   * selected revision ID and resident generation;
   * head revision ID and resident generation;
   * focus kind/session/campaign;
   * admissibility;
   * scope mode;
   * complete query text.
3. It must perform **zero durable file reads and zero content hashing** to create or compare a key.
4. Query requests are no longer categorically bypassed. They may be cached when keyed by complete query text.
5. `DMB_WORLD_GRAPH_PROJECTION_CACHE=0` disables only this secondary completed-payload cache. It must not disable or bypass resident revision verification.
6. Runtime clear clears this cache. Eviction/reload produces a new resident generation, so a payload from an older generation cannot be returned.
7. Remove or retire `source_fingerprint`, `ledger_fingerprint`, and any pre/post fingerprint insertion protocol from product request paths. Retaining dead helpers that can accidentally be rewired is not acceptable unless one named non-product consumer is proven.

This cache remains optional optimization. Correctness must hold with it disabled.

### 6.6 Integrity bargain and explicit scrub

This PR intentionally changes one current test assumption:

> Ordinary warm projection requests no longer independently distrust and rehash every immutable durable byte.

After a resident generation is admitted:

* out-of-band mutation of its `graph.json`, `revision.json`, active contribution records, contribution index, or admitted source-index files does not alter the resident object;
* ordinary projection requests do not rediscover that mutation;
* an explicit internal scrub can re-run durable verification against one resident key;
* scrub success records healthy backing;
* scrub mismatch records unhealthy backing and stable diagnostics but does not mutate, evict, replace, or partially refresh the known-good resident object;
* process restart or explicit clear discards the resident object, so the next request must reverify and fail if corruption remains.

`head.json` is different: it remains a per-request observation. Malformed or mismatched head state must fail immediately even when the referenced revision is resident.

No scrub route, CLI, timer, or background worker is authorized. The internal scrub exists to make the changed trust boundary explicit and testable; scheduling it is a successor.

### 6.7 Structured observations

Emit one structured log observation per service request. At minimum include:

```text
world_id
campaign_id
selected_revision_id
head_revision_id
resident_status: hit | miss | coalesced
selected_resident_generation
head_resident_generation
backing_health: unknown | healthy | unhealthy
head_resolution_ms
resident_wait_ms
cold_load_ms (0/null on hit)
projection_cache_status: disabled | hit | miss
projection_build_ms
resident_revision_count
graph_payload_reads_this_request
revision_manifest_reads_this_request
contribution_reads_this_request
source_index_reads_this_request
nodes_returned
relationships_returned
attributes_returned
```

Rules:

* Do not put resident generations, timings, cache status, digests, or health diagnostics into the user-facing projection response.
* Do not introduce a telemetry endpoint.
* Tests must be able to inspect deterministic counters without parsing log text.
* Wall-clock timings are characterization evidence, not the sole merge proof.

### 6.8 Projection semantic equivalence

For the same exact request and unchanged durable inputs:

* cold and warm responses must be model-equal;
* response schema, snapshot fields, trust boundary, diagnostics, counts, node/relationship/attribute/evidence/source-artifact content, query context, and ordering remain unchanged;
* service status/code/diagnostic mapping remains unchanged;
* current Build, Plan, Recap, Threat, and Hermes consumers require no changes;
* no new cache metadata is serialized.

If a current projection semantic defect is discovered, record it and stop. Do not repair it inside OPT01.

### A. State and fallback matrix

| Observable path       | Loading / initializing                             | Exact success                                   | Ordinary miss                               | Dependency unavailable                                          | Integrity / contract failure                                    | Stale / superseded                                  | Retry / replay                          |
| --------------------- | -------------------------------------------------- | ----------------------------------------------- | ------------------------------------------- | --------------------------------------------------------------- | --------------------------------------------------------------- | --------------------------------------------------- | --------------------------------------- |
| Unpinned projection   | Read/validate head; coalesce head target cold load | Build/cache from exact resident head generation | World/head missing stays unavailable        | Durable cold I/O failure maps through existing service behavior | Fail closed; no resident/payload entry                          | Later head change is observed on next request       | Retry allowed; failed load not resident |
| Pinned projection     | Resolve verified head then exact selected pin      | Response names selected pin + observed head     | Missing pin → existing `revision_not_found` | Same as above                                                   | Head corruption or pin corruption fails closed                  | Old pin remains usable after a healthy head advance | Retry allowed                           |
| Warm resident read    | No graph/contribution/source-index load            | Resident context reused                         | Not applicable                              | Head file still required                                        | Malformed head fails; backing mutation is not rediscovered here | Exact resident remains valid by revision identity   | Same request is idempotent              |
| Coalesced waiter      | Waits for exact key owner                          | Receives owner’s generation                     | No fallback load                            | Receives owner’s failure                                        | No partial result                                               | Completion order cannot change head authority       | Later independent retry allowed         |
| Explicit scrub        | Reads durable backing for one resident key         | Marks healthy                                   | Missing resident → stable internal miss     | Returns scrub failure                                           | Marks unhealthy; keeps resident                                 | Does not advance/rollback head                      | Repeatable                              |
| Runtime clear/restart | Drops all process-local state                      | Next request cold-loads                         | Not applicable                              | Cold load may fail                                              | Corrupt backing fails                                           | No previous generation survives                     | Repair then retry                       |

No fallback source is permitted. In particular: no preview union, latest ingest, mutable store path, alternate campaign graph, arbitrary Markdown, or current payload cache before context resolution.

### B. Identity matrix

| Situation                      | Required rule                                                                                         | Ambiguity behavior                                   | Fallback permitted?       |
| ------------------------------ | ----------------------------------------------------------------------------------------------------- | ---------------------------------------------------- | ------------------------- |
| Resident revision key          | Exact resolved root + exact world ID + exact revision ID                                              | Any unsafe or malformed ID fails existing validation | No                        |
| Head identity                  | Exact validated `head.json` world ID and revision ID                                                  | Mismatch/corruption fails closed                     | No resident-head fallback |
| Resident generation            | Process-local opaque identity for one successful cold load                                            | Never compared across processes or persisted         | No                        |
| Label / alias / normalized key | Not used to resolve runtime identity                                                                  | Not applicable                                       | No                        |
| Rename / deletion / rebind     | Immutable revision ID does not rename; missing backing is discovered on cold load/scrub, not by label | No first-win behavior                                | No                        |

### C. Persistence and replay matrix

| Operation               | Durable representation         | Round-trip guarantee                                    | Duplicate / replay behavior               | Compatibility / migration         | Rollback / reversion               |
| ----------------------- | ------------------------------ | ------------------------------------------------------- | ----------------------------------------- | --------------------------------- | ---------------------------------- |
| Resident admission      | None; process-local only       | Derived from one fully verified existing revision       | Same key reuses generation                | No durable migration              | Clear/restart removes it           |
| Completed payload cache | None; process-local only       | Equivalent projection for exact context/request         | Same key may reuse object                 | Existing env disablement retained | Clear/TTL/LRU removes it           |
| Head advance            | Existing `head.json`           | Next request observes exact new ID                      | Repeated same head reuses resident target | No format change                  | Existing rollback behavior remains |
| Explicit scrub health   | Process-local observation only | Does not alter durable bytes or projection response     | Repeatable                                | No migration                      | Clear/restart forgets health       |
| Server restart          | Existing graph files only      | Full verification reconstructs equivalent resident data | No old process cache survives             | No migration                      | Not applicable                     |

No new persisted format, schema, identifier, manifest field, or receipt is authorized.

### D. Predecessor-to-consumer mapping

**Grounding sources:** current `WorldGraphProjectionRequest` / `WorldGraphProjection` models; current service error envelope; current `kernel.project_world_graph`; current PR #440 cache tests.

| Predecessor field / outcome                | Real shape and optionality                        | Consumer field / behavior                                 | Transformation                                                 | Proof fixture/test |
| ------------------------------------------ | ------------------------------------------------- | --------------------------------------------------------- | -------------------------------------------------------------- | ------------------ |
| `request.world_id`                         | Required string, existing validation              | Resident key + unchanged snapshot                         | Exact value only                                               | E1/E4              |
| `request.campaign_id`                      | Required campaign scope                           | Unchanged projection lens and payload-cache key           | No normalization beyond existing request model                 | E1/E7              |
| `request.revision_pin`                     | Optional exact revision ID                        | Selected resident revision                                | `None` → observed head; value → exact pin                      | E1/E5              |
| `request.focus`                            | Existing typed focus                              | Unchanged projection build and cache key                  | No semantic change                                             | E1/E7              |
| `request.admissibility`                    | Existing policy                                   | Unchanged projection validation                           | No semantic change                                             | E1                 |
| `request.scope_mode`                       | Existing campaign/world scope                     | Unchanged projection filter and cache key                 | No semantic change                                             | E1/E7              |
| `request.query_text`                       | Optional string                                   | Unchanged query context; now eligible for exact cache key | Full string, no truncation/normalization beyond existing logic | E1/E7              |
| `head.head_revision_id`                    | Required exact revision ID                        | Snapshot `head_revision_id`; `is_head` comparison         | Read/validate on each request                                  | E4/E5              |
| Cold `projection_integrity_error`          | Existing 409 service mapping                      | Same API error                                            | No new fallback                                                | E3/E4/E6           |
| PR #440 `DMB_WORLD_GRAPH_PROJECTION_CACHE` | Default enabled; disables completed payload cache | Same operator switch for payload cache                    | No longer disables resident runtime                            | E7                 |

## §7 Evidence required to merge

Structural elimination of durable work is the primary proof. Raw elapsed-time improvement is required to be recorded, but a noisy wall-clock benchmark cannot substitute for deterministic I/O and concurrency evidence.

| ID  | Guarantee / invariant clause                                                     | Owning boundary           | Evidence class            | Command or manual scenario                                               | Expected evidence                                                                                                                            | Stop condition                                                                |
| --- | -------------------------------------------------------------------------------- | ------------------------- | ------------------------- | ------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| E1  | Cold and warm projection responses preserve the existing exact contract          | Kernel projection builder | Contract/regression       | Focused runtime + projection tests                                       | Cold/warm model equality across unpinned, pinned, focused, and query requests                                                                | Any payload/schema/order/trust-boundary difference                            |
| E2  | Concurrent callers share one cold load                                           | Resident registry         | Adversarial/concurrency   | Barrier-controlled multi-thread test                                     | One manifest/graph/contribution/source-index load; same generation for all callers                                                           | Duplicate loader or divergent result                                          |
| E3  | Failed or partial cold loads never become resident and can retry                 | Cold loader/coordinator   | Failure injection         | Fail manifest, graph, contribution, and mid-load cases; repair and retry | All waiters fail safely; resident count unchanged; repaired retry succeeds                                                                   | Poisoned/partial entry or non-retryable failure                               |
| E4  | Per-request head observation remains fail-closed                                 | Head resolver/service     | Contract/adversarial      | Warm resident then corrupt/mismatch `head.json`                          | Existing 409 `projection_integrity_error`; no resident fallback                                                                              | Cached response returned or old head substituted                              |
| E5  | Head advance and stale completion cannot regress authority                       | Context resolver          | Adversarial/interleaving  | A load blocked, head advances B, B serves, A finishes; pinned old read   | B remains head-following; A exact pinned only; response IDs truthful                                                                         | Global current pointer/cache regresses to A                                   |
| E6  | Post-residency mutation cannot poison memory; scrub/restart behavior is explicit | Resident trust boundary   | Adversarial/integrity     | Warm A, mutate graph+contribution, warm reads, scrub, clear, reread      | Warm reads unchanged with zero durable reads; scrub unhealthy; post-clear read fails                                                         | Mutation enters resident, warm read hashes files, or old cache survives clear |
| E7  | Completed payload cache is subordinate to exact resident context                 | Service/cache             | Contract/adversarial      | Cache on/off, query cache, generation G1 clear/reload G2, head changes   | Zero file reads for keying; query eligible; G1 cannot answer G2; correctness with cache disabled                                             | Fingerprinting remains or cache bypasses context resolution                   |
| E8  | Warm requests perform no graph-scale durable I/O                                 | Kernel/service counters   | Deterministic performance | First request then different lenses/queries same revision                | Second+ requests: 0 revision manifest reads, 0 graph payload reads, 0 contribution reads, 0 source-index reads; `head.json` read allowed     | Any repeated graph/revision/contribution/source-index read/hash               |
| E9  | Existing Kernel boundary remains intact                                          | Repository guard          | Boundary/regression       | `tests/test_graph_kernel_boundaries.py`                                  | No new imports of storage internals outside Kernel; service imports Kernel boundary only                                                     | New exemption or illegal adapter import                                       |
| E10 | Real Eldyrwild navigation uses resident runtime across surfaces                  | Existing live surfaces    | Manual/dogfood            | Plan → Build → Plan → Threat read/query → browser hard refresh           | One cold resident load for the exact revision; subsequent requests resident/coalesced hits; exact revision unchanged; timing ledger captured | Requires UI change, write, new panel, or cannot identify exact revision       |

### Required commands

Run and record exact results:

```bash
uv run pytest tests/test_graph_kernel_world_read_runtime.py -q

uv run pytest \
  tests/test_world_graph_projection_service.py \
  tests/test_graph_kernel_world_projection.py \
  tests/test_world_graph_projection_routes.py \
  tests/test_world_graph_recap_projection.py -q

uv run pytest \
  tests/test_graph_kernel_world_retrieval.py \
  tests/test_graph_kernel_boundaries.py -q

uv run ruff check \
  src/graph_memory/kernel/world_read_runtime.py \
  src/graph_memory/kernel/world_projection.py \
  src/graph_memory/kernel/__init__.py \
  src/graph_memory/world_projection_cache.py \
  apps/live_control_server/services/world_graph_projection.py \
  tests/test_graph_kernel_world_read_runtime.py \
  tests/test_world_graph_projection_service.py \
  tests/test_graph_kernel_world_projection.py

git diff --check

git diff --stat b6d1df07fae7b28760994509dcf2ae9bd8fb74c7...HEAD -- \
  Docs/Plans/HANDOFF-opt01-resident-verified-world-revision.md \
  src/graph_memory/kernel/world_read_runtime.py \
  src/graph_memory/kernel/world_projection.py \
  src/graph_memory/kernel/__init__.py \
  src/graph_memory/world_projection_cache.py \
  apps/live_control_server/services/world_graph_projection.py \
  tests/test_graph_kernel_world_read_runtime.py \
  tests/test_world_graph_projection_service.py \
  tests/test_graph_kernel_world_projection.py

git diff --name-only b6d1df07fae7b28760994509dcf2ae9bd8fb74c7...HEAD
```

Also run repository-wide checks when practical:

```bash
uv run ruff check .
uv run pytest tests/ --maxfail=1
```

Repository-wide failures do not become green by assertion. Apply the baseline failure protocol.

### Minimal live / dogfood proof

```text
Existing surfaces used:
  Plan, Build, existing Threat read/query path. No new UI.

Smallest realistic scenario:
  Start the live server against the existing Eldyrwild world.
  1. Open Plan on one campaign/session and record exact selected/head revision.
  2. Navigate to Build and execute the existing graph reference/search read.
  3. Return to Plan.
  4. Open or query one existing Threat through the current read path.
  5. Hard-refresh the browser without restarting the server and repeat one read.

Expected observation:
  Exactly one cold resident load for each exact revision first encountered.
  Same-revision requests after that report resident hit or coalesced and zero
  graph/revision/contribution/source-index reads. Browser refresh remains warm
  at the server. Every response names the same exact revision expected by its
  request/head observation.

Evidence captured:
  Structured server log rows plus a compact table of stage timings and read
  counters. Record cold and warm timings as characterization, not as an
  unsupported universal latency claim.
```

If live proof requires a frontend fix, new instrumentation panel, graph write, or publication change, stop. Use the existing surface and server logs only.

### Baseline failure protocol

For every required command already failing on base:

* run the identical command on base and head when possible;
* record exact failing test names and counts;
* state whether head adds any failure;
* do not call the command green;
* name the operator waiver required if the failure remains an acceptance gate.

Known historical failures are not automatically accepted. Re-establish the base result for this PR.

## §8 Required review handback

The Optimization Coding Agent must return:

1. Exact PR URL or branch/head SHA.
2. The §1 Mission and merge-ready invariant copied exactly.
3. The complete §7 evidence ledger with produced result and provenance.
4. Nano-commit list and one discrete implementation/proof story per commit.
5. Base SHA and head SHA.
6. Actual changed paths and focused diff stat limited to §4.
7. Every required command and exact result.
8. Result provenance: author-local, independently rerun local, CI, or manual/dogfood.
9. Base/head comparison for every failing gate.
10. Explicit operator waivers; write `none` when none exist.
11. Paths outside §4; write `none` or a stop report.
12. Stop conditions encountered and resolution; write `none` when none exist.
13. Exact runtime data structure and lifecycle summary:

    * resident key;
    * generation identity;
    * capacity/eviction;
    * in-flight coalescing;
    * clear/restart behavior;
    * scrub behavior.
14. Deterministic read-count table for cold, warm same request, warm different query, warm different focus, pinned old revision after head advance, and post-clear reread.
15. Cold/warm characterization timing table from tests or dogfood, with hardware/process context and no universal claims.
16. Confirmation that no public request/response schema, UI caller, durable storage format, publication protocol, or contribution semantics changed.
17. Successors still false:

    * no background post-commit prewarm;
    * no bounded object/search/adjacency APIs;
    * no write/materialization optimization;
    * no DungeonMind/PostgreSQL cutover.
18. Confirmation that the authoritative handoff was implemented without compressed or omitted constraints.

## §9 Acceptance rubric

The reviewer accepts only when every bullet is true:

* [ ] Exactly one independently useful capability was delivered: reuse of one verified resident World Graph revision.
* [ ] Cold and warm projections are contract-equivalent — E1.
* [ ] One exact resident key produces one coalesced cold load — E2.
* [ ] Partial/failed loads never become ready and a repaired retry works — E3.
* [ ] `head.json` remains a per-request fail-closed authority — E4.
* [ ] Head advance and stale completion cannot regress the head-following context — E5.
* [ ] The changed integrity bargain is explicit: resident memory is stable, scrub detects backing mutation, clear/restart re-verifies — E6.
* [ ] Completed payload cache keys only from an already resolved resident context and performs no file fingerprinting — E7.
* [ ] Warm same-revision requests perform zero graph/revision/contribution/source-index durable reads or hashes — E8.
* [ ] Query requests no longer force a cold revision reconstruction — E7/E8.
* [ ] The Graph Kernel remains the sole legal storage boundary — E9.
* [ ] Existing Plan/Build/Threat navigation proves server residency survives browser refresh — E10, or an explicit operator waiver if live environment is unavailable.
* [ ] No public projection schema, route, or surface consumer changed.
* [ ] No durable graph format or contribution/publication semantic changed.
* [ ] No path outside §4 changed.
* [ ] Every required proof has exact result and provenance; baseline failures are reported truthfully.
* [ ] No hard latency claim is based only on a noisy local timing measurement.
* [ ] OPT02/OPT03/OPT04 remain unimplemented and unclaimed.

## Stop conditions

Stop and report rather than expanding if implementation discovers:

* the projection builder cannot consume resident contributions/support indexes without changing response semantics;
* exact Threat or Build consumers require a request/response change;
* a new route, response header, UI indicator, admin panel, CLI, watcher, or worker is needed;
* current publication must notify or mutate the runtime for correctness rather than later prewarm performance;
* `head.json` cannot remain a small per-request authority without a new durable generation/event contract;
* a second storage format or durable cache manifest is proposed;
* a required contribution model or merge change overlaps the Statblock publication line;
* source-index caching changes evidence/provenance semantics rather than only reusing already derived text;
* a new stable error code is required and cannot be avoided while preserving current service behavior;
* deterministic read counters cannot prove zero warm graph/revision/contribution/source-index reads;
* a path outside §4 is required;
* the base moved and an allowlisted path changed materially;
* any acceptance proof requires changing a product surface.

Use this report shape:

```text
Stop condition:
Why the current mission cannot absorb it:
Invariant clause affected:
Required evidence now missing:
New public/durable contract discovered:
Affected observable paths or ownership layers:
Proposed successor slice:
Tracker or authority update needed:
```

## Design-agent dispatch note

The implementation is successful even if broad projection construction remains expensive. OPT01’s job is to establish the correct serving substrate and remove repeat durable reconstruction. Do not hide remaining CPU, serialization, payload-size, or write latency behind this PR’s name. Record it. Those measurements decide the next Optimization slice.


---

## §8 Coding-agent review handback (filled)

### Rebase + graph-object agreement repair (post PR #509 follow-up)

Addressed the remaining merge blockers after provenance admission landed:
1. **Rebased** onto completed Build/Statblock main at `9d4f5a3005f87d07147c03d8eee499af3bd57aa3` (PR #508 publication workflow included). All evidence below is regenerated against that merge base.
2. Cold admission + scrub now group validated representatives by `graph_object_id` and apply the same projection integrity checks that previously ran only during payload construction:
   - active node assertions must agree;
   - active edge assertions must agree;
   - active assertion Threat binding must agree with materialized `edge.threat_statblock_binding`.
3. Adversarial proofs: edge-disagreement revisions fail `get_or_load_resident` with `resident_count==0`; Threat-binding mismatch fails `build_active_support_authority_index`, marks scrub `unhealthy`, and fails cold admission.

Earlier review repairs remain in force (request-before-storage, clear/scrub races, full per-support provenance authority, context/request identity, error observations).

1. **PR / branch / head:** https://github.com/Drakosfire/DungeonMindBuddy/pull/509 ; branch `opt/opt01-resident-verified-world-revision`; head `f0166564e8b20903191c059b39193259509bb169`.
2. **§1 Mission (exact):** Projection callers can reuse one exact verified World Graph revision so that repeated reads of that revision do not reread or rehash immutable graph, contribution, or admitted source-index files.
3. **§1 Merge-ready invariant (exact):** Every projection response is still derived from the exact world, selected revision, current observed head revision, campaign scope, focus, admissibility, and query named by the existing request contract, while each resident generation is admitted only after one complete fail-closed verification, concurrent callers share that generation, completed projection caches cannot outlive it, and later out-of-band backing mutation can neither poison nor silently replace the already verified in-memory authority.
4. **§7 evidence ledger**

| ID | Result | Provenance |
| --- | --- | --- |
| E1 | PASS — `test_cold_and_warm_projections_are_model_equal` plus service cold/warm model equality | independently rerun local on rebased tip |
| E2 | PASS — `test_coalesced_concurrent_cold_load_single_io_batch` | independently rerun local on rebased tip |
| E3 | PASS — malformed graph/manifest + missing supported assertion + mid-load contribution failure + provenance-only lineage corruption + edge semantic disagreement + Threat binding disagreement; all leave `resident_count==0` where applicable | independently rerun local on rebased tip |
| E4 | PASS — `test_head_corruption_fails_closed_while_resident_exists` | independently rerun local on rebased tip |
| E5 | PASS — head-advance interleaving + unpinned uses new head + clear-during-load isolation | independently rerun local on rebased tip |
| E6 | PASS — scrub/clear trust + scrub CAS + provenance corruption scrub unhealthy + Threat-binding scrub unhealthy | independently rerun local on rebased tip |
| E7 | PASS — generation-bound payload cache + query cache eligibility + cache-disabled resident correctness | independently rerun local on rebased tip |
| E8 | PASS — warm same-revision / different-focus show 0 graph/manifest/contribution/source reads; pinned-after-advance selected hit with only new-head cold reads; post-clear reloads | independently rerun local on rebased tip |
| E9 | PASS for OPT01 scope — no new illegal Kernel boundary imports in allowlisted production paths; boundary suite still has pre-existing base failures outside OPT01 | independently rerun local + base comparison |
| E10 | NOT PROVEN — required live workflow is now: Publish accepted Threat → observe new exact head → Plan → Build → Threat/Hermes read → hard refresh; new revision may cold-load once; subsequent same-revision requests must report zero graph/manifest/contribution/source-index reads. Not run in this coding session; no operator waiver on the PR | deferred / needs operator dogfood |

5. **Nano-commits**
   - OPT01 stack rebased onto `9d4f5a30`
   - graph-object agreement admission + adversarial proofs
   - this §8 evidence sync
6. **Base / head:** base `9d4f5a3005f87d07147c03d8eee499af3bd57aa3`; head `f0166564e8b20903191c059b39193259509bb169`.
7. **Changed paths / focused diffstat:** exactly the §4 allowlist (9 paths).
8. **Required commands / results (post rebase + graph-object agreement)**
   - `uv run pytest tests/test_graph_kernel_world_read_runtime.py tests/test_world_graph_projection_service.py -q` → **28 passed**
   - `uv run pytest tests/test_world_graph_projection_routes.py tests/test_world_graph_recap_projection.py tests/test_graph_kernel_world_projection.py tests/test_graph_kernel_world_read_runtime.py tests/test_world_graph_projection_service.py -q` → **122 passed, 2 failed** (both pre-existing on `9d4f5a30`: multi-source retract + recap compatibility baseline)
   - `uv run pytest tests/test_graph_kernel_world_retrieval.py tests/test_graph_kernel_boundaries.py -q` → **73 passed, 4 failed** (3 boundary + 1 retrieval; all present on `origin/main` / `9d4f5a30`)
   - scoped `ruff check` on allowlisted paths → **All checks passed!**
   - `git diff --check` → clean
   - No GitHub Actions/status checks on this head (author-local evidence only)
9. **Result provenance:** independently rerun local (author coding agent) after rebase onto `9d4f5a30`.
10. **Base/head failing gates:** identical pre-existing failures retained on the new merge base:
    - `test_multi_source_one_supporter_retracted_drops_retracted_evidence_on_head`
    - `test_recap_compatibility_replays_prechange_baseline`
    - three `test_graph_kernel_boundaries.py` failures
    - `test_repo_heading_anchor_without_admitted_digest_is_unreadable`
    Head adds **no** new failures among required owning tests.
11. **Operator waivers:** none granted on the PR. E10 remains NOT PROVEN pending the completed Threat-publication dogfood workflow above or an explicit operator waiver.
12. **Paths outside §4:** none.
13. **Stop conditions:** none.
14. **Runtime summary**
    - resident key: `(resolved_root, world_id, revision_id)`
    - generation: monotonic process-local int per successful cold load
    - capacity: default 8 via `DMB_WORLD_GRAPH_RESIDENT_CAPACITY` (min 2); LRU registry eviction only
    - coalescing: one in-flight loader per key+epoch; waiters share generation/error; clear bumps epoch, clears ready, and detaches `_inflight`
    - clear/restart: `clear_world_read_runtime()` drops ready residents and isolates future callers from pre-clear loads; pair with `clear_projection_cache()` for payload entries
    - scrub: re-verifies durable backing + full support authority including graph-object agreement / Threat binding; CAS-updates `healthy`/`unhealthy` only for the scrubbed generation
    - support authority: per-assertion validated representative + provenance, then grouped object-level node/edge/Threat agreement before readiness
    - observations: emitted for cache hit, build success, and both error branches
15. **Deterministic read-count table (service observation, local tmp world; payload cache disabled for focus/pin/clear rows)**

| Scenario | graph | manifest | contribution | source-index | resident_status | notes |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| cold unpinned | 1 | 1 | 6 | 0 | miss | first admit |
| warm same request | 0 | 0 | 0 | 0 | hit | same recipe |
| warm different focus | 0 | 0 | 0 | 0 | hit | session focus |
| pinned historical after head advance | 1 | 1 | 6 | 0 | hit | selected pin hit; counts are new-head cold only |
| post-clear reload | 1 | 1 | 6 | 0 | miss | clear + unpinned head |

16. **Cold/warm characterization timings (local tmp initialize; not a universal latency claim)**
    - cold unpinned ≈ 7.0 ms (miss + build)
    - warm unpinned ≈ 0.14 ms (resident hit + payload cache hit)
    - warm query first ≈ 4.6 ms (resident hit, projection rebuild/search)
    - warm query cached ≈ 0.11 ms
17. **Public/durable confirmation:** no projection request/response schema, UI caller, durable storage format, publication protocol, or contribution merge semantics changed.
18. **Successors still false:** no post-commit prewarm; no bounded object/search/adjacency APIs; no write/materialization optimization; no DungeonMind/PostgreSQL cutover.
19. **Authority confirmation:** authoritative handoff implemented without compressed or omitted constraints; rebased onto completed Statblock publication main; admission now matches projection graph-object integrity before residency.
