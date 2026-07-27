---
pr_body_template: |
  ## Outcome

  Recap View and Ingest's "Open Recap View" read the selected canonical recap through the World Graph recap route; every prose chip opens the shared durable graph-object card path; and the selected durable object can continue into Build as a pointer-only, read-only World Graph context without granting Build graph-write or statblock-write authority.

  ## Scope and verification

  - Base: `00fa026d98294e575ad663a473731d426dcf05b3`
  - Head: `{{HEAD_SHA}}`
  - Recap World Graph route: `POST /api/live/world-graph/recap-projection`
  - Build World Graph route: existing `POST /api/live/world-graph/projection` with campaign scope, exact incoming node ID, and optional revision pin
  - Preview-union policy: retained only for extraction diagnostics and Graph Review's legacy live lane; never a Recap or Build runtime authority or fallback
  - Build policy: exact graph-object read/open only; no graph search, node authoring, binding, extraction, statblock generation, or Agent Interaction pinning is added
  - Changed paths: `{{ACTUAL_PATHS}}`
  - Verification: `{{COMMANDS_AND_RESULTS}}`
  - Baseline-identical failures: informational; report them accurately, but no separate operator waiver or PR-body refresh is required
  - Deferred successors: Graph Review post-confirm authority transition; exact-run candidate-review projection; preview-union infrastructure retirement; cache/invalidation/telemetry; Ingest workflow simplification; extraction/identity hardening
---

# HANDOFF — PR380B World Graph Recap + Build object-consumption migration

**Created:** 2026-07-27, America/Denver.
**Status:** ACTIVE — dispatch exactly one product authority migration.
**Canonical handoff path:** `Docs/Plans/HANDOFF-pr380b-world-graph-recap-ui-migration.md`
**Repository:** `Drakosfire/DungeonMindBuddy`
**Implementation base:** `00fa026d98294e575ad663a473731d426dcf05b3` — current main after the Build-first Markdown Canvas and SBW dogfood/doc-sync merges.
**Suggested branch:** `agent/pr380b-world-graph-recap-build-consumption`
**Predecessor:** PR380A / GitHub PR #412, `POST /api/live/world-graph/recap-projection`.
**Product anchors:** Backlog `[READY] Recap View / ingest must project world graph (not session preview union)` and GitHub issue #410, the cross-surface World Graph + statblock demo spine.
**Operating rule:** reconstruct from current main; do not resurrect or cherry-pick the old PR #380 integration branch wholesale.

> **Dispatch gate:** Dispatch is prohibited until capability decomposition is complete, one independently useful mission remains, the merge-ready invariant and required evidence survive critique, every expected path is known, required contract matrices are resolved, and every acceptance claim has an owning proof.
>
> This checked-in handoff is the complete authority. The worker must not compress, omit, replace, or rewrite it before implementation. The PR description must use the frontmatter skeleton and remain a truthful merge contract; it cannot substitute for the handoff.

## §0 Capability decomposition decision

PR380B is a cross-surface read-authority migration, not a general Graph Preview cleanup, not a Build authoring expansion, and not a publication-lifecycle rewrite.


| Candidate outcome | Independently useful? | Public/durable contract changed? | User or operator surface changed? | Failure model changed? | Independently testable or revertible? | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| Recap View consumes POST /api/live/world-graph/recap-projection for the selected campaign/session | Yes | Frontend consumes existing public contract; no backend contract change | Yes | Yes | Yes | Include |
| Ingest’s “Open Recap View” opens the same World Graph-backed recap and is no longer gated by preview-union readiness | No alone; required to make all normal recap entry paths truthful | No new durable contract | Yes | Yes | Yes | Include under the same invariant |
| Recap prose chips open a surface-neutral shared GraphObjectCard renderer by exact durable node ID | No alone; required to prevent a second recap-only object navigation model | Shared UI interaction seam only | Yes | Yes | Yes | Include under the same invariant |
| Relationship traversal from the opened card continues through the existing shared exact-node resolver | No alone; required to keep chip and card navigation coherent | No new durable contract | Yes | Yes | Yes | Include under the same invariant |
| Hoist graph-native card rendering plus the exact-target relationship event/lookup contract out of PlanReferenceObjectCard into surface-neutral graph-object modules | No alone; required for Recap and Build to consume one interaction contract without importing Plan | Shared UI interaction seam only | Yes | Yes | Yes | Include under the same invariant |
| Recap card exposes a pointer-only Continue in Build action carrying campaign ID, durable node ID, and exact recap revision ID | No alone; required to prove cross-surface identity continuity | URL/read contract only | Yes | Yes | Yes | Include under the same invariant |
| Build renders an incoming durable graph object in a Build-owned adjacent context lane by loading an exact campaign-scoped World Graph projection | Yes | Frontend consumes existing generic projection contract; no backend change | Yes | Yes | Yes | Include under the same invariant |
| Build admits the incoming campaign against the loaded workspace document’s explicit campaign-or-world scope and fails closed on mismatch | No alone; required to prevent cross-campaign/world identity bleed | No new durable contract | Yes | Yes | Yes | Include under the same invariant |
| Latest recap artifact determines the default recap session when no session is requested | Existing selection behavior, still useful | No | Yes | Minor | Yes | Retain, but only as document/session selection — never graph authority |
| Remove preview-union/latest-ingest selection, manifest fields, and preview fallback from Recap runtime | No alone; demolition required by the migration | No | Yes | Yes | Yes | Include under the same invariant |
| Clarify Ingest copy so preview extraction is an unpublished candidate-review artifact, not Recap’s graph | No alone; required to make authority visible | No | Yes | No | Yes | Include under the same invariant |
| Delete the standalone GraphPreviewModule, graph-preview server routes, preview-union store builder, or run registry | Yes | Yes | Yes/operational | Yes | Yes | Successor: retire-preview-union-review-materialization |
| Replace Graph Review’s live lane with a direct exact-ExtractionRun candidate-review projection | Yes | Yes | Yes | Yes | Yes | Successor: exact-run-candidate-review-projection |
| Graph Review post-confirm flips from candidate authority to new durable World Graph revision | Yes | Yes | Yes | Yes | Yes | Successor PR380C |
| Projection cache, request coalescing, revision invalidation, telemetry | Yes | Yes | Indirectly | Yes | Yes | Successor PR380D |
| Ingest wizard primary-path redesign or removal of extraction controls | Yes | No backend graph contract; major product workflow change | Yes | Yes | Yes | Successor PR380E |
| Extraction, identity, alias, or promotion hardening | Yes | Yes | Indirectly | Yes | Yes | Successor PR380F |
| Durable Union store/contribution direction migration | Yes | Yes | No direct Recap UI requirement | Yes | Yes | Explicitly deferred |
| Auto-publish an extraction so Recap immediately includes it | Yes | Yes — changes publication authority | Yes | Yes | Yes | Reject from this slice |
| Overlay unpublished candidate nodes onto the World Graph recap response | Yes | Yes — invents a hybrid authority contract | Yes | Yes | Yes | Reject from this slice |
| Add Build graph search/browser or automatic reference insertion into Markdown | Yes | Yes — new surface capability and document-write semantics | Yes | Yes | Yes | Reject; later surface capability slice |
| Add Build node authoring, graph binding, statblock generation/acceptance, or governed publication actions | Yes | Yes — write authority expansion | Yes | Yes | Yes | Reject; owning Build/SBW/Graph Review successors |
Persist or pin graph context in Agent Interaction across routes


Yes


Yes — thread/context ledger contract


Yes


Yes


Yes


Reject; hoisted-agent successor


Selected capability: a GM can open a selected recap from Plan or Ingest and read it against the campaign’s durable World Graph, open prose chips and connected objects through one shared exact-ID graph-object card contract, and carry that exact durable object into Build as read-only context over an exact World Graph snapshot.


Why the included rows share one invariant: each changed UI/API seam establishes the same authority claim: Recap, Ingest entry, and Build object context resolve durable identities from World Graph projections and one shared exact-ID card contract, while ingest-run and preview-union state may describe unpublished extraction work but can never supply, supplement, gate, or replace those graph reads.


Named successors:


PR380C — Graph Review post-confirm authority transition.


exact-run-candidate-review-projection — replace Graph Review’s preview-union projection with a direct exact-ExtractionRun review lens.


retire-preview-union-review-materialization — remove preview-union lifecycle requirements, dormant Graph Preview UI, and legacy endpoints after all consumers move.


PR380D — cache, request coalescing, revision invalidation, and telemetry.


PR380E — Ingest primary-path simplification.


PR380F — extraction and identity hardening.


Durable Union store/contribution direction migration — still deferred.


## §1 Mission

Recap View and Ingest’s “Open Recap View” read the selected canonical recap through the World Graph recap route; every prose chip opens the shared durable graph-object card path; and the selected durable object can continue into Build as a pointer-only, read-only World Graph context without granting Build graph-write or statblock-write authority.


### Invariant

> 

Every graph object presented or opened by Recap or Build is addressed by exact durable node ID and derived from an explicit World Graph projection snapshot. Recap uses the exact WorldGraphRecapProjection for the selected campaign/session; Build resolves an incoming pointer against an exact campaign-scoped generic World Graph projection, optionally pinned to the recap revision. Latest-ingest manifests, preview-union stores, fixtures, candidate extraction state, Build document prose, and statblock drafts never select, supplement, or substitute for graph identity.


### Mission falsification test

```text

This is not one slice if implementation must also:
- publish or confirm an extraction into the World Graph;
- change Graph Review prepare/confirm semantics;
- replace Graph Review’s live preview-union lane;
- delete preview-union server/storage infrastructure;
- redesign the Ingest workflow or remove extraction controls;
- add cache, coalescing, invalidation, polling, or telemetry;
- change the World Graph recap response schema;
- widen recap scope from campaign to world;
- infer aliases, nodes, relationships, or evidence from prose;
- change extraction, identity resolution, promotion, or durable storage;
- migrate Union store direction values;
- add Build graph search, Markdown reference insertion, node authoring, or graph writes;
- add ThreatDraft/statblock generation, validation, acceptance, or binding actions to Build;
- persist/pin graph context in Agent Interaction or create a cross-route thread ledger;
- put World Graph loading or graph-object presentation inside generic `MarkdownCanvas` modules.

```

## §2 Context, authority, and boundaries

### Parent authority

Parent authority

Read in this order before editing:


Docs/Design/DECISION-graph-lens-projection-boundary.md


Docs/Plans/HANDOFF-pr412-world-graph-recap-projection-contract.md


Docs/Design/ARCHITECTURE-campaign-supergraph.md


Docs/Plans/PR-TRACKER-campaign-supergraph.md


Backlog [READY] Recap View / ingest must project world graph (not session preview union)


GitHub issue #410 — Cross-surface World Graph + hoisted agent continuity demo


Docs/Roadmaps/ROADMAP-cross-surface-statblock-demo.md


Docs/Design/DESIGN-shared-markdown-canvas-surface-composition.md


This checked-in handoff


Current implementation and owning-boundary tests on base 00fa026d98294e575ad663a473731d426dcf05b3


Archived PR #414 / #416 / #423 / #427 graph-lens handoffs for predecessor semantics only


### Repository rules

Repository rules

AGENTS.md


.cursor/rules/external-agent-pr-loop.mdc


.cursor/skills/external-agent-pr-loop/SKILL.md


.cursor/skills/external-agent-pr-loop/templates/HANDOFF.template.md


existing frontend TypeScript, Vitest, and projection-boundary conventions


### Authority precedence

Authority precedence

1. Accepted graph-lens decision and campaign-supergraph architecture
2. PR380A / PR #412 World Graph recap route contract
3. Active tracker and Backlog product invariant
4. This checked-in handoff
5. Current main implementation and tests
6. Archived predecessor handoffs
7. Attached/local Project Sources
8. Chat summaries

The old PR #380 branch is source material only. Do not copy behavior from it when it conflicts with current contracts or this handoff.


### Preconditions already true on main

Preconditions already true on main

PR380A / PR #412 ships POST /api/live/world-graph/recap-projection.


PR #414 ships the CommonMark-safe neutral mention linker.


PR #416 derives recap node views from generic World Graph views and closes World Graph relationship direction.


PR #423 migrates Union recap mentions onto the same CommonMark-safe linker.


PR #427 closes the shared snake_case Union-compatible direction vocabulary.


GraphProjectionReader already supports an external exact-node onInspectNode callback.


ProjectionContext already supports openPlanReferenceResolution for Plan.


PlanReferenceObjectCard already renders shared GraphObjectCard, but its graph-native renderer wiring and World Graph adapter are still Plan-owned and must be hoisted before Recap and Build consume them.


Build already mounts a hardened MarkdownCanvasSessionProvider, BuildIngestToolbar, and BuildSurfaceShell; graph context must remain a Build-owned adjacent read tool and must not enter the generic Markdown canvas.


Build publishes exact workspace-document campaign/document/revision context to Agent Interaction, but persistent pinned graph context remains a later capability.


The SBW dogfood path has matured candidate/statblock mechanics workflows, but Build must not silently acquire those write capabilities in this slice.


planSurface/reference/worldGraphProjectionAdapter.ts already maps generic camelCase World Graph node views to the shared snake_case card/reader model, but it is Plan-named ownership. Hoist that pure adapter to worldGraph/ and leave the Plan path as a compatibility re-export rather than copying the mapping into Recap or Build.


### Exact predecessor contract consumed

Exact predecessor contract consumed

**Route**


POST /api/live/world-graph/recap-projection


**Request — existing WorldGraphProjectionRequest constrained by PR380A**


schema: dmb_world_graph_projection_request_v1

worldId: string

campaignId: string

focus:

kind: session

sessionId: string

campaignId: string | null

admissibility: gm

revisionPin: null in this slice

queryText: null/absent

scopeMode: campaign


**Response — existing WorldGraphRecapProjection**


schema: dmb_world_graph_recap_projection_v1

campaignId: string

sessionId: string

graphId: string                    // equals snapshot.revisionId

snapshot: WorldGraphProjectionSnapshot

markdown: string                   // canonical normalized recap with dmb-node links

focus: WorldGraphRecapFocusOverlay

nodeViews: Record<nodeId, WorldGraphProjectionNodeView>

mentions: WorldGraphRecapMention[]

sourceSpans: WorldGraphRecapSourceSpan[]  // v1 currently empty

diagnostics: WorldGraphProjectionDiagnostic[]

trustBoundary: WorldGraphProjectionTrustBoundary


### Exact input consumed by the UI

Exact input consumed by the UI

1. Selected Recap campaign ID and recap/session ID.
2. One neutral shared campaign → world mapping consumed by Plan, Recap, and Build adapters.
3. One `WorldGraphRecapProjection` response for Recap.
4. One pointer-only Build handoff: campaign ID, exact durable node ID, and exact Recap revision ID.
5. One generic `WorldGraphProjection` response for Build, campaign-scoped and revision-pinned when the handoff came from Recap.
6. The admitted Build `WorkspaceDocumentRecord` when a document is selected, used only to verify that its explicit campaign-or-world scope admits the incoming campaign and to preserve document authority.
7. One shared surface-neutral World Graph node adapter, graph-object card renderer, and exact-target lookup helper.
8. Recap artifact records only for document/session discovery and labels — never graph selection.

### Critical authority distinction

Critical authority distinction

getRecapArtifacts() may remain in Recap View to enumerate which recap documents exist and to preserve the current default-to-latest-recap behavior.


It must not contribute any of these fields to the graph request or card resolution:


run_manifest_uri;


graph_run_refs;


default_graph_run_uri;


source_sha256 as an ingest-run selector;


preview-union path;


latest graph-ingest status;


candidate graph path.


Selecting the latest recap document is allowed. Selecting the latest extraction graph as recap authority is prohibited.


### Build Surface integration boundary

Build Surface integration boundary

Build is included because it is now a real first-class surface with a hardened document authority seam, and the cross-surface demo requires the same durable object to survive the transition from recap memory into active creation. The inclusion is intentionally narrow.


### Incoming pointer contract

Incoming pointer contract

/build?campaign=<campaign_id>&graphNodeId=<durable_node_id>&graphRevision=<revision_id>


campaign and graphNodeId are required for an incoming graph-object handoff.


graphRevision is required when the handoff originates from Recap and must equal the Recap response snapshot.revisionId; Build pins its initial generic World Graph read to that revision.


The URL carries pointers only. It must not carry node JSON, evidence bodies, statblock definitions, preview-store paths, run IDs, or copied summaries.


A loaded Build workspace document remains the authority for document identity. Per the active Workspace Document Identity contract, its campaign_id may represent either a narrative campaign scope or the containing world scope. Admit graph context only when that value equals the incoming campaign ID or the resolved World Graph worldId; otherwise display a bounded mismatch state and refuse to resolve the object.


With no selected document, Build may show the read-only object context beside the new-source form and prefill the campaign field from the admitted incoming campaign. It must not auto-create a source.


With no incoming graphNodeId, Build behavior is unchanged.


Build document-scope admission


The Workspace Document Identity v1 contract explicitly allows WorkspaceDocumentRecord.campaign_id to hold either a campaign scope or a world scope. Do not reinterpret that field through naming heuristics. Resolve the incoming campaign through the shared campaign→world map, then apply this closed matrix:


Document campaign_id


Incoming campaign C


Resolved world W


Verdict


Projection request campaign


C


C


W


Admit campaign-scoped document


C


W


C


W


Admit world-scoped document


C


another campaign


C


W


Reject with bounded scope mismatch


No request


another world


C


W


Reject with bounded scope mismatch


No request


blank/unknown


C


W


Reject; do not guess scope


No request


A world-scoped Build document does not widen the graph read to scopeMode=world; it only admits the document as a valid authoring surface for campaign C. The graph projection remains campaign-scoped to the incoming campaign.


### Build projection recipe

Build projection recipe

```text
POST /api/live/world-graph/projection
  schema: dmb_world_graph_projection_request_v1
  worldId: resolved by the shared campaign→world mapping
  campaignId: incoming campaign (never replace it with a world-scoped document value)
  focus: { kind: none, sessionId: null }
  admissibility: gm
  scopeMode: campaign
  revisionPin: incoming graphRevision when present
  queryText: absent/null
```

Build then performs one exact lookup: projection.nodes.find(node.nodeId === graphNodeId). It must not search by label, alias, document text, ThreatDraft name, statblock name, or extraction candidate identity.


### Presentation boundary

Presentation boundary

Build owns the adjacent context lane and surface copy.


Surface-neutral graph-object modules own card rendering, evidence/relationship presentation, and the exact-target relationship event/lookup contract. Recap and Build use the same pure exact-map helper; Plan keeps its existing resolver callback and fallback semantics.


MarkdownCanvasSession and MarkdownCanvas remain document-only and import no World Graph, Build graph-context, Graph Review, ThreatDraft, or statblock types.


Build’s context card is read-only in this slice. No “author node,” “bind mechanics,” “generate statblock,” “accept mechanics,” “publish,” or document mutation action is admitted.


### Graph Preview policy after this slice

Graph Preview policy after this slice

The repository currently uses “Graph Preview” for several different concepts. PR380B must make their boundaries explicit:


Concept


Authority after PR380B


Product visibility


Candidate extraction/run diagnostics in Ingest


Unpublished exact-run state


May remain visible as diagnostics and a route to Graph Review


Preview-union projection used by Graph Review’s legacy live lane


Unpublished, internal compatibility infrastructure


Remains operational; not a Recap source


Standalone GraphPreviewModule and legacy graph-preview API family


Dormant/legacy product infrastructure


Do not extend; removal is a named successor


Recap View


Durable World Graph recap projection only


Normal GM-facing read path


Ingest “Open Recap View”


Opens durable Recap View


Must not require preview-union readiness


Build incoming graph-object context


Exact campaign-scoped generic World Graph projection, optionally revision-pinned


Read-only adjacent context; never preview union, extraction candidate, or document prose identity


PR380B does not need to delete dormant Graph Preview code merely to prove product retirement. It must ensure no active normal Recap or Build graph-object path navigates to, falls back to, or describes preview-union/candidate state as the graph the GM is reading.


### What remains false after this slice

What remains false after this slice

An extraction is not published automatically.


Newly extracted candidate nodes do not appear in Recap View until Graph Review confirmation creates a durable World Graph revision.


Graph Review still consumes preview-union projection for its live lane.


Legacy graph-ingest manifests may still require preview_union_store_ready for promotion.


The standalone Graph Preview component and backend routes may still exist as dormant/legacy infrastructure.


No post-confirm automatic authority flip or recap reload is delivered.


No revision cache, coalescing, invalidation event, polling, or telemetry is delivered.


No exact revision pin is exposed in the Recap UI.


Plan keeps its current resolver semantics; Recap and Build traverse only the exact node maps loaded for their current response/pinned projection. App-level warm-cache and invalidation continuity remain PR380D.


No source-span highlighting is created when the v1 recap route returns sourceSpans=[].


No Ingest wizard simplification is delivered.


No extraction/identity improvement is delivered.


Build gains no graph search/browser, Markdown insertion, node authoring, extraction review, graph write, or statblock action.


No persistent Agent Interaction pinned-context ledger or cross-route thread handoff is delivered.


No generic Markdown canvas module learns about World Graph objects; the Build integration remains a surface-owned adjacent tool.


### Base movement rule

Base movement rule

Before implementation:


run git rev-parse HEAD;


compare current main with 00fa026d98294e575ad663a473731d426dcf05b3;


specifically inspect movement in:


apps/live-control-ui/src/api/types.ts;


apps/live-control-ui/src/api/liveApi.ts;


apps/live-control-ui/src/planSurface/graphPreview/RecapGraphModule.tsx;


apps/live-control-ui/src/planSurface/graphProjectionReader/GraphProjectionReader.tsx;


apps/live-control-ui/src/planSurface/reference/*;


apps/live-control-ui/src/modules/IngestionModule.tsx;


apps/live-control-ui/src/buildSurface/BuildSurfacePage.tsx;


apps/live-control-ui/src/buildSurface/BuildSurfaceShell.tsx;


apps/live-control-ui/src/buildSurface/buildMarkdownCanvasAdapter.tsx;


apps/live-control-ui/src/markdownCanvas/**;


apps/live-control-ui/src/graphObjectCard/**;


Docs/Design/DESIGN-shared-markdown-canvas-surface-composition.md;


related tests;


verify the route and frontend generic World Graph types have not materially changed.


If the World Graph recap contract, node-view shape, shared card seam, or projection context changed materially, stop and report the re-anchor consequence before editing.


## §3 Observable-path inventory

| Observable path | Current behavior on base | Required behavior after this slice | Same invariant? | Owning boundary |
| --- | --- | --- | --- | --- |
| Plan → Recap with explicit campaign and session URL | Loads getUnionSupergraphProjection(...useLatestGraphIngest=true) | POST the World Graph recap request for exactly that campaign/session | Yes | Recap module + API client |
| Plan → Recap without explicit session | Chooses latest recap artifact, then latest preview union | May keep choosing the latest recap artifact as the document focus, but graph authority is the World Graph recap route | Yes | Recap module |
| Campaign/session numbers collide across campaigns | Artifact selection is campaign-aware, union query receives manifest/source fields | Request exact selected campaign/session using existing campaign→world mapping; no manifest or source selector | Yes | context helper + Recap module |
| Selected session has canonical recap and durable World Graph but no preview-union store | Recap fails and says projection is not ready | Recap succeeds from World Graph recap route | Yes | Recap module |
| Selected session has canonical recap; latest graph extraction is blocked | Ingest says chips may be unavailable; Recap depended on preview | Ingest reports candidate extraction blocked, but Recap remains available and shows current published World Graph | Yes | Ingest copy + CTA + Recap module |
| Selected session has preview union but no newly confirmed World Graph contribution | Recap shows candidate nodes as if runtime graph | Recap shows only durable World Graph nodes; unconfirmed candidates remain in Ingest/Graph Review | Yes | Recap module |
| World Graph response contains a prior-session/cross-session node | Preview union often omitted it | Recap node map and chip/card can show it with prior-context posture | Yes | response adapter + component |
| Prose contains a dmb-node: link emitted by the route | Opens recap-local GraphNodeExplorer | Open the surface-neutral GraphObjectProjectionCard using the exact response node ID and node view | Yes | Recap projection component + neutral card renderer |
| User opens a connected object from the shared card | Recap-local explorer traverses local preview nodes | Neutral renderer emits the exact durable target ID; the shared exact-map helper resolves it from the loaded projection; no label-first rebind | Yes | graph-object renderer + exact-target helper |
| User chooses Continue in Build from a Recap object | No durable cross-surface object handoff | Navigate with pointer-only campaign/node/revision URL fields from the exact recap response | Yes | Recap surface action + Build route parser |
| Build opens with incoming campaign/node/revision and no document selected | Build only shows the new-source form | Show the same durable object in a read-only adjacent context lane and prefill, but do not submit, the source campaign | Yes | Build page + context component |
| Build opens with an admitted workspace document scoped to the incoming campaign or its resolved world | Build has document/canvas only | Load the exact revision-pinned campaign projection and render the exact node through the shared card renderer beside the canvas | Yes | Build shell + generic World Graph client |
| Build document scope is neither the incoming campaign nor its resolved world | No graph-context contract | Fail closed with a bounded scope-mismatch message; no alternate campaign, label lookup, or document mutation | Yes | Build context component |
| Build projection does not contain the incoming exact node ID | No graph-context contract | Show unresolved exact-node state; no alias, label, preview, extraction, or statblock fallback | Yes | Build context component |
| Build relationship traversal | No Build graph object card | Use the shared exact-map helper to traverse only exact target IDs present in the same pinned projection; missing target remains unresolved | Yes | neutral renderer + exact-target helper |
| Build opens without graphNodeId | Existing Build canvas/new-source behavior | Preserve existing behavior byte-for-byte except harmless refactor wiring | Yes — negative boundary proof | Build regressions |
| Mention targets a node missing from nodeViews | Runtime chip may be inert or undefined | Do not invent or label-resolve; render unresolved/inert behavior with a bounded diagnostic or fail component test explicitly | Yes | Recap projection component |
| Route loading | “Loading union supergraph projection…” | “Loading published World Graph recap…” or equivalent truthful copy | Yes | Recap module |
| Route returns 404 recap_markdown_unavailable | Union-specific “no lineage-matched preview union” error | Explain that the canonical normalized recap is unavailable for the selected session; no fallback | Yes | Recap module |
| Route reports missing/uninitialized World Graph | Union path attempted preview selection | Explain that published graph memory is unavailable; no preview fallback | Yes | Recap module |
| Route returns 422 invalid request/context | Union path treated 400/404 as expected misses | Show stable request/context error; no session/world guessing | Yes | API client + Recap module |
| Route returns unexpected error | Union-specific error | Show error and Retry; retry sends the same World Graph request | Yes | Recap module |
| Head advances between retries with no pin | Latest union selection could change by run | Retry may read current World Graph head, as allowed by predecessor contract; source copy displays returned revision identity | Yes | route contract + component |
| Campaign has no known world mapping | Existing plan resolver returns unavailable | Recap fails closed before request or with a stable unavailable state; do not add a duplicate hardcoded world map | Yes | shared context helper |
| Session list API fails but requested/default session is known | Recap falls back to hardcoded dogfood options/default | Still request the known selected session through World Graph; artifact list failure must not trigger a graph fallback | Yes | Recap module |
| Ingest has normalized recap but no session-memory materialization | CTA may remain gated by materialization/preview | “Open Recap View” is available once the canonical normalized recap exists; retrieval/materialization readiness is not recap-read authority | Yes | Ingest module |
| Ingest has normalized recap and preview-union store | CTA opens preview-backed recap | CTA opens World Graph-backed Recap; preview status remains a separate diagnostic | Yes | Ingest module |
| Ingest has candidate extraction ready for review | “Open Recap View” language can imply candidate graph is visible there | Direct user to Graph Review for unpublished candidates; Recap View is described as published memory | Yes | Ingest module |
| Graph Review selects a live run | Uses preview-union projection | Must remain unchanged and operational in this slice | Yes — negative boundary proof | Graph Review regression |
| Standalone dormant Graph Preview route/component | Legacy code exists | No new normal navigation or fallback to it; deletion deferred | Yes — negative boundary proof | surface config + diff review |
| Same campaign/session replay | Latest-run selection may select a different run | Same World Graph revision/source bytes yield equivalent component state; no writes | Yes | route + component |
| Source spans are empty | Preview UI copy promised evidence highlights | Recap does not claim source highlighting; cards may show graph evidence metadata only | Yes | Recap projection component |

A required row is merge-blocking. Low durable graph coverage is an honest result, not authorization to overlay candidate nodes or infer aliases.

## §4 Files in scope — allowlist

Every changed path must appear below or be admitted by the bounded discovery exception.

| Action | Path | Purpose: how this establishes or proves §1 |
| --- | --- | --- |
| Create | Docs/Plans/HANDOFF-pr380b-world-graph-recap-ui-migration.md | Canonical dispatch authority |
| Modify | apps/live-control-ui/src/api/types.ts | Add the exact existing WorldGraphRecapProjection frontend contract using current World Graph nested types; no backend/schema change |
| Modify | apps/live-control-ui/src/api/liveApi.ts | Add the typed Recap POST client; reuse the existing generic World Graph POST client for Build; retain Union clients for Graph Review |
| Modify | apps/live-control-ui/src/api/liveApi.test.ts | Prove exact Recap route/body/error parsing and generic Build projection request usage |
| Create | apps/live-control-ui/src/worldGraph/worldGraphSurfaceContext.ts | Hoist the single campaign→world mapping, neutral request builders, and exact campaign-or-world document-scope admission helper so Plan, Recap, and Build do not import one another |
| Create | apps/live-control-ui/src/worldGraph/worldGraphSurfaceContext.test.ts | Prove campaign/session Recap recipe, campaign/no-focus Build recipe, revision pin, campaign-scoped document admission, world-scoped document admission, mismatched scope rejection, unknown campaign, and no invented query fields |
| Modify | apps/live-control-ui/src/planSurface/reference/planGraphContextRequest.ts | Become a thin Plan adapter/re-export over the neutral mapping; preserve existing Plan behavior |
| Modify | apps/live-control-ui/src/planSurface/reference/planGraphContextRequest.test.ts | Preserve Plan request regressions after the mapping hoist |
| Create | apps/live-control-ui/src/graphObjectCard/GraphObjectProjectionCard.tsx | Hoist exact-node card rendering and relationship-selection UI into a surface-neutral renderer with surface-supplied actions and callbacks |
| Create | apps/live-control-ui/src/graphObjectCard/GraphObjectProjectionCard.test.tsx | Prove exact-node rendering, exact target-ID relationship events, disabled/loading state, action injection, and absence of Plan/Build-specific semantics |
| Create | apps/live-control-ui/src/worldGraph/worldGraphNodeViewAdapter.ts | Hoist the existing pure camelCase World Graph → shared snake_case node-view adapter for Plan, Recap, and Build |
| Create | apps/live-control-ui/src/worldGraph/worldGraphNodeViewAdapter.test.ts | Prove complete field-preserving adaptation, closed directions, exact IDs, and no invented fields |
| Modify | apps/live-control-ui/src/planSurface/reference/worldGraphProjectionAdapter.ts | Become a compatibility re-export/thin alias over the neutral adapter; retain current Plan import behavior |
| Modify | apps/live-control-ui/src/planSurface/reference/worldGraphProjectionAdapter.test.ts | Preserve Plan adapter behavior after the ownership hoist |
| Modify | apps/live-control-ui/src/planSurface/reference/PlanReferenceObjectCard.tsx | Delegate graph-native card rendering to the neutral renderer while retaining Plan’s existing relationship resolver, projection-container behavior, corpus fallback, and actions |
| Modify | apps/live-control-ui/src/planSurface/reference/PlanReferenceObjectCard.test.tsx | Prove Plan behavior remains unchanged after delegation |
| Modify | apps/live-control-ui/src/planSurface/graphPreview/RecapGraphModule.tsx | Replace latest-ingest/Union selection and fallback with the World Graph recap request while retaining recap-document/session selection only |
| Create | apps/live-control-ui/src/planSurface/graphPreview/WorldGraphRecapProjection.tsx | Render published-memory copy, use the neutral adapter/card renderer/exact-target helper, and expose pointer-only Continue in Build |
| Delete | apps/live-control-ui/src/planSurface/graphPreview/UnionSupergraphRecapProjection.tsx | Remove the preview-authority renderer from normal Recap View; only delete after proving no remaining non-Recap consumers |
| Create | apps/live-control-ui/src/planSurface/graphPreview/worldGraphRecapFixture.ts | Real-shape Recap fixture with focus/prior-context nodes and exact snapshot revision |
| Modify | apps/live-control-ui/src/planSurface/graphPreview/RecapGraphModule.test.tsx | Own request selection, no fallback, exact card open, Continue in Build URL, and cross-session behavior |
| Modify | apps/live-control-ui/src/modules/IngestionModule.tsx | Decouple Open Recap View from preview readiness and distinguish unpublished candidate review from published memory |
| Modify | apps/live-control-ui/src/modules/IngestionModule.test.tsx | Prove exact CTA context and missing/blocked/ready preview matrix |
| Create | apps/live-control-ui/src/buildSurface/BuildGraphObjectContext.tsx | Parse/admit pointer-only graph context, load the exact generic projection, enforce scope/revision identity, adapt through the neutral node adapter, and render the neutral card renderer |
| Create | apps/live-control-ui/src/buildSurface/BuildGraphObjectContext.test.tsx | Prove no-document, campaign-scoped document, world-scoped document, mismatched-scope, missing-node, revision-pin, relationship, and no-fallback paths |
| Modify | apps/live-control-ui/src/buildSurface/BuildSurfacePage.tsx | Admit incoming graph context beside the new-source form and prefill campaign without auto-creating |
| Modify | apps/live-control-ui/src/buildSurface/BuildSurfaceShell.tsx | Compose the Build-owned adjacent context lane beside MarkdownCanvas; do not modify generic canvas ownership |
| Modify | apps/live-control-ui/src/buildSurface/BuildSurfacePage.test.tsx | Preserve create/load behavior and prove pointer admission with no selected document |
| Modify | apps/live-control-ui/src/buildSurface/BuildSurfaceShell.test.tsx | Preserve Build document/extraction/Agent context behavior while the read-only graph context lane is mounted |

First-commit characterization gate

First-commit characterization gate

The first commit on the implementation branch must change only:


apps/live-control-ui/src/planSurface/graphPreview/worldGraphRecapFixture.ts

apps/live-control-ui/src/planSurface/graphPreview/RecapGraphModule.test.tsx

apps/live-control-ui/src/modules/IngestionModule.test.tsx

apps/live-control-ui/src/api/liveApi.test.ts

apps/live-control-ui/src/worldGraph/worldGraphSurfaceContext.test.ts

apps/live-control-ui/src/worldGraph/worldGraphNodeViewAdapter.test.ts

apps/live-control-ui/src/planSurface/reference/planGraphContextRequest.test.ts

apps/live-control-ui/src/planSurface/reference/worldGraphProjectionAdapter.test.ts

apps/live-control-ui/src/graphObjectCard/GraphObjectProjectionCard.test.tsx

apps/live-control-ui/src/planSurface/reference/PlanReferenceObjectCard.test.tsx

apps/live-control-ui/src/buildSurface/BuildGraphObjectContext.test.tsx

apps/live-control-ui/src/buildSurface/BuildSurfacePage.test.tsx

apps/live-control-ui/src/buildSurface/BuildSurfaceShell.test.tsx


It may be red or fail TypeScript compilation because the new API/type/helper/components do not exist yet. Its purpose is to lock the required behavior before production edits.


The first commit must prove at least these current-main failures:


Recap still calls getUnionSupergraphProjection with useLatestGraphIngest: true.


Recap still passes run manifest and recap source lineage fields into the Union selector.


Recap still errors when recap memory exists but preview union is absent.


Recap chip opens the local GraphNodeExplorer, not the surface-neutral shared graph-object renderer.


Ingest still ties Recap availability/copy to preview-union or materialization state.


No typed frontend client exists for the World Graph recap route.


Graph-native card rendering and the World Graph node-view adapter remain Plan-owned; no neutral renderer/adapter exists for Recap and Build.


Recap exposes no pointer-only Continue in Build handoff.


Build has no exact World Graph object context lane and cannot preserve an incoming durable node/revision.


Build has no campaign-or-world scope admission, mismatch, or missing-node fail-closed behavior because it has no graph-object read contract.


Do not rewrite fixtures after production code merely to match implementation output. Any fixture change after the first commit requires a report naming the predecessor-contract misunderstanding.


### Bounded discovery exception

Bounded discovery exception

Directories:

apps/live-control-ui/src/planSurface/

apps/live-control-ui/src/buildSurface/

apps/live-control-ui/src/graphObjectCard/

apps/live-control-ui/src/worldGraph/

apps/live-control-ui/src/modules/

Maximum additional paths: 5

Allowed path kinds:

- one existing projection/container path if Recap or Build requires a real surface host already owned elsewhere;
- one existing surface config or registry path if current main exposes a normal Graph Preview entry that must be removed;
- one existing CSS file for the Build adjacent context lane or truthful Recap source copy;
- one existing URL-selection helper when query parsing cannot remain local without duplication;
- one colocated fixture/helper required by an owning-boundary test.
Decision rule for including a path:

include only when it directly proves durable Recap/Build read authority or the shared exact-node card contract.

Required report when a path is added:

name the path, current consumer, why an allowlisted path cannot own the guarantee, and why the addition does not begin Build authoring, agent pinning, statblock integration, or preview-infrastructure retirement.


No backend, generic Markdown canvas, Graph Review production, extraction, promotion, statblock, storage, cache, Agent Interaction persistence, or telemetry path is admitted by this exception.


## §5 Files and capabilities explicitly out of scope

| Path, ownership layer, or capability | Why this slice must not touch or claim it |
| --- | --- |
| apps/live_control_server/routes/world_graph_projection.py | PR380A route contract already exists; frontend migration must consume it without changing it |
| apps/live_control_server/services/world_graph_recap_projection.py | Same; a missing field is a stop condition, not silent backend expansion |
| src/graph_memory/projection/world_recap_projection.py | Same predecessor schema boundary |
| apps/live_control_server/routes/graph_preview.py | Still owns legacy diagnostics and Graph Review dependencies; retirement successor |
| apps/live_control_server/services/union_supergraph_projection_adapter.py | Recap must stop consuming it; do not alter it to make migration easier |
| src/graph_memory/union_supergraph/preview_run_materialize.py | Legacy review infrastructure; successor |
| src/graph_memory/union_supergraph/preview_import.py | Candidate read-model builder; successor |
| apps/live-control-ui/src/planSurface/graphPreview/GraphPreviewModule.tsx | Dormant/legacy product component; do not extend or broadly delete in this migration unless bounded discovery proves an active normal entry |
| apps/live-control-ui/src/planSurface/graphPreview/GraphIngestProjectionPanel.tsx | Legacy diagnostic component; Graph Review/retirement successor |
| apps/live-control-ui/src/planSurface/graphReviewWorkbench/** | Graph Review authority lifecycle and candidate-review replacement are separate |
| apps/live_control_server/services/extract_promote.py | Publication prepare/confirm is PR380C/other lifecycle work |
| src/graph_memory/extract_promote_ops.py | Same |
| apps/live_control_server/services/promotable_ingest_run.py | Legacy/canonical run promotability is not Recap runtime authority |
| apps/live-control-ui/src/planSurface/projection/projectionContext.tsx | Existing Plan container behavior remains; it is not hoisted into Build in this slice |
| apps/live-control-ui/src/markdownCanvas/** | Generic canvas remains document-only; Build graph context is an adjacent surface-owned tool |
| apps/live-control-ui/src/agentInteraction/** | Persistent pinned context/thread continuity is a later cross-surface capability |
| Build graph search, reference insertion, node authoring, extraction review, or graph write paths | This slice admits exact read/open only |
| ThreatDraft/statblock candidate, validation, acceptance, binding, or publication paths | Owning SBW/Graph Review slices; no Build write authority expansion |
| apps/live-control-ui/src/planSurface/graphProjectionReader/GraphProjectionReader.tsx | Existing external inspection callback is sufficient; do not fold generic-reader copy cleanup into this slice unless required by an owning test |
| Ingest primary action ordering, number of steps, advanced controls, or extraction operations | PR380E |
| Auto-starting graph extraction in the background | Separate workflow and job-lifecycle capability |
| Auto-publishing successful extraction | Violates review/confirm authority boundary |
| Hybrid World Graph + unpublished candidate overlay in Recap or Build | Creates a second public read authority; prohibited |
| Scope widening to world | PR380A v1 is campaign-scoped |
| Party registry supplementation | A second node authority source; prohibited |
| New aliases, relationship synthesis, evidence repair, or source-span generation | Extraction/identity/evidence successors |
| Revision cache, invalidation events, stale banners, telemetry | PR380D |
| Durable Union direction migration | Explicitly deferred |
| Project Source updates | Separate operator-managed workflow |
## §6 Implementation contract and conditional matrices

### Public consumer contract

Public consumer contract

Input:

Recap: selectedCampaignId + selectedSessionId

Build handoff: campaignId + exact graphNodeId + exact graphRevision

Build document when selected: exact WorkspaceDocumentRecord campaign/document identity

one shared campaign→world mapping


Primary APIs:

Recap: POST /api/live/world-graph/recap-projection

Build context: POST /api/live/world-graph/projection


Outputs consumed:

Recap: WorldGraphRecapProjection v1

Build: WorldGraphProjection v1


UI output:

canonical normalized recap prose

durable dmb-node chips

World Graph node views adapted to one shared reader/card model

exact snapshot/revision source identity

focus-session versus prior-context presentation in Recap

pointer-only Continue in Build handoff

read-only exact object context beside Build’s document canvas/new-source form

shared GraphObjectCard open/navigation across Plan, Recap, and Build


Invariant:

identical to §1


Failure behavior:

unknown campaign→world mapping

→ fail closed in the Recap UI; no duplicate mapping and no guessed worldId

404 recap_markdown_unavailable

→ selected recap source unavailable message; no Union/fixture fallback

World Graph missing/unreadable

→ published graph unavailable message; no preview fallback

422 invalid request

→ stable request/context error; no inferred session/scope

node mention not present in nodeViews

→ no label/alias rebinding; unresolved/inert behavior with test coverage

unexpected API/network failure

→ error + Retry using the same request

Build document scope is neither the incoming campaign nor its resolved world

→ bounded mismatch; no request against a substituted campaign or world-as-campaign value

Build exact node is absent from the pinned projection

→ unresolved exact-node state; no label/alias/preview/statblock fallback


Replay / idempotency:

same selected campaign/session + same returned revision/source bytes

→ deterministic equivalent rendered recap and card model

changed selected session

→ new exact session-focus request; reset active reader/card state

changed selected campaign

→ new mapping/request; URL campaign/session remain synchronized

changed unpinned World Graph head

→ next request may return the new head per PR380A

duplicate request

→ safe; read-only

retry after failure

→ safe; read-only


Trust boundary:

Verifies:

- exact response schema in TypeScript;
- request uses existing campaign→world mapping;
- focus session/campaign and campaign scope;
- node ID exists in response nodeViews before direct card open;
- shared card model is built from the exact response node view;
- no Union/latest-ingest client is called by Recap;
- Ingest CTA does not depend on preview-union readiness;
- Recap→Build carries pointer-only campaign/node/revision identity;
- Build request uses the shared campaign→world mapping and exact revision pin;
- Build document scope equals either the incoming campaign or its resolved world before graph context is admitted;
- Build and Recap use the same neutral node adapter, card renderer, and exact projected-target helper; Plan delegates rendering while retaining its existing resolver.
Records or trusts without proving:

- semantic completeness of durable graph identity;
- whether unconfirmed extraction candidates should be published;
- cross-request snapshot continuity after the head advances;
- source-span highlighting when sourceSpans is empty;
- persistent cross-route Agent Interaction context;
- any Build graph/statblock write capability.
Rejects:

- latest graph-ingest selection;
- manifest/run/path selectors for Recap graph;
- preview-union fallback;
- fixture fallback;
- recap-only graph-shaped placeholders;
- label/alias rebinding for a durable dmb-node chip;
- candidate overlay into published recap;
- invented world IDs, scope, aliases, edges, evidence, or focus state;
- copied node bodies in URL/local storage;
- document prose, extraction candidates, or ThreatDraft/statblock labels as graph identity;
- Build graph/statblock writes.

### Required request construction

Required request construction

The frontend must use one shared mapping seam. The Recap component must not define a second WORLD_ID_BY_CAMPAIGN table.


For selected campaign C and selected session S, the request is equivalent to:


```json
{
  "schema": "dmb_world_graph_projection_request_v1",
  "worldId": "<resolved by the existing shared campaign→world helper>",
  "campaignId": "C",
  "focus": {
    "kind": "session",
    "sessionId": "S",
    "campaignId": "C"
  },
  "admissibility": "gm",
  "scopeMode": "campaign"
}
```


The request must not include:


revisionPin          // absent/null; no UI pin in this slice

queryText            // absent/null

run manifest path

preview union path

candidate graph path

source recap path

source recap sha256

latest ingest selector

allow recap-only selector

preview fixture/source selector


### Required Build object-context request

Required Build object-context request

For admitted incoming campaign C, node N, and recap revision R, Build sends a generic request equivalent to:


```json
{
  "schema": "dmb_world_graph_projection_request_v1",
  "worldId": "<resolved by the shared campaign→world helper>",
  "campaignId": "C",
  "focus": { "kind": "none", "sessionId": null },
  "admissibility": "gm",
  "revisionPin": "R",
  "scopeMode": "campaign"
}
```


The request must not include queryText, session focus, run/manifest paths, preview stores, extraction IDs, source document paths, ThreatDraft IDs, statblock IDs, or copied node data.


When Build is opened directly with no graphRevision, it may read the current head only if the user supplied an explicit campaign/node pointer outside the Recap handoff. A Recap-originating Continue in Build action must always include the exact Recap revision.


### Recap → Build handoff contract

Recap → Build handoff contract

1. Recap card is built from exact response nodeViews[nodeId].
2. Surface action serializes only campaignId, nodeId, and snapshot.revisionId.
3. Build parses and validates the pointer.
4. If a document is loaded, admit only when `document.campaign_id === campaignId` or `document.campaign_id === resolvedWorldId`; the projection request still uses `campaignId`.
5. Build loads the exact generic World Graph projection, pinned when revision is present.
6. Build exact-matches nodeId, adapts it through the neutral World Graph adapter, and renders the shared card renderer.
7. No graph or document write occurs.

Prohibited:


- passing the node JSON or card model through navigation state;
- falling back to the latest extraction or preview union;
- deriving graph identity from Build document prose;
- auto-creating a Build source;
- auto-inserting a graph reference into Markdown;
- enabling graph authoring, statblock generation, acceptance, or binding.

### Shared card-open contract

Shared card-open contract

Initial chip open:


1. TipTap chip emits exact nodeId from dmb-node link.
2. Recap component looks up nodeViews[nodeId] exactly.
3. Shared exact-node helper builds the surface-neutral GraphObjectCard model from that exact WorldGraphProjectionNodeView.
4. `GraphObjectProjectionCard` renders `GraphObjectCard` and emits the exact relationship `targetId` without resolving by label.
5. Recap and Build resolve that target through the shared pure exact-map helper over their currently loaded projection; Plan passes its existing resolver callback unchanged.
6. Recap hosts the renderer in its reader layout; Build hosts it in a Build-owned adjacent context lane; `PlanReferenceObjectCard` delegates only graph-native rendering to it.

Prohibited initial-open behavior:


- refetch by label;
- unique-alias lookup;
- corpus fallback;
- preview-union lookup;
- local GraphNodeExplorer as the Recap product card;
- synthetic object/card fields not present in the exact node view.

Relationship traversal after the card opens:


- reuse the surface-neutral relationship event plus pure exact-map helper for Recap and Build;
- relationship target identity is exact durable node ID;
- Plan retains its existing resolver state/failure rules behind the same renderer callback;
- do not add label-based or prose-based Recap/Build relationship navigators.

### Ingest authority copy contract

Ingest authority copy contract

Ingest may continue to show:


candidate extraction status;


candidate node/edge counts;


preview-union path/status as technical proof;


“Review in workbench” for unpublished candidate review;


replace/re-extract controls.


Ingest must not claim:


preview-union generation makes candidate nodes visible in Recap;


blocked candidate extraction makes published Recap chips unavailable;


Recap is a preview of the latest extraction;


“Open Recap View” requires a preview-union store.


Required semantic distinction:


Recap View = current published World Graph + selected canonical recap.

Graph Review = inspect and decide whether unpublished extraction should change the World Graph.

Preview/candidate status = extraction evidence, not runtime recap authority.


### Build authority copy contract

Build authority copy contract

Build may describe the incoming object as:


Published World Graph context

Exact object from revision <R>

Read-only context for this Build source


Build must not imply that opening the card:


binds the object to the workspace document;


adds the object to Agent Interaction context;


authors or edits graph memory;


launches or accepts extraction;


creates, validates, accepts, or binds a statblock;


changes the World Graph head.


A scope mismatch must name the incoming campaign, the document scope, and the resolved world at a human-usable level while keeping raw paths/hashes secondary.


### Commit point

Commit point

Not applicable — this slice is read-only UI/API consumption and introduces no durable graph, corpus, registry, cache, or run mutation.


## §6A State and fallback matrix

| Observable path | Loading or initializing | Exact success | Ordinary miss | Dependency unavailable | Integrity or contract failure | Stale or superseded | Retry or replay |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Recap artifact/session list | Show loading or preserve requested/default focus | Enumerate canonical recap sessions; latest document may be default | No records: retain requested/default session option | List failure does not select another graph source | Malformed records are filtered by existing rules | Refresh on campaign change | Safe |
| Campaign→world context | Resolve through shared map | Build exact campaign/session request | Unknown campaign: unavailable | N/A | No duplicate/guessed mapping | Mapping changes require re-render/re-request | Safe |
| World Graph recap request | Show published-recap loading | Render exact response | 404 recap missing: honest unavailable | World missing/network failure: error | 422/schema mismatch: fail closed | Unpinned retry may read new head | Safe |
| Node-view adaptation | Adapt all response nodeViews once per payload | Shared reader/card model | Missing node for mention: unresolved/inert | N/A | Invalid shape fails test/typecheck | New response replaces map and resets active state | Deterministic |
| Chip open | Exact nodeId lookup | Open shared neutral card from exact response node | Missing nodeId: do not rebind | Host unavailable: bounded component error, not fallback | No label/alias fallback | Payload change resets selection | Safe |
| Recap → Build pointer | Serialize exact campaign/node/revision | Navigate pointer-only | Missing required pointer: action unavailable | N/A | Malformed pointer rejected | Revision remains pinned for initial Build read | Safe |
| Build context admission | Parse pointer; resolve world; compare document scope | Admit when document scope equals incoming campaign or resolved world | No node pointer: preserve normal Build | World Graph unavailable: context error; canvas remains truthful | Scope mismatch/malformed revision fails closed | Pinned revision remains exact | Safe |
| Build World Graph request | Loading context lane only | Exact campaign projection/revision | Node missing: unresolved | World/revision missing: context error | Schema mismatch fails closed | Explicit pin does not float to head | Safe |
| Build card | Exact node lookup in loaded projection | Shared card and exact relationships | Missing target unresolved | N/A | No label/alias/document fallback | New pointer/request resets card | Deterministic |
| Build canvas | Existing document lifecycle | Unchanged editor/save/extraction behavior | No document: existing form | Existing behavior | Graph context cannot mutate canvas | Document switch revalidates campaign | Existing rules |
| Relationship traversal | Controller owns active exact-node trail | Open exact target from the same loaded projection | Exact target absent: unresolved | Loading/unavailable/error follow the owning surface request | No label-first rebind for graph-native target | Recap/Build remain on their loaded snapshot; Plan preserves existing behavior | Safe |
| Ingest CTA | Derive from normalized recap readiness | Navigate to exact campaign/session Recap | No normalized recap: disabled/hidden with truthful reason | World Graph availability is resolved by Recap, not preview fallback | Invalid session: disabled | Later normalized recap enables CTA | Safe |
| Candidate extraction status | Existing Ingest lifecycle | Report unpublished candidate status | Missing preview: report missing/pending | Extraction blocked: report blocked | Invalid run stays error | Superseded run behavior unchanged | Existing retry rules |
| Graph Review live lane | Existing loading | Continue preview-union projection | Existing unavailable state | Existing error | Existing integrity rules | Existing selected run semantics | Existing behavior |
| Dormant Graph Preview | N/A | No normal navigation added | N/A | N/A | N/A | Remains legacy until successor | N/A |

Permitted fallback sources for Recap graph authority: none.

Recap must not consult:

getUnionSupergraphProjection;

getDefaultUnionSupergraphProjection;

getLatestGraphIngestRun;

GraphIngestRun registry;

graph run manifest;

preview-union store;

default preview fixture;

recap-only placeholder projection;

corpus-index graph fallback;

world-scope retry;

party registry supplementation.

Permitted fallback sources for Build graph authority: none.

Build must not consult or derive identity from:

preview-union or Graph Preview routes;

GraphIngestRun or ExtractionRun registries;

Build Markdown text, title, or document class;

workspace-document campaign_id as a replacement for the incoming campaign when it is world-scoped;

ThreatDraft, statblock candidate, or accepted-mechanics labels;

corpus-index or Plan reference fallback;

label/alias search;

an unpinned current head when a Recap-originating graphRevision was supplied;

world-scope retry after a campaign-scoped miss.

## §6B Identity matrix

| Situation | Required matching rule | Ambiguity behavior | Fallback permitted? | Persistence consequence |
| --- | --- | --- | --- | --- |
| Recap chip initial open | Exact nodeId from dmb-node: link must exist as exact key in response nodeViews | Missing key does not rebind | No | None; transient UI state |
| Direct-node resolution helper | Exact WorldGraphProjectionNodeView.nodeId only | N/A when exact object supplied | No | None |
| Relationship target | Exact durable target node ID from card relationship | Existing graph-native unresolved state | No label/alias fallback | None |
| Recap session | Exact session-N selected from URL/control/default document record | Invalid value rejected/normalized by existing session helper; no graph-run reinterpretation | No | URL only |
| Campaign | Exact selected campaign ID | Unknown mapping unavailable | No guessed mapping | URL only |
| Recap → Build handoff | Exact campaign ID + exact node ID + exact snapshot revision ID | Missing/malformed fields reject the handoff | No | Pointer-only URL |
| Build loaded document scope | Exact equality with incoming campaign or resolved world before graph request | Any other campaign/world scope is visible and unresolved | No campaign switching; world scope never replaces request campaign | Existing document state unchanged |
| Build node | Exact nodeId present in exact generic projection | Missing remains unresolved | No label/alias/document/extraction fallback | None |
| Build revision | Exact incoming graphRevision becomes revisionPin | Missing revision allowed only for direct non-Recap entry | No latest-preview substitution | URL only |
| Label/alias | Display and mention text only after backend linked to durable ID | Must never choose initial card identity | No | None |
| Rename | Durable node ID remains identity; label may change in later response | No old-label rebind without exact ID | No | No new persistence |
| Deletion | Exact node absent in later response becomes unresolved | No recreation/label rebind | No | No new persistence |
| Head advance | Recap card remains on its loaded response; Recap-originating Build handoff pins that revision | Exact IDs remain required | No preview fallback | New unpinned Recap request may read head; Build handoff remains exact |

First-win label matching is prohibited for graph-native Recap and Build object opens.

## §6C Persistence and replay matrix

| Operation | Durable representation | Round-trip guarantee | Duplicate or replay behavior | Compatibility or migration | Rollback or reversion |
| --- | --- | --- | --- | --- | --- |
| Recap campaign/session selection | Existing URL campaign + session parameters | Reload requests same selected recap focus when values remain valid | Repeated selection is idempotent | Existing URL compatibility retained | Revert frontend commit |
| Recap response | None added; transient HTTP response | Exact typed fields adapt deterministically | Duplicate request is read-only | Consumes existing v1 route | Revert frontend commit |
| Active card selection | Surface-local React state | No save/reload guarantee inside the same surface | Duplicate click reopens same exact object | No storage migration | Close card/revert commit |
| Recap → Build graph pointer | URL campaign + graphNodeId + graphRevision | Reload repeats exact pointer resolution | Duplicate navigation is idempotent | New optional URL fields only; no storage migration | Remove params/revert frontend commit |
| Build graph context card | Transient HTTP/React state | Reconstructed from URL and exact World Graph projection | Duplicate request is read-only | No workspace-document schema change | Close/remove pointer |
| Ingest draft | Existing localStorage schema | No schema change in this slice | Existing behavior | No migration | Existing clear-flow behavior |
| Preview-union/run state | Existing files/manifests | Unchanged | Existing behavior | No migration | Outside scope |

No new persisted format, durable identifier, migration, or compatibility adapter is allowed.

## §6D Predecessor-to-consumer mapping

### Grounding sources

- `src/graph_memory/projection/world_recap_projection.py`
- `src/graph_memory/projection/world_projection.py`
- `apps/live_control_server/routes/world_graph_projection.py`
- `apps/live-control-ui/src/api/types.ts` generic World Graph types
- `apps/live-control-ui/src/planSurface/reference/worldGraphProjectionAdapter.ts`

| Predecessor field/outcome | Real shape and optionality | Consumer field or behavior | Transformation | Proof fixture/test |
| --- | --- | --- | --- | --- |
| schema | Literal dmb_world_graph_recap_projection_v1 | Frontend discriminant | Preserve exact literal | liveApi.test.ts, fixture typecheck |
| campaignId | Required string | Selected-campaign consistency and display/test | Preserve | Recap module test |
| sessionId | Required session-N string | Session control and request/result consistency | Preserve | Recap module test |
| graphId | Required string; equals revision ID | Reader reset key/source identity | Preserve; never treat as preview store ID | Recap projection test |
| snapshot.revisionId | Required durable revision ID | Published source note/debug metadata | Display bounded identity; no mutation | Recap projection test |
| snapshot.headRevisionId | Required | Optional trust/debug copy | Preserve | Fixture/typecheck |
| snapshot.isHead | Required boolean | Optional “current/pinned” source semantics | No pin UI; preserve if displayed | Fixture/typecheck |
| markdown | Required string with dmb-node: links | GraphProjectionReader.markdown | Preserve exactly; no relinking in frontend | Recap component test |
| focus.focusSessionId | Optional string but required by valid recap route semantics | Current-session labels | Preserve | Fixture/component test |
| focus.focusedNodeIds | List of exact node IDs | Presentation only if needed | Preserve; do not synthesize | Fixture/typecheck |
| nodeViews | Record keyed by durable node ID; values are generic World Graph node views | Reader map and shared card direct-node helper | Apply the hoisted neutral World Graph node-view adapter per node; Plan compatibility export delegates to the same function; key remains exact node ID | Fixture + adapter + chip/card test |
| nodeViews[*].anchoredToFocusSession | Required boolean | current-session vs prior-context posture | Existing adapter to snake_case | Cross-session fixture test |
| nodeViews[*].adjacency | Exact World Graph adjacency | GraphObjectCard relationships | Existing adapter only | Card/relationship test |
| nodeViews[*].suggestedExpansions | Exact World Graph expansions | Shared card/reader model | Existing adapter only | Fixture/typecheck |
| mentions | Navigation-only records | Mention count/debug only; actual links already in Markdown | Do not infer evidence | Component test |
| sourceSpans | v1 empty list | Reader source spans | Pass empty list; do not claim highlights | Component copy test |
| diagnostics | Bounded list | Optional error/trust details | Preserve; no control flow fallback | Fixture/typecheck |
| trustBoundary | Required can/cannot-trust lists | Truthful source/trust copy if exposed | Preserve semantics | Component copy test |
| Generic WorldGraphProjection.snapshot.revisionId | Required | Build pinned source identity | Must equal incoming graphRevision for Recap-originating handoff | Build context test |
| Generic WorldGraphProjection.nodes[] | Exact durable node views | Build exact node lookup/card model | Exact ID only; adapt through same card adapter | Build fixture/context test |
| Generic node adjacency | Exact durable target IDs | Recap/Build relationship traversal | Neutral renderer emits exact target ID; shared exact-map helper resolves only within the loaded projection; no lookup by label | Shared card + Recap/Build tests |
| 404 recap_markdown_unavailable | Stable World Graph error envelope | Recap unavailable message | Parse through existing LiveApiError fields | API + module test |
| World missing/unreadable error | Stable World Graph error envelope | Published memory unavailable | No Union fallback | Module test |
| 422 invalid request | Stable error envelope | Context/request error | No inferred session/world | API + module test |

The frontend fixture must use actual camelCase response vocabulary. Do not build a snake_case “close enough” fixture and then adapt the wrong contract.

## §7 Verification ownership map and commands

| Guarantee | Owning boundary | Command or scenario | Expected evidence |
| --- | --- | --- | --- |
| Typed client uses exact route/method/body | API client test | focused liveApi.test.ts | POST /api/live/world-graph/recap-projection; exact body; error fields preserved |
| Explicit campaign/session request reuses one world mapping | context helper test | focused planGraphContextRequest.test.ts | correct world/campaign/session/focus/scope; unknown campaign unavailable; no query/pin |
| Exact-node helper builds the shared card model from exact node | neutral adapter/renderer tests | focused graph-object tests plus Plan resolver regression | exact node ID/model; no label/alias lookup |
| Recap no longer calls Union/latest-ingest client | Recap component test | focused RecapGraphModule.test.tsx | World recap client called; Union/latest clients not called; no manifest/source fields |
| Recap succeeds without preview-union state | Recap component test | focused test with only World recap fixture | published recap renders |
| Cross-session durable node is visible | Recap component test | fixture with non-focus node | prior-context node/card present |
| Chip opens shared GraphObjectCard content | Recap/neutral-renderer integration test | Recap test with the real neutral renderer | exact node card opens; local GraphNodeExplorer is not the product path |
| Relationship navigation uses exact target ID | shared card integration regression | Recap/shared-card test | related target opens by exact durable ID; no label fallback |
| Shared graph-native card logic is no longer Plan-owned | neutral adapter/renderer tests + Plan regression | neutral world adapter, GraphObjectProjectionCard.test.tsx, PlanReferenceObjectCard.test.tsx | Plan compatibility path delegates; Recap/Build import neutral modules; generic modules import no surfaces |
| Recap Continue in Build is pointer-only and revision exact | Recap component test | click action and inspect URL | campaign/node/revision only; no body/run/preview fields |
| Build request uses campaign scope and exact revision pin | Build context test | no-document, campaign-scoped document, and world-scoped document cases | generic World Graph POST; incoming campaign retained; focus none; exact pin; no query/preview |
| Build document scope mismatch fails closed | Build context test | document scope is neither incoming campaign nor resolved world | no API call or alternate campaign; bounded message |
| Build exact node missing does not rebind | Build context adversarial test | node absent, same-label node present | unresolved; no wrong card |
| Build with no pointer remains unchanged | Build page/shell regressions | existing tests | canvas/new-source/extraction/Agent context unchanged |
| Missing node target does not rebind | Recap component test | malformed mention fixture | no wrong card; bounded unresolved behavior |
| Ingest CTA is independent of preview-union readiness | Ingestion component test | missing/blocked/ready preview matrix | CTA availability derives from normalized recap; URL contains exact campaign/session |
| Ingest copy distinguishes candidate review from published Recap | Ingestion component test | blocked/ready preview matrix | no “chips unavailable because preview blocked” or “preview graph is Recap” claim |
| Graph Review live lane remains operational | Graph Review regression | existing live projection tests | no changed behavior/production paths |
| Backend predecessor remains green | Python predecessor tests | PR380A focused tests | no backend contract regression |
| No active Recap Union selector remains | static inspection | rg commands below | no prohibited imports/calls/copy in Recap files |
| No unexpected paths | diff inspection | git commands below | all paths in §4 or admitted report |

### Required commands

Run from repository root unless noted:

```bash

Run from repository root unless noted:

# Backend predecessor contract — no backend edits expected.
uv run pytest \
  tests/test_world_graph_recap_projection.py \
  tests/test_graph_kernel_boundaries.py \
  -q

cd apps/live-control-ui

# Focused API, context, resolver, Recap, Ingest, and shared-card ownership.
npm test -- --run \
  src/api/liveApi.test.ts \
  src/worldGraph/worldGraphNodeViewAdapter.test.ts \
  src/planSurface/reference/planGraphContextRequest.test.ts \
  src/planSurface/reference/worldGraphProjectionAdapter.test.ts \
  src/planSurface/reference/graphAwareReferenceResolver.test.ts \
  src/planSurface/graphPreview/RecapGraphModule.test.tsx \
  src/modules/IngestionModule.test.tsx \
  src/planSurface/reference/PlanReferenceObjectCard.test.tsx \
  src/graphObjectCard/GraphObjectProjectionCard.test.tsx \
  src/graphObjectCard/buildGraphObjectCardFromNodeView.test.ts \
  src/worldGraph/worldGraphSurfaceContext.test.ts \
  src/buildSurface/BuildGraphObjectContext.test.tsx \
  src/buildSurface/BuildSurfacePage.test.tsx \
  src/buildSurface/BuildSurfaceShell.test.tsx

# Regression: preview infrastructure remains available to Graph Review.
npm test -- --run \
  src/planSurface/graphReviewWorkbench/GraphReviewLoadSurface.test.tsx \
  src/planSurface/graphReviewWorkbench/GraphReviewGenericRun.test.tsx \
  src/planSurface/graphProjectionReader/GraphProjectionReader.test.tsx

npm run typecheck
npm run build

cd ../..

# Recap runtime must not retain latest-ingest/preview authority.
! rg -n \
  "getUnionSupergraphProjection|getDefaultUnionSupergraphProjection|getLatestGraphIngestRun|useLatestGraphIngest|graphRunManifestPath|previewUnionStorePath|latest graph-ingest preview|session preview union" \
  apps/live-control-ui/src/planSurface/graphPreview/RecapGraphModule.tsx \
  apps/live-control-ui/src/planSurface/graphPreview/WorldGraphRecapProjection.tsx

# The deleted renderer must have no remaining imports.
! rg -n "UnionSupergraphRecapProjection" apps/live-control-ui/src

# The World Graph recap route must be the positive Recap client path.
rg -n \
  "world-graph/recap-projection|postWorldGraphRecapProjection|WorldGraphRecapProjection" \
  apps/live-control-ui/src/api \
  apps/live-control-ui/src/planSurface/graphPreview

# Build must use pointer-only exact World Graph context.
rg -n \
  "graphNodeId|graphRevision|postWorldGraphProjection|revisionPin|scopeMode" \
  apps/live-control-ui/src/buildSurface \
  apps/live-control-ui/src/worldGraph

# Generic Markdown canvas remains graph-free; Build owns the adjacent context lane.
! rg -n \
  "WorldGraph|GraphObjectProjectionCard|BuildGraphObjectContext|graphNodeId|graphRevision" \
  apps/live-control-ui/src/markdownCanvas

# Preview semantics may remain in Ingest and Graph Review, but Recap authority wording must be absent.
rg -n \
  "preview_union_store_ready|preview union|candidate graph|Review in workbench" \
  apps/live-control-ui/src/modules/IngestionModule.tsx \
  apps/live-control-ui/src/planSurface/graphReviewWorkbench

git diff --check
git diff --stat 00fa026d98294e575ad663a473731d426dcf05b3...HEAD -- \
  Docs/Plans/HANDOFF-pr380b-world-graph-recap-ui-migration.md \
  apps/live-control-ui/src/api/types.ts \
  apps/live-control-ui/src/api/liveApi.ts \
  apps/live-control-ui/src/api/liveApi.test.ts \
  apps/live-control-ui/src/worldGraph/worldGraphSurfaceContext.ts \
  apps/live-control-ui/src/worldGraph/worldGraphSurfaceContext.test.ts \
  apps/live-control-ui/src/worldGraph/worldGraphNodeViewAdapter.ts \
  apps/live-control-ui/src/worldGraph/worldGraphNodeViewAdapter.test.ts \
  apps/live-control-ui/src/planSurface/reference/worldGraphProjectionAdapter.ts \
  apps/live-control-ui/src/planSurface/reference/worldGraphProjectionAdapter.test.ts \
  apps/live-control-ui/src/graphObjectCard/GraphObjectProjectionCard.tsx \
  apps/live-control-ui/src/graphObjectCard/GraphObjectProjectionCard.test.tsx \
  apps/live-control-ui/src/planSurface/reference/planGraphContextRequest.ts \
  apps/live-control-ui/src/planSurface/reference/planGraphContextRequest.test.ts \
  apps/live-control-ui/src/planSurface/reference/PlanReferenceObjectCard.tsx \
  apps/live-control-ui/src/planSurface/reference/PlanReferenceObjectCard.test.tsx \
  apps/live-control-ui/src/planSurface/graphPreview/RecapGraphModule.tsx \
  apps/live-control-ui/src/planSurface/graphPreview/WorldGraphRecapProjection.tsx \
  apps/live-control-ui/src/planSurface/graphPreview/UnionSupergraphRecapProjection.tsx \
  apps/live-control-ui/src/planSurface/graphPreview/worldGraphRecapFixture.ts \
  apps/live-control-ui/src/planSurface/graphPreview/RecapGraphModule.test.tsx \
  apps/live-control-ui/src/modules/IngestionModule.tsx \
  apps/live-control-ui/src/modules/IngestionModule.test.tsx \
  apps/live-control-ui/src/buildSurface/BuildGraphObjectContext.tsx \
  apps/live-control-ui/src/buildSurface/BuildGraphObjectContext.test.tsx \
  apps/live-control-ui/src/buildSurface/BuildSurfacePage.tsx \
  apps/live-control-ui/src/buildSurface/BuildSurfacePage.test.tsx \
  apps/live-control-ui/src/buildSurface/BuildSurfaceShell.tsx \
  apps/live-control-ui/src/buildSurface/BuildSurfaceShell.test.tsx

git diff --name-only 00fa026d98294e575ad663a473731d426dcf05b3...HEAD

```

If repository scripts differ on current main, use the canonical equivalent and report the exact command rather than silently skipping the gate.


### Minimal live proof

Minimal live proof

Existing surfaces used:

/plan Recap tool

/ingest

/build


Scenario A — durable cross-session Recap:

Initial state:

- a campaign World Graph head exists;
- one canonical normalized recap exists for the selected session;
- the durable campaign graph contains at least one node not anchored only to that focus session.
Action:

- open /plan?tool=recap&campaign=<campaign>&session=<session-N>;
- click a dmb-node chip;
- click one related object when available.
Expected observation:

- source copy says published/current World Graph, never latest preview union;
- the recap loads even when no preview-union store exists for that session;
- the initial click opens the neutral GraphObjectCard renderer;
- the card node ID/label matches the exact response node;
- related navigation uses the durable target ID from the same loaded response;
- prior-context posture is visible where live data supports it.

Scenario B — Ingest authority boundary:

Initial state:

- canonical normalized recap exists;
- candidate extraction is missing or blocked, or preview-union is absent.
Action:

- open /ingest for that campaign/session;
- click Open Recap View.
Expected observation:

- CTA is available based on normalized recap readiness, not preview-union state;
- navigation includes exact campaign and session;
- Recap opens current published World Graph;
- Ingest separately directs unpublished candidate review to Graph Review.

Scenario C — exact Recap → Build handoff:

Initial state:

- Scenario A Recap is open on revision <R>;
- one exact durable object <N> is open.
Action:

- choose Continue in Build;
- inspect the Build URL;
- observe Build with no selected document;
- repeat with a matching admitted Build document;
- repeat with a document from a different campaign.
Expected observation:

- the URL carries only campaign, graphNodeId, and graphRevision pointer fields;
- graphRevision equals <R>;
- with no document, the same object card appears beside the new-source form and campaign is prefilled without submission;
- with either a campaign-scoped document or a world-scoped document for the resolved world, the same node ID and pinned revision render beside the canvas;
- related-object traversal stays within the same pinned projection;
- with a document scoped to another campaign/world, Build refuses graph context without altering the document;
- no graph write, Markdown insertion, extraction launch, Agent Interaction pin, or statblock action occurs.

Evidence captured:

- screenshots or a short screen recording;
- Recap network request showing POST /api/live/world-graph/recap-projection;
- Build network request showing POST /api/live/world-graph/projection with campaign scope and revisionPin;
- Recap response revision ID and clicked node ID;
- Build URL pointer fields and rendered node/revision identity;
- note whether live data included a prior-context node.

Do not build a new diagnostics panel merely to capture this proof.


### Baseline failure protocol

Baseline failure protocol

Baseline-identical failures are informational, not an independent merge gate for this project workflow.


For any required command failing on base:


run or cite the same command on base and head when practical;


record exact base/head results and whether head adds failures;


do not claim the command is green;


do not require a separate operator waiver or PR-description refresh merely because a baseline-identical failure remains;


new failures introduced by this slice remain merge-blocking.


Use this evidence shape:


Command


Base result


Head result


New failure introduced?


Acceptance effect


<command>


<result>


<result>


Yes / No


New failure blocks; baseline-identical failure is informational


## §8 Required implementation handback

The PR body or implementation handback must include:


Base SHA.


Head SHA.


Commit list, identifying the first characterization-only commit and first production commit.


Actual changed paths.


Focused diff stat limited to §4 paths.


Every §7 command and exact result.


Provenance of each result: author-local, independently rerun local, CI, or manual observation.


Live proof evidence or a precise reason it could not run.


Base/head comparison for any baseline failure.


Paths outside §4: none or the bounded-discovery report.


Stop conditions encountered and resolution: none when none.


Deviations from §6 matrices: none when none.


Confirmation that Recap makes no Union/latest-ingest/preview fallback call.


Confirmation that Ingest preview state remains diagnostic and does not gate Recap View.


Confirmation that Graph Review preview-union behavior remains operational.


Confirmation that Recap Continue in Build carries pointer-only campaign/node/revision identity.


Confirmation that Build loads an exact campaign-scoped generic World Graph projection, admits campaign- or containing-world-scoped documents, and fails closed on other scopes or a missing exact node.


Confirmation that Build document editing, extraction, Agent Interaction publication, and statblock workflows remain unchanged.


Confirmation that no generic Markdown canvas module imports graph-object or Build context code.


Confirmation that no backend World Graph or preview-union production path changed.


Named successor capabilities still false.


Confirmation that the complete handoff was implemented without compression or omitted constraints.


The handback does not need an operator-waiver section or a PR-body refresh gate beyond truthful technical evidence.


## §9 Acceptance rubric

The reviewer accepts only when every item is true.


### Authority migration

Authority migration

Recap View calls POST /api/live/world-graph/recap-projection with the selected campaign/session — proved by API and Recap tests.


Recap View no longer calls Union/latest-ingest/default-preview APIs — proved by component spies and static search.


Recap graph loading is independent of preview-union existence — proved by the missing-preview component test.


Recap artifact records are used only for recap document/session selection — proved by request assertions and diff inspection.


No manifest, run, source SHA, preview path, or fixture selector enters the Recap graph request — proved by request assertions.


Error states never fall back to preview union, fixture, recap-only graph, corpus graph, or world scope — proved by the state matrix tests.


### Shared object navigation

Shared object navigation

World Graph nodeViews are adapted through the existing shared adapter — proved by fixture/type tests and diff inspection.


Clicking a Recap chip opens the surface-neutral GraphObjectCard renderer — proved by the interaction test.


Initial chip open uses exact durable node ID and exact response node view — proved by direct-node helper tests.


Missing exact node IDs do not label/alias rebind — proved by adversarial test.


Related-object selection uses the neutral renderer’s exact target-ID contract; Recap/Build share one exact-map helper and Plan retains its existing resolver — proved by integration/regression tests.


Recap no longer presents GraphNodeExplorer as its product object card — proved by interaction test and component composition.


### Ingest boundary

Ingest boundary

“Open Recap View” becomes available from canonical normalized recap readiness, not preview-union readiness — proved by matrix tests.


The CTA navigates with exact selected campaign/session — proved by interaction test.


Blocked/missing preview extraction does not claim published Recap chips are unavailable — proved by copy tests.


Preview/candidate state remains clearly unpublished and routes to Graph Review for review — proved by copy/CTA tests.


Ingest extraction controls and lifecycle remain otherwise unchanged — proved by focused diff and regression tests.


### Build Surface durable-object consumption

Build Surface durable-object consumption

Recap object cards expose Continue in Build using only exact campaign/node/revision pointers — proved by interaction and URL tests.


Build resolves the pointer through the existing generic World Graph route with campaign scope and exact revision pin — proved by API/context tests.


A loaded Build document must be explicitly scoped to the incoming campaign or its resolved world before graph context is admitted — proved by campaign-scope, world-scope, and mismatch tests.


Build opens the exact durable node through the same neutral adapter/GraphObjectCard renderer used by Recap and delegated to by Plan — proved by shared modules and surface tests.


Build relationship traversal uses exact IDs from the same pinned projection — proved by interaction test.


Missing exact nodes never rebind through label, alias, document prose, extraction candidates, ThreatDraft names, or statblock names — proved by adversarial test.


Build without a graph pointer preserves existing canvas/new-source/extraction/Agent Interaction behavior — proved by regressions.


Build context is read-only: no graph authoring, Markdown insertion, statblock generation/acceptance/binding, publication, or Agent Interaction pinning is added — proved by changed-path and copy inspection.


MarkdownCanvasSession and MarkdownCanvas remain free of World Graph and Build graph-context imports — proved by boundary/static tests.


### Preview infrastructure boundary

Preview infrastructure boundary

Graph Review live preview-union lane remains operational — proved by existing regression tests.


No preview-union backend/storage path changed — proved by changed-path inspection.


No new normal navigation or Recap fallback to standalone Graph Preview was added — proved by surface config/diff inspection.


Dormant Graph Preview and preview-union retirement remain named successors, not claimed as complete.


### Scope and evidence

Scope and evidence

Exactly one coherent cross-surface durable-object read capability from §1 was delivered.


Every changed layer establishes or proves the §1 invariant.


Every applicable observable path in §3 follows the same invariant.


No backend/schema/storage/publication/cache contract was silently introduced.


First characterization commit precedes production changes.


The frontend fixture preserves actual PR380A camelCase vocabulary.


Required tests, typecheck, build, static searches, and diff checks are reported accurately.


New failures are absent; baseline-identical failures are reported as informational.


No unexpected path changed.


The authoritative handoff survived dispatch without omitted constraints.


## §10 Reviewer protocol

Review the authority invariant before reviewing individual files.


Restate the mission and invariant.


Inspect the commit order: characterization before production.


Compare actual changed paths with §4 and §5.


Trace the exact Recap request from selected campaign/session to the API body.


Confirm the shared campaign→world mapping is reused rather than copied.


Search Recap production files for every prohibited Union/latest-ingest selector.


Verify every error path has no preview fallback.


Trace one dmb-node: click from Markdown to exact response node view to shared card.


Verify the direct-node helper cannot perform label/alias resolution.


Trace relationship navigation and confirm exact durable target identity.


Check Ingest’s missing/blocked/ready preview matrix and CTA URL.


Read all changed user-facing copy for authority confusion.


Trace Continue in Build and inspect that only campaign/node/revision pointers cross the route.


Verify Build uses the shared campaign→world mapping, campaign scope, and exact revision pin.


Verify campaign-scoped and containing-world-scoped documents are admitted, while other scopes and missing-node cases fail closed without changing the canvas.


Trace Build relationship navigation through the neutral exact-target helper and same pinned projection; confirm Plan still uses its existing resolver callback.


Inspect generic Markdown canvas boundaries for graph/Build leakage.


Run Graph Review regressions and inspect that no Graph Review production path changed.


Confirm no backend, extraction, promotion, statblock, Agent Interaction persistence, storage, cache, or migration path changed.


Verify the live proof uses existing surfaces and does not add a diagnostics product.


Confirm all successors remain false and explicitly named.


Do not request a PR-description refresh or separate operator waiver when technical evidence is complete and remaining failures are baseline-identical.


## §11 Re-review protocol

Begin every re-review from the prior finding ledger.


Prior finding


Claimed fix


Owning files/tests


Verified?


New consequence?


<finding>


<claimed resolution>


<paths/tests>


Yes / No


<none or consequence>


For each prior finding:


verify the exact fix;


rerun the whole authority invariant;


recheck all Recap entry paths and Ingest preview-state variants;


recheck exact-ID chip/card/relationship navigation;


recheck Recap→Build pointer identity, Build campaign-or-world document-scope admission, revision pin, and exact-node resolution;


recheck Build no-pointer regressions and Markdown canvas boundaries;


re-run Graph Review preview-union regressions;


inspect whether the fix added a new fallback, duplicated mapping, graph/statblock write, Agent Interaction persistence, or backend dependency;


add any new finding to the ledger.


Do not review only the literal line changed after a comment.


Stop conditions


Stop and report rather than broadening scope when implementation discovers:


the World Graph recap response lacks a field required to render the existing shared card;


the frontend generic World Graph node type materially disagrees with the backend response;


the only way to open a chip is label/alias lookup rather than exact node ID;


GraphProjectionReader.onInspectNode or ProjectionContext.openPlanReferenceResolution is no longer sufficient;


Graph Review imports the renderer proposed for deletion;


deleting UnionSupergraphRecapProjection.tsx would break a non-Recap consumer;


current main exposes a normal Graph Preview entry whose removal requires more than the bounded discovery allowance;


Ingest cannot identify canonical normalized recap readiness without changing its persistence/lifecycle contract;


Recap success requires publishing or overlaying the just-ingested candidate graph;


selected campaign→world mapping requires a new registry or second hardcoded table;


an exact relationship target cannot resolve without a new cache or revision-pin contract;


Build cannot render the exact graph object without modifying generic Markdown canvas authority;


Build’s existing campaign-or-world document scope cannot be admitted against the incoming campaign using the shared campaign→world mapping without changing workspace-document persistence;


the generic World Graph projection cannot honor the exact Recap revision pin;


a useful Build handoff requires graph search, document insertion, node authoring, Agent Interaction persistence, ThreatDraft/statblock actions, or publication;


any backend, Graph Review production, extraction, promotion, statblock, Agent Interaction persistence, storage, cache, or telemetry path is required;


a required path falls outside §4 and the bounded discovery exception;


the predecessor contract differs materially from the fixture/mapping in §6D;


a handoff requirement cannot be implemented without reinterpretation.


Use this report:

```text

Stop condition:
Why the current mission cannot absorb it:
New public/durable contract discovered:
Affected observable paths:
Affected ownership layers:
Required path outside scope:
Proposed successor slice:
Tracker or authority update needed:
Operator decision required:

```

The worker must not resolve a stop condition by silently widening Recap scope, adding a preview fallback, or changing publication behavior.

The worker must not resolve a stop condition by silently widening Recap scope, adding a preview fallback, or changing publication behavior.


## Final dispatch check

- §0 records one coherent product authority migration.
- §1 states one invariant reused across Recap, Ingest, Build, and shared card navigation.
- PR380A / PR #412 is the exact predecessor contract.
- Latest recap document selection is distinguished from latest graph-ingest authority.
- Graph Preview product retirement is distinguished from preview-infrastructure deletion.
- Graph Review’s current preview-union dependency is preserved and named for successor replacement.
- Exact durable node-ID behavior is explicit.
- Recap→Build pointer-only campaign/node/revision handoff is explicit.
- Build’s read-only adjacent context boundary and campaign-or-world document-scope admission are explicit.
- Generic Markdown canvas, graph-write, statblock-write, and Agent Interaction persistence exclusions are explicit.
- Error and fallback behavior is explicit.
- Persistence and replay consequences are explicit.
- First-commit characterization is required.
- Changed paths are bounded.
- Owning-boundary tests and live proof are specified.
- Baseline-identical failures are informational; no operator-waiver or PR-refresh gate is imposed.
- Stop conditions prevent backend, publication, Graph Review, cache, and Ingest-workflow scope creep.

## Dispatch summary for the coding agent

Implement PR380B from base 00fa026d98294e575ad663a473731d426dcf05b3.


The product result is simple to state but strict in authority:


Recap View reads the selected canonical recap through the durable World Graph recap route.

Ingest opens that same view.

A recap chip opens the surface-neutral durable GraphObjectCard renderer by exact node ID.

Continue in Build carries only campaign, exact node ID, and exact recap revision.

Build re-resolves that pointer through an exact campaign-scoped World Graph projection and shows the same read-only object beside its document canvas/new-source form.

Preview-union state remains unpublished Graph Review infrastructure and never becomes a Recap or Build source or fallback.


Begin with the characterization-only commit. Then make the smallest production changes in §4. Do not delete Graph Review preview infrastructure, change backend contracts, overlay unpublished candidates into Recap or Build, modify generic Markdown canvas authority, or add Build graph/statblock writes.

