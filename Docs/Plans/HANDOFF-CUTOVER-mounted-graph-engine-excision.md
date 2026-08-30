---
pr_body_template: |
  ## Handoff pointer
  - Workstream: CUTOVER / D.3A — mounted production graph-engine excision
  - Flow: CUTOVER
  - Direction: DESIGN → CODE
  - Handoff: `Docs/Plans/HANDOFF-CUTOVER-mounted-graph-engine-excision.md`
  - Frozen design authority: `Docs/Plans/HANDOFF-CUTOVER-buddy-graph-engine-demolition.md` §§6–7
  - Predecessor: Buddy #662 / D.2C4 manual Graph Review authoring continuity
  - Predecessor accepted head: `1ab48453cb556ca9d01ff84173ab3e2fdf81d1ec`
  - Predecessor merge: `2f1b44aa8ad8bad78269c0cadf624882cd0f459f`
  - Predecessor formal review cycles: 4
  - Predecessor final review: Cycle 4 PASS-equivalent `5059141212`
  - Steward re-anchor base before this handoff commit: `2f1b44aa8ad8bad78269c0cadf624882cd0f459f`
  - Branch: `cutover/mounted-graph-engine-excision`
  - PR title: `CUTOVER: excise Buddy graph engine from production`
  ## Verification pointer
  The checked-in handoff, cumulative diff, nano-commit story, exact import-blocked
  mounted witness, filesystem-absence witness, and verification provenance are the
  review contract. The PR body is transport metadata.

---

# HANDOFF — CUTOVER D.3A: mounted production graph-engine excision
**Created:** 2026-08-29
**Status:** COMPLETE / MERGED — Buddy #665 (accepted head `189ffd50157534d192b2af008c48a76d12ccbc4c`; merge `1a98bdb8a462ecc088ee70c2cecbed5c0d99ac3b`; 3 formal review cycles; Cycle 3 PASS-equivalent `5059851179`)
**Canonical handoff:** `Docs/Plans/HANDOFF-CUTOVER-mounted-graph-engine-excision.md`
**Workstream / flow:** CUTOVER
**Direction:** DESIGN → CODE
**Repository:** `Drakosfire/DungeonMindBuddy`
**Branch:** `cutover/mounted-graph-engine-excision`
**PR title:** `CUTOVER: excise Buddy graph engine from production`
**Frozen design authority:** `Docs/Plans/HANDOFF-CUTOVER-buddy-graph-engine-demolition.md` §§6–7
**Steward re-anchor base before this handoff commit:** `2f1b44aa8ad8bad78269c0cadf624882cd0f459f`
**Named successor:** D.3B — physical legacy-package deletion / `cutover/delete-legacy-graph-engine`
**Exact dispatch base (implementation start):** `619aa2b0c4be67e1d3931ff50899d126d2dafa13` (contains handoff commit `6b7706eec400129dbe01288630c443ae2d8a1e67`). **PR base / current Buddy `main` at Review Cycle 1:** `9570bd2636231b1f4ed9b6651da6c9a653abaa07`.
> This is the execution wrapper for the already-reviewed D.3A design. It does not
> reopen the frozen FAIL_CLOSED / REHOME_DTO / REWRITE_PORT choices in the D.3
> demolition handoff.
>
> D.3A removes the **mounted production dependency graph** first. D.3B deletes the
> legacy source packages afterward. D.3 is **not DONE** when D.3A merges.

## Dispatch law
The worker must branch from the current `main` **containing this handoff**, record
that exact SHA before changing executable code, and re-check active PRs/write leases.
The immutable predecessor merge from which this handoff was designed is:
```text
D.2C4 / Buddy #662
accepted head   1ab48453cb556ca9d01ff84173ab3e2fdf81d1ec
merge           2f1b44aa8ad8bad78269c0cadf624882cd0f459f
formal cycles   4
final review    5059141212 — PASS-equivalent
```
No implementation should start from the old D.3 design base or from the accepted
but pre-merge #662 head.

---

## §1 Mission and merge-ready invariant
**Mission:** Make the mounted DungeonBuddy product independent of the retired Buddy
World Graph engine so that production can boot, read, review, publish, initialize,
and recover entirely through DungeonMind while the legacy engine source still
exists only as unmounted historical/fixture code awaiting D.3B deletion.
**Merge-ready invariant:** The real mounted application can boot and execute every
retained World Graph product workflow with imports of
`graph_memory.kernel`, `graph_memory.world_supergraph`, and
`graph_memory.union_supergraph` blocked **before app import**, with no legacy graph
filesystem present or created, no `buddy_files` / `quiesced` / alternate-root
production authority branch, no hydration/local fallback on DungeonMind failure,
and every intentionally retired mounted capability returning its frozen explicit
410 contract rather than silently disappearing, importing the old engine, or being
rewritten into a new authority.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed path? | **Yes.** Every change answers one question: can the mounted product function with the three retired graph-engine namespaces unavailable? Physical source deletion is deliberately D.3B. |
| Most likely adversarial sequence | Start a fresh interpreter → install forbidden-import finder → configure DungeonMind authority + an empty/nonexistent legacy graph root → import/create the real app → enter lifespan → execute retained read/write/init/Graph Review paths → hit retired preview/bootstrap/merge-reconciliation routes → retry/recover writes → assert forbidden modules never loaded and legacy graph directory never appeared. |
| Would the evidence detect a false demolition? | **Yes only if the blocker is installed before app import.** In-process blockers installed after cached imports are explicitly invalid evidence. Route-only helper tests cannot own this invariant. |
| Easiest boundary to under-test | Boot/lifespan and transitive imports. A route can look DungeonMind-native while a top-level import, selector parser, prewarm worker, DTO, or mechanics helper still imports the legacy engine. |
| What forces STOP/split? | A retained mounted capability still genuinely requires local Buddy head/revision/store semantics, or requires a new DungeonMind provider contract, after applying the already-frozen retirement/relocation choices. |

---

## §2 Authority, predecessor truth, and boundaries

### 2.1 Authority order
Read before editing, in this order:
1. `AGENTS.md`
2. `Docs/Plans/PR-TRACKER-campaign-supergraph.md`
3. `Docs/Plans/HANDOFF-CUTOVER-buddy-graph-engine-demolition.md` §§6–7
4. this handoff
5. D.2C3 handoff / merged implementation
6. D.2C4 handoff / merged implementation
7. current mounted seams and their owning tests
If current `main`, an active write lease, or a mounted dependency contradicts this
handoff, stop and report the exact conflict before widening scope.

### 2.2 Completed predecessors
```text
D.2C2 first-world initialization
  Buddy #645
  accepted head f772db17e00cbe2c0198ae53f169a10a6332a3ed
  merge         3ff46922e679ad6bef2ef0cf37f0bf87e4542a6c
  formal cycles 2
D.2C3 native genesis continuity
  Buddy #651
  accepted head 9508b71655665005df8f12da74c239fe7eb17c0c
  merge         84f3401b23fcac32a57416d5419dc7d33cf6eabc
  formal cycles 4
D.2C4 manual Graph Review authoring continuity
  Buddy #662
  accepted head 1ab48453cb556ca9d01ff84173ab3e2fdf81d1ec
  merge         2f1b44aa8ad8bad78269c0cadf624882cd0f459f
  formal cycles 4
  final review  5059141212 — PASS-equivalent
```
Current DungeonMind pin remains:
```text
5ca5d688612349034f8ca490d465af166d883e6e
```
D.3 design authority:
```text
Buddy #647
accepted design head 1f5676c204ee917d18efd553106c07306541e820
merge                d96a21363fd0decbcb8c4390f951a6316b53060c
formal cycles         7
Cycle 7 PASS          5034239255
```

### 2.3 What D.3A delivers
After this slice:
```text
mounted reads                         → DungeonMind native
WorldGraphAuthority                   → DungeonMind only
WorldGraphInitializationAuthority     → DungeonMind only
WorldGraphSourceAdmissionAuthority    → DungeonMind only
Graph Review prepare/commit           → D.2C4 governed DungeonMind publication
Threat publication/recovery           → DungeonMind
worldbuilding publication/recovery    → DungeonMind
first-world D_0                       → DungeonMind reviewed initialization
existing-world adoption               → DungeonMind existing-world adoption
legacy authority selector             → retired/fail-closed compatibility parsing
legacy graph filesystem               → not required and not created
legacy engine source packages         → still present but unmounted, for D.3B
```

### 2.4 What remains false
D.3A does **not** prove physical source deletion. The following remain D.3B work:
```text
src/graph_memory/kernel/**                    still exists
src/graph_memory/world_supergraph/**          still exists
src/graph_memory/union_supergraph/**          still exists
historical migration/conformance consumers   may still exist after classification
legacy-only tests/fixtures                    may still exist
D.3                                           NOT DONE
```

### 2.5 Current-main dependency seeds already observed
These are **inventory seeds, not a closed list**. Re-prove them on the actual
dispatch head.
```text
config.world_graph_authority_mode
  → graph_memory.world_supergraph.storage
world_graph_authority_access
  → BuddyFilesWorldGraphAuthorityAdapter fallback for alternate root / old modes
world_graph_initialization_access
  → BuddyFilesWorldGraphInitializationAdapter fallback for alternate root / old modes
main.py lifespan
  → world_graph_prewarm coordinator
routes.graph_preview
  → union_supergraph_projection_adapter at module import
routes.graph_authoring
  → graph_merge_reconciliation_materialize at module import
  while /prepare + /commit are now D.2C4 governed survivors
routes.world_graph_bootstrap
  → legacy bootstrap service at module import
world_graph_writes
  → graph_memory.world_graph_mutation_context
  → graph_memory.kernel.identity_* transitively
world_graph_reads
  → graph_memory.projection DTOs; these may survive only if their own import
    closure is storage-neutral
threat query/hydration
  → legacy union-supergraph statblock/mechanics value ownership in the frozen design
```
The D.2C4 source-admission adapter is already proven importable with the three
legacy package families blocked. D.3A must preserve that property.

---

## §3 Frozen observable-path matrix
The worker does not choose new fates for these paths. Apply the frozen D.3 design.

| Observable path | Required D.3A behavior | Owning boundary |
|---|---|---|
| App import + `create_app()` | Succeeds with forbidden namespaces blocked before import | fresh-interpreter mounted witness |
| Lifespan | Starts/stops without Kernel prewarm; no retired graph engine import | `main.py` + mounted witness |
| World Graph projection/retrieval | Native DungeonMind behavior unchanged | existing routes/services + PG witness |
| Search / exact object / neighborhood | Native DungeonMind behavior unchanged | retrieval owning tests |
| Evidence / source-anchor | Native DungeonMind behavior unchanged | retrieval/source-anchor owning tests |
| Exact-run Graph Review read/review | Still works on native authority | existing exact-run tests |
| Graph Review `/prepare` + `/commit` | **KEEP WORKING.** D.2C4 governed source admission + `WorldGraphAuthority` publication | D.2C4 owning witness under blocker |
| Graph Review `merge-reconciliation/prepare|apply` | **KEEP_MOUNTED_410**, code `graph_authoring_store_retired`; no materializer import | route test under blocker |
| `/graph-preview/union-supergraph/projection` | **KEEP_MOUNTED_410**, code `union_supergraph_preview_retired`; no adapter import | route test under blocker |
| Other graph-preview routes | Stay mounted and retain accepted behavior | graph-preview owning tests under blocker |
| World-graph-bootstrap `status|prepare|confirm` | **KEEP_MOUNTED_410**; no legacy bootstrap service import | route test under blocker |
| Plan “Open Union Graph” | No longer presented as a working store-preview action; retirement is explicit | UI test |
| Graph Review live candidate store-preview lane | Does not call retired UnionSupergraph projection; committed DungeonMind projection remains | UI/state tests |
| Graph merge materialization UI | Does not present file-apply as working durable write | UI test |
| Statblock create-context | Stops using bootstrap status as World/head oracle; uses already-landed native World Graph authority/read seam | Statblock UI/API owning test |
| Threat publish/recover | Same child/retry/recovery semantics | D.2A owning tests under blocker |
| Existing-world worldbuilding publish/recover | Same child/retry/recovery semantics | D.2B owning tests under blocker |
| First-world review/prepare/confirm | One DungeonMind D_0; same retry/restart/concurrency semantics | D.2C2 owning PG tests under blocker where practical |
| Native reviewed-init D_0 read/write | D.2C3 continuity unchanged | D.2C3 owning witness under blocker |
| D.2C4 source admission | Exact source pair remains snapshot-provable and blocker-safe | D.2C4 source-admission + PG tests |
| Hermes/latest-recap graph read | Native graph comparison/read still works | Hermes owning boundary |
| Authority env unset | DungeonMind | config/factory matrix |
| Authority env `dungeonmind` | DungeonMind | config/factory matrix |
| Authority env `buddy_files` | Clear configuration failure; never file adapter | config/factory matrix |
| Authority env `quiesced` | Clear configuration failure; never file adapter | config/factory matrix |
| Authority env unknown | Clear configuration failure | config matrix |
| Alternate/non-production `world_root` passed to mounted factory | Clear configuration failure; never file adapter | factory test |
| `<configured-root>/graph_memory/worlds` absent | Product still works and does not create it | filesystem-absence mounted witness |
| DungeonMind unavailable/integrity failure | Fail closed; no local/hydrated fallback | route/service tests |

### Adversarial sequences

| Sequence | Required safe outcome |
|---|---|
| Block legacy imports → import app → enter lifespan | Boot succeeds; no cached/pre-import escape. |
| Unset authority env → mounted read/write | DungeonMind is selected; no Buddy path. |
| `buddy_files` or `quiesced` env → app/factory use | Explicit configuration failure before any file adapter construction. |
| Alternate `world_root` → mounted authority accessor | Explicit failure; alternate root cannot become hidden legacy authority. |
| DungeonMind read failure after D.3A | Error remains error; no hydrated/local fallback. |
| Graph Review governed prepare/commit under blocker | One DungeonMind child / exact recovery; no legacy writer import. |
| Retired route called under blocker | Stable 410 response; route remains registered, not 404. |
| Graph-preview retained route called under blocker | Existing accepted behavior; router was not retired wholesale. |
| Legacy graph directory absent → full mounted proof → inspect filesystem | Directory remains absent. No head/revision/cache is recreated. |

---

## §4 Files in scope — write lease
The frozen D.3 design authorizes a large but bounded excision surface. This handoff
narrows it into named owners plus a strict discovery rule. Every changed path must
be listed in the final handback with its original classification.

### 4.1 Core server / authority lease
```text
apps/live_control_server/main.py
apps/live_control_server/config.py
apps/live_control_server/ports/world_graph_authority_access.py
apps/live_control_server/ports/world_graph_initialization_access.py
apps/live_control_server/ports/world_graph_source_admission_access.py
apps/live_control_server/integrations/buddy_files/**
apps/live_control_server/integrations/dungeonmind/world_graph_reads.py
apps/live_control_server/integrations/dungeonmind/world_graph_writes.py
apps/live_control_server/integrations/dungeonmind/world_graph_authority_adapter.py
apps/live_control_server/integrations/dungeonmind/world_graph_initialization_adapter.py
apps/live_control_server/integrations/dungeonmind/world_graph_source_admission_adapter.py
apps/live_control_server/integrations/dungeonmind_kernel/**
  only to stop mounted product from importing/calling it; do not perform D.3B deletion
apps/live_control_server/models/world_graph_contribution_values.py
apps/live_control_server/models/extract_promote.py
apps/live_control_server/models/threat_query_hydration.py
apps/live_control_server/routes/world_graph_bootstrap.py
apps/live_control_server/routes/graph_authoring.py
apps/live_control_server/routes/graph_preview.py
apps/live_control_server/routes/threat_query_hydration.py
apps/live_control_server/services/world_graph_bootstrap.py
apps/live_control_server/services/graph_merge_reconciliation_materialize.py
apps/live_control_server/services/union_supergraph_projection_adapter.py
apps/live_control_server/services/graph_object_candidate_sources.py
apps/live_control_server/services/world_graph_recap_projection.py
apps/live_control_server/services/world_graph_prewarm.py
apps/live_control_server/services/world_graph_projection.py
apps/live_control_server/services/world_graph_retrieval.py
apps/live_control_server/services/first_world_graph.py
apps/live_control_server/services/first_world_graph_publication.py
apps/live_control_server/services/world_graph_*.py
apps/live_control_server/services/graph_review_*.py
apps/live_control_server/services/worldbuilding_graph_publication.py
apps/live_control_server/services/threat_*.py
src/graph_memory/projection/**
```
Globs above are **family leases from the frozen D.3 design**, not permission to edit
unrelated files in those directories. The handback must enumerate exact paths.

### 4.2 Pure-value relocation allowance
New narrowly named Buddy-owned modules are allowed only for values/transforms still
needed by mounted product flows, for example:
```text
apps/live_control_server/models/<narrow contribution value owner>.py
apps/live_control_server/models/<narrow mechanics/statblock value owner>.py
apps/live_control_server/models/<narrow world-graph mutation-context value owner>.py
```
Permitted content is pure data/validation/deterministic transformation only.
Do **not** relocate local graph storage, replay, publication, merge authority, head
mutation, or filesystem semantics under a new name.
The current `world_graph_writes → graph_memory.world_graph_mutation_context →
graph_memory.kernel.identity_*` chain is a known candidate for such a pure-value
relocation. Preserve canonical bytes, IDs, digests, validation, identity semantics,
and ordering exactly.

### 4.3 Frontend lease
```text
apps/live-control-ui/src/api/liveApi.ts
apps/live-control-ui/src/api/types.ts
apps/live-control-ui/src/planSurface/graphPreview/GraphIngestProjectionPanel.tsx
apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphReviewLiveReviewState.ts
apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphMergeReconciliationMaterializationPanel.tsx
apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.tsx
owning tests for those exact surfaces
```
Do not redesign Plan or Graph Review. This lease only removes/labels dead
store-backed actions and switches Statblock create-context off the retired bootstrap
oracle.

### 4.4 Owning tests
Expected existing families plus one new owning demolition witness:
```text
tests/test_cutover_mounted_graph_engine_excision.py                 NEW preferred
tests/test_cutover_graph_review_authoring_continuity.py
tests/test_world_graph_source_admission.py
tests/test_cutover_native_genesis_continuity.py
tests/test_cutover_dungeonmind_world_graph_authority.py
tests/test_cutover_dungeonmind_first_world_initialization.py
tests/test_cutover_direct_dungeonmind_world_graph_reads.py
tests/test_cutover_worldbuilding_authority_port_integration.py
tests/test_live_query_hermes_graph.py
tests/test_first_world_graph.py
tests/test_live_extract_promote_api.py
existing route tests for graph-preview / graph-authoring / bootstrap
focused Threat/worldbuilding tests owning any changed seam
frontend owning tests for the §4.3 surfaces
```
Do not claim all `tests/**` as a lease.

### 4.5 Backward-looking state-authority sync lease
D.3A owns the now-knowable D.2C4 completion sync. Update together in the
implementation PR:
```text
Docs/Plans/PR-TRACKER-campaign-supergraph.md
Docs/Roadmaps/ROADMAP-campaign-supergraph.md
Docs/Design/STATUS-world-graph-continuity-spine.md
Docs/Plans/STEWARDS-ANCHOR-cutover.md
Docs/Sources/design-agent/ACTIVE_AUTHORITY/PR-TRACKER-campaign-supergraph.md
Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-campaign-supergraph.md
Docs/Plans/HANDOFF-CUTOVER-buddy-graph-engine-demolition.md
Docs/Plans/HANDOFF-CUTOVER-manual-authoring-continuity-code.md
Docs/Plans/HANDOFF-CUTOVER-mounted-graph-engine-excision.md
```
Record exactly:
```text
D.2C4 COMPLETE / MERGED
PR #662
accepted head 1ab48453cb556ca9d01ff84173ab3e2fdf81d1ec
merge         2f1b44aa8ad8bad78269c0cadf624882cd0f459f
formal review cycles 4
final PASS-equivalent review 5059141212
D.3A DOING / this PR
D.3B BLOCKED
D.3 NOT DONE
```
> **Post-merge note:** The block above is the historical in-flight D.3A sync lease
> from dispatch. Live status is now D.3A `COMPLETE` / `MERGED` (#665), D.3B `DOING`
> (`cutover/delete-legacy-graph-engine`), D.3 still `NOT DONE` — see header Status.

Do **not** pre-mark D.3A complete or invent its future merge SHA/review count.
Tracker/roadmap mirrors must remain byte-identical.

### 4.6 Bounded discovery exception
A previously unnamed executable file under `apps/live_control_server/**`, mounted
`src/**`, or the four frozen frontend surfaces may be added only when **all** are
true:
1. the dispatch-base executable import/call graph reaches a retired namespace or
   one of the frozen retired store capabilities;
2. D.3A only replaces that dependency with a frozen owner, pure-value relocation,
   or import-free 410 stub;
3. no surviving public semantics change except the already-frozen retirements;
4. no active PR owns the path;
5. the handback names the exact path, original dependency, classification, and fix.
Any other path need is STOP/re-brief.

---

## §5 Explicitly out of scope
```text
D.3B physical deletion of:
  src/graph_memory/kernel/**
  src/graph_memory/world_supergraph/**
  src/graph_memory/union_supergraph/**
  buddy_files integration source
new DungeonMind commands / UoWs / publication families / provider contracts
DungeonMind repository changes or pin movement
new World Graph semantics
new identity-merge authority
reopening D.2C3 genesis logic
reopening D.2C4 operation/source-admission algebra
shipping merge_objects as a durable Graph Review write
retiring Graph Review /prepare or /commit
turning extract-promote into manual Graph Review
Plan/Play/Agent UX redesign
APP-STATE / Play Runtime implementation
broad historical Eldyrwild migration/conformance deletion
source/evidence/extraction redesign
automatic deletion of user legacy graph data
renaming every surviving graph_memory DTO purely for aesthetics
telemetry/observability expansion unrelated to proving demolition
```
Historical tools may remain executable after D.3A only if they are **not mounted**
and the handback classifies them for D.3B. Do not rewrite them merely to make a
repository-wide grep reach zero.

---

## §6 Implementation contract

### 6.1 Step 0 — re-anchor and classify before editing
Record the exact dispatch `main`, open PRs, and current DungeonMind pin.
Run at minimum:
```bash
rg -n \
  '(^|[[:space:]])(from|import)[[:space:]]+graph_memory\.(kernel|world_supergraph|union_supergraph)' \
  apps/live_control_server src scripts tests
rg -n \
  'DUNGEONMIND_WORLD_GRAPH_AUTHORITY|buddy_files|quiesced|route_service_read|ensure_hydrated_authority|WORLD_GRAPH_AUTHORITY_CACHE' \
  apps/live_control_server src scripts tests
```
Classify every executable hit:
```text
MOUNTED_PRODUCT
DUNGEONMIND_ADAPTER
PURE_PRODUCT_VALUE
LEGACY_FIXTURE
HISTORICAL_TOOL
DEAD
```
Every `MOUNTED_PRODUCT` hit must be gone/replaced or be a STOP. Every retained
`HISTORICAL_TOOL` / `LEGACY_FIXTURE` hit must be named in handback as D.3B inventory.

### 6.2 Establish surviving pure-value owners first
Relocate only values/transforms still needed by mounted product code while both old
and new implementations can be compared.
For every relocated family, prove parity for all applicable dimensions:
```text
model_dump(mode="json")
canonical bytes
stable assertion/contribution IDs
source/contribution SHA-256
deterministic ordering
validation accept/reject behavior
identity redirect / alias-owner semantics
```
After callers switch, the new module is the mounted owner. Do not keep dual mounted
implementations.

### 6.3 Retire authority selection
Rehome the parser/constants out of `graph_memory.world_supergraph.storage`.
Frozen matrix:
```text
unset        → DungeonMind
dungeonmind  → DungeonMind
buddy_files  → explicit configuration failure
quiesced     → explicit configuration failure
unknown      → explicit configuration failure
```
Mounted authority and initialization factories become one-way DungeonMind.
`WorldGraphSourceAdmissionAuthority` is already DungeonMind-only and remains so.
An explicit alternate `world_root` may not select a file adapter. Preserve the
argument only if required for compatibility, but it must fail closed rather than
becoming a test-mode escape hatch.

### 6.4 Execute frozen route/product retirements

#### Graph preview
Keep `routes.graph_preview` mounted.
`GET /api/live/graph-preview/union-supergraph/projection` becomes an import-free
410 response:
```json
{
  "detail": {
    "code": "union_supergraph_preview_retired",
    "message": "..."
  }
}
```
Exact message wording is not authority; status and stable code are.
Remove the top-level `union_supergraph_projection_adapter` import from the router.
Retained extraction/gold/manual/recap routes continue to work.

#### Graph authoring
Keep `/api/live/graph-authoring/prepare` and `/commit` exactly as the D.2C4 governed
correction cockpit.
Only these obsolete file-writer routes retire:
```text
POST /api/live/graph-authoring/merge-reconciliation/prepare
POST /api/live/graph-authoring/merge-reconciliation/apply
```
They stay registered and return 410 with stable code:
```text
graph_authoring_store_retired
```
The router must not import the materialization service merely to return 410.

#### World graph bootstrap
Keep routes registered:
```text
GET  /api/live/world-graph-bootstrap/status
POST /api/live/world-graph-bootstrap/prepare
POST /api/live/world-graph-bootstrap/confirm
```
All become import-free 410 retirement responses. Do not rewrite them onto reviewed
first-world initialization.

#### UI
Stop presenting UnionSupergraph store preview and merge file-apply as working
product actions. Retirement/unavailable state must be explicit; 410 must not be
misread as a missing ingest artifact.
Statblock create-context must stop using the retired bootstrap status as its World
Graph head oracle. Consume an already-landed native World Graph authority/read
contract. If no existing contract can supply the required pin without new semantics,
STOP rather than inventing a new bootstrap replacement.

### 6.5 Retire prewarm/hydration/local fallback
No mounted lifespan worker may require Kernel prewarm. Start/stop helpers may become
no-op or be removed from the mounted lifecycle; do not keep a lazy legacy import.
Remove mounted DungeonMind→Buddy hydrated read/cache routing and any local/file
fallback. DungeonMind failure is a truthful failure.
`WORLD_GRAPH_AUTHORITY_CACHE_ROOT` compatibility may remain only if some unmounted
historical/tooling path still names it; mounted product cannot consume it.

### 6.6 Preserve D.2 authority semantics
No semantic rewrite is authorized. Preserve:
```text
GM / PLAYER admissibility
search / exact object / neighborhood / evidence / source-anchor
revision pin/head semantics
existing-world adoption Buddy-A → D_A bridge
reviewed-init D_0 with no legacy Buddy revision
Threat one-child publication + exact retry/recovery
worldbuilding one-child publication + exact retry/recovery
first-world one-D_0 retry/restart/concurrency
D.2C3 native D_0 read/write continuity
D.2C4 source admission + object/link/relationship governed authoring
D.2C4 stale-parent/tamper/expiry/recovery behavior
stable contribution/source IDs and digests
```

### 6.7 No destructive cleanup
The proof requires the legacy graph filesystem to be absent, but D.3A must never
delete user data.
Forbidden implementation behavior includes:
```text
rm -rf
shutil.rmtree
startup cleanup of a user's graph root
migration code that silently deletes old heads/revisions
```
Tests create a clean temporary root whose legacy directory never existed.

---

## §7 Required evidence ledger

### 7.1 Owning fresh-interpreter demolition witness — merge blocker
Create `tests/test_cutover_mounted_graph_engine_excision.py` (preferred name) or an
equivalently focused owning test.
The witness must launch a **fresh Python interpreter/subprocess**. Inside that
process:
1. install an import blocker before importing `apps.live_control_server.main`;
2. block every FQN equal to or prefixed by:
   ```text
   graph_memory.kernel
   graph_memory.world_supergraph
   graph_memory.union_supergraph
   ```
3. fail if any forbidden module is already in `sys.modules`;
4. configure the real DungeonMind authority database and a clean temporary graph
   root;
5. assert `<root>/graph_memory/worlds` does not exist before app boot;
6. import/create the real FastAPI app and enter the real lifespan;
7. execute the representative mounted boundaries below with the blocker still active;
8. assert the forbidden modules never appeared in `sys.modules`;
9. assert `<root>/graph_memory/worlds` still does not exist afterward.
A test that imports the app/adapter first and installs the blocker later is invalid.
Monkeypatching the legacy engine into harmless behavior is invalid as the owning
proof.

### 7.2 Mounted boundaries under the blocker
The owning proof plus focused tests must cover at least:
```text
app boot + lifespan
health
World Graph projection
search
exact object
neighborhood
evidence
source-anchor resolution
exact-run Graph Review package/read boundary
existing-world adopted-world read
first-world reviewed-init D_0 read
D.2C3 D_0 → child publication
D.2C4 Graph Review object prepare/confirm + exact retry/recovery
D.2C4 source admission snapshot proof
Threat publish/recover
worldbuilding publish/recover
Hermes/latest-recap graph comparison or its exact owning service boundary
```
Use real PostgreSQL for publication/initialization/genesis/manual-authoring cohorts
where their accepted handoffs require it. Required integration witnesses have zero
required skips.

### 7.3 Retired route contract proof
With the blocker active, prove:
```text
GET  /api/live/graph-preview/union-supergraph/projection
  → 410 / union_supergraph_preview_retired
POST /api/live/graph-authoring/merge-reconciliation/prepare
POST /api/live/graph-authoring/merge-reconciliation/apply
  → 410 / graph_authoring_store_retired
GET  /api/live/world-graph-bootstrap/status
POST /api/live/world-graph-bootstrap/prepare
POST /api/live/world-graph-bootstrap/confirm
  → 410 / stable bootstrap retirement code
```
Also prove:
```text
/api/live/graph-authoring/prepare + /commit still registered and working
retained graph-preview endpoints still registered
no retired route falls to 404
no retired route imports its legacy implementation
```

### 7.4 Selector/factory matrix — merge blocker
Prove all six cases:
```text
unset                    → DungeonMind
"dungeonmind"            → DungeonMind
"buddy_files"            → configuration failure; no file adapter
"quiesced"               → configuration failure; no file adapter
unknown                   → configuration failure
alternate world_root      → configuration failure; no file adapter
```
Arm constructor tripwires on BuddyFiles adapters so a false-green error after
construction cannot pass.

### 7.5 Legacy filesystem absence — merge blocker
Before/after the real mounted witness:
```text
<configured-root>/graph_memory/worlds  DOES NOT EXIST
```
Also prove no Buddy head/revision/cache tree is created as a side effect of reads,
writes, retries, startup, or shutdown.

### 7.6 Pure-value parity
For every value family moved out of the legacy packages, retain an old-vs-new parity
fixture while the old source is still present. The handback must name each family and
exact parity assertions.
A relocation that changes IDs/digests/validation is a blocker, not an acceptable
cleanup delta.

### 7.7 D.2 regression cohorts
At minimum include the existing owning suites for changed seams. A likely baseline is:
```bash
uv run pytest \
  tests/test_cutover_graph_review_authoring_continuity.py \
  tests/test_world_graph_source_admission.py \
  tests/test_cutover_native_genesis_continuity.py \
  tests/test_cutover_dungeonmind_world_graph_authority.py \
  tests/test_cutover_dungeonmind_first_world_initialization.py \
  tests/test_cutover_direct_dungeonmind_world_graph_reads.py \
  tests/test_cutover_worldbuilding_authority_port_integration.py \
  tests/test_live_query_hermes_graph.py \
  -q
```
Add the new D.3A owning witness and exact route/factory tests. If a named test path is
absent on the actual dispatch base, record base absence rather than silently replacing
it; choose the existing owning equivalent and explain it.

### 7.8 Frontend proof
Run the exact owning tests for:
```text
GraphIngestProjectionPanel
Graph Review live-review state
GraphMergeReconciliationMaterializationPanel
StatblockWorkbenchModule
liveApi 410 classification / API contract if changed
```
Then:
```bash
npm run typecheck
npm run build
```

### 7.9 Static/final gates
```bash
uv run ruff check <all changed Python files>
git diff --check
```
Final-head gates also include:
```text
- exact changed-path list against this §4 lease
- `pyproject.toml` / `uv.lock` unchanged unless STOP/re-brief explicitly authorizes otherwise
- DungeonMind pin unchanged
- tracker/roadmap mirrors byte-identical
- no new product selector/header/query/test-mode that can reactivate Buddy authority
- no destructive user-data cleanup
```

### 7.10 Verification provenance
Handback must classify each result as:
```text
author-local
reviewer-independent rerun
CI
manual/operator dogfood
BLOCKED_DEPENDENCY
NOT_RUN
```
Do not imply independent or CI evidence when none exists.

---

## §8 Acceptance criteria
D.3A is merge-ready only when all are true:
1. Worker re-anchored from current `main` containing this handoff and recorded exact dispatch SHA.
2. D.2C4 is backward-synced as COMPLETE/MERGED with exact #662 head/merge/4-cycle facts.
3. D.3A is the active CUTOVER slice; D.3B remains blocked; D.3 remains not DONE.
4. Fresh-interpreter import blocker is installed before app import.
5. Mounted app boots and enters/exits lifespan with all three legacy namespaces blocked.
6. No forbidden legacy namespace appears in `sys.modules` during the owning proof.
7. No mounted product path imports/calls the retired engine through a transitive helper.
8. `config` no longer imports `graph_memory.world_supergraph.storage` for authority selection.
9. Unset and `dungeonmind` select DungeonMind.
10. `buddy_files`, `quiesced`, unknown values, and alternate `world_root` fail closed without constructing a file adapter.
11. Mounted WorldGraphAuthority and WorldGraphInitializationAuthority are DungeonMind-only.
12. Source admission remains DungeonMind-only and retains D.2C4 behavior.
13. No DungeonMind failure falls back to hydrated/local Buddy graph state.
14. Kernel prewarm is absent from mounted runtime/lifespan.
15. `/graph-preview/union-supergraph/projection` is registered 410, import-free.
16. Other graph-preview routes remain mounted and usable.
17. Graph Review `/prepare` and `/commit` remain governed D.2C4 writes.
18. Graph-authoring merge-reconciliation routes are registered import-free 410.
19. Bootstrap status/prepare/confirm are registered import-free 410.
20. UI no longer offers store-backed Union Graph preview or merge file-apply as working actions.
21. Statblock create-context no longer depends on bootstrap status.
22. Existing-world native reads retain the Buddy-A → D_A adoption bridge.
23. Reviewed-init D_0 reads/writes retain D.2C3 semantics.
24. D.2C4 object/link/relationship authoring retains exact publication/recovery/source closure.
25. Threat and worldbuilding publication/recovery regressions stay green.
26. First-world initialization/retry/restart/concurrency regressions stay green.
27. Hermes/latest-recap native graph read regression stays green.
28. Every relocated pure value proves serialization/ID/digest/validation parity.
29. The configured legacy graph directory does not exist before the mounted proof and is not created afterward.
30. No user-data deletion mechanism is introduced.
31. Every retained executable legacy import is classified as unmounted fixture/historical tooling for D.3B.
32. Required PostgreSQL witnesses report zero required skips.
33. Frontend owning tests, typecheck, and build pass.
34. Ruff, diff check, dependency immutability, DungeonMind pin, and mirror gates pass.
35. No D.3B physical package deletion is performed.

---

## §9 STOP / re-brief conditions
STOP if any of the following becomes true:
1. A retained mounted capability still needs Buddy local head/revision/store semantics after the frozen retirements.
2. Eliminating a mounted dependency requires a new DungeonMind command, UoW, schema, publication family, provider capability, or pin move.
3. A pure-value relocation changes canonical serialization, durable IDs, digests, acceptance semantics, or public wire shape.
4. A supposed pure value materially requires local graph state/replay.
5. A production deployment genuinely depends on `buddy_files` or `quiesced` rather than historical tests/tooling.
6. Import-blocked app boot is impossible without deleting/replacing a product capability not already frozen for retirement.
7. Filesystem absence can only be achieved by deleting user data.
8. A required path is leased by another active PR and cannot be cleanly split/transferred.
9. Statblock create-context cannot stop using bootstrap status without inventing new World Graph semantics.
10. A retained graph-preview route requires UnionSupergraph store semantics not covered by the frozen retirement choices.
11. Graph Review `/prepare` or `/commit` would need to be 410'd, disabled, or routed back through a legacy writer.
12. D.2C4 source admission or publication only works by importing one of the forbidden namespaces.
13. A historical executable tool must remain mounted to preserve production behavior.
14. Implementation starts deleting the legacy package trees rather than merely detaching mounted product consumers.
15. Any change broadens into Play/Application-State/Agent feature work or product redesign.
Do not convert a STOP into a hidden compatibility branch.

---

## §10 Preferred nano-commit story
Exact count is not contractual, but the review story should remain separable:
1. **CUTOVER: sync merged Graph Review predecessor and freeze D.3A inventory**
   Backward-sync #662 truth; record dispatch inventory/classifications; no executable behavior yet.
2. **CUTOVER: rehome surviving graph product values**
   Move only pure contribution/mechanics/mutation-context values with parity proof.
3. **CUTOVER: make mounted World Graph authority DungeonMind-only**
   Rehome selector parser, fail closed retired modes/alternate roots, remove BuddyFiles factory branches and hydration fallback.
4. **CUTOVER: retire mounted legacy graph routes and prewarm**
   Import-free 410 stubs, retained router survival, lifespan/prewarm cleanup.
5. **CUTOVER: retire store-backed graph UI actions**
   Union preview / merge materialization / bootstrap-status callers reflect frozen retirement without Graph Review redesign.
6. **CUTOVER: prove mounted graph-engine absence**
   Fresh-process import blocker + filesystem absence + D.2 regression witnesses + final static gates.
If a commit needs to mix semantic relocation with physical legacy package deletion,
stop: that is D.3B scope leakage.

---

## §11 CODE → REVIEW handback contract
Return one cumulative handback containing:
1. PR / branch / exact final head SHA.
2. Exact dispatch base (the `main` commit containing this handoff) and any later rebase.
3. #662 predecessor: accepted head, merge SHA, 4 formal cycles, final PASS review.
4. Current DungeonMind pin and proof it did not move.
5. Active PR/write-lease check at dispatch and final review handback.
6. Exact cumulative changed paths, each mapped to §4 or the bounded-discovery rule.
7. Full Step-0 import/selector inventory with every retained executable hit classified.
8. Exact pure-value relocations and parity evidence.
9. Authority selector/factory matrix results for all required states.
10. Fresh-interpreter import-blocker setup proving blocker installed before app import.
11. App boot/lifespan result under blocker.
12. Exact mounted boundaries exercised under blocker.
13. Legacy filesystem absence before/after proof.
14. Retired 410 route response codes and proof the routes remain registered.
15. Retained graph-preview route proof.
16. D.2C4 Graph Review prepare/commit result under blocker, including retry/recovery/source proof.
17. D.2C3 native D_0 continuity result under blocker.
18. Threat/worldbuilding/first-world regression results.
19. Hermes/latest-recap regression result.
20. Frontend retirement behavior and Statblock context result.
21. Every test/build/lint command with exact pass/fail/skip counts.
22. Required PostgreSQL witness skip count (must be zero required skips).
23. Verification provenance table.
24. `git diff --check`, Ruff, dependency immutability, pin, and mirror results.
25. Explicit confirmation that no destructive user-data cleanup exists.
26. Explicit confirmation D.3B package deletion is still false.
27. Backward state sync result: D.2C4 DONE/MERGED; D.3A active; D.3B blocked; D.3 not DONE.
28. Stop conditions encountered, or `none`.
The handoff/dispatch seed is **not Review Cycle 1**. Review Cycle 1 begins only
when a distinct executable implementation head plus complete handback is formally
reviewed.

---

## §12 Post-merge successor law
After D.3A merges:
1. record accepted D.3A head, merge SHA, and formal review-cycle count in the next dependent implementation sync;
2. re-anchor `main`;
3. prove production dependency count remains zero;
4. inventory all remaining executable consumers of the three legacy package trees;
5. dispatch **D.3B physical legacy-package deletion**;
6. keep D.3 NOT DONE until D.3B merges and final physical-absence proof passes.
D.3B should be deletion, not another hidden semantic migration. If D.3A leaves a
storage-neutral product value inside a package D.3B is supposed to delete, D.3A is
not complete.
