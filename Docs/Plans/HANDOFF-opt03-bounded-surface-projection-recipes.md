# HANDOFF — OPT03 warm bounded surface projection recipes

Created: 2026-08-06.
Status: ACTIVE — ready for implementation from merged OPT02 base.
Canonical handoff path: `Docs/Plans/HANDOFF-opt03-bounded-surface-projection-recipes.md`
Conversation name: Optimization — Bounded Surface Bootstrap Recipes
Flow / agent: OPTIMIZATION
Handoff direction: DESIGN → CODE
Design agent: Optimization Designing Agent
Code agent: Optimization Coding Agent
PR title: `OPTIMIZATION: warm bounded surface projection recipes`
Suggested branch: `opt/opt03-bounded-surface-projection-recipes`
Immutable base: `fd05c7f20ccae22f2f43ec24642bf70290b0d9c7` — merge of PR #511 / OPT02.

Operating rule: This document exists to transfer design intent into a fresh coding context. Once code exists, the code and its tests represent the implementation. Reviewers must reason from executable behavior and reproducible interleavings, not from whether the PR description or handoff prose was followed literally.

Dispatch gate: Re-resolve `origin/main` before coding. If the merged OPT02 coordinator, `world_graph_projection.py`, or the completed projection cache differs materially from the shapes described below, stop and re-anchor the design before implementing.

Capability gate: This slice owns only process-local, bounded warming of recently successful head-following generic World Graph projection requests. It must not add a new projection API, a UI bootstrap schema, durable recipe persistence, static campaign configuration, surface-specific publication hooks, query-result prediction, write behavior, or graph authority.

## §0 Optimization line charter

The optimization line reduces latency while preserving the existing graph authority and projection semantics.

| Slice | Capability |
| --- | --- |
| OPT01 | verified resident revision read runtime |
| OPT02 | revision-ready notification and post-commit resident prewarm |
| OPT03 | bounded head-following projection recipes / surface bootstrap ← this handoff |
| OPT04 | delta-aware publication and materialization — later successor |

OPT01 makes an exact immutable revision safely resident.

OPT02 notices a newly committed head and admits that exact revision in the live-server process before demand.

OPT03 remembers a small set of projection request shapes that real surfaces have successfully used. After OPT02 makes a new head resident, OPT03 replays only those eligible shapes against that exact revision and fills the existing completed projection cache. The next matching Plan, Build, Recap, Graph Review shell, or other generic projection consumer can reuse the response without rebuilding it.

OPT03 does not introduce a second projection engine. It does not define what a surface means. It does not precompute arbitrary queries. It does not make a cache or recipe registry authoritative.

### Current executable facts

The merged base already provides:

- `WorldReadRuntime`, keyed by exact `(resolved_root, world_id, revision_id)`, with complete fail-closed admission and resident-generation identity.
- OPT02 revision-ready notification and one process-local coordinator that prewarms the exact current head.
- `apps/live_control_server/services/world_graph_projection.py`, which validates projection request policy; resolves selected and head resident contexts; checks a completed projection cache; builds through `kernel.project_world_graph_from_context(...)`; emits request observations.
- `src/graph_memory/world_projection_cache.py`, which keys payloads by exact root, world, campaign, selected revision, head revision, selected/head resident generations, focus, admissibility, scope mode, and query text; intentionally does not key on `revision_pin`; is process-local, LRU-bounded, TTL-bounded, and optional via `DMB_WORLD_GRAPH_PROJECTION_CACHE=0`.

Existing generic request shapes:

- Plan: head-following, no query, campaign/world scope, none/session focus
- Build: head-following, no query, campaign scope, no focus
- Recap: head-following generic projection beneath the recap-specific markdown composition
- Graph Review committed transition: exact `revision_pin`
- Hermes and Threat search/hydration: query-bearing requests

The exact-cache omission of `revision_pin` is useful and safe:

- warming a pinned request for revision B while B is also current head produces the same exact cache key as a later unpinned request for current head B;
- warming historical A after head has advanced to B produces a distinct key because selected revision/generation and head revision/generation differ;
- therefore a stale historical result cannot satisfy a current-head request.

### Shared vocabulary

| Term | Definition |
| --- | --- |
| Projection recipe | A normalized, process-local copy of one previously successful, eligible generic `WorldGraphProjectionRequest`, excluding any revision pin. It is a request shape, not a payload and not authority. |
| Eligible request | A successful generic projection request with no `revision_pin` and no `query_text`. |
| Head-following request | A request that selects the authoritative current head because it carries no explicit revision pin. |
| Recipe registry | A tiny LRU+TTL process-local set of eligible request shapes. It stores no graph payloads. |
| Recipe replay | Reissuing an eligible request with `revision_pin` set to the exact OPT02-ready revision. |
| Warm batch | The bounded set of most-recent eligible recipes replayed for one exact ready revision. |
| Completed projection cache | The existing exact-generation payload cache in `world_projection_cache.py`. OPT03 reuses it; OPT03 does not create a second payload cache. |
| Single-flight projection build | One exact cache key has at most one active builder; concurrent callers wait for and reuse that result or failure. |
| Surface bootstrap | The ordinary existing surface projection request returning from an already-built exact payload. No new bootstrap endpoint or response schema is introduced. |
| Superseded warm | Recipe work for revision A that is abandoned because current head became B. |
| Process-local | State disappears on process restart and is not shared across workers or hosts. |

### Nano-commit contract

Use the OPTIMIZATION flow. A suitable sequence is:

1. add the bounded recipe registry and eligibility contract;
2. add exact projection-build single-flight around the existing completed cache;
3. register successful eligible requests without changing response semantics;
4. replay recipes after OPT02 resident readiness;
5. prove publication, supersession, concurrency, failure, and cache-disabled behavior;
6. add bounded structured observations;
7. rerun focused and neighboring regression suites.

Each commit should tell one executable behavior or proof story. Do not bundle roadmap, tracker, broad cleanup, UI changes, or unrelated projection semantics.

## §1 Mission and merge-ready invariant

**Mission:** After a World Graph head becomes resident, the live server can prebuild the most recently used eligible projection shapes so the next matching surface load reuses an exact completed payload.

**Merge-ready invariant:** Only previously successful normalized head-following non-query projection requests become process-local recipes; registry size, age, warm count, and in-flight work remain bounded; every replay is pinned to the exact OPT02-ready revision and builds only through the existing projection service and completed cache; stale, failed, disabled, or absent recipe work cannot alter graph authority, publication success, projection semantics, or ordinary request correctness.

See the full design transcript in the originating conversation for §2–§9 (context, paths, adversarial sequences, allowlist, implementation contract, evidence E1–E9, handback, acceptance rubric). Implementation agents must treat executable tests as authority over this prose summary.

### Bounds (defaults)

- maximum retained recipes: 16 process-wide
- maximum recipes replayed for one ready revision: 4
- recipe TTL: 15 minutes from most recent successful use
- ordering: most-recently used first
- deduplication: exact recipe key

### Eligibility

Eligible only when all are true: projection succeeded; `revision_pin is None`; `query_text is None`; policy validation succeeded; closed request model. Cache-disabled mode registers and replays nothing.

### Allowlist (§4)

Create:

- `apps/live_control_server/services/world_graph_projection_recipes.py`
- `tests/test_world_graph_projection_recipes.py`

Modify:

- `apps/live_control_server/services/world_graph_projection.py`
- `apps/live_control_server/services/world_graph_prewarm.py`
- `src/graph_memory/world_projection_cache.py`
- `tests/test_world_graph_projection_service.py`
- `tests/test_world_graph_prewarm_service.py`
- `tests/test_live_control_server_lifespan.py` (only if needed)

Handoff file may be checked in. Do not update roadmap/tracker/status documents in the code PR.

### Dispatch resolution (2026-08-06)

- `origin/main` = `fd05c7f20ccae22f2f43ec24642bf70290b0d9c7` (OPT02 merge)
- Projection service, completed cache (generation-keyed, no `revision_pin`), and OPT02 coordinator match the shapes described above
- Implementation branch: `opt/opt03-bounded-surface-projection-recipes`
