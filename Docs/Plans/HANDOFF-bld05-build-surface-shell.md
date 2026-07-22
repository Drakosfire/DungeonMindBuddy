# HANDOFF — BLD-05 Build surface shell

- **Created:** 2026-07-22
- **Status:** DRAFT — dispatch only after BLD-01 and BLD-03 are merged and re-anchored
- **Canonical handoff path:** `Docs/Plans/HANDOFF-bld05-build-surface-shell.md`
- **Suggested branch:** `agent/bld05-build-surface-shell`

## Shared vocabulary

| Term | Definition |
|---|---|
| Build surface | Editor-first source authoring route; not a graph publication surface. |
| Source metadata | Domain, document class, authority, visibility, and optional scope shown with the document. |
| Shell | Route, page, layout, metadata panel, and save controls before extraction launch. |
| Surface adapter | Build-owned mapping from shared editor state to source-document persistence. |

## §1 Mission

A GM can navigate directly to `/build` and author, classify, save, and reopen a
worldbuilding source document through the shared Markdown editor without a
session-planning or graph-publication requirement.

**Invariant:** Build is an explicit source-authoring surface whose terminal
write is a reviewable source document, never a graph-head mutation.

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | `Docs/Plans/ROADMAP-build-surface-worldbuilding-ingest.md`, Phase 4 |
| Sequencing authority | `Docs/Plans/PLAN-build-surface-worldbuilding-ingest-pr-slices.md`, BLD-05 |
| Repository rules | `AGENTS.md`, `.cursor/rules/dungeonbuddy-git-workflow.mdc`, `.cursor/rules/external-agent-pr-loop.mdc` |
| Base revision | Dispatch-time immutable merge SHA containing BLD-01 and BLD-03; current `8ff2339f` is reference only |
| Predecessor contract | Shared Markdown editor, source-document API/registry, existing AppChrome and route conventions |
| Exact input consumed | URL route, source document record, source metadata, shared editor props, and save adapter |
| Named successor | BLD-06 extraction toolbar and run handoff |
| What remains false | Extraction launch, candidate graph rendering, Graph Review commit, PDF import |
| Explicit non-goals | New extraction API calls, graph cards, direct graph writes, raw filesystem access, Play redesign, Plan redesign |

Read in order:

1. `Docs/Plans/ROADMAP-build-surface-worldbuilding-ingest.md`
2. `Docs/Plans/PLAN-build-surface-worldbuilding-ingest-pr-slices.md`
3. `apps/live-control-ui/src/App.tsx`
4. `apps/live-control-ui/src/chrome/AppChrome.tsx`
5. `apps/live-control-ui/src/chrome/appChromeConfig.ts`
6. Shared editor and source-document API contracts
7. Existing AppChrome/App route tests

If current AppChrome has a different navigation ownership seam, preserve the
existing seam and stop if a second chrome is required.

## §3 Observable-path inventory

| Path | Current behavior | Required behavior | Same invariant? | Owning boundary |
|---|---|---|---:|---|
| Direct `/build` navigation | No Build page/route | Render real Build shell | Yes | App route |
| Primary navigation | Plan/Ingest/Play/etc. are configured | Build appears as one consistent surface item | Yes | AppChrome config |
| New source | No Build source creation flow | Create/open a source record with explicit metadata | Yes | Build page + source API |
| Editor load | Plan/Spike consumers only | Shared editor loads Build source content | Yes | Build page |
| Dirty/save state | Surface-specific | Build displays and respects source save state | Yes | Build shell/adapter |
| Missing source | Route may not have document | Show explicit empty/new-source state | Yes | Build shell |
| API unavailable | Existing surfaces show errors | Build shows recoverable error without fake content | Yes | Build shell |
| Browser refresh | Route state may reset | Reload exact source identity and metadata | Yes | Build page/source API |

## §4 Files in scope (allowlist)

| Action | Path | Purpose |
|---|---|---|
| Modify | `apps/live-control-ui/src/App.tsx` | Add `/build` route and page dispatch |
| Modify | `apps/live-control-ui/src/chrome/appChromeConfig.ts` | Add Build navigation item |
| Create | `apps/live-control-ui/src/buildSurface/BuildSurfacePage.tsx` | Build page composition |
| Create | `apps/live-control-ui/src/buildSurface/BuildSurfaceShell.tsx` | Editor/metadata/save layout |
| Create | `apps/live-control-ui/src/buildSurface/buildSurfaceConfig.ts` | Build source defaults and surface tools |
| Create | `apps/live-control-ui/src/buildSurface/BuildSurfacePage.test.tsx` | Route/page state proof |
| Create | `apps/live-control-ui/src/buildSurface/BuildSurfaceShell.test.tsx` | Metadata, dirty, save/error proof |
| Modify | `apps/live-control-ui/src/styles.css` | Build shell layout styles only |
| Modify | `apps/live-control-ui/src/App.test.tsx` | Route and navigation contract proof |

**Bounded discovery exception:** Not applicable — paths are enumerated.

## §5 Files and capabilities explicitly out of scope

| Path, layer, or capability | Why out of scope |
|---|---|
| `apps/live-control-ui/src/buildSurface/BuildIngestToolbar.tsx` | Extraction launch belongs to BLD-06 |
| `apps/live-control-ui/src/api/liveApi.ts` | API client changes belong to BLD-06 unless BLD-02 contract is incomplete; stop if so |
| `apps/live-control-ui/src/planSurface/**` | Plan is a compatibility consumer, not a Build dependency to redesign |
| `apps/live-control-ui/src/ingestSurface/**` | Ingest/Graph Review boundary remains separate |
| `apps/live-control-ui/src/playSurface/**` | Play remains an intentional stub |
| `apps/live_control_server/**` | No backend capability in this UI shell PR |
| `corpus/**`, `evals/**` | No content or benchmark mutation |

## §6 Implementation contract and conditional matrices

```text
Input:
  /build route, optional source-document ID, source registry record, source
  metadata, shared Markdown editor, and BLD-02 save adapter.

Output:
  A navigable Build surface with explicit metadata, editor state, save state,
  and source-document reload behavior.

Invariant:
  Build writes only source documents and remains unable to advance a graph head.

Failure behavior:
  Missing source → explicit new-source/empty state.
  Load failure → visible recoverable error; no fabricated document.
  Save failure/conflict → preserve dirty content and show stable error.
  Invalid metadata → block source save and show field-level validation.

Replay / idempotency:
  same URL/source ID → same document load;
  refresh after save → same source identity and committed content;
  retry after conflict → re-read current source before retry;
  navigation away with dirty state → existing surface guard/visible dirty state,
  never silent discard.

Trust boundary:
  Verifies: route selection, source metadata shape, editor/save state, and
  server responses.
  Records or trusts without proving: Markdown semantic truth and graph meaning.
```

### State and fallback matrix

| Path | Loading | Success | Miss | Dependency unavailable | Integrity failure | Stale | Retry |
|---|---|---|---|---|---|---|---|
| Route mount | Show shell loading state | Render source/editor | New-source state | Error state | No fabricated source | N/A | Reload exact source |
| Source load | Loading indicator | Populate metadata/editor | Explicit empty state | Recoverable error | Reject malformed record | Show conflict/reload action | Re-read source |
| Save | Disabled/working state | Clear dirty state on committed response | No target is validation error | Preserve dirty state | Show diagnostics | Preserve dirty state, reload/resolve | Explicit retry |
| Navigation | Current state visible | Route changes | N/A | Keep current page | Do not hide error | Do not silently discard | User retries |

### Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback |
|---|---|---|---|
| Route source ID | Use durable source-document ID | Unknown ID is explicit not-found | New source only when no ID |
| Display title | Never acts as identity | Duplicate titles allowed | No label lookup |
| Source metadata | Persist explicit enum values | Invalid combination blocks save | No default authority |
| Navigation item | Stable route key `/build` | Duplicate route is test failure | No alternate hidden route |

### Persistence and replay matrix

| Operation | Durable representation | Round-trip guarantee | Replay behavior | Compatibility | Rollback |
|---|---|---|---|---|---|
| New source | BLD-02 registry record | Reload retains metadata and ID | Duplicate handled by API | Plan/runbook unchanged | Delete only through existing API, not this PR |
| Editor draft | Local/React state owned by Build | Dirty state is visible | Refresh follows existing draft policy | Shared editor contract | No new draft store |
| Source save | BLD-02 prepare/commit response | Reload reads committed source | Conflict is explicit | Existing save adapter | Existing write rollback |

### Predecessor-to-consumer mapping

| Predecessor | Consumer | Transformation | Proof |
|---|---|---|---|
| App route switch | Build page | Add one route branch without changing existing route behavior | App test |
| AppChrome item config | Build nav | Add route/label/icon contract consistent with current chrome | AppChrome/App test |
| Shared editor | Build shell | Supply source adapter and Build tools | Shell test |
| Source record | Metadata panel | Render explicit domain/class/authority/visibility | Shell test |

## §7 Verification ownership map and commands

| Guarantee | Owning boundary | Command | Expected evidence |
|---|---|---|---|
| `/build` route renders | App router | `npm test -- --run src/App.test.tsx` | Direct route test green |
| Build nav is consistent | AppChrome/config | Same App test | Item/route assertions green |
| Metadata and dirty/save state work | Build shell | `npm test -- --run src/buildSurface/BuildSurfaceShell.test.tsx` | State/error tests green |
| Refresh loads exact source | Build page | `npm test -- --run src/buildSurface/BuildSurfacePage.test.tsx` | Source ID preserved |
| No backend/extraction scope creep | Git | `git diff --name-only "$(git merge-base HEAD origin/main)"...HEAD` | Only §4 paths |

```bash
cd apps/live-control-ui
npm test -- --run src/App.test.tsx
npm test -- --run src/buildSurface/BuildSurfacePage.test.tsx
npm test -- --run src/buildSurface/BuildSurfaceShell.test.tsx
npm run typecheck
npm run build
git diff --check
git diff --name-only "$(git merge-base HEAD origin/main)"...HEAD
```

### Minimal live proof

```text
Existing surface used: application shell
Smallest scenario: direct /build navigation, create/open one source, edit,
save, refresh, and navigate to another existing surface
Expected observation: Build persists source state and existing surfaces remain intact
Evidence captured: focused UI test output and screenshot/manual notes if used
```

## §8 Required handback

1. Base and head SHA.
2. Focused diff stat limited to §4.
3. Exact result of every §7 command.
4. Provenance for each result.
5. Direct-route and refresh live proof.
6. Base/head comparison for baseline failures.
7. Operator waivers; `none` if none.
8. Paths outside §4; `none` or stop report.
9. Stop conditions; `none` if none.
10. Confirmation that BLD-06 owns extraction launch.
11. Confirmation that Build cannot commit graph changes.

## §9 Acceptance rubric

- [ ] `/build` is a real React route — proved by App route tests.
- [ ] Build appears in shared navigation without changing other routes — proved by AppChrome/App tests.
- [ ] A source can be opened, classified, edited, saved, and reloaded — proved by Build page/shell tests.
- [ ] Load/save/conflict failures remain visible and do not fabricate content — proved by state tests.
- [ ] Build has no extraction or graph publication behavior — proved by allowlist/diff inspection.
- [ ] Empty Play remains unchanged — proved by existing App tests.
- [ ] No path outside §4 changed — proved by changed-path command.
- [ ] BLD-06 remains unimplemented and unclaimed.

## Stop conditions

Stop and report if:

- source persistence cannot be consumed through BLD-02’s contract;
- a new backend route is required;
- Build needs extraction controls to be useful in this shell PR;
- AppChrome requires a second navigation architecture;
- Play/Plan behavior must change to render Build.

```text
Stop condition:
Why the current mission cannot absorb it:
New contract discovered:
Affected paths:
Proposed successor slice:
Authority update needed:
```
