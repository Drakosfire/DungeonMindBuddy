---
pr_body_template: |

  ## Handoff pointer

  * Conversation/workstream: SURFACE-INTEGRATION / SI-5A
  * Flow: SURFACE-INTEGRATION
  * Direction: DESIGN → CODE → REVIEW
  * Handoff: `Docs/Plans/HANDOFF-SURFACE-INTEGRATION-build-graph-information-adoption-v1.md`
  * Branch / PR: `agent/surface-integration-build-graph-information-v1` / `SURFACE-INTEGRATION: move Build graph reads onto Surface Information`

  ## Verification pointer

  * Base: `010634f8ea48ed396024c79db90f41d6ba92f249`
  * Predecessor: PR #679 merged @ `010634f8ea48ed396024c79db90f41d6ba92f249`
  * Changed paths: HANDOFF §4
  * Verification: HANDOFF §7

  The checked-in handoff, cumulative diff, nano-commit story, and independently
  rerun evidence are the review contract. This body is transport metadata.
---

# HANDOFF — Build World Graph Surface Information Adoption v1

**Created:** 2026-09-02
**Status:** COMPLETE — SURFACE-INTEGRATION SI-5A

**Completion record:**
```text
PR #680 merged
merge SHA            a543af46f21d31d6ad83a88c3b2911ca4e0e4016
final implementation 4ccbe0fad1f5c9c60c3ced6173d842a77b162289
formal review cycles 3
successor            SI-5B Ingest APP-STATE Run Information adoption
```
**Canonical handoff path:** `Docs/Plans/HANDOFF-SURFACE-INTEGRATION-build-graph-information-adoption-v1.md`
**Conversation/workstream:** `SURFACE-INTEGRATION / SI-5A`
**Flow / owner:** `SURFACE-INTEGRATION`
**Direction:** DESIGN → CODE → REVIEW
**Base revision:** `010634f8ea48ed396024c79db90f41d6ba92f249`
**Predecessor:** PR #679 / SI-4 merged at `010634f8ea48ed396024c79db90f41d6ba92f249`; final implementation head `55414e141f6508049c56c82bfb37bce7d9f3ba51`; two formal review cycles
**PR title:** `SURFACE-INTEGRATION: move Build graph reads onto Surface Information`

> Repository law: [`AGENTS.md`](../../AGENTS.md).
> Parent program: [`ROADMAP-surface-integration.md`](../Roadmaps/ROADMAP-surface-integration.md).
> Surface Information authority: [`CONTRACT-surface-information-v1.md`](../Design/CONTRACT-surface-information-v1.md).
> Reference implementation: [`HANDOFF-SURFACE-INTEGRATION-plan-graph-information-reference.md`](HANDOFF-SURFACE-INTEGRATION-plan-graph-information-reference.md).
> Completed persistence predecessor: [`HANDOFF-SURFACE-INTEGRATION-ingest-application-state-authority-v1.md`](HANDOFF-SURFACE-INTEGRATION-ingest-application-state-authority-v1.md).

---

## §0 Steward design ruling

SI-5 is an adoption phase, not one six-surface mega-PR.

Repository law requires one independently useful capability per slice. Re-anchor shows two immediate SI-5 migrations with different owning boundaries:

1. **Build World Graph information** already has a working exact-request loader, but it carries changing graph observations through `SurfaceInteractionPublication.projectionBindings`.
2. **Ingest run information** now has the correct PostgreSQL authority from SI-4, but `/ingest` still needs a DB-backed catalog/read API and must move product selection away from legacy `manifestPath` identity toward canonical `ExtractionRun.run_id`.

Those are separate contracts. Do not bundle them.

### SI-5 decomposition

This PR is **SI-5A — Build World Graph Surface Information adoption**.

Named successor is **SI-5B — Ingest application-state Surface Information adoption**.

Later SI-5 slices will dispose Play / Combat-facing information and Agent consumption against the same contract before SI-6. Do not pre-design those implementations in this PR.

### Why Build first

Build is the lowest-risk second production adoption of the SI-2 contract because it needs no new backend endpoint and no new authority decision. It already consumes the same DungeonMind World Graph projection shape as Plan.

The current Build implementation contains the exact architectural smell SI-2 separated:

```text
BuildReferenceCapability
  → useBuildWorldGraphProjection()
  → changing projection state / error / revision / items
  → BuildReferenceContextBinding
  → SurfaceInteractionPublication.projectionBindings
  → BuildReferenceSearchProjection
```

`BuildReferenceContextBinding` currently contains:

```text
projectionState
projectionError
requestedRevisionId
loadedRevisionId
loadedIsHead
items
```

That makes Surface Interaction publication carry changing information. Build therefore republishes structural interaction state when graph observations change.

The current Build loader also has two legitimate request modes:

- exact request equals the app-scoped World Graph lens request → reuse the shared projection;
- exact request differs (for example a pinned revision or a Build-specific exact lens) → perform one secondary exact projection read.

SI-5A preserves that product behavior while moving **both modes** onto `SurfaceInformationChannel<WorldGraphProjection>`.

### Chosen architecture

```text
Build exact request resolution
        |
        +-- same exact request as app provider
        |      → reuse the existing WorldGraphLens Surface Information channel
        |      → zero Build-owned authority reads
        |
        +-- distinct exact Build request
               → Build owns one request-scoped Surface Information channel
               → one postWorldGraphProjection read
               → mapWorldGraphLensObservation(...)

Surface Interaction publication
        → structural Build tool + callbacks + stable channel HANDLE
        → never projection bytes / items / observation status / generation

BuildReferenceSearchProjection
        → useSyncExternalStore(channel.subscribe, channel.getSnapshot)
        → renders current observation in place
```

A channel handle may cross the projection-binding seam because it is a stable reference to the Surface Information plane. **The observation may not.** The binding must not contain snapshot state, generation, graph items, revision, diagnostics, or projection bytes.

This is intentionally different from Plan's narrow React context because Build's projection host is registered/rendered outside the `BuildReferenceCapability` child subtree. Do not restructure AppChrome or create a global Surface Information registry merely to force the Plan transport mechanism onto Build.

---

# §1 Mission and merge-ready invariant

## Mission

The GM can use Build → Find existing object against the current exact DungeonMind graph lens while graph observations update through Surface Information rather than Surface Interaction publication.

## Merge-ready invariant

Given one accepted Build document and one exact Build World Graph request:

> **Build publishes structural reference capability once for a stable request/channel identity; the Find projection subscribes directly to the active `SurfaceInformationChannel<WorldGraphProjection>` and updates in place for observation generations; an exact request already owned by the app-scoped graph-lens provider causes zero secondary Build reads, a distinct exact Build request owns exactly one Build channel/read, verified observations become READY or EMPTY at an exact DungeonMind revision, failures become UNAVAILABLE or INTEGRITY_ERROR, late superseded work cannot mutate the current channel, and retained View/Insert callbacks re-read current information and fail closed rather than authorizing against render-captured graph state.**

Graph-information-only changes must not require a new `SurfaceInteractionPublication`.

---

# §2 Context, authority, and lane

| Field | Required content |
| --- | --- |
| Parent authority | `ROADMAP-surface-integration.md`; `CONTRACT-surface-information-v1.md`; SI-3 Plan reference implementation |
| Base revision | `010634f8ea48ed396024c79db90f41d6ba92f249` |
| Predecessor | SI-4 / PR #679 merged; final implementation `55414e141f6508049c56c82bfb37bce7d9f3ba51`; two formal review cycles |
| Current slice | **SI-5A — Build World Graph Surface Information adoption** |
| Named successor | **SI-5B — Ingest application-state Surface Information adoption** |
| Branch | `agent/surface-integration-build-graph-information-v1` |
| PR title | `SURFACE-INTEGRATION: move Build graph reads onto Surface Information` |
| Parallel lane | PR #674 remains OPEN / PARKED and read-only |
| Feature freeze | Unchanged: no feature thaw before SI-6 acceptance |

### Backward-looking predecessor sync

This implementation PR must record:

```text
PR #679 merged
merge SHA            010634f8ea48ed396024c79db90f41d6ba92f249
final implementation 55414e141f6508049c56c82bfb37bce7d9f3ba51
formal review cycles 2
successor             SI-5A Build World Graph Surface Information adoption
```

Update:

- `HANDOFF-SURFACE-INTEGRATION-ingest-application-state-authority-v1.md` → COMPLETE / merged facts.
- `ROADMAP-surface-integration.md` → SI-4 DONE; decompose SI-5 and mark SI-5A CURRENT; retain SI-6 feature-thaw gate.

Do not churn `CONTRACT-surface-information-v1.md`, SI-3's completed handoff, or stable architecture docs: their claims already support this slice.

---

# §3 Normative implementation design

## §3.1 Exact request ownership remains Build-owned

`resolveBuildFindGraphLens(...)` and `buildBuildWorldGraphRequestFromLens(...)` remain the source of Build's exact requested information identity.

Do not move Build lens policy into Surface Information and do not let the channel choose campaign/scope/revision.

For a ready lens, compute the exact `WorldGraphProjectionRequest` and `requestKey` exactly as today.

The current app-scoped `WorldGraphLensProjectionProvider` remains unchanged and remains the owner of its own exact request.

## §3.2 Shared-provider reuse rule

Build must consume both:

```ts
useOptionalWorldGraphLensProjection()          // desired exact shared request identity only
useOptionalWorldGraphLensInformationChannel()  // changing shared observation
```

If:

```text
sharedProjection.requestKey === buildRequestKey
```

then the app provider owns the authority read.

Build must:

- wait for a matching shared information-channel descriptor;
- return/use that exact channel handle;
- never call `postWorldGraphProjection` for that request;
- never create a mirrored Build channel and copy shared observations into it.

### Transient replacement rule

A shared desired request can change before the matching new shared channel is installed.

If the **shared desired request key already equals Build's request key** but the currently visible shared channel is null or still belongs to the previous request, Build waits in a no-current-observation/loading posture.

It must **not** interpret that transient as permission to issue a secondary Build POST. This is the same duplicate-read class repaired during SI-3.

## §3.3 Secondary exact Build provider

When Build's exact `requestKey` differs from the app provider's desired `requestKey`, Build may own a secondary exact projection request.

Create a Build-specific request-scoped channel.

Suggested pure helper:

```ts
buildWorldGraphInformationDescriptor(
  request: WorldGraphProjectionRequest,
): SurfaceInformationDescriptor
```

Descriptor semantics:

```ts
{
  channelId: `build-world-graph:${requestKey}`,
  informationKind: "world_graph_projection",
  providerId: "build_world_graph_projection",
  authority: "dungeonmind",
  subject: { kind: "world", id: request.worldId },
  scope: /* exactly the same request scope semantics as worldGraphLensInformationDescriptor */,
}
```

Do not fork World Graph scope semantics. It is acceptable to derive the Build descriptor from `worldGraphLensInformationDescriptor(request)` and override only `channelId` + `providerId`.

For the secondary provider:

- one channel per exact Build request descriptor;
- request identity change → old channel disposed, new channel created;
- begin an observation before issuing the read;
- if `beginObservation()` returns null, issue **no** authority read;
- exactly one `postWorldGraphProjection(request)` per accepted load;
- commit with the existing `mapWorldGraphLensObservation({ request, response, error })`;
- no Build-specific reimplementation of READY / EMPTY / UNAVAILABLE / INTEGRITY mapping;
- no `unrevisioned` DungeonMind observations;
- no STALE emission in this provider;
- stale/superseded/disposed tickets cannot mutate a replacement channel.

Do not add another server endpoint or backend projection service.

## §3.4 Replace the current loader result with an information source

`useBuildWorldGraphProjection.ts` currently returns a second legacy state machine:

```text
projection
state
error
loadedRevisionId
loadedIsHead
generation
items
```

That result is what leaks changing graph information into Surface Interaction.

Refactor the hook so its authoritative output is structural/request ownership plus the active channel handle, for example:

```ts
interface UseBuildWorldGraphInformationResult {
  request: WorldGraphProjectionRequest | null;
  requestKey: string | null;
  loadKey: string;
  revisionMode: "head" | "pinned";
  requestedRevisionId: string | null;
  channel: SurfaceInformationChannel<WorldGraphProjection> | null;
  source: "none" | "shared_pending" | "shared" | "secondary";
}
```

Exact shape may vary, but the hook must no longer be a competing observable projection-state store.

No custom Build `generation` counter is needed for authority observation ordering; channel generations/tickets own that job.

Lens `invalid` / `selection_required` remains structural Build state and performs no graph request.

## §3.5 Surface Interaction binding separation

`BuildReferenceContextBinding` must stop carrying changing graph information.

Current fields to remove from the structural binding:

```text
projectionState
projectionError
requestedRevisionId   # derive from structural lens/request instead
loadedRevisionId
loadedIsHead
items
```

Because the shape changes materially, version the binding rather than silently mutating `dmb_build_reference_context_v1` semantics.

Use:

```text
dmb_build_reference_context_v2
```

The structural binding may contain:

```text
documentId
documentCampaignId
lens
selectCampaign(...)
viewExact(nodeId)
insertChip(nodeId)
editorInsertDisabled   # editor/document capability only, not graph observation state
```

Add a separate binding ID for the channel handle, for example:

```text
build-world-graph-information-channel
```

Its value is:

```ts
SurfaceInformationChannel<WorldGraphProjection> | null
```

The Build search projection registration requires both binding IDs.

### Hard prohibition

Neither structural binding may contain:

```text
SurfaceInformationSnapshot
SurfaceInformationState
generation
WorldGraphProjection bytes
GraphReferenceSearchItem[]
loaded authority revision
diagnostics
```

Graph-observation changes on the same channel must not cause `buildBuildSurfaceInteractionPublication(...)` to produce a new publication merely because the observation changed.

## §3.6 Connected Build search projection

`BuildReferenceSearchProjection` becomes a connected Surface Information consumer.

It receives:

- structural Build context binding v2;
- active channel handle binding.

It subscribes directly with:

```ts
useSyncExternalStore(channel.subscribe, channel.getSnapshot)
```

Use a stable fallback snapshot/accessor when channel is null; do not create fake authority data.

Render mapping:

```text
lens invalid
  → existing structural error; no authority request

lens selection_required
  → existing selection guidance; no authority request

ready lens + no matching channel yet
  → loading / waiting for exact information provider

LOADING
  → loading

READY
  → current graph items; exact revision summary

EMPTY
  → successful empty result; zero items; not error

UNAVAILABLE
  → explicit unavailable state

INTEGRITY_ERROR
  → explicit integrity/error state; zero actionable items

STALE
  → explicit stale state; fail closed for mutation
```

The World Graph providers used in this slice do not emit STALE. Consumer handling must still be truthful if a synthetic/future stale observation appears. The minimum acceptable behavior is an explicit stale message with mutation disabled; do not silently label STALE as READY.

Search items are adapted from the **current snapshot value**, never copied into the structural publication.

## §3.7 Current-information authorization

The current implementation authorizes View/Insert through render-captured `projection` objects plus mutable refs.

After migration, retained callbacks must re-read the channel at invocation.

### View

`viewExact(nodeId)` must:

1. resolve the currently active exact channel/request identity;
2. call `channel.getSnapshot()` at invocation;
3. require a currently usable observation;
4. find the node by ID in the current projection value;
5. derive exact graph scope from that same current value;
6. no-op if request/channel changed, node vanished, or exact scope is absent.

Do not authorize View using a `GraphReferenceSearchItem` object captured by the projection render.

For SI-5A, READY is always usable. If STALE viewing is retained, it must be explicitly labeled stale and must use the stale value/revision from that snapshot. Otherwise fail closed on STALE. Do not invent a false READY mapping merely to satisfy the legacy `GraphReferenceProjectionState` type.

### Insert

`insertChip(nodeId)` must additionally require:

- current channel snapshot status is **READY**;
- current node exists in that READY value;
- current Build document/editor owner is still committed/live;
- editor is interactive now;
- node campaign tenancy is admitted for the current document;
- exact graph reference comes from the current node.

EMPTY / STALE / LOADING / UNAVAILABLE / INTEGRITY_ERROR all deny insertion.

### Committed editor gate

Do not solve retained-callback safety with a render-mutated ref.

Use a committed gate (`useLayoutEffect` or equivalent) for the live Build editor/document capability and fail closed in cleanup on owner unmount/replacement, following the lesson from SI-3 Plan insert review cycles.

Render-time button/search disabled state may be computed directly from render state. Invocation authorization uses the committed gate.

## §3.8 Chip runtime and relationship resolution

`GraphNodeChipRuntimeProvider` must derive node views / exact graph scope from the current subscribed information observation, not from structural publication data.

Existing graph-reference relationship resolution may remain on its current registration API, but any resolver/open callback changed in this PR must re-read current channel information at invocation and fail closed across request replacement.

Do not modify the Agent Interaction or generic GraphReference contracts in this slice. If truthful STALE relationship semantics require widening those contracts, stop and rebrief; STALE is not emitted by the provider today and does not justify a second public-contract change here.

## §3.9 No AppChrome / core Surface Interaction changes

Do not modify:

```text
AppChrome
SurfaceInteractionPublication production types
projection host implementation
surfaceInformation production contract/channel
WorldGraphLensProjectionProvider
worldGraphLensSurfaceInformation mapping
```

This PR proves the existing abstractions are sufficient for a second production Surface.

---

# §4 Files in scope — exclusive write lease

| Action | Path | Purpose |
| --- | --- | --- |
| Create | `Docs/Plans/HANDOFF-SURFACE-INTEGRATION-build-graph-information-adoption-v1.md` | This implementation/review contract |
| Modify | `Docs/Plans/HANDOFF-SURFACE-INTEGRATION-ingest-application-state-authority-v1.md` | Backward-looking SI-4 completion sync |
| Modify | `Docs/Roadmaps/ROADMAP-surface-integration.md` | SI-4 DONE; decompose SI-5; SI-5A CURRENT; freeze preserved |
| Create | `apps/live-control-ui/src/buildSurface/reference/buildWorldGraphSurfaceInformation.ts` | Build secondary descriptor + pure snapshot/view adaptation |
| Create | `apps/live-control-ui/src/buildSurface/reference/buildWorldGraphSurfaceInformation.test.ts` | Descriptor/state adaptation tests |
| Modify | `apps/live-control-ui/src/buildSurface/reference/useBuildWorldGraphProjection.ts` | Replace custom observable loader with shared/secondary channel ownership |
| Modify | `apps/live-control-ui/src/buildSurface/reference/useBuildWorldGraphProjection.test.tsx` | Shared reuse, secondary provider, replacement/late-response tests |
| Modify | `apps/live-control-ui/src/buildSurface/reference/buildReferenceIds.ts` | Add information-channel binding id |
| Modify | `apps/live-control-ui/src/buildSurface/reference/buildBuildSurfaceInteractionPublication.ts` | v2 structural binding; channel-handle binding; remove graph payload/state |
| Modify | `apps/live-control-ui/src/buildSurface/reference/buildBuildSurfaceInteractionPublication.test.ts` | Structural/data-plane separation witnesses |
| Modify | `apps/live-control-ui/src/buildSurface/reference/BuildReferenceSearchProjection.tsx` | Direct channel subscription + truthful state rendering |
| Modify | `apps/live-control-ui/src/buildSurface/reference/BuildReferenceSearchProjection.test.tsx` | Same-handle reactive update / EMPTY / failure state witnesses |
| Modify | `apps/live-control-ui/src/buildSurface/reference/BuildReferenceCapability.tsx` | Current-snapshot View/Insert/chip/resolver authorization + committed editor gate |
| Modify | `apps/live-control-ui/src/buildSurface/reference/BuildReferenceCapability.test.tsx` | Retained callback, current-channel, unmount/replacement, no-republication tests |
| Modify | `apps/live-control-ui/src/buildSurface/BuildSurfacePage.test.tsx` | Assembled Build/ToolHost integration regression |

No production path beyond this table is leased.

**Bounded test-only discovery:** up to **2 additional existing** `apps/live-control-ui/src/**/*.test.ts` or `*.test.tsx` files may be added only if the `dmb_build_reference_context_v2` binding change causes a directly related compile/runtime regression in an existing Build/Surface Interaction compatibility witness. Record path + reason in the handback before editing. No additional production path is permitted without rebrief.

No package/lockfile change expected.

---

# §5 Explicitly out of scope / collision boundary

Do not modify:

```text
apps/live-control-ui/src/surfaceInformation/**
apps/live-control-ui/src/graphLens/useWorldGraphLensProjection.ts
apps/live-control-ui/src/graphLens/worldGraphLensSurfaceInformation.ts
apps/live-control-ui/src/chrome/**
apps/live-control-ui/src/surfaceInteraction/**
apps/live-control-ui/src/api/**
apps/live-control-ui/src/ingestSurface/**
apps/live-control-ui/src/planSurface/graphReviewWorkbench/**
apps/live-control-ui/src/playSurface/**
apps/live-control-ui/src/agentInteraction/**
apps/live_control_server/**
src/application_state/**
DungeonMind repository
package.json / package-lock.json / pyproject.toml / uv.lock
Docs/Roadmaps/ROADMAP-con-ready.md
```

PR #674 remains parked and read-only. This Build lease does not overlap its known Agent/Play production paths; do not opportunistically rebase or dispose #674 here.

Do not:

- create an Ingest catalog endpoint;
- migrate `manifestPath` selection;
- create a global Surface Information registry;
- add a second app-scoped World Graph provider;
- remove legacy GraphReference contracts;
- redesign Build lens/campaign tenancy;
- add new Build product capability or UX beyond truthful information-state rendering required by this migration.

---

# §6 Required adversarial and product witnesses

A. **Shared exact request / zero duplicate read.** App desired request key equals Build request key. Build uses the exact shared Surface Information channel and issues zero Build `postWorldGraphProjection` calls.

B. **Shared replacement transient.** App desired request already equals Build request B while the visible shared channel still belongs to A/null. Build waits; it does not issue a secondary POST. When matching channel B appears, Build consumes it.

C. **Secondary exact READY.** Build request differs from app request. Exactly one Build-owned POST occurs; Build channel descriptor says provider `build_world_graph_projection`, authority `dungeonmind`, exact request scope; verified response commits READY at exact revision.

D. **Secondary EMPTY.** Verified zero-node response commits EMPTY with exact revision. Build search renders successful zero results, not unavailable/error.

E. **Secondary UNAVAILABLE.** Request failure commits UNAVAILABLE and renders unavailable; no stale previous items remain actionable.

F. **Secondary INTEGRITY_ERROR.** Wrong world/campaign/scope/head/pinned revision or missing exact revision maps to INTEGRITY_ERROR through the shared mapping; zero actionable items.

G. **Replacement / late response.** Secondary request A is in flight, request B replaces it, B commits. Late A completion cannot alter B channel/snapshot and cannot re-authorize A callbacks.

H. **No graph-information Surface Interaction republish.** With one stable structural Build request and channel handle, commit LOADING → READY (and another accepted observation generation if useful). Search UI updates, while Surface Interaction publication count/identity does not change because of graph information alone.

I. **Binding separation.** `dmb_build_reference_context_v2` contains no graph projection state/error/items/revision/generation. The separate information binding contains only channel handle/null, never snapshot/value.

J. **Connected projection continuity.** One mounted `BuildReferenceSearchProjection` observes multiple generations from the same channel via `useSyncExternalStore` without remounting/re-registering the structural projection.

K. **Retained View uses current information.** Retain a View callback from observation A, transition same or replacement request to B, invoke retained callback. It must resolve only from current admissible information or no-op; it cannot open A's vanished node/scope.

L. **Retained Insert uses current information + committed editor gate.** Retain Insert, then make graph non-READY, lock/replace/unmount the editor owner, or change document campaign admission. Invocation no-ops. READY + current committed editor + admitted current node inserts exactly once.

M. **Owner unmount closes capability.** A retained Insert callback after `BuildReferenceCapability`/document owner unmount cannot insert into the removed editor, even if the old channel snapshot was READY.

N. **Pinned exact revision preserved.** A pinned Build request remains a distinct secondary exact channel when it differs from shared head; exact pinned revision mismatch is INTEGRITY_ERROR with no head fallback.

O. **Build assembled regression.** Existing `/build` document load, Find existing object, View, Insert, graph chip open, campaign selection, Save, and Build→Ingest handoff tests remain green. This PR does not change Build product behavior beyond truthful observation rendering.

---

# §7 Evidence required to merge

From `apps/live-control-ui` unless otherwise noted:

```bash
npm test -- --run \
  src/surfaceInformation/channel.test.ts \
  src/surfaceInformation/boundaries.test.ts \
  src/graphLens/worldGraphLensSurfaceInformation.test.ts \
  src/graphLens/useWorldGraphLensProjection.test.tsx \
  src/buildSurface/reference/buildWorldGraphSurfaceInformation.test.ts \
  src/buildSurface/reference/useBuildWorldGraphProjection.test.tsx \
  src/buildSurface/reference/buildBuildSurfaceInteractionPublication.test.ts \
  src/buildSurface/reference/BuildReferenceSearchProjection.test.tsx \
  src/buildSurface/reference/BuildReferenceCapability.test.tsx \
  src/buildSurface/BuildSurfacePage.test.tsx

npm test -- --run \
  src/buildSurface/reference/BuildReferenceObjectProjection.test.tsx \
  src/agentInteraction/surfaceInteractionCompat.test.ts

npm run typecheck
npm run build
npm test
```

From repository root:

```bash
git diff --check
```

### Exact-head evidence rule

Because this PR changes production Build information ownership, the full focused floor above must be rerun on every final production head submitted for formal review. Do not reuse a previous head's green output after a production fix.

### Full-suite baseline rule

Run the full UI suite on the exact head. Any new failure in:

```text
surfaceInformation
graphLens
Build reference capability/search/object projection
BuildSurfacePage
Surface Interaction compatibility
Agent Interaction compatibility touched indirectly by Build publication
```

is a blocker.

Unrelated established baseline failures must be reproduced on base `010634f8…` and documented exactly.

### Search/demolition evidence

Record searches proving changing World Graph observation data no longer travels in Build Surface Interaction publication.

At minimum inspect occurrences of:

```text
BuildReferenceContextBinding
projectionState
projectionError
loadedRevisionId
loadedIsHead
items
BUILD_REFERENCE_CONTEXT_BINDING_ID
```

The old data-bearing binding path must be absent from Build production after migration.

Also record the number of production `postWorldGraphProjection` owners for Build and prove:

- app provider owns shared exact request;
- Build secondary provider owns only distinct exact requests;
- no third/mirrored request path was introduced.

---

# §8 Required review handback

Record:

1. exact head/base and nano-commit story;
2. SI-4 predecessor sync: PR #679 merge SHA, final implementation head, two review cycles;
3. final SI-5 decomposition recorded in roadmap (SI-5A current, SI-5B named successor);
4. Build request-ownership rule: shared exact vs secondary exact;
5. Build secondary channel descriptor/provider identity;
6. explicit statement that shared exact request performs zero secondary Build reads, including transient channel replacement;
7. final structural Build binding v2 shape and information-channel binding shape;
8. proof that graph snapshot/status/items/revision/generation are absent from Surface Interaction publication;
9. READY / EMPTY / UNAVAILABLE / INTEGRITY / STALE-consumer mapping;
10. retained View/Insert invocation-time authorization and committed editor cleanup behavior;
11. late-response / descriptor replacement evidence;
12. exact-head test/typecheck/build/full-suite evidence and any base-reproduced noise;
13. path reconcile, including bounded extra tests if used;
14. PR #674 unchanged/open;
15. what remains false: Ingest DB Surface Information adoption, Play/Combat-facing adoption, Agent consumption/#674 disposition, SI-6 clean-start witness, feature thaw.

---

# §9 Acceptance rubric

Merge-ready only when all are true:

- [ ] SI-4 is backward-synced DONE with exact PR #679 merge/review facts.
- [ ] Roadmap decomposes SI-5 and marks SI-5A current without pre-marking it complete.
- [ ] Build exact request resolution semantics are unchanged.
- [ ] Shared exact request consumes the existing app Surface Information channel with zero Build-owned POSTs.
- [ ] Shared desired-request/channel replacement cannot trigger a duplicate secondary POST.
- [ ] Distinct exact Build request owns one Build-specific Surface Information channel/read.
- [ ] Secondary observations use the existing World Graph observation mapper and exact DungeonMind revision semantics.
- [ ] Build Surface Interaction publication no longer carries graph state/error/items/revision/generation/projection bytes.
- [ ] Build search projection subscribes to the channel with `useSyncExternalStore` and updates in place.
- [ ] EMPTY is distinct from UNAVAILABLE/INTEGRITY and renders truthfully.
- [ ] Retained View re-reads current channel information.
- [ ] Insert requires current READY information plus current committed/live Build editor/document admission.
- [ ] Owner unmount/replacement closes retained mutation capability.
- [ ] Late/superseded secondary work cannot mutate or authorize against the current request.
- [ ] Existing Build product behavior remains green.
- [ ] No Surface Information core, AppChrome, backend, Ingest, Play, Combat, or Agent production path was modified.
- [ ] PR #674 remains parked/read-only.
- [ ] Feature freeze remains explicit through SI-6.

Named successor: **SI-5B — Ingest application-state Surface Information adoption**. That slice should expose/query canonical DB-backed `ExtractionRun` catalog information and remove legacy manifest-path identity from `/ingest`; it must not be pulled into this Build migration.

---

# Stop conditions

Stop and rebrief if implementation requires any of the following:

- changing `SurfaceInformationChannel` or `SurfaceInformationState` production contract;
- modifying `WorldGraphLensProjectionProvider` or its observation mapper to make Build work;
- changing AppChrome / ToolHost / generic Surface Interaction production contracts;
- creating a global Surface Information registry;
- adding a backend endpoint or changing the World Graph server request/response contract;
- adding a second read for an exact request already owned by the app provider;
- mirroring/copying shared channel observations into a Build-owned channel;
- carrying snapshots/values/items/revisions/generations back through Surface Interaction bindings;
- requiring Ingest/Play/Combat/Agent production edits;
- requiring a package/lockfile change;
- changing PR #674 collision paths;
- discovering that truthful Build STALE relationship semantics require widening the generic GraphReference contract. In that case, fail closed for STALE in SI-5A and rebrief the generic-contract work separately.