# DOGFOOD: direct Build authoring workspace

Status ACTIVE for document authoring/navigation presentation under explicit operator
"Do it" and PRIME design ownership confirmation; UI leases released. Node write
portion BLOCKED pending ARCHITECTURE identification of an existing governed command
or a DungeonMind-owned contract. No native mutation adapter is authorized.
Base fetched main 66b24a54; branch codex/build-authoring-workspace; isolated checkout
/tmp/buddy-build-authoring-workspace. Topology serial one independently useful UI PR;
no new durable/public contract. PRIME currently owns serving runtime/ports exclusively; DOGFOOD has a temporary GET-only 5203 static preview lease proxying healthy API8000, no POST/provider/DB mutation, stopped after render. Preserve serving5202 processes250351/250352.

Invariant: Build is a directly editable framed document, with stationary nonmodal
Edit/Tools companions. Save in Build navbar invokes existing document CAS command;
source actions are compact. Outline navigates live editor headings. Existing graph
reference pills retain inspection behavior and document Save never mutates Graph.
Node workspace must explicitly distinguish source/candidate/accepted authority and
node Apply from document Save; no fake enabled Apply without governed capability.

Expected exclusive document UI write set:
- Docs/Plans/HANDOFF-DOGFOOD-build-authoring-workspace.md
- apps/live-control-ui/src/buildSurface/BuildSurfaceShell.tsx
- apps/live-control-ui/src/buildSurface/BuildSurfaceContext.tsx
- apps/live-control-ui/src/buildSurface/buildSurface.css
- apps/live-control-ui/src/buildSurface/BuildSurfacePage.test.tsx
- apps/live-control-ui/src/buildSurface/BuildSurfaceContext.test.tsx
- apps/live-control-ui/src/buildSurface/BuildSurfaceShell.test.tsx

Node workspace is deferred as a separate owner contract: existing governed Graph Review does not provide general existing-node attribute updates. No Node Apply in this PR. Shared hosts
remain shared; Build-scoped CSS removes modal backdrops without changing other
surface behavior. Preserve dirty/conflict recovery, source navigation and chip
serialization. No provider, source Save, Graph publication or runtime switch in QA.
Mounted owning tests, typecheck/build and exact rendered checks required. Review
cumulative diff, commit/push/open one PR; PRIME separate merge authority. Render only after PRIME-confirmed matched health or on the separately authorized
GET-only 5203 preview.

## Exact-ref design gate and draft disclosure

This handoff is pinned alone before further implementation. Five product/test
files already contain draft edits from operator-authorized exploration; those
uncommitted edits are preserved and are not accepted implementation evidence.
ARCHITECTURE design ACCEPTABLE on pinned 884866e3bf4f9be9166d0b44d3fc063479bbd6cd
against base66b24a54; implementation must separately pass exact-head review. The amended seven-path lease is exclusive and Plan/Play unchanged.

Nonmodal acceptance includes pointer and keyboard access to the editor while
companions are open, no focus trap/inert/aria-modal mismatch, stable frame and
scroll, explicit close and predictable focus restoration. CSS-only backdrop
removal is insufficient if shared-host semantics prevent those behaviors; request
an exact lease amendment rather than silently editing shared hosts.

Owning tests/render must cover dirty→navbar CAS Save and conflict preservation,
live duplicate/changed heading navigation, tools-open typing, exact saved evidence
separate from dirty draft, Graph reference chips/serialization, desktop/narrow
without remount or data loss. Preserve existing formatting/undo paths. Save writes
the document only; Node Apply remains deferred to its real owner contract.

## Test-only lease amendment

PRIME approved adding `apps/live-control-ui/src/buildSurface/BuildSurfaceShell.test.tsx`
to this implementation lease. Its legacy tests asserted the removed Read/Edit
switch and a single rendered reader. Update those expectations to continuous
authoring while preserving source-navigation, dirty-state and persistence
coverage. No additional production paths or capability are included.

## Narrow overlay review response

ARCHITECTURE HOLD on `8fc0687b0f54f714dc9f88285414b603fabc6343` identified that
the shared narrow Edit-dock backdrop selector outranked the original Build
override. The Build CSS now scopes both Edit and Tools backdrop removal to the
Build document marker, disables pointer events on those backdrops, and gives the
narrow drawers a full-width bottom-sheet bound of 42dvh. The shared selectors
remain unchanged. A CSS contract test in `BuildSurfaceShell.test.tsx` checks
Build-only scoping, the specificity increase, non-intercepting backdrop rules,
and narrow drawer bounds; the owning UI suites pass 59 tests, with UI TypeScript,
production build, and `git diff --check` passing.

Rendered acceptance remains pending. From the DOGFOOD executor, `127.0.0.1:8000`
refused connections and no `5203` listener was present, despite a relay saying
the API was healthy. No `5202` process or data was changed. Request another exact
head review through PRIME; only after that review passes and the serving lease is
coordinated may this Build branch replace the 5202 UI.

ARCHITECTURE's follow-up HOLD on `dd8f0e9efb93f169f9bb144248241a3a82d62763`
found the shared open-dock geometry selector at `(0,5,0)` still outranked the
narrow Build Edit drawer selector at `(0,4,1)`. The Build Edit drawer selector
now includes the open-dock `:has()` state and has `(0,6,1)` specificity. The CSS
contract test compares those exact competing selectors and requires Build to
win, in addition to asserting the bottom-sheet geometry. This closes the CSS
cascade issue; rendered narrow interaction, desktop stationarity and Plan/Play
acceptance are still required before using 5202.
