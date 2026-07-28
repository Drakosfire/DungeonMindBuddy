# HANDOFF — R10a app-scoped projection host lift

**Created:** 2026-07-27
**Status:** ACTIVE — dispatch exactly one implementation capability.
**Dispatch gate:** Cleared 2026-07-27 — PR #438 merged as `16f4210d85ba42a771e0c3d4a5adc9ec8f495676` (contains accepted head `a7dc6a1efa6fdbb1ea8d88e5d60164c1ed735063`).
**Canonical handoff path:** `Docs/Plans/HANDOFF-r10a-app-scoped-projection-host-lift.md`
**Implementation base:** `16f4210d85ba42a771e0c3d4a5adc9ec8f495676`
**Required predecessor head:** PR #438 head `a7dc6a1efa6fdbb1ea8d88e5d60164c1ed735063`, rebased or merged with current `main`
**Suggested branch:** `agent/r10a-app-scoped-projection-host`
**Suggested PR title:** `refactor(ui): lift projection host into AgentInteractionProvider`

---

## Dispatch gate

Cleared 2026-07-27:

* [x] PR #438 is merged (`16f4210d85ba42a771e0c3d4a5adc9ec8f495676`);
* [x] merge ancestry includes accepted R10a-deps head `a7dc6a1efa6fdbb1ea8d88e5d60164c1ed735063`;
* [x] implementation base replaced with that exact merge SHA;
* [x] implementation branch created from that SHA (`agent/r10a-app-scoped-projection-host`);
* [x] PR #430 is not used as an implementation base;
* [x] current `main` still owns projection via route-local `ProjectionProvider` / `AdaptiveProjectionContainer` (predecessor topology intact; no conflicting app-level host).

Merged shape matches accepted head; no re-audit stop triggered.

---

## §0 Capability decomposition decision

| Candidate outcome                                                                                                                                    |                                 Independently useful? | Public or durable contract changed? | Operator surface changed? |                  Failure model changed? | Independently testable or revertible? | Decision                                   |
| ---------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------: | ----------------------------------: | ------------------------: | --------------------------------------: | ------------------------------------: | ------------------------------------------ |
| Move selected-projection state, projection registrations, and the singular adaptive container into the existing app-level `AgentInteractionProvider` |                                                   Yes |     Internal typed runtime contract | No intended visual change |                                     Yes |                                   Yes | **Include**                                |
| Add exact, nullable, tokenized surface publication for Plan, Ingest, Build, and inactive routes                                                      | Yes, but required to make the ownership lift truthful |     Internal typed runtime contract |                        No |                                     Yes |                                   Yes | **Include — same invariant**               |
| Remove production route-local `ProjectionProvider` and `AdaptiveProjectionContainer` ownership                                                       |            No useful outcome separately from the lift |                                  No |                        No |                                     Yes |                                   Yes | **Include — same invariant**               |
| Preserve Plan and Ingest projection interactions through the R10a-deps adapters                                                                      |        No separate capability; required compatibility |                                  No |                        No |                                     Yes |                                   Yes | **Include — proof of the lift**            |
| Let Build publish an empty-tools, no-content surface binding                                                                                         |                       No separate operator capability |           Internal runtime contract |                        No |                                     Yes |                                   Yes | **Include — inactive-host truth**          |
| Finish neutral `reference_render`, `reference_insert_existing`, and `reference_project` capability extraction                                        |                                                   Yes |                                 Yes |        No intended change |                                     Yes |                                   Yes | **Successor: MC-02a**                      |
| Enable Build reference chips, search, insertion, or graph-object glance                                                                              |                                                   Yes |                                 Yes |                       Yes |                                     Yes |                                   Yes | **Successor: MC-02b**                      |
| Replace the current right-side drawer with the bottom Agent Interaction pane                                                                         |                                                   Yes |                                 Yes |                       Yes |                                     Yes |                                   Yes | **Successor: R10b**                        |
| Persist selected projection, pane state, recent runs, or notifications                                                                               |                                                   Yes |                Yes, durable storage |               Potentially |                                     Yes |                                   Yes | **Successor: R10b / localStorage Phase A** |
| Move or redesign `PlanAgentInteractionBar`                                                                                                           |                                                   Yes |                                 Yes |                       Yes |                                     Yes |                                   Yes | **Successor: R10b**                        |
| Rewrite hard navigation into an SPA router                                                                                                           |                                                   Yes |                                 Yes |                       Yes |                                     Yes |                                   Yes | **Reject / separate routing capability**   |
| Reuse PR #430 as the implementation                                                                                                                  |                                                    No |    Conflicts with current authority |                        No | Preserves obsolete ancestry assumptions |                                    No | **Reject**                                 |

**Selected capability**

Plan and Ingest consume one projection host owned by the existing app-level `AgentInteractionProvider`, while each route publishes an exact transient surface binding and Build truthfully publishes no enabled projections.

**Why the included work shares one invariant**

Moving state without moving the container leaves multiple hosts. Moving the container without tokenized nullable surface publication lets it act through stale route configuration. Removing local providers without preserving R10a-deps registrations breaks Plan and Graph Review. These changes establish one runtime ownership invariant and are not independently useful in partial form.

**Named successors**

* MC-02a — remaining neutral graph-reference capability extraction;
* MC-02b — Build enables shared existing-object reference capabilities;
* R10b — bottom Agent Interaction pane and bounded localStorage Phase A;
* BLD inspection truth and Stay-on-Build work remain their independent lane.

---

## §1 Mission

Plan and Ingest can use one app-scoped projection host owned by `AgentInteractionProvider`, so projection state is singular and surface changes cannot render or mutate through stale route configuration.

### Invariant

```text
At runtime there is exactly one selected-projection owner and exactly one
AdaptiveProjectionContainer under AgentInteractionProvider.

Every projection render, mutation, dependency registration, and cleanup is
authorized by the exact currently published surface lease.

No route owns a private ProjectionProvider or private adaptive container.
```

### Mission falsification test

```text
This is not one slice if implementation must also:

- enable any new Build graph-reference interaction;
- finish the neutral reference capability API;
- replace the drawer with the bottom Agent Interaction pane;
- persist projection state;
- migrate PlanAgentInteractionBar into app chrome;
- redesign projection chrome or tool navigation;
- change Graph Review authority, dispositions, or exact-run policy;
- rewrite the route system;
- change graph identity, reference matching, or corpus fallback policy.
```

---

## §2 Context, authority, and boundaries

| Field                         | Required content                                                                                                                                       |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Parent authority              | `Docs/Design/ARCHITECTURE-plan-surface-toolbox.md`                                                                                                     |
| Active sequencing authority   | `Docs/Plans/PLAN-shared-markdown-canvas-build-first.md`                                                                                                |
| Active shared-canvas design   | `Docs/Design/DESIGN-shared-markdown-canvas-surface-composition.md`                                                                                     |
| Repository rules              | `AGENTS.md`; `.cursor/rules/external-agent-pr-loop.mdc`; `.cursor/skills/external-agent-pr-loop/SKILL.md`                                              |
| Base revision                 | `16f4210d85ba42a771e0c3d4a5adc9ec8f495676` (merge of PR #438 onto main)                                                                                                                  |
| Predecessor contract          | R10a-deps typed Plan reference binding, Graph Review diagnostics payload, exact-registration cleanup, and renderer independence                        |
| Existing app host             | `AgentInteractionProvider`, already mounted above the route switch                                                                                     |
| Existing surface context seam | `publishSurfaceContext` and `rehydrateScope`; these remain separate from projection publication                                                        |
| Exact inputs consumed         | `SurfaceConfig`, `ActiveProjection`, R10a-deps projection bindings, configured tool IDs, Plan reference resolutions, Graph Review diagnostics payloads |
| Named successor               | MC-02a                                                                                                                                                 |
| What remains false            | Build cannot search, insert, render, or open graph references; bottom pane and projection persistence do not exist                                     |
| Explicit non-goals            | Reference capability redesign, Build enablement, routing rewrite, Agent Interaction UI migration, Graph Review policy, backend work                    |

### Authority precedence

```text
1. Docs/Design/ARCHITECTURE-plan-surface-toolbox.md
2. Docs/Plans/PLAN-shared-markdown-canvas-build-first.md
3. Docs/Design/DESIGN-shared-markdown-canvas-surface-composition.md
4. The checked-in R10a-deps handoff and merged implementation
5. This checked-in R10a handoff
6. Current implementation and owning-boundary tests at the declared base
7. Open implementation PRs used only as reconnaissance
8. Attached project sources and chat summaries
```

### Read authoritative inputs in this order

1. `Docs/Design/ARCHITECTURE-plan-surface-toolbox.md`
2. `Docs/Plans/PLAN-shared-markdown-canvas-build-first.md`
3. `Docs/Design/DESIGN-shared-markdown-canvas-surface-composition.md`
4. `Docs/Plans/HANDOFF-r10a-deps-projection-host-dependency-extraction.md`
5. `apps/live-control-ui/src/App.tsx`
6. `apps/live-control-ui/src/agentInteraction/AgentInteractionProvider.tsx`
7. `apps/live-control-ui/src/agentInteraction/agentInteractionTypes.ts`
8. `apps/live-control-ui/src/planSurface/projection/projectionContext.tsx`
9. `apps/live-control-ui/src/planSurface/projection/AdaptiveProjectionContainer.tsx`
10. `apps/live-control-ui/src/planSurface/projection/projectionRegistry.tsx`
11. `apps/live-control-ui/src/planSurface/PlanSurfaceShell.tsx`
12. `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.tsx`
13. `apps/live-control-ui/src/buildSurface/BuildSurfacePage.tsx`
14. Existing Agent Interaction, projection, Plan, Graph Review, Build, and App integration tests
15. Repository implementation and review-loop rules

### Existing ambient-context boundary

The existing Agent Interaction surface context and thread scope are not the projection binding:

```text
AgentInteractionSurfaceContext
  → ambient question/retrieval context and pointer-only continuity

ProjectionSurfacePublication
  → transient render/action authorization for the one projection host
```

Do not silently merge these contracts. Existing `publishSurfaceContext`, `rehydrateScope`, thread persistence, selected source behavior, and storage keys remain unchanged unless a compile-only adjustment is unavoidable.

### Stale PR warning

PR #430 is not a predecessor.

Its implementation:

* creates a separate app-level `ProjectionProvider`;
* keeps `AdaptiveProjectionContainer` route-local;
* depends on route-local context ancestry;
* uses an identity key without exact registration ownership;
* predates R10a-deps.

Rules:

* do not branch from PR #430;
* do not cherry-pick it;
* do not retain its sibling `ProjectionProvider`;
* do not retain route-local containers;
* do not copy its surface-key function without re-evaluating exact identity and cleanup;
* it may be inspected only as negative reconnaissance.

---

## §3 Current implementation seam

After R10a-deps, the expected predecessor topology is:

```text
App
  AgentInteractionProvider
    Route content

PlanSurfaceShell
  EditCapabilityProvider
    ProjectionProvider
      PlanGraphLensProvider
        PlanGraphReferenceResolverProvider
          PlanReferenceProjectionBinding
          Plan canvas
          AdaptiveProjectionContainer
          PlanAgentInteractionBar

GraphReviewWorkbenchModule
  ProjectionProvider
    GraphReviewLiveStateProvider
      GraphReviewDiagnosticsProjectionBinding
      Graph Review workbench
      AdaptiveProjectionContainer

BuildSurfacePage
  Build surface
  no ProjectionProvider
  no AdaptiveProjectionContainer
```

R10a-deps has already made projected Plan reference cards and Graph Review diagnostics render from explicit registered dependencies. R10a must now move their common owner without reversing that work.

`AgentInteractionProvider` already sits above route selection and already owns transient app-level interaction state plus surface-context publication. It is the required owner. This slice must not create another app-level provider beside it.

The current adaptive container still receives a non-null `SurfaceConfig` prop and assumes a Plan-shaped context. Its app-level form must instead read the current nullable surface publication from the provider.

Moving the container outside the Plan root also removes inherited Plan theme variables. The active publication must therefore carry the current theme, and the app-level container must apply those tokens and theme attributes itself.

The container also currently caches the latest ingested session in component state. Once singular across surfaces, that cache must be keyed or cleared by exact campaign/surface identity rather than reused across unrelated publications.

---

## §4 Observable-path inventory

| Observable path                                                        | Current behavior                                     | Required behavior                                                                                            | Same invariant? | Owning boundary                |
| ---------------------------------------------------------------------- | ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ | --------------: | ------------------------------ |
| App starts on a route with no projection surface                       | App-level provider exists but no app-level container | Host is inactive; no toggle, drawer, backdrop, or body-open class renders                                    |             Yes | Agent Interaction host         |
| Plan loads its document/config                                         | Route-local provider and container mount             | Plan publishes one exact surface lease into the app host                                                     |             Yes | Plan publication integration   |
| Open Plan Recap, Party Registry, or Statblock                          | Local provider closes over Plan config               | App host validates exact enabled tool ID and opens equivalent drawer                                         |             Yes | Provider + container           |
| Open a Plan graph-reference chip                                       | Local state opens content projection                 | App host opens the exact supplied resolution under the current Plan lease                                    |             Yes | Plan canvas + provider         |
| Expand a compact Plan reference                                        | Local container changes size                         | Singular container expands the current lease-owned content                                                   |             Yes | Provider + container           |
| Traverse a Plan graph relationship                                     | R10a-deps binding resolves and opens                 | Same exact returned resolution opens only if Plan surface and binding leases remain current                  |             Yes | Binding + provider             |
| Async chip resolution completes after leaving Plan                     | Could become dangerous only after global lift        | Completion is ignored; it cannot open on Build or Ingest                                                     |             Yes | Provider surface-lease gate    |
| Open Plan statblock action from projected card                         | R10a-deps binding calls `openTool`                   | Opens only if current Plan publication still enables `statblock`                                             |             Yes | Provider                       |
| Ingest landing finishes loading                                        | Route-local provider/container mount                 | Ingest publishes one exact app-host lease                                                                    |             Yes | Graph Review integration       |
| Open Ingest Recap from empty Graph Review state                        | Local toolbox remains reachable                      | Existing behavior remains available through app host                                                         |             Yes | Graph Review + container       |
| Open Graph Review diagnostics                                          | Local container consumes registered payload          | App host renders latest current-lease diagnostics payload                                                    |             Yes | Diagnostics binding + provider |
| Change Graph Review diagnostics selection                              | Payload callbacks mutate live state                  | Existing callbacks remain interaction-equivalent                                                             |             Yes | Diagnostics renderer           |
| Navigate Plan → Build with projection open                             | Provider is normally destroyed by hard navigation    | In an in-memory route transition, Plan lease is invalidated synchronously; no stale frame or action survives |             Yes | Agent Interaction provider     |
| Build new-source route                                                 | No projection binding                                | Build publishes an empty-tools, null-context lease; no projection UI appears                                 |             Yes | Build publication              |
| Build loaded document                                                  | No projection binding                                | Build publishes an exact document-scoped empty-tools lease                                                   |             Yes | Build publication              |
| Navigate Build → Ingest                                                | New local provider mounts                            | Build cleanup cannot erase the newer Ingest lease; Ingest tools work                                         |             Yes | Registration identity          |
| Surface republishes same identity with changed label/theme/tool config | Local provider is recreated or rerendered            | Latest config wins; active projection is preserved only if still valid                                       |             Yes | Provider revalidation          |
| Current tool is removed from same surface identity                     | Not a normal current path                            | Active tool clears rather than rendering an unavailable/stale tool                                           |             Yes | Provider revalidation          |
| Current surface unmounts with no replacement                           | Local provider disappears                            | Host becomes inactive and clears selected projection and surface-scoped dependencies                         |             Yes | Provider cleanup               |
| Late cleanup from old surface                                          | Previously isolated by provider destruction          | Cleanup may remove only its exact registration and never the newer lease                                     |             Yes | Provider                       |
| Stale callback invokes `openTool`, `openContent`, `expand`, or `close` | Previously route-local                               | Mutation is ignored unless its captured surface lease is current                                             |             Yes | Provider                       |
| URL requests an enabled tool                                           | Each local container reads URL                       | Singular container opens it for the current surface only                                                     |             Yes | Container                      |
| URL requests an unavailable tool                                       | Existing `openTool` no-ops                           | Remains a no-op; no tool is inferred or substituted                                                          |             Yes | Provider                       |
| Campaign changes while singular container remains mounted              | Previously remounted container resets cache          | Session lookup cache resets or is keyed by campaign identity                                                 |             Yes | Container                      |
| Active surface theme changes                                           | Container inherited route-local CSS variables        | App-level container applies the published theme tokens directly                                              |             Yes | Container                      |
| Malformed surface publication has tools but no required render context | Previously impossible by type                        | New surface supersedes old one, but projections fail closed and no stale config is used                      |             Yes | Publication validation         |
| Projection close, Escape, or backdrop click                            | Local container closes local state                   | Same interaction closes only the current surface-owned projection                                            |             Yes | Container + provider           |

Every row belongs to the singular-host invariant. A newly discovered interaction not covered here is a scope-review trigger.

---

## §5 Files in scope — allowlist

Every changed path must appear below or satisfy the bounded discovery exception.

| Action           | Path                                                                                                | Purpose                                                                                                               |
| ---------------- | --------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| Create           | `Docs/Plans/HANDOFF-r10a-app-scoped-projection-host-lift.md`                                        | Check in this complete implementation authority                                                                       |
| Modify           | `Docs/Plans/PLAN-shared-markdown-canvas-build-first.md`                                             | Mark R10a-deps DONE and R10a ACTIVE; link this handoff without redesigning other lanes                                |
| Modify           | `apps/live-control-ui/src/App.tsx`                                                                  | Host exactly one `AdaptiveProjectionContainer` as a direct child of `AgentInteractionProvider`, outside route content |
| Modify           | `apps/live-control-ui/src/App.test.tsx`                                                             | Prove one app-level container and route publication behavior                                                          |
| Modify           | `apps/live-control-ui/src/agentInteraction/AgentInteractionProvider.tsx`                            | Absorb projection state, exact surface lease, dependency registrations, validation, and actions                       |
| Modify           | `apps/live-control-ui/src/agentInteraction/AgentInteractionProvider.test.tsx`                       | Prove ownership, replacement, cleanup, stale action rejection, and no persistence                                     |
| Modify           | `apps/live-control-ui/src/agentInteraction/agentInteractionTypes.ts`                                | Declare typed transient projection-host state/actions without altering stored thread schemas                          |
| Create           | `apps/live-control-ui/src/agentInteraction/projectionSurfacePublication.ts`                         | Define exact nullable surface publication and stable identity helpers                                                 |
| Create           | `apps/live-control-ui/src/agentInteraction/projectionSurfacePublication.test.ts`                    | Prove identity construction and validation without labels or first-win behavior                                       |
| Modify           | `apps/live-control-ui/src/planSurface/types.ts`                                                     | Permit host-facing Build/null context while preserving non-null Plan/Ingest consumer types                            |
| Modify           | `apps/live-control-ui/src/planSurface/projection/projectionContext.tsx`                             | Remove the standalone provider; retain a thin hook/helper facade over Agent Interaction ownership                     |
| Modify           | `apps/live-control-ui/src/planSurface/projection/projectionContext.test.tsx`                        | Prove hook compatibility and absence of a second owner                                                                |
| Modify           | `apps/live-control-ui/src/planSurface/projection/AdaptiveProjectionContainer.tsx`                   | Read current publication from host, render nothing when inactive, apply theme, and reset keyed cache                  |
| Modify           | `apps/live-control-ui/src/planSurface/projection/AdaptiveProjectionContainer.test.tsx`              | Prove inactive, empty-tools, URL, theme, cache, and existing chrome paths                                             |
| Modify           | `apps/live-control-ui/src/planSurface/projection/projectionBindings.test.tsx`                       | Rebase R10a-deps sibling/adaptor proofs onto `AgentInteractionProvider`                                               |
| Create           | `apps/live-control-ui/src/planSurface/projection/projectionTestHost.tsx`                            | Provide a test-only app-host publisher without recreating a production projection owner                             |
| Modify           | `apps/live-control-ui/src/planSurface/PlanSurfaceShell.tsx`                                         | Publish Plan config; remove local provider/container                                                                  |
| Modify           | `apps/live-control-ui/src/planSurface/PlanSurfaceShell.test.tsx`                                    | Prove Plan publication and interaction-equivalent ownership                                                           |
| Modify           | `apps/live-control-ui/src/planSurface/components/PlanSurfaceCanvas.tsx`                             | Only if required to bind async chip opens to the captured surface lease                                               |
| Modify           | `apps/live-control-ui/src/planSurface/reference/PlanReferenceObjectCard.test.tsx`                   | Replace test-only local provider wrappers with app host                                                               |
| Modify           | `apps/live-control-ui/src/planSurface/reference/PlanReferenceProjectionBinding.tsx`                 | Keep the production Plan adapter under resolver ancestry while consuming the app-owned projection facade             |
| Modify           | `apps/live-control-ui/src/planSurface/dogfood/GraphObjectDogfoodPanel.test.tsx`                     | Replace test-only local provider wrapper if present at base                                                           |
| Modify           | `apps/live-control-ui/src/planSurface/selectedObject/SelectedObjectCard.test.tsx`                   | Replace test-only local provider wrapper if present at base                                                           |
| Modify           | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.tsx`          | Publish Ingest config; remove local provider/container                                                                |
| Modify           | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.test.tsx`     | Prove Ingest behavior through the app host                                                                            |
| Modify           | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewDiagnosticsProjectionBinding.tsx` | Keep diagnostics payload registration surface-scoped and stable across app-host rerenders                          |
| Modify           | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphReviewLiveStateTestHarness.tsx`     | Replace shared test harness ownership where required                                                                  |
| Modify           | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewExtractPromoteSheet.test.tsx` | Replace test-only provider wrapper if present at base                                                                 |
| Modify           | `apps/live-control-ui/src/buildSurface/BuildSurfacePage.tsx`                                        | Publish Build’s exact empty-tools lease for both new and loaded documents                                             |
| Create or modify | `apps/live-control-ui/src/buildSurface/BuildSurfacePage.test.tsx`                                   | Prove Build publishes no projection capability and clears stale surface state                                         |
| Modify           | `apps/live-control-ui/src/buildSurface/buildSurfaceConfig.ts`                                       | Define the minimal Build host publication without Plan context                                                        |
| Modify           | `apps/live-control-ui/src/planSurface/planSurface.css`                                              | Only if DOM relocation requires a narrowly scoped style fix preserving current drawer chrome                          |

### Bounded discovery exception

```text
Directories:
- apps/live-control-ui/src/agentInteraction/
- apps/live-control-ui/src/planSurface/
- apps/live-control-ui/src/buildSurface/

Maximum additional paths:
4

Allowed path kinds:
- an existing focused test importing the removed ProjectionProvider;
- one focused type-only module needed to break a runtime import cycle;
- one existing surface config test needed to prove nullable context;
- one existing CSS entry point needed solely because the container moved outside the surface root.

Decision rule:
The path must be necessary to compile or prove the singular-host invariant.
It may not add a surface, capability, route, persistence format, graph operation,
or new operator interaction.

Required report:
Record the exact path, why the allowlist was insufficient, the owning guarantee,
and why the change does not belong to MC-02a, MC-02b, or R10b.
```

Any other path is a stop condition.

---

## §6 Files and capabilities explicitly out of scope

| Path, layer, or capability                                                    | Why excluded                                             |
| ----------------------------------------------------------------------------- | -------------------------------------------------------- |
| `apps/live-control-ui/src/planSurface/components/PlanAgentInteractionBar.tsx` | Bottom-bar consolidation and UI migration belong to R10b |
| `apps/live-control-ui/src/agentInteraction/agentInteractionStorage.ts`        | Projection persistence is explicitly deferred            |
| Existing thread schemas and stored Agent Interaction payloads                 | R10a is transient ownership only                         |
| `apps/live-control-ui/src/graphReference/**`                                  | Neutral graph-reference capability work is MC-02a        |
| Build Markdown chip runtime or Edit dock                                      | Build enablement is MC-02b                               |
| Build search, insertion, glance, or graph lens                                | Build enablement is MC-02b                               |
| Backend routes, graph APIs, extraction, review packages, and promotion        | Separate ownership                                       |
| Graph Review dispositions, correction, elevation, prepare, or confirm         | Graph Review authority is unchanged                      |
| App routing rewrite or history listener redesign                              | Separate route capability                                |
| Bottom Agent Interaction Pane/Bar                                             | R10b                                                     |
| `localStorage` projection state                                               | R10b                                                     |
| New projection kinds or tools                                                 | Not required for ownership lift                          |
| Projection registry redesign                                                  | Registry behavior remains current                        |
| Graph or reference identity rules                                             | Kernel and existing resolver ownership                   |
| Closing, rebasing, or modifying PR #430                                       | Repository-management action outside this implementation |
| BLD inspection-truth lane                                                     | Independently executable and unrelated                   |

Do not introduce:

* a second app-level provider;
* a retained hidden route-local container;
* a test-only production `ProjectionProvider` export;
* a global mutable registry outside React ownership;
* a surface label as identity;
* first-registration-wins behavior;
* raw rendered `ReactNode` values in surface publication;
* persisted callbacks or payloads;
* a fallback from Build to Plan configuration;
* a fabricated Plan context for Build;
* a tool inferred from label, route, or prior surface state.

---

## §7 Implementation contract

### §7.1 App-level ownership

`AgentInteractionProvider` becomes the sole owner of:

* current projection surface registration;
* active projection;
* active Plan reference resolution;
* Plan projection state;
* R10a-deps Plan reference binding;
* R10a-deps Graph Review diagnostics payload;
* all projection open, expand, close, registration, and cleanup actions.

`App.tsx` renders exactly one `AdaptiveProjectionContainer` inside the provider and outside route-specific content:

```tsx
<AgentInteractionProvider>
  {routeContent}
  <AdaptiveProjectionContainer />
</AgentInteractionProvider>
```

Equivalent composition is acceptable only when:

* the provider remains the sole state owner;
* the container is still a single app-level instance;
* no runtime import cycle is introduced;
* no route-local container remains.

`AgentInteractionProvider` must not import and render a component in a way that creates a provider ↔ container ↔ projection-hook runtime cycle. Use a type-only or composition boundary where required.

### §7.2 Projection hook compatibility

Existing consumers may continue importing:

```ts
useProjection()
useOptionalProjection()
projectionContainerClass()
```

from the existing projection module.

After R10a:

* `useProjection` is a facade over the projection slice owned by `AgentInteractionProvider`;
* it does not read a second React context;
* no `ProjectionProvider` component remains in production or test support;
* consumers outside `AgentInteractionProvider` retain the existing clear error behavior;
* `useOptionalProjection` returns `null` outside the app host.

A compatibility facade is allowed. A compatibility owner is not.

### §7.3 Surface publication contract

Use a typed transient publication equivalent to:

```ts
interface ProjectionSurfaceIdentity {
  surfaceId: string;
  instanceKey: string;
}

interface ProjectionSurfacePublication {
  identity: ProjectionSurfaceIdentity;
  config: SurfaceConfig;
}
```

The exact type name may differ, but the following semantics are mandatory:

* `surfaceId` identifies the surface mode, not an entity kind;
* `instanceKey` is exact and surface-owned;
* labels are display-only and never identity;
* publication is in-memory only;
* `SurfaceConfig.context` may be `null` for a non-consuming surface;
* Plan and Ingest preserve a statically non-null context in their specialized types;
* Build uses `context: null`, `tools: []`, no `sessionDescriptor`, and its exact document identity;
* an inactive route publishes nothing;
* tool IDs remain exact existing IDs.

Required identity inputs:

```text
Plan:
  surfaceId = plan
  instance identity includes:
    planning document UUID
    campaign ID
    live session
    exact memory/graph focus represented by the Plan config

Ingest:
  surfaceId = ingest
  instance identity includes:
    campaign ID
    live session
    ingest/focus session represented by the toolbox config

Build:
  surfaceId = build
  instance identity includes:
    workspace document UUID when loaded
    a stable explicit new-source identity when no document is selected
```

Use exact structural comparison or an unambiguous stable tuple encoding. Do not concatenate uncontrolled fields into an ambiguous delimiter string.

Graph Review’s selected run, candidate selection, evidence selection, and diagnostics state are payload updates, not surface identity changes.

### §7.4 Registration and cleanup identity

Each surface publication receives an internal registration token.

Rules:

1. Latest valid registration wins.
2. Cleanup removes only its own current registration.
3. Late cleanup from Plan cannot erase Build or Ingest.
4. Late cleanup from Build cannot erase Ingest.
5. Replacement and cleanup update an authoritative ref synchronously before React state flushes.
6. A new surface identity synchronously invalidates the previous active projection.
7. Rendering and actions validate the current surface token, not only eventually updated React state.
8. StrictMode effect replay must not leave the host inactive or multiply containers.

A replacement with the same exact surface identity is a config update:

* latest config wins;
* active tool may remain only if the same exact tool ID is still enabled;
* active Plan content may remain only if the publication still contains the required Plan rendering context;
* otherwise active projection clears;
* dependency registrations must be transferred, republished, or invalidated truthfully.

A replacement with a different identity always clears the selected projection.

### §7.5 Surface-bound action leases

Every mutating action returned to a route consumer must be bound to the surface token current when that consumer received it.

This includes:

* `openTool`;
* `openContentFromChip`;
* `openPlanReferenceResolution`;
* `expandContent`;
* `close`;
* Plan reference dependency registration;
* tool-payload registration.

Required behavior:

```text
Old surface callback + current token differs
  → no-op

Old surface callback + surface unbound
  → no-op

Current surface callback + exact enabled operation
  → existing behavior

Current surface callback + tool not enabled
  → no-op
```

This must close both post-render and pre-rerender races.

Example required proof:

```text
1. Capture Plan's openContentFromChip.
2. Publish Build in the same act/turn.
3. Invoke captured Plan action before provider rerender.
4. No projection opens.
```

Repeat the boundary for `openTool` and cleanup identity.

### §7.6 Surface-scoped R10a-deps registrations

The Plan reference binding and Graph Review diagnostics payload must be associated with the surface lease under which they register.

Rules:

* a Plan binding registered under Plan cannot be consumed under Build or Ingest;
* a diagnostics payload registered under Ingest cannot render under Plan or Build;
* changing surface identity makes previous dependency registrations unreadable immediately;
* stale cleanup may clear only its exact dependency registration;
* the dependency binder may republish after the new surface registration becomes visible;
* missing current dependency renders the R10a-deps fail-closed state;
* no stale payload may briefly appear while the next route is mounting.

If effect ordering means a binder runs before surface publication, the initial registration may no-op and must retry after the host publishes the surface. Do not solve this with a global unscoped fallback.

### §7.7 Selected-projection ownership

Internally associate selected projection state with its owning surface lease.

Equivalent shape:

```ts
interface LeasedActiveProjection {
  surfaceToken: symbol;
  projection: ActiveProjection;
}
```

The exact internal representation may differ.

The provider/container must not render an active projection whose lease is not the current surface lease, even during the render before asynchronous clearing state has flushed.

The same ownership applies to:

* active Plan reference;
* Plan projection state;
* expanded/compact state.

### §7.8 Surface validation

A publication with `tools.length > 0` but no required render context is invalid.

Required failure behavior:

* it still supersedes the previous surface identity so stale content cannot remain;
* its enabled projection set becomes empty;
* the app route continues rendering;
* the container renders nothing;
* `openTool` and content actions no-op;
* it does not borrow the previous surface’s context;
* it does not invent campaign/session values.

A Build publication with `context: null` and `tools: []` is valid and expected.

### §7.9 Adaptive container contract

`AdaptiveProjectionContainer` no longer accepts a route-owned `config` prop.

It reads the current validated publication from the app host.

When no surface is published:

```text
render null
remove plan-toolbox-open body class
register no Escape handler
render no toggle, backdrop, nav, or drawer
```

When Build publishes empty tools:

```text
render null
do not show a disabled or empty Tools toggle
```

When Plan or Ingest publishes tools:

* preserve current button, drawer, backdrop, Escape, header, nav, sizing, URL, and close behavior;
* preserve compact reference glance and Expand;
* preserve exact configured tool order and labels;
* do not add bottom-pane chrome;
* do not rename visible copy.

The app-level wrapper must apply:

* the active publication’s theme token values;
* its `data-md-theme` value where present.

Theme values from an old surface must not remain after unbind or replacement.

### §7.10 URL and latest-session behavior

Existing URL behavior remains:

* exact enabled `?tool=` or hash tool opens;
* unavailable tool IDs no-op;
* the current path/query is updated by tool navigation as before;
* no route rewrite is introduced.

The existing latest-ingested-session cache must no longer be a single unkeyed value across the app-scoped container.

It must be:

* reset when campaign/surface identity changes; or
* stored by exact campaign ID.

A session inferred for one campaign must never be written into another campaign’s URL.

Build and inactive surfaces perform no recap-artifact lookup.

### §7.11 Route publication

#### Plan

`PlanSurfaceShell`:

* publishes `null` while the planning document/config is loading or rejected;
* publishes exact Plan identity once config is ready;
* removes its local `ProjectionProvider`;
* removes its local `AdaptiveProjectionContainer`;
* retains `PlanGraphLensProvider`;
* retains `PlanGraphReferenceResolverProvider`;
* retains `PlanReferenceProjectionBinding` beneath the resolver;
* retains existing Plan canvas and `PlanAgentInteractionBar`.

A planning-document UUID or graph-focus change is a surface identity change and clears active projection.

A revision/title/theme update with unchanged identity updates publication and revalidates active projection.

#### Ingest / Graph Review

`GraphReviewWorkbenchModule`:

* publishes `null` during the predecessor loading state where the toolbox did not previously exist;
* publishes exact Ingest toolbox config when the workbench becomes toolbox-capable;
* removes its local `ProjectionProvider`;
* removes its local `AdaptiveProjectionContainer`;
* retains `GraphReviewLiveStateProvider`;
* retains `GraphReviewDiagnosticsProjectionBinding` beneath live state.

Changing applied run or diagnostics selection does not create a new surface lease.

#### Build

`BuildSurfacePage` publishes a valid minimal Build surface for:

* the new-source form;
* a loaded document;
* a changed document ID.

Required Build publication:

```ts
{
  id: "build",
  label: existing Build label,
  context: null,
  tools: [],
  canvas: { documentId },
  theme: {}
}
```

Build gains no projection trigger or renderer.

Existing `BuildSurfaceShell` ambient Agent Interaction publication remains independent.

#### Other routes

Index, Live Control, and the Tiptap spike do not need projection publications in this slice.

With no publication, the host remains inactive.

### §7.12 No persistence

All new state is transient React state.

Do not:

* add projection fields to an Agent Interaction thread;
* create projection storage keys;
* persist callbacks, configs, bindings, payloads, active tools, or references;
* rehydrate projection state;
* add migration logic;
* alter existing thread persistence.

Because `AgentInteractionProvider` already performs unrelated thread persistence, tests must prove projection actions do not create or modify projection-related storage.

---

## §8 State and fallback matrix

| Path                        | Loading/initializing                                               | Exact success                      | Ordinary miss                         | Dependency unavailable                       | Integrity/contract failure                                     | Stale/superseded                           | Retry/replay                      |
| --------------------------- | ------------------------------------------------------------------ | ---------------------------------- | ------------------------------------- | -------------------------------------------- | -------------------------------------------------------------- | ------------------------------------------ | --------------------------------- |
| Surface publication         | Host inactive                                                      | Exact lease becomes current        | Null publication leaves host inactive | Route may remain visible without projections | Invalid publication supersedes old surface but enables nothing | New token wins; stale cleanup ignored      | Route may republish               |
| Plan tool open              | No-op until Plan published                                         | Exact enabled tool opens           | Unknown tool no-op                    | No current Plan lease → no-op                | Missing context → no-op                                        | Old callback no-op                         | Operator may retry                |
| Plan content open           | Existing resolution loading remains route-owned                    | Exact supplied resolution opens    | Existing unresolved/fallback card     | Missing Plan binding fails closed            | No borrowed config or inferred node                            | Old surface completion no-op               | Operator may retry                |
| Plan relationship traversal | Existing card loading state                                        | Exact returned resolution opens    | Existing unresolved result            | Binding unavailable → action absent/disabled | Existing resolver error policy                                 | Old binding or surface lease cannot commit | Operator may retry                |
| Ingest Recap                | No toolbox during predecessor loading state                        | Existing tool opens                | Tool absent → no-op                   | No current Ingest lease → no-op              | Null render context enables nothing                            | Prior surface callback no-op               | Operator may retry                |
| Diagnostics                 | Existing loading/empty states                                      | Latest current payload renders     | Existing select-run state             | Explicit unavailable state                   | No latest-run inference                                        | Old payload unreadable                     | Binder republishes                |
| Build                       | Minimal empty-tools lease                                          | No projection UI                   | Not applicable                        | Valid inactive consumer                      | Malformed publication still clears old host                    | Old Plan/Ingest state hidden immediately   | Republish on document change      |
| Surface replacement         | Current projection invalidated synchronously when identity differs | New surface renders its own config | Null replacement makes host inactive  | No fallback                                  | No old config reuse                                            | Exact newest token wins                    | New route may republish           |
| Same-identity update        | Existing active may remain                                         | Latest config/theme visible        | Removed tool clears active            | Missing dependency fails closed              | Invalid update enables nothing                                 | Stale cleanup ignored                      | Corrected update may republish    |
| URL tool request            | Wait for current publication                                       | Exact enabled ID opens             | Unknown ID no-op                      | No surface → no-op                           | No inferred replacement                                        | Request cannot open against stale config   | Re-evaluated on valid publication |
| Latest-session lookup       | No lookup without eligible tool/context                            | Campaign-keyed result used         | No record leaves session unchanged    | Request failure leaves session unchanged     | Never reuse another campaign                                   | Old campaign result ignored                | Later attempt allowed             |
| Close/expand                | Current active projection only                                     | Existing behavior                  | No active → no-op                     | No surface → no-op                           | No cross-surface mutation                                      | Old lease action no-op                     | Current operator action allowed   |

Named fallback behavior remains exactly as before this slice. R10a introduces no new graph, corpus, run, tool, campaign, or session fallback.

---

## §9 Identity matrix

| Situation                 | Required matching rule                                        | Ambiguity behavior                          | Fallback permitted?                                    | Persistence consequence                 |
| ------------------------- | ------------------------------------------------------------- | ------------------------------------------- | ------------------------------------------------------ | --------------------------------------- |
| Surface mode              | Exact `surfaceId`                                             | No label matching                           | No                                                     | None                                    |
| Surface instance          | Exact structured `instanceKey` inputs                         | Collision is a contract defect; fail closed | No                                                     | None                                    |
| Registration              | Exact opaque registration token                               | Latest registration wins                    | No                                                     | None                                    |
| Same-identity replacement | Exact identity equality                                       | Latest config wins; active revalidated      | No                                                     | None                                    |
| Different identity        | Exact inequality                                              | Clear active immediately                    | No                                                     | None                                    |
| Tool                      | Exact configured tool ID                                      | Unknown ID no-op                            | No                                                     | None                                    |
| Plan document             | Exact workspace document UUID                                 | No title/path substitution                  | No                                                     | Existing document persistence unchanged |
| Build document            | Exact workspace document UUID or explicit new-source identity | No campaign/title substitution              | No                                                     | Existing document persistence unchanged |
| Campaign/session context  | Exact published config fields                                 | No latest/first matching context            | No                                                     | None                                    |
| Dependency payload        | Exact surface token + dependency registration token           | Stale registration unreadable               | No                                                     | None                                    |
| Graph/reference identity  | Existing predecessor behavior                                 | Existing ambiguous state                    | Existing corpus fallback only where already authorized | Unchanged                               |

This slice must not change alias resolution, graph matching, reference rebinding, rename, deletion, corpus fallback, or World Graph identity.

---

## §10 Persistence and replay matrix

```text
Not applicable — R10a introduces only transient app-level React state and exact
runtime leases. Projection state must not survive provider remount, page reload,
or process restart. Existing Agent Interaction thread persistence is unchanged.
```

Required negative proofs:

* opening a tool creates no projection storage key;
* opening a reference creates no projection storage key;
* replacing surfaces creates no projection storage key;
* no projection callback, dependency payload, surface config, or selected projection appears in stored thread JSON.

---

## §11 Predecessor-to-consumer mapping

**Grounding source**

```text
Merged R10a-deps implementation containing approved PR #438 head
a7dc6a1efa6fdbb1ea8d88e5d60164c1ed735063, updated onto current main.
```

| Predecessor field/outcome                     | Real shape                                   | R10a consumer                          | Transformation                              | Required proof                           |                                    |
| --------------------------------------------- | -------------------------------------------- | -------------------------------------- | ------------------------------------------- | ---------------------------------------- | ---------------------------------- |
| Route-local `ProjectionProvider` active state | `ActiveProjection                            | null`                                  | Agent Interaction projection slice          | Move ownership; preserve shape/behavior  | Provider + Plan/Ingest integration |
| `activePlanReference`                         | `PlanReferenceResolution                     | null`                                  | Leased app-host content state               | Associate with surface lease             | Async stale-open test              |
| `planProjectionState`                         | Existing Plan enum/null                      | Leased app-host content state          | Direct, no semantic change                  | Plan reference tests                     |                                    |
| `openTool(toolId)`                            | Exact configured tool lookup                 | Surface-bound provider action          | Validate current lease and current tool set | Stale callback + tool tests              |                                    |
| `openContentFromChip`                         | Exact supplied ref/resolution                | Surface-bound provider action          | Preserve resolution; add lease gate         | Deferred chip test                       |                                    |
| `openPlanReferenceResolution`                 | Exact supplied resolution                    | Surface-bound provider action          | Preserve resolution; add lease gate         | Relationship/search tests                |                                    |
| `registerPlanReferenceBinding`                | Exact-registration cleanup                   | Surface-scoped dependency registration | Add owning surface lease                    | R10a-deps regression tests               |                                    |
| `registerToolProjectionPayload`               | Typed diagnostics payload                    | Surface-scoped tool payload            | Add owning Ingest lease                     | Diagnostics replacement/navigation tests |                                    |
| Plan `SurfaceConfig`                          | Non-null Plan context and session descriptor | Plan publication                       | Direct publication plus exact identity      | Plan shell test                          |                                    |
| Ingest `SurfaceConfig`                        | Non-null Plan-shaped toolbox context         | Ingest publication                     | Direct publication plus exact identity      | Workbench test                           |                                    |
| Build document selection                      | UUID or no document                          | Minimal Build publication              | Context null, tools empty                   | Build page test                          |                                    |
| Container `config` prop                       | Non-null route-owned `SurfaceConfig`         | Current provider publication           | Remove prop; read host                      | Container test                           |                                    |
| Surface theme tokens                          | Inherited from route root                    | App-level wrapper style/data attribute | Explicitly apply current theme              | Theme replacement test                   |                                    |
| Latest ingested session cache                 | One component-local nullable ID              | Campaign-keyed/reset cache             | Prevent cross-surface reuse                 | Two-campaign test                        |                                    |
| `publishSurfaceContext`                       | Existing ambient Agent Interaction setter    | Unchanged                              | No merge with projection publication        | Existing provider tests                  |                                    |

Do not invent replacement fixture vocabulary. Use the repository’s current canonical types and builders.

---

## §12 Verification ownership map and commands

| Guarantee                              | Owning boundary               | Command/scenario                      | Expected evidence                                 |
| -------------------------------------- | ----------------------------- | ------------------------------------- | ------------------------------------------------- |
| One provider owns projection state     | AgentInteraction provider     | Focused provider tests + source guard | No standalone provider owner                      |
| One production container exists        | App composition               | App test + source guard               | Exactly one production mount                      |
| Inactive host renders nothing          | App/container                 | Container integration test            | No toggle/drawer/body class                       |
| Plan behavior is equivalent            | Plan shell + canvas + host    | Plan integration tests                | Tools, chip, expand, relationship, statblock work |
| Ingest behavior is equivalent          | Graph Review workbench + host | Workbench tests                       | Recap and diagnostics work                        |
| Build enables nothing                  | Build page + host             | Build test                            | Empty publication, no Tools UI                    |
| Surface replacement clears stale state | Provider                      | Route harness                         | No stale render or callback                       |
| Pre-rerender stale action is blocked   | Provider                      | Same-turn replacement tests           | Old action no-op                                  |
| Dependency payloads are surface-scoped | Provider + bindings           | R10a-deps regression tests            | No cross-surface payload                          |
| Same-identity update revalidates       | Provider                      | Focused state tests                   | Valid active preserved; removed active cleared    |
| Theme follows active surface           | Container                     | Theme replacement test                | Current tokens only                               |
| Session cache is campaign-safe         | Container                     | Two-campaign lookup test              | No cross-campaign reuse                           |
| No persistence introduced              | Provider/storage boundary     | localStorage assertions               | No projection data stored                         |
| Existing thread behavior unchanged     | AgentInteraction provider     | Existing provider suite               | Thread tests remain green                         |

Run from `apps/live-control-ui`:

```bash
npm test -- \
  src/App.test.tsx \
  src/agentInteraction/AgentInteractionProvider.test.tsx \
  src/agentInteraction/projectionSurfacePublication.test.ts \
  src/planSurface/projection/projectionContext.test.tsx \
  src/planSurface/projection/AdaptiveProjectionContainer.test.tsx \
  src/planSurface/projection/projectionBindings.test.tsx \
  src/planSurface/PlanSurfaceShell.test.tsx \
  src/planSurface/reference/PlanReferenceObjectCard.test.tsx \
  src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.test.tsx \
  src/buildSurface/BuildSurfacePage.test.tsx

npm test -- src/planSurface/projection src/planSurface/reference src/agentInteraction

npm run typecheck
npm run build
```

Required source guards from repository root:

```bash
# No production route-local provider owner remains.
if rg -n 'ProjectionProvider' apps/live-control-ui/src \
  --glob '!**/*.test.tsx' \
  --glob '!**/*.md'; then
  echo "Unexpected production ProjectionProvider reference"
  exit 1
fi

# Exactly one production adaptive-container mount.
test "$(
  rg -n '<AdaptiveProjectionContainer' apps/live-control-ui/src \
    --glob '!**/*.test.tsx' |
  wc -l
)" -eq 1

# Build must not gain graph-reference or projection triggers.
git diff <BASE>...HEAD -- apps/live-control-ui/src/buildSurface |
  rg 'openTool|openContentFromChip|openPlanReferenceResolution|PlanGraphRefSearch|GraphNodeChipRuntimeProvider' &&
  exit 1 || true

git diff --check
git diff --stat <BASE>...HEAD -- <all §5 paths>
git diff --name-only <BASE>...HEAD
```

Adjust guard syntax only for shell portability. Do not weaken what the guards prove.

### Minimal live proof

**Existing surfaces used:** `/plan`, `/build`, `/ingest`

**Scenario**

1. Start from the root launcher.
2. Open Plan.
3. Open each configured Plan tool.
4. Open a reference chip, expand it, and traverse one relationship.
5. Leave a projection open and navigate to Build.
6. Confirm no toolbox toggle or drawer appears on Build.
7. Open a loaded Build document and confirm it remains projection-inactive.
8. Navigate to Ingest.
9. Open Ingest Recap.
10. Open Diagnostics before and after selecting a live run.
11. Confirm only one toolbox drawer exists in the DOM at every step.
12. Confirm Escape, backdrop, close, and URL-selected tool behavior remain unchanged.

**Expected observation**

* Plan and Ingest remain interaction-equivalent;
* Build gains no graph interaction;
* no stale Plan content appears on Build or Ingest;
* no duplicate toggle/drawer appears;
* active surface theme is applied to the drawer;
* no console render-loop or stale-context errors appear.

**Evidence captured**

Record exact route, action, and observation. Screenshots are optional; console errors and DOM duplication are not.

### Baseline failure protocol

PR #438 reported `typecheck` and `build` as baseline-red. Re-evaluate on the final merged R10a base.

| Command             | Base result         | Head result         | New failure introduced? | Acceptance effect                                                          | Waiver                |
| ------------------- | ------------------- | ------------------- | ----------------------: | -------------------------------------------------------------------------- | --------------------- |
| `npm run typecheck` | Record exact output | Record exact output |                  Yes/No | Blocked if new failures; otherwise explicit waiver if baseline remains red | Required if still red |
| `npm run build`     | Record exact output | Record exact output |                  Yes/No | Blocked if new failures; otherwise explicit waiver if baseline remains red | Required if still red |

Do not report either command as passing when it remains baseline-red.

---

## §13 Required implementation handback

The PR body must include:

1. Exact immutable base SHA.
2. Exact head SHA.
3. Actual changed paths.
4. Focused diff stat limited to §5 paths.
5. Every §12 command and exact result.
6. Result provenance:

   * author-local;
   * independently rerun;
   * CI;
   * manual observation.
7. Live-proof observations.
8. Baseline typecheck/build comparison.
9. Explicit operator waivers, or `none`.
10. Paths outside the allowlist, or `none`.
11. Bounded-discovery paths and justification, or `none`.
12. Stop conditions and resolution, or `none`.
13. Contract deviations, or `none`.
14. Exact count of production `ProjectionProvider` owners: `0`.
15. Exact count of production `AdaptiveProjectionContainer` mounts: `1`.
16. Confirmation that Build has:

    * context `null`;
    * tools `[]`;
    * no graph-reference affordance.
17. Confirmation that no projection state is persisted.
18. Confirmation that MC-02a, MC-02b, and R10b remain false.
19. Confirmation that PR #430 was not used.
20. Confirmation that this handoff was implemented without compression or omitted constraints.

---

## §14 Acceptance rubric

The reviewer accepts only when every statement is true.

* [ ] Exactly one projection state owner exists: `AgentInteractionProvider`.
* [ ] Exactly one production adaptive container exists and is hosted above route content.
* [ ] No production `ProjectionProvider` remains.
* [ ] No hidden route-local container remains.
* [ ] Plan publishes an exact document/focus-scoped surface lease.
* [ ] Ingest publishes an exact toolbox surface lease.
* [ ] Build publishes a valid empty-tools, null-context lease.
* [ ] Inactive routes render no projection chrome.
* [ ] Surface cleanup is exact-token safe.
* [ ] Replacement is synchronously authoritative before React rerender.
* [ ] Different surface identity clears selected projection immediately.
* [ ] Same-identity updates preserve only still-valid active projections.
* [ ] Old surface callbacks cannot mutate the current host.
* [ ] Async Plan chip completion cannot open after leaving Plan.
* [ ] Plan relationship completion remains protected by the R10a-deps binding gate.
* [ ] Plan and Graph Review dependency registrations are surface-scoped.
* [ ] No stale diagnostics payload appears on another surface or run.
* [ ] Plan tool, reference, expand, relationship, and statblock behavior is equivalent.
* [ ] Ingest Recap and Diagnostics behavior is equivalent.
* [ ] Existing URL tool behavior remains exact-ID only.
* [ ] Latest-session lookup cannot leak across campaigns.
* [ ] App-level container applies the current surface theme.
* [ ] Build gains no graph-reference capability.
* [ ] No bottom-pane redesign ships.
* [ ] No projection state is persisted.
* [ ] Existing Agent Interaction thread persistence remains compatible.
* [ ] No unexpected file changed.
* [ ] Baseline failures are reported honestly with explicit waiver where required.
* [ ] MC-02a is still required after this PR.
* [ ] The complete checked-in handoff survived dispatch intact.

---

## §15 Reviewer protocol

Review the invariant before individual files.

1. Confirm the implementation base contains merged PR #438.
2. Count projection owners and production container mounts.
3. Trace state ownership from `App` into `AgentInteractionProvider`.
4. Trace Plan publication, dependency registration, and content opening.
5. Trace Ingest publication and diagnostics payload registration.
6. Trace Build publication and verify no capability was enabled.
7. Test different-identity replacement.
8. Test same-identity config replacement.
9. Test stale cleanup before and after rerender.
10. Test stale surface callbacks before and after rerender.
11. Test async Plan chip completion after surface replacement.
12. Verify dependency registrations cannot cross surface leases.
13. Verify container theme and campaign cache replacement.
14. Inspect existing Agent Interaction storage for accidental projection persistence.
15. Compare every changed path with §5 and §6.
16. Confirm PR #430 code was not reused as authority.
17. Confirm MC-02a, MC-02b, and R10b remain unclaimed.
18. Compare typecheck/build base and head results.

A passing Plan test alone does not prove app-level ownership. A provider unit test alone does not prove Plan/Ingest integration. Both boundaries are required.

---

## §16 Re-review protocol

Begin from the prior finding ledger.

| Prior finding | Claimed fix | Owning files/tests | Verified? | New consequence?        |
| ------------- | ----------- | ------------------ | --------: | ----------------------- |
| `<finding>`   | `<fix>`     | `<paths>`          |    Yes/No | `<none or consequence>` |

For every correction:

1. Verify the literal fix.
2. Re-test singular ownership.
3. Re-test Plan, Ingest, Build, and inactive surfaces.
4. Re-test pre-rerender replacement and cleanup.
5. Re-test stale async callbacks.
6. Re-test dependency surface scoping.
7. Re-check persistence and theme consequences.
8. Re-run production owner/container counts.
9. Re-check successors remain false.

---

## Stop conditions

Stop and report rather than expanding scope when:

* PR #438 is not merged or its merged shape differs materially;
* current `main` has another projection-host implementation;
* a route still requires provider ancestry not removed by R10a-deps;
* the lift requires retaining a route-local container;
* the implementation requires a sibling app-level provider;
* Build must gain a projection tool to prove the host;
* MC-02a capability IDs are required to complete the ownership lift;
* `PlanAgentInteractionBar` must move to app chrome;
* the right drawer must be replaced to make the app-level DOM work;
* projection state must persist to make the slice useful;
* hard navigation must be replaced with SPA routing;
* a new graph/reference identity rule is required;
* Agent Interaction stored-thread schemas must change;
* more than four undeclared paths are required;
* typecheck/build introduces new failures;
* current CSS cannot preserve existing chrome without a wider visual redesign;
* surface publication cannot be made exact without inventing a durable ID.

Use this report:

```text
Stop condition:
Why R10a cannot absorb it:
Current repository evidence:
New contract discovered:
Affected observable paths:
Affected ownership layers:
Required path outside scope:
Proposed successor slice:
Authority/tracker update required:
Operator decision required:
```

---

## Final dispatch check

* [x] PR #438 is merged.
* [x] Implementation base is an exact immutable SHA.
* [x] Branch starts from that SHA.
* [x] R10a is still next in the sequencing authority.
* [x] PR #430 is not in branch ancestry.
* [ ] §0 proves this is one capability.
* [ ] §1 invariant is reused throughout.
* [ ] All observable paths are inventoried.
* [ ] Every expected changed path is listed.
* [ ] Surface identity and cleanup semantics are exact.
* [ ] Same-identity and different-identity policies are explicit.
* [ ] Stale action and async completion behavior is explicit.
* [ ] Dependency registrations are surface-scoped.
* [ ] Build’s inactive contract is explicit.
* [ ] Theme and cache consequences of a singular container are explicit.
* [ ] Persistence is explicitly excluded.
* [ ] Every acceptance claim maps to an owning-boundary proof.
* [ ] Baseline-red gates have a truthful comparison protocol.
* [ ] MC-02a, MC-02b, and R10b are named and remain false.
