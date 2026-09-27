---
pr_body_template: |
  ## Handoff pointer
  - Workstream: DEMO / ordinary World selection
  - Direction: PRIME design → DEMO steward activation → CODE → PRIME review
  - Handoff: Docs/Plans/HANDOFF-DEMO-world-selection-primitive-v1.md
  - PR topology: serial

  ## Review contract
  A verified World selection scopes ordinary Build, Plan, Ingest and Play
  navigation/admission while the two process-level DB connections stay fixed.
  The ACTIVE handoff, cumulative diff and owning-boundary evidence govern review.
---

# HANDOFF — DEMO: ordinary World selection on stable storage

**Created / activated:** 2026-09-27
**Status:** ACTIVE — one serial implementation slice
**Canonical path:** `Docs/Plans/HANDOFF-DEMO-world-selection-primitive-v1.md`
**Flow / owner:** DEMO / Buddy product integration
**Direction:** PRIME design → DEMO steward activation → CODE → PRIME review
**Pinned design authority:** OverMind `936c7c9`, `Docs/Plans/HANDOFF-DEMO-world-selection-primitive-v1.md`
**Design authority base:** `029004be50057fa7f31d50e0b071633ed36f52f9`
**Activation base:** Buddy `main@029004be50057fa7f31d50e0b071633ed36f52f9` (#775 merge)
**Activation gate:** satisfied: #775 independently accepted and merged; predecessor authority synchronized in this guarded activation transaction
**Dispatch base:** fresh `origin/main` containing this ACTIVE handoff; record exact SHA in the PR
**PR topology:** serial; no open DEMO implementation PR
**Authorized PR:** open/update exactly one PR titled `DEMO: switch Worlds without reconfiguring storage`, suggested branch `codex/demo-world-picker`; no successor/repair PR without new steward decision.
**Runtime/state ownership:** serialize ports 8813/5194 and the exact isolated Of Conks DB pair with the predecessor witness; one implementation checkout owns its World/source registry and synthetic corpus roots.

## §1 Mission and invariant

A GM can create or select an ordinary named World, then move among Build, Plan,
Ingest and Play without changing environment variables, restarting a server, or
provisioning another database. The selected World is visible and another World
cannot show, create, resume or mutate the first World's work by accident.

**One merge-ready invariant:** a server-verified World selection determines the
scope of every claimed ordinary surface transition and object admission.
URL and remembered preference are inputs, never authority. A World with no
published graph head remains usable for source/Plan authoring but graph/Ask
truthfully report unavailable. This is local application correctness, not a
new tenancy/security contract.

| Pre-dispatch critique | Finding |
|---|---|
| Hardest adversarial sequence | Select A → open/save A document → switch to B on the same route → stale A URL/async response or global active Run restores A under B. |
| Owning proof | Browser in one runtime/DB pair, exact API request assertions, and DB-backed A/B service proof; a picker label alone is insufficient. |
| Existing foundation | #775 verified managed selection, Plan Ask/graph routing and fail-closed mismatches; server list filters already accept campaign IDs for documents and Runs. |
| Second-contract test | No new durable World pointer, per-World DB, Run lifecycle, schema or publication rule. If needed, stop and rebrief. |
| Current collision | Rules #763–#765 are open but their current paths do not overlap this narrowed lease; especially avoid `planSurface/config/planSurfaceConfig.ts` and `planSurface/projection/`. |

## §2 Authority, topology and runtime

| Field | Contract |
|---|---|
| Runtime/state ownership | Serialized 8813/5194 witness and the exact disposable World/APP-STATE DB pair; one Buddy runtime checkout owns registry and source roots. |

- Parent authority: OverMind pinned design `936c7c9`; Buddy
  `Docs/Roadmaps/ROADMAP-demo.md` and its byte-identical active mirror;
  `Docs/Plans/STEWARDS-HANDOFF-demo.md`; existing
  `Docs/Design/CONTRACT-world-container-v1.md` and APP-STATE document/Run
  contracts. #775 merged at `029004be50057fa7f31d50e0b071633ed36f52f9`
  after PRIME's Review Cycle 2 completion. Its synthetic live witness proves
  routing, **not** imported-adventure retrieval. The original Of Conks run is
  cataloged, but its file-backed evidence is unavailable; do not reconstruct
  or confirm it here.
- The process-level DungeonMind and APP-STATE DB URLs remain stable. DungeonMind
  keys graph storage by `world_id`; Buddy documents/Runs use campaign identity.
  Managed `campaign_id == world_id` is the current compatibility rule. C1/C2
  continue to map to Eldyrwild, not duplicate managed Worlds.
- World/source registry and corpus roots belong to the Buddy runtime checkout.
  A deployment consists of those durable files **and** its DB pair. Pointing
  another checkout at the same DSNs is not a complete migration.
- Runtime/state lease: serialize 8813/5194 and the isolated
  `dungeonmind_demo_ofconks_v1` / `dungeonbuddy_application_state_demo_ofconks_v1`
  pair with the completed #775 witness. Preserve the local Of Conks source,
  cataloged run, unconfirmed original candidate, and synthetic World/source.
  Prove A/B switching in **one** deployment/registry and DB pair; do not use
  two deployments as isolation evidence. No paid model call is required.
- The completed predecessor's mutable-state sync is performed in this activation
  transaction. During implementation, only correct already-knowable facts in
  the §4 authority paths; do not pre-mark this slice complete. After its merge,
  guarded steward sync settles this handoff and both roadmap copies before a
  dependent dispatch.
- Named successor: resume the DEMO-J1 imported-adventure journey and remaining
  Play/knowledge work only after this primitive's actual product witness.
  Full DEMO, extraction quality, source durability migration and hosted
  tenancy remain false.

## §3 Observable paths and failure behavior

| Path / sequence | Required behavior and owner |
|---|---|
| Shared selector / launcher | Named Worlds from server list; existing New World route; selection visible, retryable on registry error. Same-path selection, back/forward and reload update the verified context. |
| Build A → Plan A → Build A | Source/Plan inventories are A-scoped. Plan `documentId` must not travel into Build as a source ID (the observed #775 Plan→Build defect); each surface carries only its own admitted identity. |
| Switch A → B → A | Clear old document, extraction-review, Run and other scope-bound route identities when switching. Preserve document-keyed drafts and warn before losing any unsaved state not otherwise retained. A's saved work reopens unchanged on return. |
| Source create/import | Default destination is selected World. An explicitly chosen alternate destination changes selection coherently after success; no stale conflicting `world` query survives. Server-owned create/list and duplicate rules remain authoritative. |
| Exact document/Run link | Verify server-owned World/campaign binding before mounting actionable surface or side-effecting hydration. Explicit mismatch fails visibly; absent explicit World may derive from exact object. |
| Play chooser/resume | Filter Runbooks/Runs with existing campaign filters. Explicit B must not resume global active A. A stale active pointer is convenience only. A/B exact Run admission occurs before progress mutation. |
| Ingest / Graph / Ask | Preserve #775 exact review binding and honest missing-head result; late A response cannot appear under B or enable B actions. Preserve C1/C2 focus/union behavior. |
| Unknown/empty/malformed World or registry failure | Distinct loading/empty/error states, retry/choose-another recovery, no silent C2/Eldyrwild fallback or actionable stale content. |

No new backend production route, API schema, durable preference, authority
store, DB router or migration is authorized. The accepted existing server
filters are the service boundary; if they cannot enforce one required path,
return the exact gap for PRIME rebrief rather than inventing a client-only
policy.

## §4 Files in scope — ACTIVE write lease

The exact expected frontend production paths are narrowed from the pinned
design's directory-level forecast. Focused tests beside those files and the
explicitly named new tests are included. Do not edit another path first and
ask forgiveness later.

| Action | Path | Purpose |
|---|---|---|
| Modify | `apps/live-control-ui/src/selectedWorld/SelectedWorldContext.tsx` | Verified selection, loading/error recovery, stale response guard. |
| Modify | `apps/live-control-ui/src/selectedWorld/SelectedWorldContext.test.tsx` | Resolver/provider regressions. |
| Create | `apps/live-control-ui/src/selectedWorld/WorldSelector.tsx` | Named picker and recovery, not durable authority. |
| Create | `apps/live-control-ui/src/selectedWorld/WorldSelector.test.tsx` | Picker/recovery behavior. |
| Create | `apps/live-control-ui/src/selectedWorld/worldSelectionNavigation.ts` | Scope-clearing navigation. |
| Create | `apps/live-control-ui/src/selectedWorld/worldSelectionNavigation.test.ts` | Exact URL identity transitions. |
| Modify | `apps/live-control-ui/src/App.tsx` | Shared route admission and launcher links. |
| Modify | `apps/live-control-ui/src/App.test.tsx` | App integration proof. |
| Modify | `apps/live-control-ui/src/test/appNavigation.test.tsx` | Navigation boundary proof. |
| Modify | `apps/live-control-ui/src/chrome/AppChrome.tsx` | Visible picker and scope-carrying links. |
| Modify | `apps/live-control-ui/src/chrome/AppChrome.test.tsx` | Chrome integration proof. |
| Modify | `apps/live-control-ui/src/chrome/appNavigation.ts` | Same-path/back-forward transition. |
| Modify | `apps/live-control-ui/src/styles.css` | Minimal shared selector/recovery presentation only. |
| Modify | `apps/live-control-ui/src/buildSurface/useBuildWorkspaceDocumentController.ts` | Scope source inventory and create/import destination. |
| Modify | `apps/live-control-ui/src/buildSurface/useBuildWorkspaceDocumentController.test.ts` | Controller regression. |
| Modify | `apps/live-control-ui/src/buildSurface/BuildDocumentSelector.tsx` | A/B source choices. |
| Modify | `apps/live-control-ui/src/buildSurface/BuildDocumentSelector.test.tsx` | Selector regression. |
| Modify | `apps/live-control-ui/src/buildSurface/BuildDocumentCreateControl.tsx` | Coherent alternate destination. |
| Modify | `apps/live-control-ui/src/buildSurface/BuildDocumentCreateControl.test.tsx` | Create destination regression. |
| Modify | `apps/live-control-ui/src/buildSurface/BuildSurfacePage.tsx` | Reject stale foreign document, including Plan→Build. |
| Modify | `apps/live-control-ui/src/buildSurface/BuildSurfacePage.test.tsx` | Surface integration proof. |
| Modify | `apps/live-control-ui/src/buildSurface/buildDocumentNavigation.ts` | Exact scoped Build URL. |
| Modify | `apps/live-control-ui/src/buildSurface/buildDocumentNavigation.test.ts` | Build URL regression. |
| Modify | `apps/live-control-ui/src/planSurface/PlanSurfacePage.tsx` | Verified managed Plan scope. |
| Modify | `apps/live-control-ui/src/planSurface/PlanSurfacePage.test.tsx` | Plan page regression. |
| Modify | `apps/live-control-ui/src/planSurface/PlanSurfaceShell.tsx` | Scope prep inventory/admission. |
| Modify | `apps/live-control-ui/src/planSurface/PlanSurfaceShell.test.tsx` | Plan integration proof. |
| Modify | `apps/live-control-ui/src/planSurface/components/PlanDocumentSelector.tsx` | A/B prep choices. |
| Modify | `apps/live-control-ui/src/planSurface/components/PlanDocumentSelector.test.tsx` | Prep selector regression. |
| Modify | `apps/live-control-ui/src/planSurface/config/planSessionDescriptor.ts` | Remove campaign-specific example from new managed Plan template. |
| Modify | `apps/live-control-ui/src/planSurface/config/planSessionDescriptor.test.ts` | Template/admission regression. |
| Modify | `apps/live-control-ui/src/playSurface/PlaySurfacePage.tsx` | Exact Run admission, scoped inventory, active-pointer guard. |
| Create | `apps/live-control-ui/src/playSurface/PlaySurfacePage.test.tsx` | Play surface boundary proof. |
| Modify | `apps/live-control-ui/src/playSurface/StartRunPanel.tsx` | Scoped Runbook inventory. |
| Modify | `apps/live-control-ui/src/playSurface/StartRunPanel.test.tsx` | Runbook regression. |
| Modify | `apps/live-control-ui/src/ingestSurface/MemoryIngestPage.tsx` | Clear stale review identity on switch. |
| Modify | `apps/live-control-ui/src/ingestSurface/useIngestRunCatalogInformation.ts` | Preserve exact run binding under selected World. |
| Modify | `apps/live-control-ui/src/ingestSurface/useIngestRunCatalogInformation.test.tsx` | Ingest regression. |
| Modify | `apps/live-control-ui/src/workspaceDocument/workspaceDocumentNavigation.ts` | Scope-safe document query handling. |
| Modify | `apps/live-control-ui/src/workspaceDocument/workspaceDocumentNavigation.test.ts` | Query regression. |
| Modify | `apps/live-control-ui/src/workspaceDocument/useWorkspaceDocumentUrlSelection.ts` | URL/back-forward selection. |
| Modify | `apps/live-control-ui/src/api/liveApi.ts` | Existing filter/read options only, if needed. |
| Modify | `apps/live-control-ui/src/api/liveApi.test.ts` | Filter/read regression. |
| Modify | `apps/live-control-ui/src/api/types.ts` | Existing DTO-only adaptation, if needed. |
| Create | `tests/test_demo_world_selection_integration.py` | Same-DB A/B service proof using existing APIs. |
| Modify | `tests/test_selected_world_plan_context.py` | Managed Plan service regression. |
| Modify | `tests/test_live_play_runs.py` | Run filtering/admission regression. |
| Create | `Docs/Guides/GUIDE-local-world-storage.md` | Concise explanation that DB pair plus checkout-owned registry/source files comprise local deployment. |
| Modify | `Docs/Plans/HANDOFF-DEMO-world-selection-primitive-v1.md`, `Docs/Plans/HANDOFF-DEMO-selected-world-context-v1.md`, `Docs/Roadmaps/ROADMAP-demo.md`, `Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-demo.md` | Factual activation/predecessor corrections only; no in-flight completion claim. |

**Bounded discovery:** at most six additional *focused test or immediate
presentation-adapter* paths in the named frontend directories when a listed
consumer cannot compile or prove §1 without them. Name each and its causal
need in the PR handback. No additional controller, production route, shared
registry, package/lockfile, generated schema or broad CSS path under this
exception. A second durable/public contract or path owned by another lane is
a stop/rebrief signal.

## §5 Explicit exclusions and stop conditions

No DungeonMind/WorldKeeper change, APP-STATE migration, per-World DSN, root
config/env edit, new server production route, extraction/profile work, Graph
publication, Play/Combat mechanics, theme/parchment redesign, Canvas, Rules
or licensed content. No direct SQL head fabrication. Test-only synthetic
native initialization uses supported APIs and stays in a disposable fixture.
Do not confirm the original Of Conks candidate or spend on a new extraction.

Stop for PRIME if server filters/admission cannot prove required scope, dirty
drafts would be silently lost, another active lease owns a needed path, a new
public/durable contract emerges, or the observable proof requires a second
implementation PR. Keep C1/C2 compatibility intact.

## §6 Contract matrix

| Input | Result |
|---|---|
| No explicit managed World | Accepted legacy C1/C2 behavior; no invented managed World. |
| Known managed W, no head | W source/Plan authoring available; graph/Ask unavailable. |
| Known W with exact matching object | W-scoped editor/Run/graph view, verified before action. |
| Explicit W plus object from X | Visible mismatch; no remount, relabel, hydration or mutation under W. |
| Exact object without W | Derive admitted World from server-owned object binding where legacy behavior permits. |
| Switch W→X with stale response | Response discarded; no stale content/action under X. |
| Unknown/malformed W or registry failure | Recovery state with retry/choose-another; no actionable fallback. |
| Explicit W in Play with global active X Run | W chooser/empty state; never auto-resume X. |

## §7 Evidence required before review

| Guarantee | Owning proof |
|---|---|
| Two named Worlds in one deployment | Browser create/select A and B against one API/DB pair/registry; author/save source and Plan in both, switch/reload/back/forward/same route, reopen A unchanged. |
| Durable scope isolation | DB-backed two-World service test for document, Run and graph filtering on same DSNs. Do not infer from mock or separate deployments. |
| Exact admission / active Run | Play surface tests and product witness for A/B Run inventories, stale global active A under explicit B, mismatched exact Run blocked before mutation. |
| Failure/recovery | UI integration tests for loading/empty/unknown/registry error, foreign document/Run, async stale completion, draft continuity, alternate import destination. |
| C1/C2 | Existing relevant graph, Build, Plan, Ingest, Play regressions assert legacy mapping/focus. |

Run at least the following exact-head commands; report any baseline failure with
base evidence, not as green. The worker may add focused tests within §4 and
must list the final exact command set/result in the PR.

```bash
npm --prefix apps/live-control-ui test -- --run src/selectedWorld src/chrome src/buildSurface src/planSurface src/playSurface src/ingestSurface src/workspaceDocument src/test/appNavigation.test.tsx
uv run pytest -q tests/test_demo_world_selection_integration.py tests/test_selected_world_plan_context.py tests/test_live_play_runs.py
npm --prefix apps/live-control-ui run typecheck
npm --prefix apps/live-control-ui run build
uv run ruff check tests/test_demo_world_selection_integration.py tests/test_selected_world_plan_context.py tests/test_live_play_runs.py
git diff --check
```

The browser witness uses the inherited disposable pair, stable DSNs, and one
runtime registry. Retain the synthetic #775 fixture but do not claim it proves
licensed adventure retrieval or complete DEMO acceptance. Record the exact
implementation head, DB schema/readiness, World and document/Run identities,
API/request scopes, browser URLs and whether any model call occurred.

## §8 Review handback

Provide PRIME: PR URL, exact head/base, pinned handoff/design refs, cumulative
changed paths vs §4, nano-commit story, exact tests/build/baseline comparison,
same-runtime A/B browser witness, DB-backed service result, adversarial
failure outcomes, C1/C2 regressions, and material limits. PRIME independently
reviews each distinct head and holds the merge decision; DEMO executes only an
explicitly approved merge. No implementation self-approval.

## §9 Acceptance checklist

- [ ] Handoff is ACTIVE and durably on `main` before implementation branch.
- [ ] One verified selected World scopes every claimed ordinary path.
- [ ] A/B same-runtime, same-DB browser and DB-backed evidence passes.
- [ ] Exact object/Run mismatch and stale async response fail closed.
- [ ] No phantom per-World DB config, new durable pointer or C1/C2 regression.
- [ ] Exact-head checks, diff lease audit, and PRIME review are complete.
- [ ] No successor PR or full-DEMO completion claim is made by this slice.
