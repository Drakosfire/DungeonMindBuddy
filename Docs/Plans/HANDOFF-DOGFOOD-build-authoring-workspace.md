# DOGFOOD: direct Build authoring workspace

Status ACTIVE for document authoring/navigation presentation under explicit operator
"Do it" and PRIME design ownership confirmation; UI leases released. Node write
portion BLOCKED pending ARCHITECTURE identification of an existing governed command
or a DungeonMind-owned contract. No native mutation adapter is authorized.
Current fetched `origin/main` is `199a7404701d6a53fa8f4a1d68b2c7874df6771a`;
branch `codex/build-authoring-workspace`; isolated checkout
`/tmp/buddy-build-authoring-restored`. The serial implementation is assigned to
PR #1183; no new durable/public contract. PRIME owns serving runtime/ports
exclusively. The user is rendering the GET-only 5203 preview, which proxies API
GETs to API8000 and denies writes. Preserve serving 5202 and its data.

Invariant: Build is a directly editable framed document, with stationary nonmodal
Edit/Tools companions. Save in Build navbar invokes existing document CAS command;
source actions are compact. Outline navigates live editor headings. Existing graph
reference pills retain inspection behavior and document Save never mutates Graph.
Node workspace must explicitly distinguish source/candidate/accepted authority and
node Apply from document Save; no fake enabled Apply without governed capability.

Expected exclusive document UI write set:
- Docs/Plans/HANDOFF-DOGFOOD-build-authoring-workspace.md
- apps/live-control-ui/src/buildSurface/BuildSurfacePage.tsx
- apps/live-control-ui/src/buildSurface/BuildSurfaceShell.tsx
- apps/live-control-ui/src/buildSurface/BuildSurfaceContext.tsx
- apps/live-control-ui/src/buildSurface/buildSurface.css
- apps/live-control-ui/src/buildSurface/BuildSurfacePage.test.tsx
- apps/live-control-ui/src/buildSurface/BuildSurfaceContext.test.tsx
- apps/live-control-ui/src/buildSurface/BuildSurfaceShell.test.tsx
- apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx
- apps/live-control-ui/src/agentInteraction/WorldAgentConversation.planPlay.integration.test.tsx

## No-document Build landing lease amendment

PRIME approves adding `apps/live-control-ui/src/buildSurface/BuildSurfacePage.tsx`
to the exclusive lease for this existing PR. Its only purpose in this slice is
to render the no-document landing inside Build's existing framed projection and
shared `DocumentConversationDock`. Preserve loaded-document behavior, existing
route/context semantics, Plan/Play, shared hosts, APIs, graph state, source/save
state, runtime, and 5202. Acceptance uses `BuildSurfacePage.test.tsx` to verify
that bare `/build` presents the framed landing and shared dock without creating
a source, and that opening a saved source still works. This does not authorize
PR merge or runtime replacement.

## Empty-Build conversation lease amendment

PRIME approves adding these two paths to the same PR/base and exclusive lease:

- `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx`
- `apps/live-control-ui/src/agentInteraction/WorldAgentConversation.planPlay.integration.test.tsx`

In Build only, an empty saved-source context must be stated honestly and expose
an accessible reason/action that directs the user to open, create, import, or
save a source. Keep Send disabled and dispatch no request when no source is
selected. A selected→empty transition must clear any prior source title/context;
selected-source context remains accurate. Preserve all Plan, Play, and other
surface behavior. No source-free inference, API/backend/graph/publication,
runtime, port, or data changes are authorized.

The mounted integration test uses the real controller and conversation portal
path for empty→selected and selected→empty. It proves there is no stale source,
Send is disabled and no Build API turn is sent while empty, selected state shows
the correct saved-source context and existing behavior, and no source is
auto-created. This is an additive, same-PR Build empty-state capability only;
it does not authorize merge.

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

## Paper editor render finding

The user rendered the PRIME-provided GET-only preview at `5203` and reported
that the editable content appeared as a gray panel inside the cream document.
The cause was the editor's Build dark-panel background and its inherited dark
editor variables overriding the paper projection. The Build-only paper selector
now makes that editor transparent, removes its nested panel border/padding, and
sets readable paper-theme editor variables. A CSS contract test protects the
surface. The four owning UI suites pass 60 tests, UI TypeScript passes, the
production build passes with the existing chunk-size warning, and
`git diff --check` passes. This fix still needs to be rendered in the refreshed
5203 preview; the remaining pointer/keyboard, focus, frame/scroll, dirty-state,
and Plan/Play acceptance is still a gate before this branch replaces 5202.

## No-document Build landing

Dogfooding found that `/build` without a selected source bypassed the framed
projection and shared conversation dock, leaving only a bare “Choose or create
a source above” message. The no-document branch now stays inside the same paper
workspace frame, offers clear paths to open, create, or import a source, and
mounts the shared conversation dock with no saved-source context. Loading and
unavailable-source states receive explicit status and recovery copy; the route
still does not create a document automatically.

The bare `/build` test verifies the framed landing, Build surface marker, all
three paths, source controls, no auto-create behavior, and the shared
conversation dock. The four owning suites pass 60 tests, TypeScript passes,
the production build passes with the existing chunk-size warning, and
`git diff --check` passes. This follow-up is part of PR #1183 and still needs
an exact-head review and rendered 5203 check; 5202 remains unchanged.

## Welcoming first-page treatment

The no-source Build landing now reads as a worldbuilding welcome rather than a
set of instructions: a warm editorial headline, a small decorative map-and-page
illustration, and three clearly named ways to continue (open, start, or import).
The illustration is decorative and hidden from assistive technology. The landing
does not write placeholder text into a document, select a source, or create one
automatically. The welcome stays inside the existing paper frame and shares the
same World tools and conversation dock.

An opened worldbuilding source with no body now has a temporary writing welcome
inside the paper frame. It disappears as soon as the user types; it is not
serialized into the source, and it does not appear for populated sources or
source-evidence views. The invitation gives the blank editor a clear first step
without inserting sample lore.

The collapsed Conversation launcher now occupies the dock's bottom layout row
on the no-source Build landing instead of using the shared absolute overlay.
This is scoped to that landing and leaves the shared dock presentation
unchanged on other surfaces.

After this addition, the Build page, context, shell, and shared conversation
integration suites pass 89 tests. The app TypeScript check passes with its build
info redirected to `/tmp`; the production Vite build passes with the existing
large-chunk warning, and `git diff --check` passes. The blank-source welcome has
not been rendered in 5203 yet; the current preview still lacks authenticated
write behavior, and 5202 remains unchanged.

The earlier desktop preview showed the collapsed Conversation launcher covering
part of the third welcome card. It now occupies the dock's bottom layout row on
the no-source Build landing. This is scoped to Build and the CSS contract test
passes; a refreshed rendered check is still needed to verify the visual result.

The owning Build page/context/shell suites pass 49 tests. The UI app TypeScript
check passes with its build-info output redirected to `/tmp`; the production Vite
build passes with the existing large-chunk warning, and `git diff --check`
passes. This is a visual refinement within the existing Build landing lease.
Rendered desktop/narrow acceptance still awaits the recorded preview gates; no
runtime or 5202 change is included.
