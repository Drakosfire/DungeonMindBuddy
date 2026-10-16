# DOGFOOD: direct Build authoring workspace

Status SETTLED after PR #1183 merged at `990d229d6f131985b830fabc2a6598a5b12f61a5`.
The merged Build authoring implementation and its completion lease have ended. The
older lease/path history below is retained as historical evidence and grants no
current write authority. Node write portion remains BLOCKED pending ARCHITECTURE
identification of an existing governed command or a DungeonMind-owned contract. No
native mutation adapter is authorized.
At the last #1183 integration checkpoint, fetched `origin/main` was
`9abb6c5f1903a10f784c5563081052472a3dc19e` (including merged #1211 and #1212).
The integration lane was `codex/build-1183-integrate-main`, and PR #1183 was
then updated in place after verification. No Node write contract was introduced;
PRIME owned shared serving/runtime ports, and 5202/data were preserved.

Invariant: Build is a directly editable framed document, with stationary nonmodal
Edit/Tools companions. Save in Build navbar invokes existing document CAS command;
source actions are compact. Outline navigates live editor headings. Existing graph
reference pills retain inspection behavior and document Save never mutates Graph.
Node workspace must explicitly distinguish source/candidate/accepted authority and
node Apply from document Save; no fake enabled Apply without governed capability.

Original cumulative PR authoring paths (review scope; not the current completion lease):
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

## Current completion lease and rendered acceptance — 2026-10-15

PRIME reactivated the serial #1183 completion lane against fetched
`origin/main@9abb6c5f1903a10f784c5563081052472a3dc19e`; after #1212 merged,
this existing PR was rebased to that main head. The selection-context endpoint
is server-owned and outside this Build slice. The only current writable paths
are:

- `Docs/Plans/HANDOFF-DOGFOOD-build-authoring-workspace.md`
- `apps/live-control-ui/src/buildSurface/BuildSurfacePage.test.tsx`

This completion adds only the test proving a newly created blank source keeps
navbar Save disabled while clean and enables it after the first edit. Existing
#1183 product paths remain cumulative review scope and will not be changed in this
completion. Rebase and update the existing PR branch with expected-old-head
protection; do not create a second PR. No 5202 restart/deployment is authorized.

Rendered read-only acceptance used 5205 because 5203 refused connections. The
available 5205 preview is older, assembled from `main@3a890b9e` plus the then-current
PR heads, so it is not proof of the current main-integrated PR head. At desktop
and 390×844, the
Mirathorn source was readable on the paper canvas, the Build navbar controls were
present, Plan and Play were discoverable, and the shared conversation dock opened
with its transcript, New conversation, context, options, and composer. At narrow
width, navigation is horizontally scrollable and the dock becomes a bottom sheet
with the composer visible. The dock context identifies the saved Mirathorn source
and says unsaved editor changes remain local; the World Graph is not loaded and
Explore loaded graph is disabled.

The preview already displayed “Unsaved local changes” before this acceptance. That
draft was preserved: no typing, save, discard, message send, or 5202 change occurred.
Therefore durable save/reopen and live conversation sending remain unverified; this
does not establish full World Graph integration. Use a separate disposable document
in a fresh preview for any future write-path acceptance. The viewport override was
reset after the narrow-width check.

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
without inserting sample lore. The invitation now includes a small map-and-page
illustration and optional Place, Person, and Mystery starters. A starter writes
only its selected heading into the editor after an explicit click and leaves the
cursor in the following paragraph; opening the source remains truly blank.

The collapsed Conversation launcher now occupies the dock's bottom layout row
throughout Build instead of using the shared absolute overlay. This keeps it
from covering either the empty welcome or loaded document text, and leaves the
shared dock presentation unchanged on other surfaces.

After this addition, the Build page, context, shell, and shared conversation
integration suites pass 90 tests. The app TypeScript check passes with its build
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

## Current main re-anchor and rendered acceptance — 2026-10-15

PR #1183 is replayed on fetched `origin/main@3a890b9e`. A current-main Build
preview runs at `127.0.0.1:5204` from this isolated checkout; it does not modify
5202 or use the stale 5203 integrated preview.

Rendered checks at desktop and 390px width confirm the no-source illustrated
welcome and the loaded Mirathorn paper. The conversation launcher now sits in
document flow at narrow width and no longer overlays the page text. Navigation
opens Plan and Play from the shared nav. A temporary local editor change
enabled Save, was discarded through the explicit discard confirmation, and the
saved Mirathorn source was reloaded with its original text and committed status.
No source content was saved or changed during acceptance.

Authenticated write and live conversation checks are blocked in this preview:
the dock reports local authorization rejected and disables its composer. Thus
the Save API round trip, live conversation, and data-dependent Plan/Play landing
states are not accepted here. The Build page/context/shell suites pass 52 tests;
the Build shell launcher regression passes 29 tests; TypeScript passes. The
production Vite build passes with the existing large-chunk warning, and
`git diff --check` passes.


## Integrated preview acceptance — 2026-10-15 (supersedes older pending-render notes)

The integrated local preview on 5205 was assembled from `main@3a890b9e` plus the exact then-current heads of PRs #1183, #1188, #1190, and #1191. On Build, the no-source desktop welcome rendered inside the framed workspace with the shared conversation launcher and explicit open/start/import paths; no document was created automatically. At 390px, the Build welcome remained usable. The selected Mirathorn source rendered on the paper surface with its original content readable. A temporary editor change made Save available, then was discarded through the explicit confirmation; the saved source returned to its original text and committed state. No content was saved or changed.

The desktop conversation launcher and Plan/Play navigation were present. Authenticated save/reopen and live conversation sending were not verified; this acceptance did not write to the user's source. 5202 was not modified. The combined production build passed; Build page/context/shell suites passed 52 tests, TypeScript passed, and `git diff --check` passed. The historical 5203 and 5204 pending-render notes above are superseded by this integrated render; the user-source write boundary remains untested.

## Current-head Build acceptance addendum — 2026-10-15

All observations below use the exact product head `e91ccc9f102594f580f239897357e96c1084291e` in the isolated 5207 preview. No product code changed during this acceptance; 5202 and its data remain untouched.

A new blank disposable Build source (`31e6d747-a70a-4dc6-8b94-6f2f2c7ba05d`) began clean with Save disabled, as expected. Ordinary keyboard input changed the status to “Unsaved local changes” and enabled navbar Save. Saving reached committed revision 2; a fresh tab reopened the exact text in clean Committed state. This confirms the earlier disabled-Save observation was specific to automation `setValue` producing a sealed authoritative editor draft. The existing fail-closed guard is preserved; no production Save repair was warranted.

At 390×844, the current-head Build paper/editor and conversation dock fit the viewport: document scroll width was 390px and the dock was 350px wide at x=20. The viewport override was reset after inspection. Mirathorn remained read-only. Earlier desktop Build→Play→Plan navigation remains verified.

The pending New Conversation request was resolved through its supported status/recovery controls; creating a new conversation then succeeded and cleared the transcript. A distinct follow-up question subsequently failed terminally with `hermes_worker_timeout` after 121.3 seconds. The UI recorded no answer or execution trace, and no source passage was opened. An earlier `hermes_worker_start_failed` came from a temporary API launcher missing its `__main__` guard; that launcher was fixed only under `/tmp`. The question was not replayed. Conversation answer generation and trace capture remain unaccepted backend work, separate from this Build UI slice.


## Lease settlement — 2026-10-15

PR #1183 merged on Buddy main as `990d229d6f131985b830fabc2a6598a5b12f61a5`.
This document's authoring implementation is settled; its old Build UI path list is
cumulative review history, not an active write lease. PRIME transferred any stale
Build CSS ownership needed for the successor paper-clearance repair to
`HANDOFF-DOGFOOD-build-edit-clearance.md`. No Node Apply capability was delivered.
