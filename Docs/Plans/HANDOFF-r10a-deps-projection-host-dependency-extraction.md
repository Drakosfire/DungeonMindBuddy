# HANDOFF — R10a-deps projection-host dependency extraction

**Created:** 2026-07-27
**Status:** ACTIVE — dispatch exactly one implementation capability.
**Canonical handoff path:** `Docs/Plans/HANDOFF-r10a-deps-projection-host-dependency-extraction.md`
**Implementation base:** `f9a7be22d8752830a26babb63488f167579cea66`
**Suggested branch:** `agent/r10a-deps-projection-host-dependencies`
**Suggested PR title:** `refactor(ui): extract projection-host dependencies for R10a`

---

## §0 Capability decomposition decision

| Candidate outcome                                                                        | Independently useful? |            Public/durable contract changed? |   Operator surface changed? |                                           Failure model changed? | Independently testable or revertible? | Decision                                     |
| ---------------------------------------------------------------------------------------- | --------------------: | ------------------------------------------: | --------------------------: | ---------------------------------------------------------------: | ------------------------------------: | -------------------------------------------- |
| Projected Plan and Graph Review content no longer requires route-local provider ancestry |                   Yes |        Internal typed runtime contract only |                          No | Yes—missing dependency becomes explicit rather than a hook crash |                                   Yes | **Include**                                  |
| Move projection state and container ownership into `AgentInteractionProvider`            |                   Yes | Yes—app-level surface registration contract |                 Potentially |                                                              Yes |                                   Yes | **Successor: R10a**                          |
| Extract neutral graph-reference render/search/insert/project capability APIs             |                   Yes |                                         Yes | No intended behavior change |                                                              Yes |                                   Yes | **Successor: MC-02a**                        |
| Enable graph-reference capabilities on Build                                             |                   Yes |                                         Yes |                         Yes |                                                              Yes |                                   Yes | **Successor: MC-02b**                        |
| Repair `reviewable` versus inspection-readiness truth                                    |                   Yes |                        Backend/API contract |                  Eventually |                                                              Yes |                                   Yes | **Parallel successor: BLD inspection truth** |
| Bottom Agent Interaction Bar/Pane and persistence                                        |                   Yes |                                         Yes |                         Yes |                                                              Yes |                                   Yes | **Successor: R10b**                          |
| Reuse or finish the implementation in PR #430                                            |                    No |            Conflicts with current authority |                          No |                          Preserves the wrong ancestry dependency |                                    No | **Reject**                                   |

**Selected capability**

Projected Plan reference content and Graph Review diagnostics consume typed, explicitly registered runtime dependencies rather than requiring their route-local providers to be ancestors of the projection renderer.

**Why the included work shares one invariant**

Both current projection paths fail the same future-host requirement: the renderer reaches upward into a route-local React context for data or actions. Replacing those hidden ancestry requirements with explicit registered dependencies establishes one reusable host contract. No ownership move, Build capability, or visual behavior is required.

**Named successors**

* R10a — move projection ownership into `AgentInteractionProvider`
* MC-02a — finish neutral graph-reference capability extraction
* MC-02b — enable shared graph references on Build
* BLD inspection truth — independent backend correctness lane
* R10b — bottom pane and bounded persistence

---

## §1 Mission

Plan reference projections and Graph Review diagnostics can render and preserve their existing interactions from typed, registered in-memory projection dependencies, so the renderer no longer depends on route-local provider ancestry.

### Invariant

```text
Every projected component rendered by the current shared projection registry receives
the route-owned data and actions it needs through an explicit typed projection binding;
the projected component itself does not read the Plan reference resolver or Graph Review
live-state React contexts.
```

### Mission falsification test

```text
This is not one slice if implementation must also:

- move ProjectionProvider or AdaptiveProjectionContainer above the route switch;
- change AgentInteractionProvider;
- generalize all SurfaceConfig or graph-reference capability vocabulary;
- enable projection or graph-reference behavior on Build;
- add extraction inspection behavior;
- change Graph Review disposition, publication, or promotion authority;
- introduce bottom-pane chrome or persistence.
```

---

## §2 Context, authority, and boundaries

| Field                       | Required content                                                                                                                                                                                             |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Parent authority            | `Docs/Design/ARCHITECTURE-plan-surface-toolbox.md`                                                                                                                                                           |
| Active design               | `Docs/Design/DESIGN-shared-markdown-canvas-surface-composition.md`                                                                                                                                           |
| Active sequencing authority | `Docs/Plans/PLAN-shared-markdown-canvas-build-first.md`                                                                                                                                                      |
| Repository rules            | `AGENTS.md`; `.cursor/rules/external-agent-pr-loop.mdc`; `.cursor/skills/external-agent-pr-loop/SKILL.md`                                                                                                    |
| Base revision               | `f9a7be22d8752830a26babb63488f167579cea66`                                                                                                                                                                   |
| Predecessor contract        | Current route-local `ProjectionProvider`, projection registry, Plan reference renderer, and Graph Review live-state provider at the base SHA                                                                 |
| Exact input consumed        | Existing `PlanReferenceResolution`, `PlanGraphProjectionState`, `GraphObjectRelationshipViewModel`, `PlanSessionDescriptor`, `GraphReviewLiveStateContextValue`, `ActiveProjection`, and registered tool IDs |
| Named successor             | R10a app-scoped ownership lift                                                                                                                                                                               |
| What remains false          | Projection ownership remains route-local; Build gains no graph interaction; no new chrome or persistence                                                                                                     |
| Explicit non-goals          | World Graph identity logic, search, insertion, node creation, extraction inspection, dispositions, elevation, SurfaceConfig-wide redesign                                                                    |

### Authority precedence

```text
1. Docs/Design/ARCHITECTURE-plan-surface-toolbox.md
2. Docs/Design/DESIGN-shared-markdown-canvas-surface-composition.md
3. Docs/Plans/PLAN-shared-markdown-canvas-build-first.md
4. This checked-in handoff
5. Implementation and owning-boundary tests at the declared base
6. Open or abandoned implementation PRs used only as reconnaissance
7. Chat summaries
```

### Read authoritative inputs in this order

1. `Docs/Design/ARCHITECTURE-plan-surface-toolbox.md`
2. `Docs/Design/DESIGN-shared-markdown-canvas-surface-composition.md`
3. `Docs/Plans/PLAN-shared-markdown-canvas-build-first.md`
4. This handoff
5. `apps/live-control-ui/src/planSurface/projection/projectionContext.tsx`
6. `apps/live-control-ui/src/planSurface/projection/AdaptiveProjectionContainer.tsx`
7. `apps/live-control-ui/src/planSurface/projection/projectionRegistry.tsx`
8. `apps/live-control-ui/src/planSurface/reference/PlanReferenceObjectCard.tsx`
9. `apps/live-control-ui/src/planSurface/reference/usePlanGraphReferenceResolver.ts`
10. `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewDiagnosticsToolPanel.tsx`
11. `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewLiveStateContext.tsx`
12. Existing projection, Plan reference, and Graph Review integration tests
13. Repository implementation and review-loop rules

### Stale implementation warning

PR #430 is **not** a predecessor and must not be used as the implementation base.

Its approach mounts projection state above routing while retaining `AdaptiveProjectionContainer` beneath each surface to preserve React-context ancestry. That is the dependency this slice removes before R10a.

Rules:

* do not branch from PR #430;
* do not merge or cherry-pick its ownership lift;
* do not treat its app-level `ProjectionProvider` as accepted architecture;
* its code may be inspected only as reconnaissance;
* if the implementation branch already contains PR #430 changes, stop and rebuild from the declared base.

The same warning applies to any downstream PR stacked on #430.

---

## §3 Current implementation seam

### Plan

`PlanSurfaceShell` currently mounts:

```text
ProjectionProvider
  PlanGraphLensProvider
    PlanGraphReferenceResolverProvider
      Plan canvas
      AdaptiveProjectionContainer
```

`PlanReferenceObjectCard` reaches into:

* `usePlanGraphReferenceResolver()` for relationship traversal;
* `useOptionalProjection()` for active projection state;
* `openPlanReferenceResolution()` for relationship navigation;
* `openTool("statblock")` for the statblock action.

The rendered card therefore requires route-local providers to remain its ancestors.

### Graph Review

`GraphReviewWorkbenchModule` currently mounts:

```text
ProjectionProvider
  GraphReviewLiveStateProvider
    Graph Review workbench
    AdaptiveProjectionContainer
```

`GraphReviewDiagnosticsToolPanel` calls `useGraphReviewLiveState()` directly and consumes a large live data/action model.

The diagnostics renderer therefore also requires its route-local provider to remain an ancestor.

### Shared host

`ProjectionProvider` currently owns active projection state and the open/close methods. `AdaptiveProjectionContainer` chooses a renderer through `projectionRegistry`.

This slice retains that ownership topology. It changes only how route-owned dependencies reach projected renderers.

---

## §4 Observable-path inventory

| Observable path                           | Current behavior                                          | Required behavior                                                                            |         Same invariant? | Owning boundary                       |
| ----------------------------------------- | --------------------------------------------------------- | -------------------------------------------------------------------------------------------- | ----------------------: | ------------------------------------- |
| Open a resolved Plan graph-node chip      | Card renders by reading Plan resolver/projection contexts | Card renders from explicit resolution plus registered Plan projection binding                |                     Yes | Plan reference projection integration |
| Open a corpus-fallback reference          | Fallback card renders under Plan providers                | Same visible fallback card without renderer hook dependency                                  |                     Yes | Plan reference renderer               |
| Open an ambiguous or unresolved reference | Unresolved card renders and links to corrective workflow  | Same state; no first-ranked auto-selection                                                   |                     Yes | Plan reference renderer               |
| Select a graph relationship               | Card calls resolver hook, then projection hook            | Card invokes a typed registered adapter that resolves and opens the exact returned reference |                     Yes | Plan binding + projection integration |
| Open statblock action                     | Card calls projection hook directly                       | Card invokes explicit registered `openTool` action                                           |                     Yes | Plan binding                          |
| Open Graph Review diagnostics             | Panel reads `GraphReviewLiveStateContext` directly        | Panel receives a typed diagnostics payload                                                   |                     Yes | Graph Review diagnostics integration  |
| Change diagnostics selection              | Panel calls context actions directly                      | Panel invokes actions carried by the diagnostics payload                                     |                     Yes | Graph Review diagnostics integration  |
| Graph Review state refresh                | Context rerender changes panel implicitly                 | Binding republishes the latest payload and the open projection updates                       |                     Yes | Graph Review binding                  |
| Required Plan binding absent              | Hook currently throws only when ancestry is broken        | Static content remains truthful; unavailable actions fail closed and do not throw            |                     Yes | Projection registry/renderer          |
| Required diagnostics payload absent       | Hook currently throws when ancestry is broken             | Render a stable unavailable state rather than crashing or showing stale data                 |                     Yes | Projection registry/renderer          |
| Close or replace projection               | Provider clears active projection state                   | Existing behavior remains unchanged; no binding data leaks into another projection           |                     Yes | Projection provider                   |
| Navigate between surfaces                 | Not addressed by this slice                               | Production topology remains unchanged                                                        | Yes, by remaining false | R10a successor                        |

---

## §5 Files in scope — allowlist

Every changed path must appear here or satisfy the bounded discovery exception.

| Action | Path                                                                                                    | Purpose                                                                            |
| ------ | ------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| Create | `Docs/Plans/HANDOFF-r10a-deps-projection-host-dependency-extraction.md`                                 | Check in the complete implementation authority                                     |
| Modify | `Docs/Plans/PLAN-shared-markdown-canvas-build-first.md`                                                 | Mark R10a-deps ACTIVE and link this handoff; do not otherwise redesign the roadmap |
| Create | `apps/live-control-ui/src/planSurface/projection/projectionBindings.ts`                                 | Define typed in-memory projection binding contracts and keys                       |
| Modify | `apps/live-control-ui/src/planSurface/projection/projectionContext.tsx`                                 | Own current route-local registrations and expose typed registration/read APIs      |
| Modify | `apps/live-control-ui/src/planSurface/projection/projectionRegistry.tsx`                                | Pass explicit registered dependencies to projected renderers                       |
| Modify | `apps/live-control-ui/src/planSurface/projection/AdaptiveProjectionContainer.tsx`                       | Select and pass current binding payloads; no ownership or layout move              |
| Modify | `apps/live-control-ui/src/planSurface/projection/AdaptiveProjectionContainer.test.tsx`                  | Preserve existing behavior and add missing-binding proof                           |
| Create | `apps/live-control-ui/src/planSurface/projection/projectionBindings.test.tsx`                           | Prove binder/renderer sibling topology and replacement/cleanup behavior            |
| Modify | `apps/live-control-ui/src/planSurface/PlanSurfaceShell.tsx`                                             | Mount the Plan projection binding inside the current resolver providers            |
| Create | `apps/live-control-ui/src/planSurface/reference/PlanReferenceProjectionBinding.tsx`                     | Adapt route-local Plan resolver/projection actions into the typed binding          |
| Modify | `apps/live-control-ui/src/planSurface/reference/PlanReferenceObjectCard.tsx`                            | Remove resolver/projection hook reads and accept explicit props                    |
| Create | `apps/live-control-ui/src/planSurface/reference/PlanReferenceObjectCard.test.tsx`                       | Prove rendering and interactions without resolver/projection provider ancestry     |
| Create | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewDiagnosticsProjectionBinding.tsx` | Adapt live Graph Review state into a typed diagnostics payload                     |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewDiagnosticsToolPanel.tsx`         | Replace live-state hook consumption with explicit typed props                      |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.tsx`              | Mount the diagnostics binding under the current live-state provider                |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.test.tsx`         | Prove diagnostics behavior through the owning workbench boundary                   |
| Create | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewDiagnosticsToolPanel.test.tsx`    | Prove the pure diagnostics renderer and missing-data behavior                      |

### Bounded discovery exception

```text
Directory:
- apps/live-control-ui/src/planSurface/projection/
- apps/live-control-ui/src/planSurface/reference/
- apps/live-control-ui/src/planSurface/graphReviewWorkbench/

Maximum additional paths:
2

Allowed path kinds:
- focused TypeScript type module required to break a circular type dependency;
- existing focused test file that already owns one of the §4 observable paths.

Decision rule:
The path must be necessary to compile or prove the invariant and must not add a new
surface, capability, persistent state, API request, or product interaction.

Required report:
Record the path, why the declared allowlist was insufficient, and why the addition
does not belong to R10a, MC-02a, MC-02b, or BLD inspection truth.
```

If any other path is required, stop and report before changing it.

---

## §6 Files and capabilities explicitly out of scope

| Path, ownership layer, or capability                                  | Why this slice must not touch or claim it                                      |
| --------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| `apps/live-control-ui/src/App.tsx`                                    | App-level ownership belongs to R10a                                            |
| `apps/live-control-ui/src/agentInteraction/**`                        | Absorbing projection ownership into `AgentInteractionProvider` is R10a         |
| `apps/live-control-ui/src/buildSurface/**`                            | Build graph-reference enablement is MC-02b                                     |
| `apps/live-control-ui/src/markdownCanvas/**`                          | Canvas authority is unrelated and must remain unchanged                        |
| `apps/live-control-ui/src/planSurface/config/**`                      | Build-capable `SurfaceConfig` and surface publication are R10a/MC-02b          |
| `apps/live-control-ui/src/planSurface/types.ts` except by stop report | Broad `SurfaceConfig` generalization is not required for dependency extraction |
| `apps/live-control-ui/src/graphObjectCard/**`                         | Shared card extraction already exists; no new card redesign                    |
| Backend routes, extraction, review-package, or promotion code         | BLD inspection truth and Graph Review authority are separate capabilities      |
| `localStorage`, URL persistence, thread persistence                   | R10b or existing owners                                                        |
| Bottom Agent Interaction Bar/Pane                                     | R10b                                                                           |
| World Graph matching, alias resolution, merge, identity decisions     | Kernel/Graph Review ownership                                                  |
| Existing-object search or Markdown insertion                          | MC-02a/MC-02b                                                                  |
| Node authoring or create-from-highlight                               | MC-03                                                                          |
| Closing, updating, or rebasing PRs #430–#433                          | Repository-management action outside this implementation capability            |

Do not introduce:

* a second projection registry;
* a second provider;
* a second container;
* raw `ReactNode` values as stored projection payloads;
* `unknown` payloads cast at render time;
* global mutable registries outside React ownership;
* new persistent projection data;
* new user-visible controls.

---

## §7 Implementation contract

### §7.1 Selected mechanism: typed registered dependencies

Use typed, in-memory **registered projection bindings**.

Do not store rendered React elements or component factories as the dependency contract.

The exact names may change when implementation requires clearer vocabulary, but the contract must preserve this shape:

```ts
interface PlanReferenceProjectionBinding {
  resolverState: PlanGraphProjectionState | null;

  resolveRelationship(
    relationship: GraphObjectRelationshipViewModel,
  ): Promise<PlanReferenceResolution>;

  openResolvedReference(
    resolution: PlanReferenceResolution,
    projectionState?: PlanGraphProjectionState | null,
  ): void;

  openTool(toolId: string): void;
}

type GraphReviewDiagnosticsProjectionPayload = Pick<
  GraphReviewLiveStateContextValue,
  | "campaignId"
  | "sessionId"
  | "liveRun"
  | "projection"
  | "projectionStatus"
  | "compareStatus"
  | "compare"
  | "compareError"
  | "selection"
  | "onSelectSelection"
  | "deltaIndex"
  | "sourceSpanDeltaIndex"
  | "selectedDeltaNodeId"
  | "setSelectedEvidenceDeltaId"
  | "selectedEvidenceDeltaId"
  | "selectedSourceSpanId"
  | "setSelectedSourceSpanId"
  | "evidenceSelection"
  | "evidenceDiff"
  | "evidenceStatus"
  | "evidenceError"
  | "manualBeds"
  | "manualBedsStatus"
  | "manualBedsError"
  | "selectedManualBed"
  | "selectedVariantLaneView"
  | "selectedManualVariant"
  | "onSelectManualBedId"
  | "onSelectManualVariantName"
  | "variantInventoryIndex"
  | "selectedVariantInventoryRowId"
  | "setSelectedVariantInventoryRowId"
  | "selectedVariantInventoryRow"
>;
```

The actual `Pick` list must match the fields consumed by `GraphReviewDiagnosticsToolPanel` at the base revision. Do not publish the entire live-state context merely because it is convenient.

The projection context exposes typed registration methods conceptually equivalent to:

```ts
registerPlanReferenceBinding(
  binding: PlanReferenceProjectionBinding,
): () => void;

registerToolProjectionPayload(
  toolId: "graph-review-diagnostics",
  payload: GraphReviewDiagnosticsProjectionPayload,
): () => void;
```

A generic implementation is acceptable only when its key-to-payload map remains statically typed. No `Record<string, unknown>` plus render-time casts.

### §7.2 Registration lifetime

Registration is in-memory and scoped to the current `ProjectionProvider`.

Each registration returns cleanup tied to that exact registration instance.

Required behavior:

```text
register A
register B for the same binding key
cleanup A
→ B remains registered

cleanup B
→ binding becomes absent
```

This is adapter-lifetime safety, not the full surface-registration identity contract assigned to R10a.

Do not add app-route identity, surface binding, or cross-route persistence here.

### §7.3 Plan binding

`PlanReferenceProjectionBinding` is mounted within the existing:

```text
PlanGraphLensProvider
  PlanGraphReferenceResolverProvider
```

It may call:

* `usePlanGraphReferenceResolver`;
* `useProjection`.

It registers explicit operations and current resolver state upward into the current route-local `ProjectionProvider`.

`PlanReferenceObjectCard` must no longer import or call:

* `usePlanGraphReferenceResolver`;
* `useOptionalProjection`;
* `useProjection`.

The card receives:

* `resolution`;
* `projectionState`;
* `sessionDescriptor`;
* `glanceOnly`;
* optional `PlanReferenceProjectionBinding`.

The card may retain local interaction state such as `navigatingRelationshipId`.

Relationship traversal:

1. operator selects one relationship;
2. card calls `binding.resolveRelationship(relationship)`;
3. card awaits the exact returned resolution;
4. card calls `binding.openResolvedReference(...)`;
5. errors clear the local navigating state;
6. no candidate is silently selected by label or rank.

Statblock action:

```text
binding present → binding.openTool("statblock")
binding absent → action omitted or disabled
```

The card must not fabricate a fallback navigation path when the binding is absent.

### §7.4 Graph Review diagnostics binding

`GraphReviewDiagnosticsProjectionBinding` is mounted inside the existing `GraphReviewLiveStateProvider`.

It may call `useGraphReviewLiveState()`.

It publishes only the fields and actions consumed by the diagnostics projection.

`GraphReviewDiagnosticsToolPanel` becomes a pure renderer receiving:

```ts
interface GraphReviewDiagnosticsToolPanelProps {
  payload: GraphReviewDiagnosticsProjectionPayload | null;
}
```

It must no longer import or call `useGraphReviewLiveState`.

When the payload is absent, render a stable, truthful unavailable state such as:

```text
Graph Review diagnostics are unavailable for the current projection surface.
```

Do not:

* throw;
* display stale payload from a previous registration;
* silently load another run;
* infer campaign/session state;
* change Graph Review selection or load policy.

When the live state changes, the registered payload updates and an already-open diagnostics projection rerenders from that latest payload.

### §7.5 Projection registry and container

`projectionRegistry` remains the one registry.

It must accept explicit dependencies for the two affected projections:

```text
content: Plan reference
  → PlanReferenceObjectCard(..., planReferenceBinding)

tool: graph-review-diagnostics
  → GraphReviewDiagnosticsToolPanel(payload)
```

Other registered tools and content behavior remain unchanged.

`AdaptiveProjectionContainer` remains mounted where it is today in production.

This slice must not:

* lift it into `App`;
* render a second container;
* retain one hidden container while adding another;
* change its drawer layout;
* change URL tool selection;
* change body classes;
* change open/close behavior.

### §7.6 No durable state

Projection bindings contain runtime data and callbacks.

They are not:

* serializable;
* persisted;
* copied into `localStorage`;
* included in URL state;
* added to Agent Interaction thread storage;
* treated as graph or document authority.

No raw corpus content should be copied into a new durable store.

---

## §8 State and fallback matrix

| Observable path             | Loading/initializing                                              | Exact success                      | Ordinary miss                                     | Dependency unavailable                                | Integrity/contract failure                      | Stale/superseded                                           | Retry/replay                          |
| --------------------------- | ----------------------------------------------------------------- | ---------------------------------- | ------------------------------------------------- | ----------------------------------------------------- | ----------------------------------------------- | ---------------------------------------------------------- | ------------------------------------- |
| Plan graph-node card        | Existing resolution loading behavior                              | Render exact supplied graph object | Existing unresolved/fallback behavior             | Render content; omit/disable dependency-owned actions | Fail closed; do not fabricate navigation        | New registration replaces old                              | Current provider rerender republishes |
| Plan corpus fallback        | Existing projection-state note                                    | Render exact supplied fallback     | Existing unresolved state                         | Same static fallback; no relationship traversal       | Fail closed                                     | New registration replaces old                              | Reopen or republish                   |
| Plan relationship traversal | Disable while resolver loading or another relationship is pending | Open exact returned resolution     | Returned unresolved result is rendered truthfully | Action unavailable                                    | Clear pending state; do not open another object | Completion may act only through current registered binding | Operator may retry after failure      |
| Plan statblock action       | Not applicable                                                    | Open registered `statblock` tool   | Tool missing follows existing `openTool` no-op    | Omit/disable action                                   | No alternate tool                               | Uses current binding only                                  | Operator may retry                    |
| Graph Review diagnostics    | Existing projection-status loading UI                             | Render latest registered payload   | Existing “select a live run” state                | Render explicit unavailable state                     | Fail closed; no stale run fallback              | Replacement payload wins; old cleanup cannot clear it      | Provider update republishes           |
| Diagnostics selection       | Existing action-specific loading states                           | Invoke supplied exact callback     | Existing empty-selection behavior                 | Controls unavailable with payload absent              | Do not infer or mutate hidden state             | Callback belongs to current payload                        | Existing retry behavior               |
| Projection close/replace    | Not applicable                                                    | Existing close behavior            | Not applicable                                    | Binding may remain registered while route is mounted  | No crash                                        | Active projection changes independently                    | Reopen uses current binding           |

Rules:

* Corpus fallback remains a reference-resolution policy owned by existing Plan behavior. This slice does not broaden it.
* Missing runtime binding is not equivalent to an unresolved graph reference.
* Integrity failure must never silently choose a node, run, session, or tool.
* There is no “latest run” or “first matching node” fallback in this slice.

---

## §9 Identity matrix

| Situation              | Matching rule                                               | Ambiguity behavior                                   | Fallback permitted?                                 | Persistence consequence |
| ---------------------- | ----------------------------------------------------------- | ---------------------------------------------------- | --------------------------------------------------- | ----------------------- |
| Projection binding key | Exact statically declared key                               | Duplicate registration replaces current value        | No label matching                                   | None; in-memory only    |
| Registration cleanup   | Exact registration instance/token                           | Cleanup may remove only its own current registration | No                                                  | None                    |
| Tool payload           | Exact tool ID `graph-review-diagnostics`                    | Unknown tool IDs follow existing registry behavior   | No inferred tool                                    | None                    |
| Graph node ID          | Existing `PlanReferenceResolution` contract                 | Existing ambiguous state remains ambiguous           | Existing corpus fallback only where already allowed | Unchanged               |
| Relationship target    | Exact result returned by current Plan relationship resolver | Resolver ambiguity remains unresolved                | No first-ranked selection                           | Unchanged               |
| Campaign/session/run   | Exact Graph Review live-state payload                       | No inference in diagnostics renderer                 | No latest-run fallback                              | Unchanged               |
| Surface identity       | Not introduced here                                         | R10a owns this contract                              | No                                                  | Not applicable          |

This slice must not alter graph identity, aliases, normalized matching, rename behavior, deletion behavior, or rebinding semantics.

---

## §10 Persistence and replay matrix

```text
Not applicable — all new bindings are typed in-memory React state scoped to the
current route-local ProjectionProvider. This slice introduces no durable format,
identifier, URL state, localStorage state, migration, or replay contract.
```

A proposal to persist these bindings is a stop condition and belongs to R10b or another explicitly authorized successor.

---

## §11 Predecessor-to-consumer mapping

**Grounding source**

```text
Current TypeScript types and component behavior at
f9a7be22d8752830a26babb63488f167579cea66.
```

| Predecessor field or outcome                              | Current shape                                  | Consumer field or behavior                | Transformation                            | Required proof                      |
| --------------------------------------------------------- | ---------------------------------------------- | ----------------------------------------- | ----------------------------------------- | ----------------------------------- |
| `usePlanGraphReferenceResolver().resolvePlanRelationship` | Async relationship → `PlanReferenceResolution` | `binding.resolveRelationship`             | Direct adapter; no semantic change        | Relationship integration test       |
| Resolver `projectionState`                                | `PlanGraphProjectionState`                     | `binding.resolverState`                   | Direct                                    | Loading/error disabled-state test   |
| `projection.openPlanReferenceResolution`                  | Opens supplied resolution                      | `binding.openResolvedReference`           | Direct adapter                            | Exact returned resolution assertion |
| `projection.openTool`                                     | Tool ID → active tool                          | `binding.openTool`                        | Direct adapter                            | Statblock action test               |
| `projection.active.glanceOnly`                            | Optional boolean on active content projection  | Explicit `glanceOnly` renderer prop       | Read in registry/container, pass as value | Compact/expanded card test          |
| `useGraphReviewLiveState()` consumed fields               | `GraphReviewLiveStateContextValue`             | `GraphReviewDiagnosticsProjectionPayload` | Exact typed `Pick`                        | Typecheck plus diagnostics tests    |
| Graph Review selection setters                            | Function fields                                | Payload actions                           | Direct                                    | Interaction assertions              |
| Missing Plan binding                                      | Previously impossible under valid ancestry     | Optional binding                          | Render content, fail closed on actions    | No-provider renderer test           |
| Missing diagnostics payload                               | Previously hook error under broken ancestry    | `payload: null`                           | Stable unavailable rendering              | Container/renderer test             |

Do not invent substitute fixture shapes. Tests must use current canonical TypeScript types or builders already used by repository tests.

---

## §12 Required tests

### §12.1 Plan renderer tests

Prove `PlanReferenceObjectCard` without resolver or projection provider ancestry:

1. resolved graph object renders through `GraphObjectCard`;
2. corpus fallback renders its existing banner and card;
3. unresolved reference renders existing correction state;
4. ambiguous resolution does not auto-open any node;
5. relationship selection calls the supplied binding exactly once;
6. the exact resolution returned by `resolveRelationship` is passed to `openResolvedReference`;
7. resolver loading/error disables relationship traversal consistently with existing behavior;
8. pending relationship state clears after success and rejection;
9. statblock action invokes `openTool("statblock")`;
10. missing binding does not throw and does not expose an action that cannot work.

### §12.2 Graph Review diagnostics tests

Prove `GraphReviewDiagnosticsToolPanel` without `GraphReviewLiveStateProvider` ancestry:

1. a supplied ready payload renders the same diagnostics sections;
2. payload callbacks receive the existing selection values;
3. loading and empty states remain truthful;
4. absent payload renders the explicit unavailable state;
5. payload replacement updates an already-open diagnostics projection;
6. stale cleanup does not remove a newer registration;
7. no latest run, campaign, or session is inferred by the renderer.

### §12.3 Owning-boundary topology tests

Create a focused harness equivalent to:

```tsx
<ProjectionProvider config={config}>
  <PlanGraphLensProvider>
    <PlanGraphReferenceResolverProvider>
      <PlanReferenceProjectionBinding />
    </PlanGraphReferenceResolverProvider>
  </PlanGraphLensProvider>

  <AdaptiveProjectionContainer config={config} />
</ProjectionProvider>
```

The container is a **sibling**, not a descendant, of the resolver providers.

Create the equivalent Graph Review harness:

```tsx
<ProjectionProvider config={config}>
  <GraphReviewLiveStateProvider {...props}>
    <GraphReviewDiagnosticsProjectionBinding />
  </GraphReviewLiveStateProvider>

  <AdaptiveProjectionContainer config={config} />
</ProjectionProvider>
```

Required result:

* Plan content projection renders and relationship traversal works;
* Graph Review diagnostics projection renders and actions work;
* no projected renderer relies on provider ancestry;
* production ownership remains unchanged.

### §12.4 Source guards

Tests or explicit verification must prove:

```text
PlanReferenceObjectCard.tsx
  imports neither usePlanGraphReferenceResolver nor useProjection/useOptionalProjection

GraphReviewDiagnosticsToolPanel.tsx
  does not import useGraphReviewLiveState

App.tsx
  unchanged

agentInteraction/
  unchanged

buildSurface/
  unchanged
```

---

## §13 Verification ownership map and commands

| Guarantee                                             | Owning boundary                           | Command/scenario               | Expected evidence                              |
| ----------------------------------------------------- | ----------------------------------------- | ------------------------------ | ---------------------------------------------- |
| Plan card is provider-ancestry independent            | Plan reference component                  | Focused card test              | All states and actions work from props         |
| Plan relationship traversal preserves semantics       | Plan binding + projection integration     | Binding harness test           | Exact resolver result is opened                |
| Diagnostics renderer is provider-ancestry independent | Diagnostics component                     | Focused diagnostics test       | Supplied payload renders and acts              |
| Registered payload reaches sibling container          | Projection provider/container integration | Projection binding test        | Renderer works outside route provider ancestry |
| New registration survives stale cleanup               | Projection context                        | Registration-order test        | Cleanup A does not remove B                    |
| Existing Plan projection behavior remains equivalent  | Plan shell/integration                    | Existing Plan projection tests | Existing assertions pass unchanged             |
| Existing Graph Review behavior remains equivalent     | Graph Review workbench                    | Existing workbench test        | Existing diagnostics/tool behavior passes      |
| No ownership lift occurred                            | Diff review/source guard                  | Name-only diff plus grep       | No App/Agent Interaction/Build changes         |
| Type contracts are coherent                           | TypeScript compiler                       | `npm run typecheck`            | Exit 0                                         |
| Production bundle still builds                        | Vite/TypeScript build                     | `npm run build`                | Exit 0                                         |

Run from `apps/live-control-ui`:

```bash
npm test -- \
  src/planSurface/projection/AdaptiveProjectionContainer.test.tsx \
  src/planSurface/projection/projectionBindings.test.tsx \
  src/planSurface/reference/PlanReferenceObjectCard.test.tsx \
  src/planSurface/graphReviewWorkbench/GraphReviewDiagnosticsToolPanel.test.tsx \
  src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.test.tsx

npm test -- src/planSurface/projection src/planSurface/reference

npm run typecheck
npm run build
```

Run from repository root:

```bash
! grep -n "usePlanGraphReferenceResolver\\|useOptionalProjection\\|useProjection" \
  apps/live-control-ui/src/planSurface/reference/PlanReferenceObjectCard.tsx

! grep -n "useGraphReviewLiveState" \
  apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewDiagnosticsToolPanel.tsx

git diff --check

git diff --stat \
  f9a7be22d8752830a26babb63488f167579cea66...HEAD -- \
  Docs/Plans/HANDOFF-r10a-deps-projection-host-dependency-extraction.md \
  Docs/Plans/PLAN-shared-markdown-canvas-build-first.md \
  apps/live-control-ui/src/planSurface/projection \
  apps/live-control-ui/src/planSurface/reference \
  apps/live-control-ui/src/planSurface/graphReviewWorkbench

git diff --name-only \
  f9a7be22d8752830a26babb63488f167579cea66...HEAD
```

### Minimal live proof

```text
Not required as an acceptance substitute — this slice intentionally changes no
operator-visible behavior. A brief Plan chip/relationship and Graph Review diagnostics
smoke test may supplement, but may not replace, the owning-boundary automated proofs.
```

### Baseline failure protocol

For any required command failing on the base:

1. run the exact same command on base and head;
2. record both results;
3. report whether the branch introduces new failures;
4. do not call the gate green without the required operator waiver.

---

## §14 Demolition declaration

This slice does not remove the route-local projection owner or container.

It demolishes these hidden renderer dependencies:

* `PlanReferenceObjectCard` reading Plan resolver context directly;
* `PlanReferenceObjectCard` reading projection context directly;
* `GraphReviewDiagnosticsToolPanel` reading Graph Review live-state context directly.

The replacement is:

* one typed Plan reference projection binding;
* one typed Graph Review diagnostics payload;
* registration owned by the existing route-local `ProjectionProvider`;
* explicit renderer props supplied by the existing registry/container.

Temporary compatibility shims are prohibited unless a stop report explains why the direct migration cannot land atomically.

PR #430 is superseded as an implementation path. This handoff does not close or modify it, but no code from its bare-lift approach is required for this capability.

---

## §15 Required implementation handback

The PR body or implementation handback must include:

1. Base SHA: `f9a7be22d8752830a26babb63488f167579cea66`.
2. Head SHA.
3. Actual changed paths.
4. Focused diff stat limited to §5 paths.
5. Every §13 command and exact result.
6. Result provenance:

   * author-local;
   * independently rerun local;
   * CI;
   * manual observation.
7. Baseline failure comparison, or `none`.
8. Operator waivers, or `none`.
9. Paths outside the allowlist, or `none`.
10. Bounded-discovery paths used and justification, or `none`.
11. Stop conditions encountered and resolution, or `none`.
12. Deviations from the state/identity/persistence contracts, or `none`.
13. Confirmation that:

    * production projection ownership remains route-local;
    * `AgentInteractionProvider` is unchanged;
    * Build is unchanged;
    * no second provider, registry, or container was created;
    * no persistent state was introduced;
    * MC-02a, MC-02b, R10a, R10b, and BLD inspection truth remain unclaimed.
14. Confirmation that PR #430 was not used as the implementation base.
15. Confirmation that this handoff was implemented without compression or omitted constraints.

---

## §16 Acceptance rubric

The reviewer accepts only when every item is true.

* [ ] Exactly one independently useful capability was delivered: route-provider ancestry is no longer required by the two projected renderers.
* [ ] `PlanReferenceObjectCard` consumes explicit props/binding and no longer calls Plan resolver or projection hooks.
* [ ] `GraphReviewDiagnosticsToolPanel` consumes an explicit payload and no longer calls `useGraphReviewLiveState`.
* [ ] Plan relationship navigation opens the exact resolution returned by the existing resolver.
* [ ] Ambiguous references remain ambiguous and never auto-pick a graph node.
* [ ] Graph Review diagnostics continues to render and mutate only the exact supplied live-state actions.
* [ ] Missing bindings fail closed with stable UI and no hook crash.
* [ ] A stale registration cleanup cannot erase a newer registration.
* [ ] Focused sibling-topology tests prove the container can render outside both route-local dependency-provider subtrees.
* [ ] Existing Plan and Graph Review behavior remains interaction-equivalent.
* [ ] `ProjectionProvider` and `AdaptiveProjectionContainer` remain route-local in production.
* [ ] `AgentInteractionProvider`, `App.tsx`, Build, Markdown Canvas, backend extraction, and Graph Review promotion code are unchanged.
* [ ] No new persistent or serializable projection state exists.
* [ ] No raw React elements, component factories, `unknown` payload casts, or global mutable registries were introduced.
* [ ] Only allowlisted or explicitly reported bounded-discovery paths changed.
* [ ] Typecheck and production build pass.
* [ ] Required tests pass at their owning boundaries.
* [ ] Baseline failures and evidence provenance are reported truthfully.
* [ ] R10a remains the next ownership-lift successor and is not claimed as delivered.
* [ ] MC-02a, MC-02b, R10b, and BLD inspection truth remain false.

---

## §17 Reviewer protocol

Review the invariant before individual files.

1. Confirm the base is exactly `f9a7be22d8752830a26babb63488f167579cea66`.
2. Confirm the branch is not stacked on PR #430.
3. Compare the actual diff with the §5 allowlist.
4. Verify no ownership movement occurred.
5. Inspect `PlanReferenceObjectCard` for hidden context reads.
6. Inspect `GraphReviewDiagnosticsToolPanel` for hidden context reads.
7. Inspect the binding API for static key-to-payload typing.
8. Reject `unknown` payloads, global registries, React element storage, or renderer closures that hide the dependency contract.
9. Verify registration cleanup cannot clear a newer value.
10. Exercise every Plan card state and relationship path.
11. Exercise Graph Review diagnostics loading, ready, selection, unavailable, and replacement states.
12. Confirm the sibling-topology harness actually places the container outside the route-local providers.
13. Run typecheck, build, focused tests, source guards, and diff checks.
14. Confirm successors remain deferred.

---

## §18 Re-review protocol

Begin from the prior finding ledger.

| Prior finding                                   | Claimed fix              | Owning files/tests      | Verified? | New consequence?   |
| ----------------------------------------------- | ------------------------ | ----------------------- | --------: | ------------------ |
| Projected renderer still calls route-local hook | Explicit binding/payload | Renderer + focused test |    Yes/No | Record consequence |
| Missing binding throws or shows stale data      | Stable unavailable state | Registry/container test |    Yes/No | Record consequence |
| Cleanup erases replacement registration         | Identity-safe cleanup    | Projection binding test |    Yes/No | Record consequence |
| R10a ownership work leaked into slice           | Reverted/out-of-scope    | Diff inspection         |    Yes/No | Record consequence |
| Build or Agent Interaction changed              | Reverted/out-of-scope    | Name-only diff          |    Yes/No | Record consequence |

Re-test the full invariant after every correction, not only the changed line.

---

## Stop conditions

Stop and report rather than expanding scope if implementation discovers:

* Plan reference rendering cannot be detached without designing the full neutral `GraphReferenceResolver` contract;
* Graph Review diagnostics cannot be represented without moving its live-state owner app-wide;
* `SurfaceConfig` must be broadly generalized before the binding can compile;
* `App.tsx` or `AgentInteractionProvider` must change;
* Build must publish projection state;
* a second container or provider appears necessary;
* a new persistent representation appears necessary;
* route/surface registration identity must be solved to make this slice useful;
* a new graph identity or fallback rule is required;
* another projected tool besides Graph Review diagnostics also depends on a route-local provider and must be migrated for the invariant to be truthful;
* more than two additional paths are required;
* PR #430 code has already been merged or materially changed the base topology;
* required tests fail on base and need an operator waiver.

Use this report:

```text
Stop condition:
Why the current mission cannot absorb it:
New contract discovered:
Affected observable paths:
Affected ownership layers:
Required path outside scope:
Proposed successor or revised predecessor:
Tracker/authority update needed:
Operator decision required:
```

The worker must not resolve a stop condition by silently broadening the mission.

---

## Final dispatch check

Before dispatch:

* [ ] PR #429 is present in the implementation base.
* [ ] Base SHA is exactly `f9a7be22d8752830a26babb63488f167579cea66`.
* [ ] The branch is not based on PR #430.
* [ ] This handoff is checked in at the canonical path.
* [ ] The active plan links this handoff and marks R10a-deps ACTIVE.
* [ ] §0 contains one selected capability.
* [ ] The invariant is reused consistently.
* [ ] Every observable path maps to an owning-boundary proof.
* [ ] Every expected path is allowlisted.
* [ ] The bounded discovery exception is limited to two paths.
* [ ] Missing-dependency behavior is explicit.
* [ ] Registration replacement/cleanup behavior is explicit.
* [ ] Persistence is explicitly prohibited.
* [ ] R10a, MC-02a, MC-02b, R10b, and BLD inspection truth remain named successors.
* [ ] Stop conditions are understood.
* [ ] The implementation agent receives this complete handoff without summarization.
