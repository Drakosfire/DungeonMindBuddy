---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: SURFACE-INTEGRATION / SI-5B
  - Flow: SURFACE-INTEGRATION
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: `Docs/Plans/HANDOFF-SURFACE-INTEGRATION-ingest-run-information-adoption-v1.md`
  - Branch / PR: `agent/surface-integration-ingest-run-information-v1` / `SURFACE-INTEGRATION: move Ingest run catalog onto Surface Information`

  ## Verification pointer
  - Base: `a543af46f21d31d6ad83a88c3b2911ca4e0e4016`
  - Predecessor: PR #680 merged @ `a543af46f21d31d6ad83a88c3b2911ca4e0e4016`; final implementation `4ccbe0fad1f5c9c60c3ced6173d842a77b162289`; three formal review cycles
  - Changed paths: HANDOFF §4 only, plus the bounded test-only discovery exception if used
  - Verification: HANDOFF §7 exact-head evidence + §8 review handback

  The checked-in handoff, cumulative diff, nano-commit story, and independently
  rerun evidence are the review contract. This body is transport metadata.
---

# HANDOFF — Ingest APP-STATE Run Information Adoption v1

**Created:** 2026-09-03  
**Status:** COMPLETE — merged PR #681 @ `9d8c8a51c10bb2eb56739bc2661cb37f9f401ebb`  
**Canonical handoff path:** `Docs/Plans/HANDOFF-SURFACE-INTEGRATION-ingest-run-information-adoption-v1.md`  
**Conversation/workstream:** `SURFACE-INTEGRATION / SI-5B`  
**Flow / owner:** `SURFACE-INTEGRATION`  
**Direction:** DESIGN → CODE → REVIEW  
**Base revision:** `a543af46f21d31d6ad83a88c3b2911ca4e0e4016`  
**Predecessor:** PR #680 / SI-5A merged at `a543af46f21d31d6ad83a88c3b2911ca4e0e4016`; final implementation head `4ccbe0fad1f5c9c60c3ced6173d842a77b162289`; three formal review cycles  
**PR title:** `SURFACE-INTEGRATION: move Ingest run catalog onto Surface Information`  
**Accepted implementation head:** `d0e9aaa80a78f71ad6bfd2195002eb5de67f098f`  
**Merge:** `9d8c8a51c10bb2eb56739bc2661cb37f9f401ebb`  
**Formal review cycles:** 3  
**Successor stewardship:** [`HANDOFF-STEWARDSHIP-finish-surface-integration.md`](HANDOFF-STEWARDSHIP-finish-surface-integration.md)

> Completion note: the forward-looking body below is retained as the historical SI-5B implementation/review contract. Review established that PROMOTED exact historical inspection requires a separate neutral inspection seam and remained out of this slice; it is not automatically a SURFACE-INTEGRATION closure requirement.

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../../Docs/Process/STEWARD-CYCLE.md). External PR mechanics: [`.cursor/skills/external-agent-pr-loop/SKILL.md`](../../.cursor/skills/external-agent-pr-loop/SKILL.md). Parent program: [`ROADMAP-surface-integration.md`](../Roadmaps/ROADMAP-surface-integration.md). Surface Information semantics: [`CONTRACT-surface-information-v1.md`](../Design/CONTRACT-surface-information-v1.md). Persistence predecessor: [`HANDOFF-SURFACE-INTEGRATION-ingest-application-state-authority-v1.md`](HANDOFF-SURFACE-INTEGRATION-ingest-application-state-authority-v1.md).

---

## §0 Steward design ruling

SI-4 already decided durable run authority:

```text
ExtractionRun identity / lifecycle / revision / scope / lineage / component claims
    → Buddy APP-STATE PostgreSQL `ingest.run`
```

SI-5B must make the normal `/ingest` product surface observe that authority. It must **not** make the legacy file-backed GraphIngest registry more reactive.

The current normal route is:

```text
/ingest
  → MemoryIngestPage
  → GraphReviewWorkbenchModule
  → getGraphIngestRuns({ requirePreviewUnionStore: true })
  → GET /api/live/graph-preview/graph-ingest/runs
  → discover_graph_ingest_runs(...)
  → recursive graph_ingest_run_manifest.json discovery under checkout-relative roots
```

The current browser selection identity is also a path:

```text
GraphReviewAppliedSelection.manifestPath
URL ?run=<manifest path>
sessionStorage dmb.graph-review.applied-selection.v1
catalog merge/dedupe by manifest_path
```

That is now architecturally false. A missing worktree-local `out/` can still make Graph Review look empty even while canonical runs exist in PostgreSQL.

### The one capability in this PR

> **Normal `/ingest` Graph Review observes the canonical APP-STATE ExtractionRun catalog through one Surface Information channel and identifies selected live runs by exact `run_id`; legacy GraphIngest manifests may remain compatibility/evaluation evidence after exact run selection but can no longer determine product run existence or identity.**

Do not split this into “add a list API” and “wire the UI” PRs. Either half alone leaves the product lying about authority. Conversely, do not absorb Gold/eval redesign, SourceArtifact persistence, GraphIngest packaging demolition, Play/Combat adoption, or Agent/#674 disposition into this slice.

### Authority separation

```text
APP-STATE `ingest.run`
  owns: run exists / run_id / status / revision / scope / lineage / component claims

legacy GraphIngestRunManifest + file artifacts
  may still provide: compatibility/evaluation locator or exact review evidence bytes
  does NOT own: product catalog existence or selected run identity

Gold review fixtures
  remain: optional evaluation sidecar
  may enrich an already-canonical run only by exact run_id match
  may NOT inject a live product run into the catalog
```

This is the central review rule. A solution that still starts with `getGraphIngestRuns()` and wraps its response in `SurfaceInformationChannel` fails the mission.

---

## §1 Mission and merge-ready invariant

**Mission:** The GM can open `/ingest`, see the same canonical ExtractionRuns from any supported checkout/worktree, and load one exact run by `run_id`, while changing run-catalog observations update reactively through Surface Information instead of file discovery or manifest-path identity.

**Merge-ready invariant:**

> **For the normal `/ingest` Graph Review catalog, APP-STATE `ingest.run` is the sole existence authority, the selected live-run identity is exact `run_id`, one route-lifetime `SurfaceInformationChannel` carries the catalog observation with `authority = buddy_app_state`, refreshes use channel ticket/generation semantics, and no legacy manifest path/file scan/Gold available-run list may create, replace, hide, or select a product run. Missing compatibility/evidence bytes leave the canonical run visible and fail explicitly only when exact evidence is requested.**

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | **Yes.** Server list, channel mapping, picker identity, persistence/restore, refresh, and exact-evidence handoff are all governed by “APP-STATE decides existence; run_id decides identity.” |
| Most likely adversarial sequence | DB contains run A → worktree has no `out/` → `/ingest` loads A → refresh begins → DB changes to B / A superseded → older HTTP completion returns late → browser must retain only the newest accepted catalog generation and never rediscover a file manifest. |
| Will §7 actually detect that failure? | Yes: route DB-only witness + fresh-worktree/no-out browser witness + delayed-response ticket test + exact selection reconciliation. |
| Easiest owning boundary to under-test | The catalog composition seam where `GoldReviewSessionSummary.available_runs` currently merges legacy manifest-backed runs into the product live-run list. |
| Fact that forces stop/split | If normal Graph Review cannot load/inspect a canonical run without introducing a new durable Source/Blob authority or a new compatibility lookup contract, stop and re-brief. Do not smuggle file-registry authority into the APP-STATE channel. |

---

## §2 Context, authority, and lane

| Field | Required content |
|---|---|
| Parent authority | `ROADMAP-surface-integration.md`; `CONTRACT-surface-information-v1.md`; SI-4 APP-STATE Ingest authority |
| Base revision | `a543af46f21d31d6ad83a88c3b2911ca4e0e4016` |
| Predecessor contract | SI-4: APP-STATE `ingest.run`; SI-5A: production Surface Information adoption pattern |
| Exact input consumed | Unfiltered canonical `list_extraction_runs()` result from APP-STATE, represented over HTTP as `dmb_extraction_run_catalog_v1` |
| Current slice | **SI-5B — Ingest application-state Surface Information adoption** |
| Named successor | **SI-5 remainder — re-anchor Play / Combat-facing information adoption and explicit Agent/#674 disposition after SI-5B merges** |
| What remains false | Play/Combat-facing information is not yet normalized; Agent does not yet consume the same truthful Surface information; PR #674 is still parked; SI-6 clean-start witness is not complete |
| Explicit non-goals | Gold fixture redesign; GraphIngest packaging deletion; SourceArtifact authority migration; new ingest UX; new extraction features; blob/object store; Play/Combat/Agent changes |
| Branch / isolated checkout | `agent/surface-integration-ingest-run-information-v1` in an isolated worktree/check-out from the final steward handoff commit |
| Parallel lanes / collision hotspots | PR #674 remains OPEN/PARKED at `c194c70947780d5248f938421615b28a262d7d37`; its API/Agent/Play files are read-only collision boundary (§5) |
| Runtime/state ownership | APP-STATE PostgreSQL is shared durable authority. Tests must use disposable APP-STATE DSNs/fixtures; do not run destructive migrations against an operator DB. Surface Information channel is browser-runtime only. |
| State-authority sync set after merge | This handoff, SI-5A handoff, and `ROADMAP-surface-integration.md` only |

### Backward-looking predecessor sync required in this implementation PR

Record SI-5A truth:

```text
PR #680 merged
merge SHA            a543af46f21d31d6ad83a88c3b2911ca4e0e4016
final implementation 4ccbe0fad1f5c9c60c3ced6173d842a77b162289
formal review cycles 3
successor            SI-5B Ingest APP-STATE Run Information adoption
```

Then:

- mark `HANDOFF-SURFACE-INTEGRATION-build-graph-information-adoption-v1.md` COMPLETE with those facts;
- mark SI-5A DONE and SI-5B CURRENT in `ROADMAP-surface-integration.md`;
- retain `No DungeonBuddy feature thaw before SI-6 acceptance.`

Do not pre-mark SI-5B DONE.

---

## §3 Observable paths and adversarial sequences

| Path | Current behavior | Required behavior | Same §1 invariant? | Owning boundary |
|---|---|---|---:|---|
| `/ingest` live-run catalog | File-manifest discovery via `getGraphIngestRuns` | APP-STATE list endpoint → Surface Information | Yes | server adapter + route + Ingest provider |
| Initial empty catalog | No discovered manifests can look like no product runs | DB zero rows → `EMPTY`; explicit successful empty UI | Yes | provider mapper + workbench |
| APP-STATE unavailable / schema behind | Legacy file scan may still return data or false-empty | `UNAVAILABLE`; no old/actionable rows | Yes | route error code + provider mapper |
| Malformed DB/catalog payload | Legacy parser behavior | `INTEGRITY_ERROR`; no actionable runs | Yes | server model + client mapper |
| Refresh after run creation/status change | Local React state + refresh token re-fetches file registry | Same channel begins new observation; accepted generation updates in place | Yes | provider/channel |
| Late refresh completion | Custom cancellation/local state can race | stale ticket cannot mutate latest channel generation | Yes | Surface Information channel owner |
| Explicit load selection | `manifestPath` identifies run | exact `run_id` identifies run | Yes | applied selection + picker/workbench |
| Browser restore | URL/session storage persist path | v2 storage/URL persist run_id; path-shaped legacy identity is not re-admitted | Yes | applied selection |
| Canonical run missing local bytes | Usually absent from manifest catalog | run stays visible; exact review/evidence request fails explicitly | Yes | catalog vs exact review boundary |
| Legacy manifest-only run | Can appear as product run | absent unless same run exists in APP-STATE | Yes | catalog composition |
| Gold session legacy `available_runs` | Can seed/merge live product runs | optional compatibility enrichment only after exact canonical run_id match | Yes | graphReviewWorkbenchUtils |
| Build exact-run handoff | `extractionRunId` exact path already exists | remains valid and resolves same canonical run | Yes | exact-run handoff regression |
| Terminal confirm / committed projection | runId already binds committed authority | unchanged; canonical catalog refresh may reflect PROMOTED without replacing binding | Yes | existing committed-binding tests |

### Adversarial sequences that must be proved

| Sequence | Required safe outcome | Owning §7 proof |
|---|---|---|
| DB has A; local `out/graph_memory/runs` absent | `/ingest` sees A | W1/W2 |
| DB has A; conflicting manifest claims same run_id with different scope/status | DB A wins; compatibility cannot overwrite it | W3 |
| Manifest-only B exists; DB has no B | B is absent from normal `/ingest` catalog | W4 |
| Gold fixture `available_runs` contains legacy-only B | B does not enter live product catalog | W5 |
| A selected; same session has A+B | exact A remains selected by run_id | W6 |
| A explicitly selected; refresh removes A | clear/mark unavailable exact selection; do not silently substitute B as “latest” | W7 |
| No explicit run selection | deterministic default may be offered; it must be visibly a UI default, not persisted/exposed as a “latest” authority contract | W8 |
| READY(A catalog) → refresh → READY(B catalog) → old A HTTP resolves late | B remains current; old ticket commit rejected | W9 |
| selected canonical run exists; component bytes missing | catalog still shows run; exact review surfaces evidence failure | W10 |
| APP-STATE current + zero rows | channel `EMPTY`; no “authority down” copy | W11 |
| configured APP-STATE unavailable / migration behind | channel `UNAVAILABLE`; no stale rows unless future explicit STALE policy exists | W12 |
| malformed response / duplicate run_id | `INTEGRITY_ERROR`; no selection actions | W13 |
| catalog generation changes only | no Ingest projection-surface lease unbind/rebind solely because observations changed | W14 |
| `/ingest?extractionRunId=<exact>` from Build | exact mode still resolves run and review package | W15 |
| terminal confirm promotes run then catalog refreshes | selected run remains same run_id; status updates; committed projection behavior unchanged | W16 |

---

## §4 Files in scope — exclusive write lease

### Docs / authority sync

| Action | Path | Purpose |
|---|---|---|
| Create | `Docs/Plans/HANDOFF-SURFACE-INTEGRATION-ingest-run-information-adoption-v1.md` | Current checked-in review contract |
| Modify | `Docs/Plans/HANDOFF-SURFACE-INTEGRATION-build-graph-information-adoption-v1.md` | Backward-sync #680 COMPLETE facts |
| Modify | `Docs/Roadmaps/ROADMAP-surface-integration.md` | SI-5A DONE; SI-5B CURRENT; preserve SI-6 thaw gate |

### Server provider / route

| Action | Path | Purpose |
|---|---|---|
| Create | `apps/live_control_server/services/ingest_run_catalog.py` | Thin Buddy adapter from APP-STATE list authority to typed catalog response/error codes |
| Modify | `apps/live_control_server/routes/graph_preview.py` | Add static canonical `GET /extraction-runs` list route before/alongside exact `/{run_id}` route; no file registry call |

### Browser Ingest provider

| Action | Path | Purpose |
|---|---|---|
| Create | `apps/live-control-ui/src/ingestSurface/ingestRunCatalogApi.ts` | Dedicated client + local response/error types; avoids shared `liveApi` collision with #674 |
| Create | `apps/live-control-ui/src/ingestSurface/ingestRunCatalogSurfaceInformation.ts` | Pure descriptor + success/error observation mapping |
| Create | `apps/live-control-ui/src/ingestSurface/useIngestRunCatalogInformation.ts` | Route-lifetime channel owner, refresh/ticket/dispose behavior |
| Modify | `apps/live-control-ui/src/ingestSurface/MemoryIngestPage.tsx` | Own one catalog channel for `/ingest` and pass stable handle/refresh boundary to Graph Review |

### Graph Review canonical catalog / selection

| Action | Path | Purpose |
|---|---|---|
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.tsx` | Subscribe to canonical channel; separate Gold sidecar; run_id selection; remove `getGraphIngestRuns` normal path |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphReviewAppliedSelection.ts` | v2 run_id URL/session restore contract; legacy manifest-path identity fails closed |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphReviewWorkbenchUtils.ts` | Canonical DB-run catalog composition; run_id dedupe; Gold available-runs enrichment cannot inject product runs |
| Create | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewRunPicker.tsx` | Canonical run_id picker; do not reuse manifest-keyed Gold picker |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewLanePicker.tsx` | Use canonical picker and run_id selection |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewLoadSurface.tsx` | Draft runId/loadability semantics |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewLoadLaneSummary.tsx` | Canonical selected-run summary; compatibility locator labeled as such only if exact-run matched |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewLiveStateContext.tsx` | Canonical run view/type rather than manifest summary |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphReviewLiveReviewState.ts` | Key retired live lane/committed workflow by run_id/revision/status, never manifest path |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewLaneCards.tsx` | Advanced details reflect canonical run status/revision/components; legacy path is compatibility metadata only |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphReviewReferenceLaneUtils.ts` | Primary live-lane identity/label from canonical run_id |

### Owning-boundary tests

| Action | Path | Purpose |
|---|---|---|
| Create | `tests/test_ingest_run_catalog_routes.py` | DB-only list API, empty/unavailable/integrity, file-registry non-authority |
| Create | `apps/live-control-ui/src/ingestSurface/ingestRunCatalogSurfaceInformation.test.ts` | Descriptor + READY/EMPTY/UNAVAILABLE/INTEGRITY mapping |
| Create | `apps/live-control-ui/src/ingestSurface/useIngestRunCatalogInformation.test.tsx` | Same-channel refresh, late-ticket rejection, dispose |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.test.tsx` | End-to-end normal `/ingest` catalog authority, selection, refresh, exact handoff/confirm regressions |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphReviewAppliedSelection.test.ts` | run_id v2 persistence + legacy path rejection |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphReviewWorkbenchUtils.test.ts` | canonical dedupe/composition + Gold non-injection/exact enrichment |

### Bounded test-only discovery exception

```text
Directory:
  apps/live-control-ui/src/planSurface/graphReviewWorkbench/**
  apps/live-control-ui/src/ingestSurface/**

Maximum additional paths:
  6 existing test files

Allowed path kinds:
  *.test.ts
  *.test.tsx

Decision rule:
  Only when a production type/signature in the explicit §4 lease changes and the
  existing test directly imports/constructs that changed type or owns W1-W16.
  Record every added path and reason in the PR body/§8 handback before editing.
```

Any additional **production** path is a stop/rebrief. Do not use the bounded exception for production convenience.

---

## §5 Explicitly out of scope / collision boundary

| Path | Why this slice must not touch or claim it |
|---|---|
| `apps/live-control-ui/src/api/liveApi.ts` | PR #674 collision hotspot. SI-5B gets a dedicated Ingest API client. |
| `apps/live-control-ui/src/api/liveApi.test.ts` | Same collision boundary. |
| `apps/live-control-ui/src/api/types.ts` | PR #674 collision hotspot; import existing `ExtractionRunRecord` read-only instead of changing shared types. |
| `apps/live_control_server/main.py` | PR #674 collision hotspot; graph-preview router is already mounted. |
| `apps/live_control_server/routes/agent.py` | Parked Agent lane. |
| `apps/live-control-ui/src/agentInteraction/**` | Parked Agent lane; Agent consumption is later SI-5. |
| `apps/live-control-ui/src/playSurface/**` | Parked #674 / later Play adoption. |
| `src/application_state/ingest/**` | SI-4 stable authority. Consume its service; do not redesign persistence in an adoption PR. |
| `src/application_state/migrations/**` | No schema change is required for this slice. |
| `apps/live_control_server/services/graph_ingest_run_registry.py` | Legacy compatibility/eval discovery remains, but normal `/ingest` stops using it. Do not “fix” it into product authority. |
| `apps/live_control_server/services/promotable_ingest_run.py` | Exact run/evidence resolver already prefers canonical ExtractionRun. Preserve. |
| `src/graph_memory/ingestion/graph_ingest_run.py` | Legacy packaging compatibility remains intentionally. |
| `src/graph_memory/extraction/**` | No extraction producer or packaging change. |
| `apps/live-control-ui/src/planSurface/graphGoldReview/**` | Gold/evaluation surface remains separate; create a canonical picker in Graph Review rather than mutating Gold picker contracts. |
| `Docs/Design/CONTRACT-surface-information-v1.md` | Stable authority; SI-5B adopts it rather than rewriting it. |
| DungeonMind repo/schema | Unrelated authority. |
| package/lockfiles | No dependency change required. |

### Hard prohibition

Normal `/ingest` product code may not recover missing catalog information by:

- scanning `out/graph_memory/runs`;
- calling `discover_graph_ingest_runs` / `getGraphIngestRuns`;
- treating `manifest_path`, `run_dir`, `preview_union_store_path`, or `component.exists` as run-existence authority;
- joining a legacy-only Gold `available_run` into the product catalog;
- inventing “latest run” when an explicit run_id vanished;
- synthesizing a catalog authority revision from row count, timestamps, max run revision, hashes, or channel generation.

---

## §6 Implementation contract

### §6.1 Canonical server catalog endpoint

Add:

```text
GET /api/live/graph-preview/extraction-runs
```

Response:

```json
{
  "schema_version": "dmb_extraction_run_catalog_v1",
  "runs": [ /* canonical ExtractionRun records */ ]
}
```

Rules:

- call APP-STATE `application_state.ingest.service.list_extraction_runs()` **unfiltered**;
- do not call the legacy GraphIngest registry;
- return all canonical domains; browser Graph Review decides which records fit recap/session catalog display;
- preserve exact run model fields; do not fabricate manifest paths or file availability;
- deterministic response order is allowed for rendering/testing, but ordering is not identity or “latest” authority;
- zero rows → `200` with `runs: []`;
- no automatic migration/import;
- no fallback on APP-STATE failure.

Use a new `apps/live_control_server/services/ingest_run_catalog.py` provider adapter rather than extending the persistence service with presentation concerns.

The adapter should expose typed API error codes so the dedicated browser client can distinguish integrity from dependency availability without changing shared `liveApi`:

```text
ingest_run_catalog_unavailable
  ← ApplicationStateUnavailableError

ingest_run_catalog_schema_unavailable
  ← ApplicationStateMigrationError

ingest_run_catalog_integrity_error
  ← ApplicationStateIntegrityError

ingest_run_catalog_error
  ← other ApplicationStateError
```

Keep the underlying HTTP status consistent with the existing APP-STATE error status unless a route test demonstrates a compelling existing convention. The stable `detail.code` is the browser classification seam.

### §6.2 Dedicated browser API client

Create `ingestRunCatalogApi.ts` because #674 owns shared API files.

It must:

- call only `/api/live/graph-preview/extraction-runs`;
- parse the structured error code from the new endpoint;
- validate top-level schema;
- validate `runs` is an array of objects with non-empty exact `run_id`;
- reject duplicate run_ids as integrity failure;
- not resolve component files;
- not call legacy graph-ingest endpoints;
- reuse the existing `ExtractionRunRecord` TypeScript type by import only.

Do not add a generic alternate `apiFetch` framework in this slice.

### §6.3 Surface Information descriptor and revision

One route-lifetime channel observes the whole canonical catalog:

```ts
{
  channelId: "ingest-extraction-run-catalog:v1",
  informationKind: "extraction_run_catalog",
  providerId: "ingest_extraction_run_catalog",
  authority: "buddy_app_state",
  subject: { kind: "application_state_collection", id: "ingest.run" },
  scope: {}
}
```

Exact spelling may vary only if existing Surface Information validation requires a narrower reference shape. Do not make campaign/session selection part of the descriptor; the current Load dialog spans sessions/campaigns and should not trigger duplicate catalog authority reads.

Catalog authority revision:

```ts
{ kind: "unrevisioned" }
```

Reason: APP-STATE currently exposes per-run revisions, not one exact collection revision. Individual `run.revision` remains payload data. Do not synthesize a collection revision.

Observation mapping:

| API outcome | Surface Information |
|---|---|
| valid response, `runs.length > 0` | `READY`, value = response, `unrevisioned` |
| valid response, zero rows | `EMPTY`, no value, `unrevisioned` |
| unavailable/schema-unavailable/network failure | `UNAVAILABLE`, no value |
| typed APP-STATE integrity error | `INTEGRITY_ERROR`, no value |
| malformed schema / duplicate run_id | `INTEGRITY_ERROR`, no value |
| STALE | not emitted by this provider in v1 |

Diagnostics must be bounded and credential-safe.

### §6.4 Channel owner and refresh

`MemoryIngestPage` owns one channel for the route lifetime through `useIngestRunCatalogInformation`.

On mount:

```text
create exact descriptor
beginObservation()
GET canonical list
commit mapped observation
```

On `GRAPH_REVIEW_RUNS_CHANGED_EVENT`:

```text
same channel handle
beginObservation()
GET canonical list
commit current ticket only
```

Late/older completions are rejected by channel ticket semantics. Unmount disposes the channel and makes later completion inert.

Do not mirror channel state into another authority-shaped React state machine. Graph Review subscribes directly with `useSyncExternalStore`.

### §6.5 Normal Graph Review catalog composition

Define a local Graph Review catalog run view derived from `ExtractionRunRecord`, for example:

```ts
interface GraphReviewCatalogRun {
  run: ExtractionRunRecord;
  compatibilityManifestPath: string | null;
}
```

The wrapper is UI composition, not authority.

Canonical catalog rules:

1. Start with APP-STATE channel runs only.
2. Normal session picker candidates require exact recap scope:
   - `source_domain === "recap"`
   - non-empty `campaign_id`
   - non-empty `session_id`
3. Dedupe only by `run_id`.
4. Never create a live run from `GoldReviewSessionSummary.available_runs`.
5. Gold/eval `available_runs` may provide `compatibilityManifestPath` **only** when their non-empty `run_id` exactly matches a canonical run_id and campaign/session scope also matches.
6. A conflicting legacy record is ignored for authority fields. It must never replace DB status/revision/scope/source_artifact_id.
7. Missing exact compatibility match means Gold compare is explicitly unavailable/degraded for that run; the canonical run remains usable for normal exact review.

This preserves optional Gold comparison without returning manifest paths to product identity.

### §6.6 Reviewability / inspectability

Do not use `preview_union_available` as product loadability. Store-backed UnionSupergraph preview is already retired.

Canonical status behavior:

```text
reviewable
  → inspectable and promotable candidate

promoted
  → inspectable history / exact review; not promotable again

superseded / rejected / failed
  → may remain visible as history/status but must not become a default promotable candidate

draft / prepared / extracted / validated / incomplete
  → visible if useful, but not review-ready
```

At minimum, the picker must make status truth visible and only enable actions whose existing exact-run/prepare contract accepts the current status.

A run with `REVIEWABLE` status and required component claims remains catalog-visible even if its files are absent. Catalog does not prove component bytes.

### §6.7 Product selection identity v2

Replace path identity:

```ts
interface GraphReviewAppliedSelectionV2 {
  campaignId: string;
  sessionId: string;
  runId: string | null;
}
```

Storage:

```text
dmb.graph-review.applied-selection.v2
```

URL:

```text
?campaign=<campaign>&session=<session>&run=<exact run_id>
```

`run=` is now an exact run_id in the ordinary Load dialog flow. It is not a path. Keep the existing `extractionRunId=` exact Build handoff contract working; do not rewrite that parser in this slice.

Legacy v1 storage/path behavior:

- do not silently map a v1 manifest path by scanning files;
- do not treat `/`, `\\`, `.json`, or known manifest-like URL `run=` values as canonical IDs;
- ignore/clear inadmissible legacy selection and present a normal deterministic default only when there is **no valid explicit run_id**;
- if a valid explicit run_id was selected but is absent after refresh, clear/mark that selection unavailable. Do not silently switch to another same-session run.

Default selection when no explicit run_id is a UI convenience, not “latest run” authority. Use a deterministic documented ordering. Do not persist a default as if it had been user-selected until the existing Load action commits it.

### §6.8 Exact review / evidence boundary

For one selected canonical run, use the existing exact paths:

```text
GET /api/live/graph-preview/extraction-runs/{run_id}
GET /api/live/extract-promote/runs/{run_id}/review-package
```

The existing server exact review resolver is allowed to inspect component bytes and compatibility packaging because exact identity is already fixed by APP-STATE run_id.

Required behavior:

```text
catalog says run exists
+ evidence bytes present and valid
  → exact review succeeds

catalog says run exists
+ evidence bytes missing / digest mismatch
  → catalog STILL shows run
  → exact review fails explicitly
  → no fallback to a same-id or same-session manifest
```

Do not add path fields to the APP-STATE catalog merely to make exact review easier.

### §6.9 Gold comparison is an optional sidecar

`getGoldReviewSessions()` / `getGoldReviewCompare()` remain existing evaluation support.

They must be decoupled from catalog availability:

- Gold endpoint failure does not turn a valid APP-STATE catalog into `UNAVAILABLE`;
- no Gold fixture is required to list/load a canonical run;
- Gold compare may run only when an exact canonical run_id has an exact matched compatibility manifest locator;
- if no exact locator exists, render compare as unavailable/degraded while canonical review remains present;
- Gold compatibility data may not flow back into selection identity.

If preserving Gold comparison requires a new server lookup contract beyond exact run_id matching of data already returned by `getGoldReviewSessions()`, **stop and rebrief**. Do not add another file-registry product API in this PR.

### §6.10 Structural publication stability

The current Graph Review projection-surface publication is structural. Catalog loading/refresh must not repeatedly unbind/rebind the Ingest surface lease merely because catalog observations change.

Changing:

```text
LOADING → READY
READY(A) → LOADING → READY(B)
READY → EMPTY
READY → UNAVAILABLE
```

must update the connected catalog UI via the channel. It must not require a new projection-surface identity or a catalog snapshot embedded in structural publication.

### State / fallback matrix

| Observable path | Loading/init | Exact success | Ordinary miss | Dependency unavailable | Integrity failure | Stale/superseded | Retry/replay |
|---|---|---|---|---|---|---|---|
| Canonical catalog channel | LOADING | READY unrevisioned | EMPTY unrevisioned | UNAVAILABLE | INTEGRITY_ERROR | provider emits no STALE | same handle, new ticket/generation |
| Run selection | no actionable catalog | exact run_id | explicit ID absent → unresolved/clear | no selection mutation | no selection mutation | superseded status shown truthfully | user may reselect exact ID |
| Exact review package | wait | exact selected run | 404 exact run → error | explicit unavailable/error | evidence integrity error | terminal/superseded status fails per existing exact contract | retry same exact run only |
| Gold compare | independent loading | exact run_id-matched compatibility locator | no locator → compare unavailable | compare unavailable only | compare error only | no authority effect | retry compare only |

### Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback permitted? |
|---|---|---|---|
| `run_id` | Sole product live-run identity | duplicate DB IDs → INTEGRITY_ERROR | No |
| manifest path | Compatibility/evaluation locator only after exact run_id match | conflicting/multiple locator → compare unavailable | Never for product identity |
| campaign/session | Scope/filter, not run identity | exact run scope mismatch → ignore compatibility match / integrity where applicable | No scope invention |
| label/profile/timestamp | Display/order only | never used to resolve identity | No |
| selected run deleted/vanished | explicit selection becomes unresolved | do not choose “latest” replacement | No |
| no explicit selection | deterministic UI default allowed | must not masquerade as persisted authority | Yes, UI-only default |

### Predecessor → consumer mapping

**Grounding source:** canonical `ExtractionRun` model + SI-4 APP-STATE service + existing exact Graph Review run handoff.

| Predecessor field | Consumer behavior | Transformation | Proof |
|---|---|---|---|
| `run_id` | picker key/value, URL/storage exact identity, committed binding | none | W6/W7/W15/W16 |
| `source_artifact_id` | display/exact review handoff validation | none | route + exact review tests |
| `source_domain` | recap-session catalog eligibility | exact string check | utility test |
| `status` | inspectable/promotable/read-only state | explicit status mapping | picker/workbench tests |
| `revision` | current run-record revision displayed/used as payload data | never channel revision | provider + UI test |
| `campaign_id` / `session_id` | normal catalog scope | require non-empty for recap picker | utility integrity/scope test |
| `components` | display claims / exact evidence resolver input downstream | no browser byte verification | W10 |
| `diagnostics` | bounded advanced details only | no authority override | UI test |
| supersession pointers | status/history identity | never “latest” inference | W7 |
| Gold `available_runs[].run_id` | optional compatibility join only | exact run_id + scope match | W5 |
| Gold `available_runs[].manifest_path` | compare locator only after exact match | never persisted/selected | W3/W5 |

---

## §7 Evidence required to merge

Use these witness IDs in the PR body and §8 handback.

| ID | Guarantee | Owning boundary | Required evidence |
|---|---|---|---|
| W1 | List API reads APP-STATE only | server route/provider | DB rows returned with legacy registry monkeypatched to explode / absent |
| W2 | Fresh worktree/no `out/` still sees canonical run | route + minimal browser dogfood | configured DB row visible in `/ingest`; no file manifests required |
| W3 | Conflicting same-id manifest cannot override DB fields | catalog composition | exact DB scope/status/revision wins |
| W4 | Manifest-only run absent from DB is absent from normal catalog | route/workbench | adversarial fixture |
| W5 | Gold `available_runs` cannot inject live product runs; exact run_id match may only enrich compare locator | utility/workbench | canonical set unchanged before/after Gold data |
| W6 | Two same-session runs select by exact run_id | picker + workbench | selecting A never resolves B |
| W7 | Explicit selected run vanishes | workbench selection reconciliation | no silent latest/default replacement |
| W8 | No explicit run gets deterministic UI default only | utility/workbench | default is not persisted until Load |
| W9 | Same-channel refresh rejects late old completion | Ingest channel hook | deferred A/B request test |
| W10 | Missing component bytes do not hide run | server catalog + exact review | catalog contains run; review-package fails explicitly |
| W11 | DB zero rows maps EMPTY | provider + UI | explicit empty copy; not unavailable |
| W12 | configured APP-STATE unavailable / schema unavailable maps UNAVAILABLE | server error code + provider | no stale/actionable rows |
| W13 | malformed response / duplicate run_id maps INTEGRITY_ERROR | API client/mapper | no actionable catalog value |
| W14 | catalog observation change does not republish/unbind structural Ingest projection surface | workbench/Agent host regression | stable surface identity/lease across channel generations |
| W15 | Build exact `extractionRunId` handoff remains valid | GraphReviewWorkbench regression | exact run + review package loads |
| W16 | terminal confirm/committed projection remains run_id-bound after status refresh | existing confirm/workbench cohort | no regression |
| W17 | Gold failure is independent from APP-STATE catalog | workbench | live catalog READY while compare sidecar unavailable |
| W18 | Normal product path demolished legacy catalog identity | search + tests | no `getGraphIngestRuns` call in MemoryIngestPage/GraphReviewWorkbench; no manifest path in applied-selection/picker key |
| W19 | #674 collision boundary honored | diff reconciliation | no shared API/Agent/Play path changed |

### Exact verification floor

Server, from repo root:

```bash
uv run pytest \
  tests/test_ingest_run_catalog_routes.py \
  tests/application_state/test_ingest_run_postgres.py \
  tests/test_graph_run_registry.py \
  tests/test_promotable_ingest_run.py \
  tests/test_graph_preview_routes.py
```

Client, from `apps/live-control-ui`:

```bash
npm test -- \
  src/ingestSurface/ingestRunCatalogSurfaceInformation.test.ts \
  src/ingestSurface/useIngestRunCatalogInformation.test.tsx \
  src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.test.tsx \
  src/planSurface/graphReviewWorkbench/graphReviewAppliedSelection.test.ts \
  src/planSurface/graphReviewWorkbench/graphReviewWorkbenchUtils.test.ts

npm run typecheck
npm run build
```

Also run any test files admitted through the bounded exception.

Demolition/search from repo root:

```bash
git grep -n "getGraphIngestRuns" -- \
  apps/live-control-ui/src/ingestSurface \
  apps/live-control-ui/src/planSurface/graphReviewWorkbench

git grep -nE "manifestPath|manifest_path|preview_union_available|preview_union_store_path|run_dir" -- \
  apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphReviewAppliedSelection.ts \
  apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewLanePicker.tsx \
  apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewRunPicker.tsx \
  apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewLoadSurface.tsx

git diff --check
git diff --name-only <implementation-base>...HEAD
```

Expected:

- first grep: no production normal-catalog call sites;
- second grep: no manifest/path/preview field used as selected identity or loadability. Compatibility-path mentions elsewhere are allowed only when explicitly labeled compatibility/evaluation and joined after exact run_id.

### Full-suite / baseline discipline

Run the full UI suite **serially**, not concurrently with a base suite. SI-5A established that parallel Vitest runs can create load-contaminated noise.

```bash
cd apps/live-control-ui
npm test
```

If failures occur:

1. record exact head totals + failing files;
2. reproduce claimed baseline cohorts on the immutable implementation base in a separate worktree using the same install;
3. do not infer baseline equivalence merely because a test file is unchanged;
4. distinguish owning-boundary regressions from established noise.

Server full suite may be omitted only if the focused route/APP-STATE floor is complete and the PR body records why existing broad-suite environment blockers remain unrelated. Any new collection error or Ingest owning-boundary failure is a merge blocker.

### Minimal live / dogfood proof

Required if a configured disposable/local APP-STATE DB is available:

```text
1. Use a supported fresh worktree with no `out/graph_memory/runs` tree.
2. Point DMB_APPLICATION_STATE_DATABASE_URL at the already-migrated local test/operator-safe DB.
3. Ensure at least one canonical ExtractionRun exists, or create one through an existing supported extraction/test fixture without changing production state unexpectedly.
4. GET /api/live/graph-preview/extraction-runs → run visible by run_id.
5. Open /ingest → same run visible/selectable by run_id.
6. Hard reload → selection restores by run_id, not a path.
7. If component bytes are intentionally absent, catalog remains visible and exact review reports the evidence failure explicitly.
```

If no safe configured DB exists, record that constraint; owning-boundary PostgreSQL tests remain mandatory.

---

## §8 Required review handback

For each distinct PR head, record:

1. `Review Cycle <N>` and exact PR/head SHA;
2. immutable implementation base and current `main` re-anchor;
3. cumulative changed-path list reconciled to §4 / bounded exception;
4. nano-commit/fix story;
5. W1-W19 required vs produced evidence with exact command/result provenance;
6. exact server/client focused test totals;
7. exact-head full UI suite outcome + truthful base reproduction if needed;
8. `git diff --check` and demolition-search results;
9. canonical API response example showing run_id/status/revision and **no fabricated manifest identity**;
10. Surface Information descriptor + READY/EMPTY/UNAVAILABLE/INTEGRITY examples;
11. evidence that Gold legacy runs cannot inject product catalog entries;
12. evidence that missing local bytes do not hide a canonical run;
13. evidence that explicit run selection is run_id and does not “latest” fallback;
14. evidence that #674 remained untouched/open unless steward separately changed its disposition;
15. backward SI-5A completion sync facts;
16. what remains false: Play/Combat/Agent adoption, #674 disposition, SI-6, feature thaw;
17. prior finding ledger on re-review.

---

## §9 Acceptance rubric

- [ ] SI-5A predecessor sync is backward-looking and exact: PR #680 merge `a543af46…`, implementation `4ccbe0fa…`, three cycles.
- [ ] Canonical list endpoint returns APP-STATE `ExtractionRun` records only.
- [ ] Legacy GraphIngest file discovery is absent from normal `/ingest` catalog path.
- [ ] `SurfaceInformationChannel` descriptor says `authority = buddy_app_state` and collection revision is `unrevisioned`.
- [ ] READY / EMPTY / UNAVAILABLE / INTEGRITY_ERROR are distinct and truthful.
- [ ] Same channel handle survives catalog refresh; tickets reject late completion.
- [ ] Graph Review subscribes with `useSyncExternalStore`; catalog bytes/state are not embedded in structural projection publication.
- [ ] Live product catalog starts from canonical DB runs only.
- [ ] Gold `available_runs` can enrich only an already-canonical exact run_id and cannot inject a run.
- [ ] `GraphReviewAppliedSelection` persists `runId`, not `manifestPath`.
- [ ] URL/session restore rejects legacy path identity without file-based migration.
- [ ] Explicit missing selected run never silently becomes another same-session run.
- [ ] `preview_union_available` is not product loadability authority.
- [ ] Canonical runs remain visible when component bytes are missing.
- [ ] Exact review/evidence failure happens after run identity is fixed.
- [ ] Existing Build exact-run handoff still works.
- [ ] Existing terminal confirm/committed projection workflow remains run_id-bound.
- [ ] Gold failure cannot mask a valid live APP-STATE catalog.
- [ ] Shared `api/liveApi*`, `api/types.ts`, Agent, Play, and `main.py` collision paths remain untouched.
- [ ] No APP-STATE schema/persistence change was introduced.
- [ ] No new Source/Blob/file authority was invented.
- [ ] Actual changed paths stay inside §4 / bounded test discovery.
- [ ] Exact-head evidence and baseline handling satisfy §7/§8.
- [ ] Feature freeze remains: no DungeonBuddy feature thaw before SI-6 acceptance.

---

## Stop conditions

Stop and report instead of expanding if any of these appears:

1. **A new durable authority is required.** If catalog usability needs a new SourceArtifact/blob store or persisted display projection, rebrief.
2. **Gold compare requires a new file-registry lookup contract.** Do not add it here; split evaluation compatibility from catalog authority.
3. **A production path outside §4 is required.** Especially shared API types/client, Agent/Play, APP-STATE persistence, or packaging code.
4. **PR #674 must be rebased/edited to proceed.** SI-5B must remain independent; steward resolves lane ownership separately.
5. **Canonical APP-STATE list cannot represent a required product run without manifest discovery.** That means SI-4 authority semantics are incomplete; stop rather than fallback.
6. **A single channel cannot truthfully represent the information because implementation starts mixing APP-STATE and file/eval authority in one value.** Split channels or rebrief; never use `mixed` authority.
7. **Exact run_id selection cannot preserve current confirm/review semantics without redesigning the irreversible promotion workflow.** Stop and split rather than silently changing promotion behavior.
8. **Baseline test comparison reveals new owning-boundary failures.** Repair before merge; no waiver by assertion.

Report using:

```text
Stop condition:
Invariant clause affected:
Why SI-5B cannot absorb it:
Required evidence now missing:
Affected paths / authority layers:
Proposed successor or re-brief:
State-authority update needed:
```
