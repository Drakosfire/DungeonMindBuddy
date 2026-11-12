# GRAPH: clear canvas and surface controls

Status: ACTIVE. User requested a polish pass on 2026-11-12; coordinating root assigned bounded design and implementation to this lane. Serial successor to merged packed-bubble #2475, not stacked on a draft.

## Authority and lane

Base: `d87d50f13a22704b00771a542b5aeac1362f010b`, fetched from official remote main through the supported approval route on 2026-11-12. Initial implementation base was `691096d1d04f3d4397fdd75af35f39d58016cedb`; the one successor commit changes only README/runbook documentation and does not overlap this write set. Default-sandbox fetch was initially blocked; explicit supported escalation succeeded after the user requested moving toward merge. No denied transport bypass or object reconstruction.
Branch: `codex/graph-navbar-polish-20261112`.
Checkout: `/home/drakosfire/Projects/.codex/graph-navbar-polish-20261112/DungeonMindBuddy`.
Scratch/cache/evidence: siblings under the same retained task directory, verified Projects filesystem UUID `48fa5d10-fe99-4557-9fc9-d8a2a4b41ac8`. No /tmp worktrees, global environment changes or dependency links. Keep lane until release/evidence retention is settled.

Current open ingestion #2501/#2494/#2472/#2471 and PDF diagnostics do not own the graph UI boundary. Historical #2326 is a predecessor whose implementation is already included in current main. This successor adopts its renderer/UI write ownership for the paths below, without changing/closing that PR, its branch or retained evidence. No simultaneous edits to its old lane. #2405 wrapper cleanup's API paths remain untouched.

## Invariant and failure cases

Buddy's embedded graph is a clear canvas: metadata/search/persistent tools/camera/view controls live in the existing surface navbar. World identity and partial-read status remain visible, detailed diagnostics remain reachable, and the same graph/World/revision remains authoritative. Place/select/pan/move/connect/search/inspection keep their existing data contracts. A temporary point-of-action palette remains permitted. User subsequently requested a floating transparent color legend: this is an intentional metadata exception, overlaid without affecting fit/layout, with colors shared through one extensible registry. Standalone/local consumers keep their current controls.

Fit uses visible geometry and available viewport, initially and on explicit action, without repeatedly resetting user camera. Navbar menus must work with keyboard/Escape and narrow screens. Search must still find hidden isolates; moving controls must not duplicate state, hide operation failures, bypass pending-write guards, reset drafts or reauthorize semantic writes. Partial-read status must not disappear behind a menu. No change to graph ingestion, Event/SessionBeat semantics, API/auth/schema or node identities.

## Exclusive expected write set

- This handoff.
- `apps/live-control-ui/src/nativeGraphDemo/NativeGraphDemo.tsx`
- `apps/live-control-ui/src/nativeGraphDemo/NativeGraphDemo.test.tsx`
- `apps/live-control-ui/src/App.guestEntry.test.tsx` (existing real route/auth/World tests: navigate the new menus before unchanged assertions)
- `apps/live-control-ui/src/App.test.tsx` (only graph route control-location assertions; unrelated mocks/Plan/Build untouched)
- `apps/live-control-ui/src/nativeGraphDemo/nativeGraphDemo.css`
- `apps/live-control-ui/src/localWorld/worldGraphCanvas/WorldGraphCanvas.tsx`
- `apps/live-control-ui/src/localWorld/worldGraphCanvas/WorldGraphCanvas.test.tsx`
- `apps/live-control-ui/src/localWorld/worldGraphCanvas/worldGraphCanvas.css`
- `apps/live-control-ui/src/localWorld/worldGraphCanvas/graphTypeStyles.ts`
- `apps/live-control-ui/src/localWorld/worldGraphCanvas/graphTypeStyles.test.ts`

Canvas worker owns the latter three; coordinator owns NativeGraphDemo and handoff. Shared navbar primitives are reused, not modified. Dependency manifests/locks remain unchanged.

## Verification and delivery

Focused canvas/native graph boundary tests under frontend verification lock; strict TypeScript/build; inspect cumulative base-to-head diff and independent review. Exact-head hosted verifier and discovered diagnostic remain final gates; inherited failures are not green. Reuse compatible retained development dependencies only as private copies after manifest/toolchain comparison, never writable links. Commit/push/open one PR completes implementation; After requesting the floating legend, the user explicitly directed moving toward merge. Merge remains gated on current-source verification and independent review; live runtime deployment/session creation still require coordination. No change to running 5202 UI/8000 API. Reserve existing graph preview port 5248 only after checking ownership, no port iteration or session creation. Browser acceptance remains distinct from DOM tests.
