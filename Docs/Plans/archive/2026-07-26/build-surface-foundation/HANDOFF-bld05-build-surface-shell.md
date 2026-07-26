# HANDOFF — BLD-05 Build configured Surface

- **Created:** 2026-07-22
- **Status:** SUPERSEDED pending rebuild — PR #390 draft parallel shell is not mergeable. Rebuild only after BLD-05a (`HANDOFF-bld05a-workspace-document-authoring-seam.md`) lands; Build must be a thin consumer of that seam.
- **Canonical handoff path:** `Docs/Plans/HANDOFF-bld05-build-surface-shell.md`
- **Suggested branch:** `agent/bld05-build-surface-shell`

## §0 Capability decomposition decision

| Candidate outcome | Independently useful? | Durable/public contract changed? | Decision |
|---|---:|---:|---|
| Add `/build` as a configured shared Surface for worldbuilding source authoring | Yes | Yes | Include |
| Add extraction launch/status | Yes | Yes | Successor: BLD-06 |
| Add candidate review/publication | Yes | Yes | Successor: BLD-07 |
| Generalize a second shell/projection/edit architecture | No — prohibited duplicate architecture | Yes | Reject |

**Selected capability:** a GM can author and reopen a worldbuilding workspace
document through Build as the second real consumer of the shared Surface system.

## §1 Mission

A GM can navigate to `/build` and create, classify, edit, safely save, and reopen
a `worldbuilding_source` document through the shared Surface, AppChrome, Agent
Interaction, theme, edit, and Markdown editor architecture without a session or
graph-publication requirement.

**Invariant:** Build supplies configuration and source adapters to the existing
shared Surface system; it does not create a second shell, projection container,
edit capability, navigation system, theme system, or graph write path.

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent product authority | `Docs/Plans/ROADMAP-build-surface-worldbuilding-ingest.md`, Phase 4 |
| Surface authority | `Docs/Design/ARCHITECTURE-plan-surface-toolbox.md` |
| Sequencing authority | `Docs/Plans/PLAN-build-surface-worldbuilding-ingest-pr-slices.md`, BLD-05 |
| Identity/persistence predecessor | BLD-02 workspace document API and BLD-03 source linkage types where displayed |
| Editor predecessor | BLD-01 shared Markdown editor |
| Repository rules | `AGENTS.md`, UI/git rules, `.cursor/rules/external-agent-pr-loop.mdc` |
| Base revision | Dispatch-time immutable merge SHA containing BLD-01/02/03 |
| Exact input consumed | `/build` route, optional workspace document UUID, shared Surface primitives/config, BLD-02 record/content APIs, and shared editor |
| Named successor | BLD-06 extraction toolbar and exact-run handoff |
| What remains false | no extraction launch, candidate projection, Graph Review commit, or PDF import |
| Explicit non-goals | new backend routes, second SurfaceShell architecture, second projection registry/container, Plan/Play redesign, graph cards/writes |

### Locked Surface decision

Build is the second configured product Surface. It must reuse:

```text
AppChrome
AgentInteractionProvider / shared app-level projection container
SurfaceConfig
SurfaceShell
shared edit capability
shared theme tokens
shared Markdown editor
```

`BuildSurfacePage` owns route-level data loading and Build adapters.
`buildSurfaceConfig.ts` declares Build identity, labels, theme, canvas/editor, and
enabled actions/projections through existing types.

A file named `BuildSurfaceShell.tsx` is permitted only as a thin Build-specific
composition around the shared `SurfaceShell`. It may not own private tool/edit
regions, private projection state, a second adaptive drawer/pane, or a parallel
Agent Interaction provider.

Read in order:

1. `Docs/Design/ARCHITECTURE-plan-surface-toolbox.md`
2. Build roadmap and slice plan
3. BLD-01 shared editor
4. BLD-02 workspace document API/identity contract
5. current `App.tsx`, `AppChrome`, Surface config/types, Agent Interaction provider,
   Plan surface composition, themes, and tests

Stop if the current repository lacks the shared Surface seam described by the
authority. Report the actual seam and propose the smallest shared generalization;
do not implement Build by copying Plan.

## §3 Observable-path inventory

| Path | Current behavior | Required behavior | Same invariant? | Boundary |
|---|---|---|---:|---|
| Direct `/build` | no route | render configured Build Surface | Yes | App route + Surface config |
| Shared chrome/nav | existing surfaces configured | one Build item using existing AppChrome config | Yes | AppChrome |
| Shared projection/agent host | app-level host exists/transitional seams | Build publishes ambient source context; no private container | Yes | Agent Interaction provider |
| New source | no Build flow | create BLD-02 `worldbuilding_source` UUID record | Yes | Build page + source API |
| Existing source | no Build route selection | exact `?documentId=<uuid>` load | Yes | Build page/router |
| Editor | Plan/Spike consumers | shared editor with Build adapter/tools | Yes | Build canvas/editor adapter |
| Metadata | no Build panel | explicit domain/class/authority/visibility/scope | Yes | Build source controls |
| Dirty/save/conflict | surface-specific | preserve content, show truthful lifecycle/conflicts | Yes | Build page/editor adapter |
| Refresh | route state may reset | reload exact UUID and committed content | Yes | Router/API |
| Navigation away dirty | existing behavior may vary | existing shared guard or explicit warning; no silent discard | Yes | shared surface/navigation seam |
| API unavailable/malformed record | existing errors | recoverable error; no fabricated source | Yes | Build page |
| Extraction/publication | absent | remains absent | Yes | scope/diff |

## §4 Files in scope — allowlist

| Action | Path | Purpose |
|---|---|---|
| Modify | `apps/live-control-ui/src/App.tsx` | Add `/build` route through existing app routing |
| Modify | `apps/live-control-ui/src/chrome/appChromeConfig.ts` | Add one Build navigation item through existing config |
| Create | `apps/live-control-ui/src/buildSurface/BuildSurfacePage.tsx` | Route data loading, exact document identity, and Surface context publication |
| Create | `apps/live-control-ui/src/buildSurface/BuildSurfaceShell.tsx` | Thin Build composition around shared `SurfaceShell` only |
| Create | `apps/live-control-ui/src/buildSurface/buildSurfaceConfig.ts` | Build `SurfaceConfig`, theme, source metadata controls, and enabled editor actions |
| Create | `apps/live-control-ui/src/buildSurface/BuildSurfacePage.test.tsx` | Route, UUID reload, error, and context-publication proof |
| Create | `apps/live-control-ui/src/buildSurface/BuildSurfaceShell.test.tsx` | Shared-shell composition, metadata, dirty/save/conflict proof |
| Modify | `apps/live-control-ui/src/App.test.tsx` | Route and navigation compatibility proof |
| Modify | `apps/live-control-ui/src/styles.css` | Build-specific layout using existing tokens only, if no scoped stylesheet seam exists |

### Bounded discovery exception

```text
Directory: apps/live-control-ui/src
Maximum additional paths: 3
Allowed path kinds: existing shared SurfaceConfig/SurfaceShell/AgentInteraction/theme type or test files
Decision rule: only to make Build a second consumer of an existing shared abstraction; no copied/replacement architecture
Required report: path, existing ownership seam, exact generalized contract, and why Build cannot consume it unchanged
```

## §5 Explicitly out of scope

| Path/capability | Why |
|---|---|
| `apps/live-control-ui/src/buildSurface/BuildIngestToolbar.tsx` | BLD-06 |
| backend files | BLD-02/03 provide required API; needing backend work is a stop |
| private Build projection registry/container/provider | violates shared Surface authority |
| copied Plan toolbar/edit/canvas implementation | duplicate architecture |
| Graph Review or publication APIs | BLD-07 |
| Plan/Play redesign | independent product work |
| `corpus/**`, `evals/**` | no content or benchmark mutation |

## §6 Implementation contract

```text
Input:
  /build route + optional documentId UUID + shared SurfaceConfig/Shell and Agent
  Interaction seams + BLD-02 workspace API + shared Markdown editor.

Output:
  configured Build Surface with exact source identity, metadata, editor state,
  save/conflict lifecycle, and ambient context publication.

Invariant:
  Build is a consumer/configuration of shared app architecture and writes only
  workspace source documents.

Failure behavior:
  no documentId → explicit new-source state
  unknown UUID → not-found state; never silently create replacement
  load failure/malformed record → recoverable error, no fabricated content
  invalid metadata → block save with field errors
  stale/save failure → preserve dirty content and current identity
  shared Surface seam absent → stop, do not copy Plan

Replay / idempotency:
  same URL UUID → same source load
  refresh after save → same UUID/revision/content
  create action → server-issued UUID; no title/path identity
  retry after conflict → re-read exact source before commit

Trust boundary:
  Verifies route selection, UUID, metadata shape, shared Surface composition,
  API responses, editor/save state, and ambient pointer context.
  Does not prove source truth, extraction readiness, or graph meaning.
```

### §6A State/fallback matrix

| Path | Success | Miss | Unavailable | Integrity failure | Stale | Retry |
|---|---|---|---|---|---|---|
| Route mount | configured Build Surface | new-source only with no ID | error state | no fake source | N/A | exact reload |
| Source load | exact record/editor | UUID 404 | recoverable error | reject malformed | conflict state | re-read exact UUID |
| Save | committed revision/clear dirty | no target invalid | preserve dirty | diagnostics/block | preserve dirty | explicit retry |
| Navigation | shared route change | N/A | current page remains | no silent discard | dirty warning/guard | user choice |
| Agent context | publish pointers only | absent selection allowed | host unavailable is app failure | no corpus body duplication | update pointer | republish |

### §6B Identity matrix

| Situation | Required rule | Ambiguity | Fallback |
|---|---|---|---|
| Route/document | exact workspace UUID | unknown 404 | new source only when ID absent |
| Title | display only | duplicates allowed | no lookup |
| Metadata | explicit enum/domain matrix | invalid blocks save | no default authority |
| Surface | existing `build` config ID/route | duplicate config fails tests | no hidden alternate route |
| Projection/context | pointers only | no content caching as authority | shared provider only |

### §6C Persistence/replay matrix

| Operation | Durable representation | Round trip | Replay | Compatibility | Reversion |
|---|---|---|---|---|---|
| Create/update/save | BLD-02 registry + Markdown | exact UUID/metadata/content | server CAS | plan/runbook unchanged | existing discard/backup |
| Local dirty state | existing shared/editor policy | visible and identity-bound | no duplicate writes | Plan behavior preserved | abandon/reload |
| Surface context | app pointer state | UUID/context only | republish on load | other surfaces unchanged | navigate away |

### §6D Predecessor mapping

| Predecessor | Build consumer | Transformation | Proof |
|---|---|---|---|
| shared `SurfaceConfig`/`SurfaceShell` | build config/page | configure existing regions and context | shell test |
| Agent Interaction provider | Build page | publish UUID/source metadata pointers only | page/provider test |
| BLD-01 editor | Build canvas | inject Build adapter/tools | shell test |
| BLD-02 record/API | page/metadata | exact UUID/metadata/revision | page test |
| AppChrome config | nav | one Build item | App test |

## §7 Verification ownership and commands

| Guarantee | Boundary | Command |
|---|---|---|
| `/build` route/nav | App router/AppChrome | `npm test -- --run src/App.test.tsx` |
| exact UUID load/refresh/error | Build page | `npm test -- --run src/buildSurface/BuildSurfacePage.test.tsx` |
| shared shell/editor/metadata/save states | Build shell | `npm test -- --run src/buildSurface/BuildSurfaceShell.test.tsx` |
| no Plan/shared architecture regression | shared consumers | `npm test -- --run src/planSurface` |
| type/build integrity | app | `npm run typecheck && npm run build` |
| no private duplicate architecture | diff/import inspection | changed-path checks |

```bash
cd apps/live-control-ui
npm test -- --run src/App.test.tsx
npm test -- --run src/buildSurface/BuildSurfacePage.test.tsx
npm test -- --run src/buildSurface/BuildSurfaceShell.test.tsx
npm test -- --run src/planSurface
npm run typecheck
npm run build
cd ../..
git diff --check
git diff --name-only "$(git merge-base HEAD origin/main)"...HEAD
```

### Minimal live proof

```text
Existing surface: application shell
Scenario: navigate directly to /build, create a source, edit/save, refresh exact
UUID, trigger invalid metadata and stale save, publish ambient selection context,
and navigate to Plan.
Expected: Build behaves through shared chrome/surface/editor/provider; dirty data
is preserved on failure and other surfaces remain intact.
```

## §8 Required handback

Record SHAs, actual paths including any bounded discovery, diff, all §7 results
and provenance, live proof, baseline failures, waivers, stop conditions, and a
specific statement that no private Surface/projection/edit/provider stack was
introduced.

## §9 Acceptance rubric

- [ ] `/build` is a real configured shared Surface.
- [ ] Build reuses the shared `SurfaceShell`, app-scoped projection/Agent Interaction host, edit capability, editor, and theme tokens.
- [ ] No Plan implementation was copied into a parallel Build architecture.
- [ ] Exact workspace UUID drives open/reload; labels and paths never act as identity.
- [ ] Metadata, dirty/save/conflict, and unavailable states are truthful.
- [ ] Build writes only workspace source documents and has no extraction/publication action.
- [ ] Existing Plan/App behavior remains green.
- [ ] Only §4 and approved bounded-discovery paths changed.

## Stop conditions

Stop if a backend change is required, BLD-02 cannot supply the source contract,
the shared Surface seam is materially different from authority, Build would need
a private provider/projection/edit stack, extraction controls are required for
this capability, or Plan/Play must be redesigned.
