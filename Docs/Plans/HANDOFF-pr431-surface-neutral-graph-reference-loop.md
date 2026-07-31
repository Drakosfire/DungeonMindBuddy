---
pr_body_template: |
  ## Outcome

  Plan can execute its existing World Graph reference lifecycle through one surface-neutral `graphReference` capability so a later Build slice can enable the same search, exact insertion, resolution, and projection behavior without importing Plan components or state.

  ## Merge-ready invariant

  Every current Plan reference path—search, inspect, insert, chip reopen, compatibility fallback, ambiguity, error, and relationship traversal—uses one `graphReference` public contract whose production modules import no `planSurface` symbols, preserves exact graph-node identity and current fallback rules, remains lease-safe under asynchronous surface changes, and introduces no Build behavior or new durable write authority.

  ## Evidence required to merge

  | Guarantee | Owning boundary | Required evidence | Result |
  |---|---|---|---|
  | Production graphReference modules have no planSurface dependency | Shared package boundary | §7 E1 import-boundary command | TODO |
  | Exact graph-node IDs never rebind through labels or corpus fallback | Pure resolver contract | §7 E2 resolver tests | TODO |
  | Legacy Plan references preserve unique-only graph lookup and current corpus fallback rules | Plan adapter + resolver | §7 E2 resolver tests | TODO |
  | Ambiguity remains explicit and never opens the first candidate | Resolver + projection workflow | §7 E2 and E6 adversarial tests | TODO |
  | Search, inspect, and locked-editor behavior remain interaction-equivalent in Plan | Shared search component + Plan canvas | §7 E3 and E7 component tests | TODO |
  | Insertion writes the existing RunbookReferenceAttrs shape at the current editor selection | TipTap command helper + Plan integration | §7 E4 and E7 tests | TODO |
  | App-scoped content projection remains exact-lease safe across surface replacement and late async completion | AgentInteractionProvider + adaptive container | §7 E5 and E6 adversarial tests | TODO |
  | Plan regression suite, typecheck, and production build remain green | Live Control UI package | §7 E8–E10 | TODO |

  ## Scope and explicit deferrals

  Base: TODO — exact main SHA containing this checked-in handoff; it must descend from 2c9cb97fa29a4e703f0521f56acfcff8a291f986.

  Target PR: #431.

  Existing old head e3919d5b13e0066cc3ed46dc51fddb27c29914a0 is historical evidence only and MUST NOT be rebased or cherry-picked as implementation.

  Actual changed paths: TODO — must be a subset of §4.

  Paths outside §4: TODO (none or stop report).

  Named successor still false: Build World Reference Loop v1.

  Also still false: Build graph lens UI, Build extraction inspector, candidate-assisted Find existing, node authoring, graph writes, document styling expansion, and persistent reference-schema changes.

  ## Evidence produced

  ### Automated
  TODO

  ### Adversarial
  TODO

  ### Regression
  TODO

  ### Manual / dogfood
  TODO

  ## Gaps, waivers, and stop conditions
  TODO — write none when none exist.
---

# HANDOFF — Surface-neutral existing-object graph reference loop

**Created:** 2026-07-30.  
**Status:** READY FOR IMPLEMENTATION — dispatch exactly one implementation capability; implementation base recorded below.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-pr431-surface-neutral-graph-reference-loop.md`  
**Target pull request:** #431  
**Authoring anchor:** main at `2c9cb97fa29a4e703f0521f56acfcff8a291f986`  
**Historical PR head:** `e3919d5b13e0066cc3ed46dc51fddb27c29914a0` — 148 commits behind the authoring anchor; research only.  
**Suggested branch:** `agent/pr-mc02a-graph-reference`  
**Implementation base:** TODO_BASE_SHA

> **Mechanical dispatch gate:** The handoff must first be checked into main. Replace the implementation-base TODO with that exact resulting SHA. Before the worker edits code, the target branch tip must equal that SHA exactly. If the old PR branch still contains the historical stacked implementation, the worker must stop. Rebase, merge, cherry-pick, or selective conflict resolution from the old head is not an authorized substitute for a fresh base.
>
> **Dispatch gate:** Dispatch is prohibited until capability decomposition is complete, one independently useful mission remains, the merge-ready invariant and required evidence survive critique, every expected path is known, required contract matrices are resolved, and every acceptance claim has an owning proof.
>
> This checked-in handoff is the complete authority. The worker must not compress, omit, replace, or rewrite it before implementation. The PR description must use the frontmatter skeleton and remain a truthful merge contract; it cannot substitute for the handoff.

## Shared vocabulary

| Term | Definition |
|---|---|
| Graph reference | A document or interaction pointer that identifies an existing World Graph object, or a legacy compatibility reference awaiting graph/corpus resolution. |
| Graph-native reference | A RunbookReferenceAttrs value whose refType is graph-node and whose refId is the exact durable World Graph node ID. |
| Compatibility reference | A pre-graph or corpus-oriented reference that may resolve through unique graph label/alias lookup and, only under the existing Plan rules, corpus-index fallback. |
| Reference lifecycle | Search existing objects → inspect an exact result → insert an existing reference → resolve a chip → project the object → traverse a relationship. |
| Surface-neutral contract | A caller-facing type, component, hook, or helper under `apps/live-control-ui/src/graphReference/` whose production module imports no planSurface module and contains no fabricated Plan session state. |
| Capability | A coherent behavior or contract that creates one outcome someone can use, depend on, test, or revert. |
| Independently useful outcome | An outcome that provides value or establishes a reusable contract even if neighboring work never ships. |
| Public/durable contract | A persisted format, identifier, API, event, schema, file representation, caller-facing type, or externally consumed interface that must remain interpretable beyond one call stack. |
| Observable path | A user-visible or externally observable route through behavior, including success, miss, error, retry, persistence, and operator paths. |
| Owning boundary | The layer where a guarantee becomes true and therefore must be proved: serializer, store, service, route, component, workflow, CLI, or equivalent. |
| Surface lease | The exact AgentInteractionProvider projection-surface registration token and identity governing which Surface may open or mutate app-scoped projection state. |
| Invariant | The single property every changed layer and observable path establishes or proves. |
| Evidence ledger | The mapping from each invariant clause to its owning boundary, required proof, produced result, provenance, and merge-blocking stop condition. |
| Stop condition | A discovered fact that invalidates the current slice boundaries or required proof and must be reported before implementation continues. |

## §1 Mission and merge-ready invariant

### Mission

Plan can execute its existing World Graph reference lifecycle through one surface-neutral `graphReference` capability so a later Build slice can enable the same search, exact insertion, resolution, and projection behavior without importing Plan components or state.

### Merge-ready invariant

Every current Plan reference path—search, inspect, insert, chip reopen, compatibility fallback, ambiguity, error, and relationship traversal—uses one `graphReference` public contract whose production modules import no `planSurface` symbols, preserves exact graph-node identity and current fallback rules, remains lease-safe under asynchronous surface changes, and introduces no Build behavior or new durable write authority.

### Capability decomposition decision

| Candidate outcome | Independently useful? | Public/durable contract changed? | User or operator surface changed? | Failure model changed? | Independently testable/revertible? | Decision |
|---|---:|---:|---:|---:|---:|---|
| Surface-neutral existing-object reference lifecycle used by Plan | Yes | Yes — caller-facing in-memory TypeScript contract | No intended visible change | Yes — explicit ambiguity and neutral host lease semantics | Yes | Include |
| Build enables search, inspect, insert, and chip-open | Yes | Uses this contract but adds Build lens/config/editor integration | Yes | Yes | Yes | Named successor: Build World Reference Loop v1 |
| Build graph-lens controls | Yes | Yes | Yes | Yes | Yes | Successor after the first Build reference loop |
| Stay-on-Build extraction summary/inspector | Yes | Exact-run inspection contract | Yes | Yes | Yes | Separate milestone |
| Candidate-assisted Find existing | Yes | Candidate-to-search handoff contract | Yes | Yes | Yes | Separate successor |
| Reference-format pin/head persistence changes | Yes | Durable Markdown schema | Yes | Yes | Yes | Explicitly excluded; requires its own contract slice |
| Node creation, identity merge, or graph publication | Yes | Graph write contracts | Yes | Yes | Yes | Explicitly excluded |
| General document styling/editor improvements | Yes | Editor/canvas capability | Yes | No | Yes | Separate Build milestone |

**Why the included rows share one invariant:** search, inspect, insert, resolve, project, and relationship traversal are the observable stages of one existing-object reference lifecycle. They must agree on one exact identity and resolution contract. Shipping only neutral type names while leaving Plan-owned search, app-host state, or projection binding underneath would not establish the capability.

**Named successor:** Build World Reference Loop v1 — a Build document uses these contracts with a truthful Build lens and the shared Markdown canvas to search, inspect, insert, save, reload, and reopen an existing World Graph identity.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | Yes. Every included path is read-only graph reference resolution/projection plus insertion of the already-existing reference representation into the current Plan editor. No new graph, workspace-document, or tool persistence authority is introduced. |
| What adversarial sequence is most likely to falsify it? | Plan opens a graph object → relationship resolution begins asynchronously → the app navigates to another Surface and registers a new projection lease → the old resolution completes. The completion must not open content on the new Surface or mutate its projection state. A second high-risk sequence is two graph nodes sharing one alias: resolving the alias must remain explicit ambiguity, never first-win selection. |
| Would the proposed §7 evidence actually detect those failures? | Yes. E5 exercises registration/cleanup and stale callback behavior at AgentInteractionProvider; E6 exercises late relationship completion against a replaced binding/lease; E2 freezes exact-ID, ambiguous alias, graph error, and fallback behavior at the pure resolver boundary. |
| Which owning boundary is easiest to under-test? | The app-scoped projection host. Pure resolver tests cannot prove that a late callback is rejected after a Surface lease changes. |
| What fact would force this slice to stop or split? | Any requirement to modify Build, change RunbookReferenceAttrs or Markdown serialization, add a backend/API field, fabricate a Plan session descriptor in the shared package, or introduce a second selected-object renderer/projection container. |

### Demolition declaration

This is a forward-only extraction, not a compatibility-wrapper exercise.

The accepted implementation must:

- replace PlanGraphRefSearch with a genuinely shared search component rather than export it through a neutral filename;
- move pure graph-reference resolution/search/reference-construction logic out of planSurface;
- expose neutral graph-reference state/actions from the app-scoped host rather than add aliases around openPlanReferenceResolution;
- migrate every current Plan caller in scope;
- remove unused Plan-local duplicate helpers after the migration;
- preserve the existing shared GraphNodeChipRuntime, GraphObjectCard, GraphObjectProjectionCard, AgentInteractionProvider, and single AdaptiveProjectionContainer.

A temporary compatibility re-export is allowed only when the worker identifies a named current consumer outside §4, reports it under the bounded discovery exception, and proves that removing it would widen the capability. Unnamed "safer for now" duplicate APIs are prohibited.

## §2 Context, authority, and boundaries

### Authority table

| Field | Required content |
|---|---|
| Parent authority | Docs/Reports/MAGIC-MOMENT-BUILD-SURFACE-2026-07-30.md; Docs/Design/ARCHITECTURE-plan-surface-toolbox.md; Docs/Design/DESIGN-shared-markdown-canvas-surface-composition.md; this handoff's operator-approved PR431 reanchor |
| Graph authority | Docs/Design/ARCHITECTURE-campaign-supergraph.md — World Graph owns identity; projections read one coherent revision; Surfaces do not invent identity or write semantics |
| Repository rules | AGENTS.md; .cursor/rules/external-agent-pr-loop.mdc; .cursor/skills/external-agent-pr-loop/SKILL.md; canonical handoff template |
| Authoring anchor | `2c9cb97fa29a4e703f0521f56acfcff8a291f986` |
| Implementation base | Exact main SHA after this handoff is checked in; replace the TODO before dispatch |
| Predecessor contract | R10a app-scoped projection host merged in PR #441; current graphReference/ chip runtime; current Plan resolver/search/projection implementation on the finalized base |
| Historical implementation evidence | PR #431 head `e3919d5b13e0066cc3ed46dc51fddb27c29914a0`; concepts may be re-evaluated, code must not be rebased/cherry-picked |
| Exact input consumed | WorldGraphProjection; GraphProjectionNodeView / WorldGraphProjectionNodeView; RunbookReferenceAttrs; GraphObjectCardViewModel; current Surface projection publication and lease |
| Named successor | Build World Reference Loop v1 |
| What remains false | Build has no graph-reference search/insert/project capability; Build's publication may remain projection-disabled; no Build lens UI; no new write workflow |
| Explicit non-goals | Build changes, persistent reference schema, backend/API changes, graph writes, node authoring, extraction inspector, candidate insertion, lens UI, statblock integration, bottom-pane redesign, document styling |

### PR #431 branch reanchor

At handoff authoring time:

```
main:       2c9cb97fa29a4e703f0521f56acfcff8a291f986
old base:   be638b0eec12cf1264283d23ef6ecc9f7cfe2ce9
old head:   e3919d5b13e0066cc3ed46dc51fddb27c29914a0
merge base: 88cc4038c04e4c17bb2438cb3d614063cfe6d9d5
divergence: old head is 148 commits behind authoring main
```

The old branch includes stale app-host and Graph Review changes from its former stack. Therefore:

1. The operator checks this handoff into main.
2. The operator records the exact resulting SHA in this handoff.
3. The target branch is created or reset by an authorized operator to that SHA.
4. The worker verifies `git rev-parse HEAD` equals the declared implementation base before reading old PR code.
5. The worker may inspect PR #431's patch as rejected design evidence.
6. The worker must not merge, rebase, or cherry-pick the old head.
7. If the target branch is not exactly at the declared base, stop.

### Current implementation facts to preserve

- `apps/live-control-ui/src/graphReference/` already owns shared chip-runtime and hover-presentation infrastructure. Do not create a sibling reference package.
- PlanGraphRefSearch currently owns search UI and imports Plan campaign-label and Plan projection-state vocabulary.
- `graphAwareReferenceResolver.ts` currently owns exact graph-native resolution, unique label/alias lookup, explicit ambiguous IDs, and Plan corpus fallback adaptation.
- Graph-native `refType="graph-node"` references currently resolve exact refId only and never use display-label or corpus fallback rebinding.
- PlanSurfaceCanvas currently: searches graph projection nodes; inserts RunbookReferenceAttrs; resolves chip clicks; opens content through app-scoped projection state; keeps inspect available while editing is locked.
- AgentInteractionProvider is already the singular app-scoped projection owner, but its public reference fields/actions remain Plan-named.
- AdaptiveProjectionContainer is already singular and app-scoped; do not move or duplicate it.
- PlanReferenceObjectCard already uses shared GraphObjectProjectionCard for resolved graph objects and rejects stale relationship completions when its binding changes.
- Current Plan compatibility fallback is product behavior. This slice may make the state type more truthful, but may not silently remove or broaden the fallback.
- Existing Markdown/TipTap reference serialization is durable behavior and is not owned by this slice.

### Authority precedence

1. Canonical repository architecture and accepted decisions
2. This checked-in handoff
3. Current implementation and owning-boundary tests at the finalized base
4. Current PR #431 metadata as historical context
5. Old PR #431 patch
6. Chat summaries and local reports

### Read authoritative inputs in order

1. AGENTS.md
2. `.cursor/rules/external-agent-pr-loop.mdc`
3. `.cursor/skills/external-agent-pr-loop/SKILL.md`
4. `Docs/Design/ARCHITECTURE-plan-surface-toolbox.md`
5. `Docs/Design/DESIGN-shared-markdown-canvas-surface-composition.md`
6. `Docs/Design/ARCHITECTURE-campaign-supergraph.md`
7. `Docs/Reports/MAGIC-MOMENT-BUILD-SURFACE-2026-07-30.md`
8. This handoff
9. `apps/live-control-ui/src/graphReference/`
10. `apps/live-control-ui/src/agentInteraction/AgentInteractionProvider.tsx`
11. `apps/live-control-ui/src/agentInteraction/agentInteractionTypes.ts`
12. Current Plan resolver, search, canvas, projection binding, container, registry, and tests named in §4
13. PR #431 patch only after the current implementation is understood

If the finalized base moved materially, any authority conflicts, the predecessor shape differs, or the invariant cannot be preserved, stop and report the consequence before implementation.

## §3 Observable-path and adversarial-sequence inventory

### Observable paths

| Path | Current behavior | Required behavior | Same invariant as §1? | Owning boundary |
|---|---|---|---|---|
| Search while projection is loading | Plan search shows loading status | Shared search receives neutral projection state and shows interaction-equivalent loading status | Yes | GraphReferenceSearch |
| Search while projection is ready | Plan filters by label, ID, kind, role, alias, and summary; sorts kind then label; caps visible results | Shared search preserves matching, ordering, cap, labels, and actions | Yes | shared search helpers/component |
| Search ordinary miss | Plan shows no matching objects | Shared search shows the same ordinary miss without inventing fallback or auto-opening | Yes | GraphReferenceSearch |
| Projection unavailable | Plan reports unavailable | Shared state reports unavailable; Plan copy remains interaction-equivalent | Yes | Plan adapter + shared component |
| Projection error | Plan reports error and does not present false-ready data | Shared state reports error; fallback rules remain governed by the resolver, not the search component | Yes | Plan adapter + shared component |
| Editor locked | Search and View remain available; Insert is disabled | Same behavior through shared component | Yes | Plan canvas + shared search |
| Inspect search result | Plan opens an exact graph-node resolution in the app-scoped container | Plan calls neutral openGraphReference; same card appears; no document or graph write | Yes | Agent host + adaptive container + registry |
| Insert search result | Plan writes RunbookReferenceAttrs(kind=ref, refType=graph-node, refId=exact node ID, label=display label) at current selection | Same durable representation through shared insertion helper | Yes | TipTap command helper + Plan canvas |
| Click graph-native chip | Exact refId lookup only | Same exact-ID behavior; label and alias may not rebind | Yes | pure resolver + Plan adapter |
| Graph-native exact miss | Unresolved; no corpus fallback | Same behavior with explicit neutral unresolved state | Yes | pure resolver |
| Legacy compatibility ref unique graph match | Unique exact/normalized label or alias may resolve to graph | Preserve current behavior through injected Plan compatibility adapter | Yes | neutral resolver + Plan adapter |
| Legacy compatibility ref ambiguous graph match | Current Plan returns unresolved with ambiguousNodeIds; no fallback | Neutral contract returns explicit ambiguity; Plan UI remains unresolved/repair-oriented; no first-win selection | Yes | resolver + object card |
| Legacy compatibility graph miss | Current Plan may use corpus-index fallback when projection is ready/unavailable and fallback resolution is supplied | Preserve current fallback policy exactly; no new fallback source | Yes | Plan adapter |
| Projection error during compatibility resolution | Corpus fallback disabled | Preserve fail-closed error behavior | Yes | Plan adapter |
| Open chip glance | App host opens compact content projection under current lease | Neutral state/action names; same visible card and Expand behavior | Yes | Agent host + container |
| Expand/close content | Same app-scoped content changes size or closes | Preserve current behavior | Yes | Agent host + container |
| Relationship traversal | Plan card resolves target asynchronously and opens it if binding remains current | Use neutral binding/resolution; preserve stale-completion suppression | Yes | Plan object card + neutral binding |
| Surface navigation while content is open | R10a clears/revalidates selected projection on surface registration change | Neutral reference state clears with the lease; old callbacks cannot act on new Surface | Yes | Agent host |
| Graph Review diagnostics tool | Uses the same app-scoped host but separate payload contract | Remains behavior-equivalent; neutral reference refactor must not alter diagnostics authorization/payload | Yes — sibling host path | Agent host + adaptive container |
| Build route | Build currently does not publish a usable graph-reference capability through the shared host | Remains unchanged and unenabled | Yes — required negative path | Build publication regression test or host test |

### Ordered adversarial sequences

| Sequence | Required safe outcome | Owning proof |
|---|---|---|
| Two nodes share one normalized alias → user activates legacy reference using that alias | Result is explicit ambiguous with all matching IDs; no object opens; corpus fallback is not attempted | E2 |
| Graph-native chip carries missing exact ID but its display label uniquely matches another node | Remains unresolved; must not rebind by label or alias | E2 |
| Graph projection enters error → compatibility reference has a valid corpus fallback fixture | Result is graph error; fallback remains disabled | E2 |
| Editor locked → user searches → clicks View → then attempts Insert | View opens; Insert remains disabled; no editor mutation | E3 + E7 |
| Search result uses an exact node ID containing punctuation/colons → Insert | Exact ID is preserved byte-for-byte in refId; no sanitization | E4 + E7 |
| Plan opens object A → relationship resolution begins → binding is replaced/unregistered before completion | Late completion does not open object B or update projection state | E6 |
| Plan opens object A → route changes to Build/new Surface lease → old open/expand/close callback fires | Callback is a no-op against the new lease; Build does not gain content | E5 |
| Old Plan surface cleanup runs after the next Surface has registered | Cleanup cannot clear the newer registration or its state | E5 |
| Graph Review diagnostics projection is open → neutral reference code loads/changes | Diagnostics still renders and remains separately authorized | E6/E8 |
| Same Plan graph reference is opened twice | Latest invocation may replace current content under the same lease; no duplicate durable record is created | E5/E6 |
| Reference is inserted → Plan saves/reloads through existing document pipeline | Existing reference syntax round-trips unchanged | E7 regression; no serializer changes permitted |

## §4 Files in scope — allowlist

The implementation is a cross-layer refactor because the invariant spans the shared package, app-scoped host, and the first characterized consumer. Every changed layer establishes or proves the same neutral reference lifecycle.

### Shared graph-reference capability

| Action | Path | Purpose: how this establishes or proves §1 |
|---|---|---|
| Modify | `apps/live-control-ui/src/graphReference/types.ts` | Define the neutral resolution, projection-state, search-item, and projection-binding contracts alongside the existing shared chip runtime types. |
| Modify | `apps/live-control-ui/src/graphReference/index.ts` | Export the one supported public graph-reference API. |
| Create | `apps/live-control-ui/src/graphReference/GraphReferenceSearch.tsx` | Shared search/presentation component; production module may not import planSurface. |
| Create | `apps/live-control-ui/src/graphReference/GraphReferenceSearch.test.tsx` | Prove loading/ready/unavailable/error, matching, provenance labels, View, and insert-disabled behavior. |
| Create | `apps/live-control-ui/src/graphReference/searchGraphReferences.ts` | Surface-neutral deterministic matching/sorting over a neutral search item or graph projection node contract. |
| Create | `apps/live-control-ui/src/graphReference/searchGraphReferences.test.ts` | Freeze matching, normalization, ordering, and limit behavior. |
| Create | `apps/live-control-ui/src/graphReference/referenceFromGraphNode.ts` | Construct exact graph-native RunbookReferenceAttrs without Plan vocabulary or ID sanitization. |
| Create | `apps/live-control-ui/src/graphReference/referenceFromGraphNode.test.ts` | Prove exact ID and label mapping, including punctuation/colon IDs. |
| Create | `apps/live-control-ui/src/graphReference/resolveGraphReference.ts` | Own pure graph projection indexing, exact-ID resolution, unique-only alias/label lookup, explicit ambiguity, miss/error/fallback adaptation contract. |
| Create | `apps/live-control-ui/src/graphReference/resolveGraphReference.test.ts` | Prove the identity, ambiguity, fallback, graph-native miss, and graph-error matrices. |
| Create | `apps/live-control-ui/src/graphReference/insertMarkdownReference.ts` | Execute the existing TipTap insert command against an explicit editor/attrs input; no DOM or local-storage reads. |
| Create | `apps/live-control-ui/src/graphReference/insertMarkdownReference.test.ts` | Prove focus/insert command behavior, exact attrs, and null-editor no-op/failure result. |
| Create | `apps/live-control-ui/src/graphReference/useOpenGraphReference.ts` | Surface-neutral hook over the app-scoped host's neutral openGraphReference action. |
| Create | `apps/live-control-ui/src/graphReference/useOpenGraphReference.test.tsx` | Prove the hook forwards exact neutral payload and stays lease-authorized through the host. |
| Create | `apps/live-control-ui/src/graphReference/graphReference.css` | Own shared search/reference presentation selectors if visual selectors move out of Plan. |
| Modify | `apps/live-control-ui/src/planSurface/planSurface.css` | Remove or retain only Plan layout selectors after shared reference styles move; no duplicate shared selectors. |

### App-scoped projection host

| Action | Path | Purpose |
|---|---|---|
| Modify | `apps/live-control-ui/src/agentInteraction/agentInteractionTypes.ts` | Replace Plan-named public reference state/actions with neutral graph-reference contracts. |
| Modify | `apps/live-control-ui/src/agentInteraction/AgentInteractionProvider.tsx` | Store/open/register neutral graph references under exact Surface leases; preserve R10a stale-callback and cleanup invariants. |
| Modify | `apps/live-control-ui/src/agentInteraction/AgentInteractionProvider.test.tsx` | Prove neutral registration, open/close/expand, surface replacement, late cleanup, and disabled Build path. |
| Modify | `apps/live-control-ui/src/planSurface/projection/projectionBindings.ts` | Replace PlanReferenceProjectionBinding with the neutral binding import or a Plan action adapter that does not redefine the contract. |
| Modify | `apps/live-control-ui/src/planSurface/projection/projectionContext.tsx` | Adapt existing consumers to the neutral host state/actions; do not maintain a second Plan public API. |
| Modify | `apps/live-control-ui/src/planSurface/projection/AdaptiveProjectionContainer.tsx` | Consume neutral active reference/projection state/binding while preserving singular host and Graph Review tool behavior. |
| Modify | `apps/live-control-ui/src/planSurface/projection/AdaptiveProjectionContainer.test.tsx` | Prove resolved/ambiguous/unresolved content, Expand/close, and sibling diagnostics regression. |
| Modify | `apps/live-control-ui/src/planSurface/projection/projectionRegistry.tsx` | Render the current Plan reference card from the neutral resolution contract; Plan-specific actions remain an adapter, not shared state. |

### Plan as characterized consumer

| Action | Path | Purpose |
|---|---|---|
| Modify | `apps/live-control-ui/src/planSurface/components/PlanSurfaceCanvas.tsx` | Use shared search, exact reference constructor/inserter, neutral resolution, and neutral app-host open action while preserving visible behavior. |
| Delete | `apps/live-control-ui/src/planSurface/components/PlanGraphRefSearch.tsx` | Remove the Plan-owned search implementation after the shared component is adopted. |
| Delete | `apps/live-control-ui/src/planSurface/components/PlanGraphRefSearch.test.tsx` | Replace with shared component tests plus Plan integration tests. |
| Modify | `apps/live-control-ui/src/planSurface/PlanSurfaceInsertChip.test.tsx` | Prove search → insert → chip-open workflow through the shared capability. |
| Modify | `apps/live-control-ui/src/planSurface/PlanSurfaceShell.test.tsx` | Preserve Plan shell/app-host interaction and no duplicate container behavior if current assertions name Plan reference fields. |
| Modify | `apps/live-control-ui/src/planSurface/reference/graphAwareReferenceResolver.ts` | Reduce to a Plan compatibility adapter/re-export over the neutral resolver, or delete only if all current callers migrate within this allowlist. It must no longer own duplicate pure graph identity logic. |
| Modify | `apps/live-control-ui/src/planSurface/reference/graphAwareReferenceResolver.test.ts` | Retain only Plan-specific fallback/lens adapter tests; pure identity tests move to shared resolver tests. |
| Modify | `apps/live-control-ui/src/planSurface/reference/usePlanGraphReferenceResolver.ts` | Keep Plan projection loading/lens/corpus acquisition; return and resolve through neutral contracts. |
| Modify | `apps/live-control-ui/src/planSurface/reference/resolvePlanRelationshipTarget.ts` | Return the neutral resolution contract while preserving exact-target and stale/failure behavior. |
| Delete | `apps/live-control-ui/src/planSurface/reference/runbookReferenceFromGraphNode.ts` | Remove Plan-owned exact-reference constructor after migration. |
| Delete | `apps/live-control-ui/src/planSurface/reference/runbookReferenceFromGraphNode.test.ts` | Replace with shared constructor test. |
| Delete | `apps/live-control-ui/src/planSurface/reference/searchGraphProjectionNodes.ts` | Remove Plan-owned pure search helper after migration. |
| Modify | `apps/live-control-ui/src/planSurface/reference/PlanReferenceObjectCard.tsx` | Adapt Plan-specific actions/escalation copy to neutral resolution/binding types; preserve shared GraphObjectProjectionCard rendering and stale relationship suppression. |
| Modify | `apps/live-control-ui/src/planSurface/reference/PlanReferenceObjectCard.test.tsx` | Prove explicit ambiguity, fallback/error copy, relationship traversal, and stale completion with neutral types. |

### Bounded discovery exception

```
Directories:
  apps/live-control-ui/src/planSurface/reference/
  apps/live-control-ui/src/planSurface/projection/
  apps/live-control-ui/src/agentInteraction/

Maximum additional paths:
  5

Allowed path kinds:
  Existing TypeScript/TSX tests or compatibility adapters that directly import one of the Plan-named types/actions being removed.

Decision rule for including one:
  `rg` on the finalized base proves the file is a current importer of a renamed contract, and compilation or an owning-boundary regression test cannot remain truthful without updating it. The file may only rename/adapt the same graph-reference contract; it may not add behavior.

Required report when a path is added:
  Exact path, importing symbol, reason it was not visible in the initial inventory, diff purpose, and §7 proof covering it.
```

If any non-test production path outside the table is required for new behavior rather than direct contract migration, stop and report it. Unrestricted globs are prohibited.

## §5 Files and capabilities explicitly out of scope

| Path, layer, or capability | Why this slice must not touch or claim it |
|---|---|
| `apps/live-control-ui/src/buildSurface/**` | Build enablement is the named successor and a separately dogfoodable outcome. |
| `apps/live-control-ui/src/agentInteraction/projectionSurfacePublication.ts` | Build/Surface config generalization is not needed to neutralize the current host API; requiring it is a stop condition. |
| `apps/live-control-ui/src/planSurface/types.ts` / SurfaceConfig redesign | Discriminated Build lens/context belongs to the successor. Do not fabricate Plan state or redesign Surface configuration here. |
| `apps/live-control-ui/src/tiptap/references/runbookReferences.ts` | Existing durable reference attrs/type and syntax must remain unchanged. |
| `apps/live-control-ui/src/tiptap/extensions/RunbookReferenceNode.ts` and serializer/parser files | No durable Markdown/Tiptap representation change is authorized. |
| `apps/live-control-ui/src/markdownCanvas/**` | Shared canvas and Build editor integration are successors; Plan remains the characterized consumer here. |
| `apps/live_control_server/**` | No backend or API contract change is needed. |
| `src/graph_memory/**` | World Graph identity/projection behavior is consumed, not changed. |
| `apps/live-control-ui/src/api/types.ts` | Existing projection payload shapes are predecessor authority; do not invent new API fields. |
| `apps/live-control-ui/src/App.tsx` | The singular app-scoped container is already mounted. No host relocation or extra provider. |
| Graph Review diagnostics/live-state implementation | Sibling host path is regression-only. Do not refactor its payload or authority. |
| Build graph lens, source resumption, styling, extraction inspector | Separate product milestones. |
| Corpus fallback redesign or removal | Preserve current Plan compatibility policy. Build successor may choose graph-native-only behavior separately. |
| Reference revision pin/head behavior | Persistent semantics are not yet frozen and require a separate durable-contract slice. |
| Candidate-to-reference insertion | Extraction candidates are not graph nodes. Candidate-assisted Find existing is a successor. |
| Graph object creation, merge, split, alias correction, binding, or publication | Governed Graph Review/Kernel write workflows own these capabilities. |
| Statblock Workbench integration | Separate contextual tool-handoff milestone. |
| Bottom Agent Bar/Pane redesign or projection back-stack | Separate R10 remainder/product work. |
| Old PR #431 changes to App.tsx, api/types.ts, Graph Review workbench, or stale projection-host files | Those changes came from the diverged stack and are not part of this capability. |

Nearby work is not authorization. A manual proof may use the existing Plan Surface; building a new surface, panel, persistence mechanism, or report for proof is scope expansion.

## §6 Implementation contract and conditional matrices

### Required public contract

The precise implementation shape may vary, but the resulting public contract under `graphReference/` must be equivalent to the following behavior:

```typescript
type GraphReferenceProjectionState =
  | "loading"
  | "ready"
  | "unavailable"
  | "error";

type GraphReferenceResolution =
  | {
      kind: "resolved_graph";
      locator: string;
      reference: RunbookReferenceAttrs | null;
      graphNodeId: string;
      graphObject: GraphObjectCardViewModel;
      projectionState: GraphReferenceProjectionState | null;
      message?: string | null;
    }
  | {
      kind: "resolved_corpus_fallback";
      locator: string;
      reference: RunbookReferenceAttrs | null;
      fallback: ReferenceResolution;
      projectionState: GraphReferenceProjectionState | null;
      message?: string | null;
    }
  | {
      kind: "ambiguous";
      locator: string;
      reference: RunbookReferenceAttrs | null;
      matchingGraphNodeIds: string[];
      projectionState: GraphReferenceProjectionState | null;
      message: string;
    }
  | {
      kind: "unresolved";
      locator: string;
      reference: RunbookReferenceAttrs | null;
      projectionState: GraphReferenceProjectionState | null;
      message: string;
    }
  | {
      kind: "error";
      locator: string;
      reference: RunbookReferenceAttrs | null;
      projectionState: GraphReferenceProjectionState | null;
      message: string;
    };

interface GraphReferenceProjectionBinding {
  resolverState: GraphReferenceProjectionState | null;
  resolveRelationship(
    relationship: GraphObjectRelationshipViewModel,
  ): Promise<GraphReferenceResolution>;
  openResolvedReference(
    resolution: GraphReferenceResolution,
    projectionState?: GraphReferenceProjectionState | null,
  ): void;
  openTool(toolId: string): void;
}
```

Equivalent naming is permitted only if:

- the status variants remain explicit and mutually exclusive;
- ambiguity is not encoded merely as optional metadata on unresolved;
- graph-native exact ID is distinguishable from compatibility resolution;
- production graphReference modules import no planSurface files;
- all current Plan callers migrate to the one contract;
- the PR body records any naming deviation.

### Search item contract

The shared search component must not require a PlanSessionDescriptor, PlanGraphLensProvider, Plan campaign context hook, or Plan-specific callbacks.

A neutral item must carry enough already-adapted display and action information, equivalent to:

```typescript
interface GraphReferenceSearchItem {
  nodeId: string;
  label: string;
  kind: string;
  role: string | null;
  summary: string | null;
  aliases: string[];
  scopeLabel: string;
  reference: RunbookReferenceAttrs;
  nodeView: GraphProjectionNodeView;
}
```

The Plan adapter may format scopeLabel using Plan campaign-label helpers before passing items to the shared component. The shared component must not import those helpers.

### Host action contract

The app-scoped host must expose one neutral content-open action equivalent to:

```typescript
openGraphReference({
  reference,
  resolution,
  projectionState,
  glanceOnly,
});
```

The exact signature may be flattened, but:

- it must capture the current Surface lease;
- it must require a valid current projection publication;
- identity/config mode disagreement fails closed;
- Build's current disabled publication remains unable to open content;
- an old callback must never become a wildcard against a later lease;
- active reference state and registered binding clear/revalidate on Surface identity change;
- there must not be both a public neutral API and a public Plan alias after migration.

### General contract

```
Input:
  WorldGraphProjection or pre-adapted graph node views
  RunbookReferenceAttrs
  optional precomputed corpus ReferenceResolution supplied only by the Plan adapter
  current projection state
  current exact Surface projection lease
  current editor handle for insertion
  current registered relationship/tool binding

Output:
  one neutral in-memory GraphReferenceResolution
  one exact graph-native RunbookReferenceAttrs value for selected nodes
  one app-scoped content projection request under the current Surface lease
  unchanged visible Plan reference behavior

Invariant:
  Every current Plan reference path uses one Plan-independent public contract,
  exact graph-native identity never rebinds, current compatibility fallback remains
  explicit, stale Surface operations fail closed, Build remains unenabled, and no new
  durable write authority is introduced.

Failure behavior:
  loading → deferred/unresolved loading state; no fallback
  graph error → explicit error; corpus fallback disabled
  graph unavailable → graph-native unresolved; legacy Plan compatibility may use its current corpus fallback
  graph exact miss → unresolved; no label/corpus rebind
  ambiguous alias/label → explicit ambiguous result; no fallback/open
  missing editor → insertion fails/no-ops truthfully; no DOM search
  stale Surface lease → open/close/expand/register callback no-op
  replaced relationship binding → late completion discarded
  missing projection binding → content may render read-only; relationship/tool actions fail closed

Replay / idempotency:
  same resolver input → same resolution result
  same open action under current lease → current content may be replaced with the same exact object; no durable duplicate
  same insert action → a second user-requested reference may be inserted; no hidden deduplication
  retry after graph loading/unavailable → fresh caller invocation resolves against current supplied projection/state
  retry after Surface change → old captured callback remains invalid; caller must use new Surface binding

Trust boundary:
  Verifies:
    exact node ID membership in the supplied projection
    unique-only normalized label/alias match for compatibility references
    current Surface lease identity before changing app-scoped projection state
    current relationship binding identity before applying async completion
  Records or trusts without proving:
    supplied projection is the authorized coherent graph revision
    supplied corpus fallback was produced by the existing corpus resolver
    display label, role, summary, and scope label are presentation fields
  Rejects:
    first-win alias selection
    graph-native label rebinding
    hidden corpus fallback for graph-native references
    stale Surface callbacks
    Plan session fabrication inside shared modules
```

### Commit point

Not applicable — this slice adds no new irreversible or partially durable operation.
The only document mutation is the existing TipTap insertion command and existing Plan
save pipeline, whose durable commit contract is unchanged and regression-tested.

### A. State and fallback matrix

| Observable path | Loading / initializing | Exact success | Ordinary miss | Dependency unavailable | Integrity / contract failure | Stale / superseded | Retry / replay |
|---|---|---|---|---|---|---|---|
| Shared search | Status only; no rows/actions | Filter/sort current supplied items | "No objects match" | unavailable status | error status | Caller supplies refreshed items/state | Re-render with new inputs |
| Graph-native reference resolution | Deferred/unresolved; no fallback | Exact refId found in projection | Explicit unresolved | Explicit unresolved; no corpus fallback | Explicit error | Caller must resolve against current projection | New invocation only |
| Legacy compatibility resolution | Deferred while loading | Unique exact/label/alias graph match | Plan adapter may supply current corpus fallback | Plan adapter may supply current corpus fallback only under existing rules | Graph error; fallback disabled | Caller must resolve against current projection | New invocation only |
| Ambiguous legacy match | N/A | N/A | N/A | N/A | Explicit ambiguous with matching IDs; no open/fallback | Remains tied to supplied projection | Re-resolve after projection changes |
| Search result Inspect | Disabled/deferred only if no valid host publication | Open exact resolved graph object | No action | No action | No action | Lease guard rejects stale callback | New current-lease callback |
| Search result Insert | Disabled if editor absent/locked | Existing exact attrs inserted at current selection | No action | No action | No DOM/local-storage fallback | Editor/session owns stale state | Explicit new user action |
| Chip open | Resolution state shown truthfully | Compact content projection | Unresolved card | Unavailable card/state | Error card/state | Surface-change clears/revalidates | Explicit new click |
| Relationship traversal | Block while resolver loading/error | Resolve target and open under same binding/lease | Unresolved target state | Unresolved/unavailable | Error state | Late completion discarded | Explicit new click |
| Graph Review diagnostics sibling path | Existing behavior | Existing diagnostics panel | Existing behavior | Existing behavior | Existing behavior | Existing lease rules | Existing behavior |
| Build current path | No graph-reference capability | Remains unenabled | N/A | N/A | N/A | Existing Build publication rules | Successor only |

No unnamed fallback source is permitted.

### B. Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback permitted? |
|---|---|---|---|
| Graph-native exact ID | refType=graph-node; trim surrounding whitespace only; exact refId lookup in projection | Not ambiguous: found exact ID or miss | No label, alias, normalized-key, or corpus fallback |
| Search-selected node | Construct reference from exact node ID; preserve punctuation/colons; label is display only | Search item already identifies one exact node | No alternative identity lookup during insertion |
| Legacy locator/refId | Existing candidate order may be used, but every normalized label/alias lookup is unique-only | Explicit ambiguous with all matching node IDs | Corpus fallback only after ordinary graph miss under current Plan rules |
| Legacy label/alias | Unique-only normalized key | Explicit ambiguity; never first match | Same current Plan fallback rule; ambiguity blocks fallback |
| Normalized key | Compatibility references only | More than one match is ambiguous | Never for graph-native refs |
| Rename | Graph-native reference continues by stable node ID; display label may update from projection | N/A | No rebind |
| Deletion / missing from projection | Graph-native becomes unresolved for the supplied projection | N/A | No rebind |
| Recreated object with same label | New ID is a different object | Label collision is ambiguous for compatibility refs | No graph-native rebind |
| Campaign/source scope label | Presentation only; not identity | N/A | N/A |

First-win matching is prohibited. Display labels never substitute for durable graph identity.

### C. Persistence and replay matrix

| Operation | Durable representation | Round-trip guarantee | Duplicate / replay behavior | Compatibility / migration | Rollback / reversion |
|---|---|---|---|---|---|
| Insert existing graph object | Existing RunbookReferenceAttrs and current TipTap/Markdown reference syntax | Exact refType, refId, and label survive current Plan save/reload | A second explicit insertion creates a second reference; no hidden dedupe | No schema/version change | Existing document conflict/recovery path |
| Resolve/open graph reference | In-memory only | No persistence claimed | Repeated open replaces/selects app-scoped current projection | No migration | Close or Surface change clears state |
| Register relationship binding | In-memory Surface lease | Registration valid only for exact lease | New registration replaces current binding for that lease | No migration | Cleanup token removes only its own registration |
| Neutral TypeScript resolution contract | Caller-facing compile-time/in-memory API | Current Plan behavior maps losslessly | Deterministic pure resolution for same inputs | Plan callers migrate in same PR; no persistent migration | Revert PR as one capability |
| Existing Plan document save | Existing workspace-document revision/receipt | Existing reference round-trip remains green | Existing writer semantics unchanged | No change | Existing conflict/recovery |

**Stop condition:** Any need to modify RunbookReferenceAttrs, the TipTap node schema, Markdown serializer/parser, workspace-document format, or migration behavior is a second durable contract and must not be absorbed.

### D. Predecessor-to-consumer mapping

Grounding sources:

- `apps/live-control-ui/src/planSurface/reference/graphAwareReferenceResolver.ts`
- `apps/live-control-ui/src/planSurface/reference/usePlanGraphReferenceResolver.ts`
- `apps/live-control-ui/src/planSurface/components/PlanGraphRefSearch.tsx`
- `apps/live-control-ui/src/planSurface/components/PlanSurfaceCanvas.tsx`
- `apps/live-control-ui/src/agentInteraction/AgentInteractionProvider.tsx`
- `apps/live-control-ui/src/planSurface/projection/projectionBindings.ts`
- existing owning tests on the finalized base

| Predecessor field/outcome | Real shape and optionality | Neutral consumer field/behavior | Transformation | Proof |
|---|---|---|---|---|
| PlanGraphProjectionState | `"loading" \| "ready" \| "unavailable" \| "error"` | GraphReferenceProjectionState with identical variants | Rename/move only | E2, E3 |
| PlanReferenceResolution.kind="graph-node" | Exact graph object and graphNodeId; optional refType/refId; source world-graph | kind="resolved_graph" | Lossless field mapping | E2 |
| kind="corpus-index" | Precomputed ReferenceResolution; no graph object | kind="resolved_corpus_fallback" | Lossless field mapping | E2 |
| kind="unresolved" + nonempty ambiguousNodeIds | Ambiguity encoded as optional metadata | kind="ambiguous" + matchingGraphNodeIds | Make state explicit; preserve all IDs/message | E2, E6 |
| kind="unresolved" without ambiguous IDs | Miss/unavailable/deferred | kind="unresolved" | Preserve locator/reference/state/message | E2 |
| kind="error" | Graph load/contract error; fallback disabled | kind="error" | Preserve message/state | E2 |
| RunbookReferenceAttrs from graph node | {kind:"ref", refType:"graph-node", refId: exact node_id, label} | Same exact object | Move constructor only | E4 |
| PlanGraphRefSearch node props | GraphProjectionNodeView[], Plan state, Plan campaign label formatting | neutral search items + neutral state | Plan adapts presentation label before shared component | E3, E7 |
| openContentFromChip / openPlanReferenceResolution | Plan-named host actions with current lease closure | one neutral openGraphReference action | Consolidate without changing projection semantics | E5, E7 |
| activePlanReference | app-scoped active Plan resolution | activeGraphReference | Rename/type migration | E5/E6 |
| planProjectionState | active content resolver state | graphReferenceProjectionState | Rename/type migration | E5/E6 |
| PlanReferenceProjectionBinding | resolver, relationship open, tool open | GraphReferenceProjectionBinding | Move public contract; Plan supplies implementation | E5/E6 |
| Plan resolved graph card | GraphObjectProjectionCard via PlanReferenceObjectCard | Same shared card; Plan actions injected by Plan adapter | Type migration only | E6/E7 |
| Plan corpus fallback card | Plan-specific corpus model/actions | Remains Plan adapter over neutral resolution | Preserve visible behavior | E6/E8 |
| Plan unresolved repair link | Plan session-aware /ingest link | Remains Plan adapter concern | Not moved into shared identity contract | E6 |

Invented "close enough" fixture vocabulary is prohibited. Tests must use actual RunbookReferenceAttrs, graph projection node IDs, and current resolution payload shapes.

## §7 Evidence required to merge

All commands run from the repository root unless a `cd` is shown.

### Evidence ledger

| ID | Guarantee / invariant clause | Owning boundary | Evidence class | Command or manual scenario | Expected evidence | Stop condition |
|---|---|---|---|---|---|---|
| E1 | Production graphReference modules import no planSurface symbols and no shared component wraps PlanGraphRefSearch | Shared package boundary | Contract/static | `! rg -n 'planSurface\|PlanGraphRefSearch\|PlanReferenceResolution\|PlanReferenceProjectionBinding' apps/live-control-ui/src/graphReference --glob '!.test.*'` | Exit 0; no prohibited production imports/names | Any prohibited import/wrapper remains |
| E2 | Exact-ID, unique alias, explicit ambiguity, miss, error, and fallback matrices hold | Pure resolver | Contract/adversarial | `cd apps/live-control-ui && npm test -- --run src/graphReference/resolveGraphReference.test.ts src/planSurface/reference/graphAwareReferenceResolver.test.ts` | All matrix cases pass with real predecessor shapes | Graph-native fallback/rebind, first-win alias, or changed Plan fallback |
| E3 | Shared search preserves current matching, state, View, provenance, and insert-disabled behavior | Shared component | Component/regression | `cd apps/live-control-ui && npm test -- --run src/graphReference/GraphReferenceSearch.test.tsx src/graphReference/searchGraphReferences.test.ts` | Current Plan search behavior is represented without Plan provider dependency | Shared component needs Plan context or changes behavior |
| E4 | Exact graph-native attrs are constructed and inserted at current editor selection without DOM/local-storage reads | TipTap helper | Contract/component | `cd apps/live-control-ui && npm test -- --run src/graphReference/referenceFromGraphNode.test.ts src/graphReference/insertMarkdownReference.test.ts` | Exact IDs including colons survive; null/locked input is truthful | Reference schema or serializer change required |
| E5 | Neutral host registration/open/close/expand obey exact Surface lease and old callbacks cannot affect a new Surface | AgentInteractionProvider | Adversarial/integration | `cd apps/live-control-ui && npm test -- --run src/agentInteraction/AgentInteractionProvider.test.tsx src/graphReference/useOpenGraphReference.test.tsx` | Late cleanup/callback tests pass; Build disabled path remains false | Stale callback acts, Build becomes enabled, or second host introduced |
| E6 | Adaptive container and Plan card render neutral resolved/fallback/ambiguous/error state; late relationship completion is discarded; diagnostics sibling path remains | Container/renderer | Adversarial/regression | `cd apps/live-control-ui && npm test -- --run src/planSurface/projection/AdaptiveProjectionContainer.test.tsx src/planSurface/reference/PlanReferenceObjectCard.test.tsx` | Same object card/actions; explicit ambiguity; stale binding suppressed; diagnostics unaffected | New selected-object renderer or Graph Review regression |
| E7 | Plan's user-visible loop remains interaction-equivalent through the neutral capability | Plan workflow | Integration | `cd apps/live-control-ui && npm test -- --run src/planSurface/PlanSurfaceInsertChip.test.tsx src/planSurface/PlanSurfaceShell.test.tsx` | Locked search/View, unlock/Insert, exact attrs, chip click, shared projection all pass | Plan behavior changes or direct Plan helper path remains |
| E8 | Existing reference/projection and sibling tests remain green | Live Control UI | Regression | `cd apps/live-control-ui && npm test -- --run src/graphReference src/agentInteraction src/planSurface/reference src/planSurface/projection src/planSurface/PlanSurfaceInsertChip.test.tsx src/planSurface/PlanSurfaceShell.test.tsx` | All selected suites pass | New failure without explicit base/head evidence |
| E9 | Full UI test suite remains green | Package | Regression | `cd apps/live-control-ui && npm test -- --run` | All tests pass, or baseline protocol records exact pre-existing failures | Unexplained failure |
| E10 | Type and production bundle remain valid | Package | Build/type | `cd apps/live-control-ui && npm run typecheck && npm run build` | Both exit 0 | Compile/build failure |
| E11 | Diff is bounded and clean | Repository | Scope | `git diff --check && git diff --stat <BASE>...HEAD -- <§4-paths> && git diff --name-only <BASE>...HEAD` | No whitespace errors; every path in §4/bounded exception | Unexpected path |
| E12 | Existing Plan Surface works with real graph data | Existing /plan Surface | Manual/dogfood | Scenario below | Search/View while locked; Insert after unlock; chip opens same exact object; no save required | Requires new UI, Build changes, or cannot identify exact object |

### Required adversarial test cases

E2, E5, and E6 must include named tests for all of the following:

- graph-native exact ID with matching wrong label → exact ID wins;
- graph-native missing ID with uniquely matching display label → unresolved, no rebind;
- two legacy alias matches → ambiguous, all IDs retained, no fallback;
- graph error + available corpus fallback fixture → error, fallback disabled;
- graph unavailable + graph-native ref → unresolved, no fallback;
- graph unavailable + legacy ref + corpus fallback → current Plan fallback succeeds;
- relationship resolution completes after binding replacement → no open;
- open callback captured before Surface replacement → no-op after replacement;
- old cleanup executes after new Surface registration → new registration survives;
- Graph Review diagnostics registration remains independently authorized.

### Import boundary proof

The worker must also run:

```bash
rg -n \
  'Plan(Graph|Reference|Session)|planSurface|PlanGraphRefSearch|openPlanReference|activePlanReference|registerPlanReference' \
  apps/live-control-ui/src/graphReference \
  --glob '!*.test.*'
```

Expected result: no production matches except explanatory comments explicitly naming rejected legacy symbols. Prefer removing those comments too.

### Minimal live / dogfood proof

```
Existing surface used:
  /plan with an existing Longmont C2 planning document and a ready World Graph projection.

Smallest realistic scenario:
  1. Open Plan with editing locked.
  2. Search for a known exact object such as Mireward Reach or Tripod Null-Calf.
  3. Open View; confirm the shared object projection appears while Insert remains disabled.
  4. Close the projection.
  5. Unlock editing.
  6. Insert the exact graph reference at the cursor.
  7. Click the inserted chip.
  8. Confirm the same exact node ID/object opens in the shared projection.
  9. Do not save; discard/reload the local edit after evidence capture.
  10. Navigate to Build and confirm no new graph-reference search, content projection, or tools appeared there.

Expected observation:
  Plan behavior is visibly unchanged, exact identity is preserved, and Build remains unenabled.

Evidence captured:
  PR body records the object label and exact node ID used, screenshots or short recording,
  whether editing was locked/unlocked, and confirmation that no durable save occurred.
```

If this proof requires a new search surface, fixture management UI, persistence mechanism, or dedicated panel, stop for split review.

### Required command block

Replace `<BASE>` with the finalized immutable implementation base.

```bash
cd apps/live-control-ui
npm test -- --run \
  src/graphReference/resolveGraphReference.test.ts \
  src/graphReference/GraphReferenceSearch.test.tsx \
  src/graphReference/searchGraphReferences.test.ts \
  src/graphReference/referenceFromGraphNode.test.ts \
  src/graphReference/insertMarkdownReference.test.ts \
  src/graphReference/useOpenGraphReference.test.tsx \
  src/agentInteraction/AgentInteractionProvider.test.tsx \
  src/planSurface/reference/graphAwareReferenceResolver.test.ts \
  src/planSurface/reference/PlanReferenceObjectCard.test.tsx \
  src/planSurface/projection/AdaptiveProjectionContainer.test.tsx \
  src/planSurface/PlanSurfaceInsertChip.test.tsx \
  src/planSurface/PlanSurfaceShell.test.tsx

npm test -- --run \
  src/graphReference \
  src/agentInteraction \
  src/planSurface/reference \
  src/planSurface/projection \
  src/planSurface/PlanSurfaceInsertChip.test.tsx \
  src/planSurface/PlanSurfaceShell.test.tsx

npm test -- --run
npm run typecheck
npm run build
cd ../..

! rg -n \
  'planSurface|PlanGraphRefSearch|PlanReferenceResolution|PlanReferenceProjectionBinding|openPlanReference|activePlanReference|registerPlanReference' \
  apps/live-control-ui/src/graphReference \
  --glob '!*.test.*'

git diff --check
git diff --stat <BASE>...HEAD -- \
  apps/live-control-ui/src/graphReference \
  apps/live-control-ui/src/agentInteraction/AgentInteractionProvider.tsx \
  apps/live-control-ui/src/agentInteraction/AgentInteractionProvider.test.tsx \
  apps/live-control-ui/src/agentInteraction/agentInteractionTypes.ts \
  apps/live-control-ui/src/planSurface/components/PlanSurfaceCanvas.tsx \
  apps/live-control-ui/src/planSurface/components/PlanGraphRefSearch.tsx \
  apps/live-control-ui/src/planSurface/components/PlanGraphRefSearch.test.tsx \
  apps/live-control-ui/src/planSurface/PlanSurfaceInsertChip.test.tsx \
  apps/live-control-ui/src/planSurface/PlanSurfaceShell.test.tsx \
  apps/live-control-ui/src/planSurface/reference \
  apps/live-control-ui/src/planSurface/projection \
  apps/live-control-ui/src/planSurface/planSurface.css

git diff --name-only <BASE>...HEAD
```

### Baseline failure protocol

For any required command already failing on the finalized base:

- run the identical command on base and head;
- record exact failing tests/errors and environment;
- state whether head introduces any new failure;
- do not call the gate green;
- identify the explicit operator waiver needed if the failing command remains an acceptance gate.

Required table in the PR body:

| Command | Base result | Head result | New failure introduced? | Acceptance effect | Waiver |
|---|---|---|---|---|---|
| `<command>` | `<result>` | `<result>` | Yes / No | blocked / acceptable with waiver | none / exact waiver |

## §8 Required PR description and implementation handback

The PR description must use the frontmatter skeleton and remain current throughout review.

It must include:

- §1 Mission copied exactly.
- §1 merge-ready invariant copied exactly.
- The complete §7 evidence ledger with required evidence, produced result, and provenance.
- Finalized base SHA and head SHA.
- Confirmation that branch tip equaled the declared base before implementation.
- Confirmation that no commit/code was cherry-picked or rebased from old head `e3919d5b13e0066cc3ed46dc51fddb27c29914a0`.
- Actual changed paths and focused diff stat limited to §4.
- Every §7 command/scenario and exact result.
- Provenance of each result: author-local; independently rerun local; CI; manual/dogfood.
- Baseline failures with base/head comparison.
- Explicit operator waivers; write none when none exist.
- Paths outside §4; write none or include a stop report.
- Bounded-discovery paths and why each qualified; write none when none were used.
- Stop conditions encountered and resolution; write none when none exist.
- Deviations from §6 contracts/matrices; write none when none exist.
- Named successor capabilities deferred and still false.
- Confirmation that:
  - Build was not modified or enabled;
  - RunbookReferenceAttrs and serializer/parser files were not changed;
  - no backend/API/graph write contract changed;
  - one app-scoped provider/container remains;
  - no Plan-named public aliases remain in graphReference;
  - the old Plan duplicate search/helpers were removed where no named consumer remained.
- Confirmation that the authoritative handoff was implemented without compressed or omitted constraints.

A generic Summary/Test Plan PR body is not acceptable.

## §9 Acceptance rubric

The reviewer accepts only when every bullet is true and each behavioral bullet names its §7 proof.

- Exactly one independently useful capability was delivered: the surface-neutral existing-object graph reference lifecycle — proved by E1–E7 and diff review.
- The merge-ready invariant holds across every observable path and adversarial sequence in §3 — proved by E2–E7.
- Production graphReference modules import no planSurface module and expose no Plan-named public compatibility API — proved by E1.
- Shared search is a real neutral component, not a wrapper around PlanGraphRefSearch — proved by E1, E3, and deletion/diff review.
- Pure resolution logic has one owner; Plan retains only projection-loading/lens/corpus policy adapters — proved by E1, E2, and diff review.
- Graph-native references resolve exact ID only and never rebind through label, alias, normalized key, or corpus indexes — proved by E2.
- Legacy compatibility references preserve current unique-only graph lookup and corpus fallback rules — proved by E2.
- Ambiguity is an explicit neutral state and never silently opens the first candidate or falls back — proved by E2 and E6.
- Exact graph IDs, including punctuation and colons, are preserved through construction and insertion — proved by E4 and E7.
- Search and View remain available while Plan editing is locked; insertion remains blocked — proved by E3 and E7.
- App-scoped graph-reference state/actions are neutral, exact-lease guarded, and stale callbacks cannot act on a later Surface — proved by E5.
- Relationship traversal rejects late completion after binding or Surface replacement — proved by E6.
- The singular AgentInteractionProvider and AdaptiveProjectionContainer remain the only host/container — proved by diff review and E5/E6.
- Graph Review diagnostics remain interaction-equivalent as a sibling host path — proved by E5/E6/E8.
- Plan's search → View → Insert → chip-open behavior remains interaction-equivalent — proved by E7 and E12.
- Build gains no behavior and no Build file changes — proved by changed-path inspection and E5/E12.
- No new durable write authority or persistent reference representation was introduced — proved by §6C, E4/E7, and diff review.
- No serializer, parser, backend, API, graph kernel, or workspace-document contract changed — proved by changed-path inspection.
- Old Plan-local duplicate helpers/components are removed unless a named current consumer justified a bounded compatibility adapter — proved by diff/import search.
- The PR description restates the exact invariant and exposes a complete truthful evidence ledger.
- Every required proof has a produced result and provenance, or an explicit operator waiver.
- No path outside §4/bounded discovery changed — proved by E11.
- Baseline failures are reported truthfully and any required waiver is explicit.
- Minimal live proof did not grow into a new product or operator surface — proved by E12.
- The named successor, Build World Reference Loop v1, remains unimplemented and unclaimed.
- The branch began from the finalized base and did not integrate old head `e3919d5b13e0066cc3ed46dc51fddb27c29914a0`.

## Stop conditions

Stop and report rather than expanding if implementation discovers:

- the target branch tip does not equal the declared implementation base;
- implementation requires rebasing, merging, or cherry-picking the old PR head;
- a second independently useful outcome;
- a new public/durable contract not owned by §1;
- an invariant that cannot govern every claimed observable path;
- required evidence that cannot be produced at the owning boundary;
- an untested adversarial sequence that can mutate or misreport state;
- a need to modify any Build path;
- a need to add Build publication/config/lens state;
- a need to modify SurfaceConfig or fabricate a Plan descriptor for a shared caller;
- a need to modify RunbookReferenceAttrs, TipTap reference nodes, Markdown parser/serializer, or migration behavior;
- a need for backend/API/World Graph changes;
- a need to broaden or remove corpus fallback to make the neutral model compile;
- a need to create a second selected-object renderer, provider, registry, or adaptive container;
- a need to move Graph Review diagnostics or change its payload/authority;
- unresolved identity, state, fallback, persistence, replay, or compatibility semantics;
- a predecessor contract materially different from §6D;
- a required path outside §4 or its bounded discovery exception;
- a new product/operator surface disguised as verification;
- a base/head failure requiring operator waiver before acceptance;
- inability to remove Plan-named public aliases without a named current consumer.

Use this report:

```
Stop condition:
Why the current mission cannot absorb it:
Invariant clause affected:
Required evidence now missing:
New public/durable contract discovered:
Affected observable paths or ownership layers:
Required path outside scope:
Old-branch dependency discovered:
Proposed successor or reconnaissance slice:
Tracker or authority update needed:
Operator decision required:
```

The worker must not resolve a stop condition by silently widening the mission, preserving duplicate APIs "temporarily," or presenting Build enablement as verification.
