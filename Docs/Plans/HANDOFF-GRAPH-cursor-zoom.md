# GRAPH: cursor-anchored zoom

Status: ACTIVE. Separate serial successor to merged #2504. User requested plus/minus shortcuts and Ctrl+scroll zoom next, then continuation toward merge.

## Lane and authority

Base: fetched `main@6464347ec6e478699a1f539778b96f2a2a8801f7`.
Branch: `codex/graph-cursor-zoom-20261112`.
Reuse retained development checkout `/home/drakosfire/Projects/.codex/graph-navbar-polish-20261112/DungeonMindBuddy` after #2504 merged; clean branch, compatible private node_modules, no new worktree/install for iteration. Scratch/evidence remains on verified Projects filesystem under this task. Do not mutate live 5202/8000 services or any World data. Stable offline preview remains5248; no new ports.

## Invariant and critique

Plus/equal/minus and0(Fit) already operate when SVG or a bubble is focused. Preserve that scope and explain it in controls/help. Add Ctrl+wheel zoom anchored to cursor: the graph coordinate beneath the cursor stays fixed after zoom, including pan, responsive sizing and SVG letterboxing. Plain wheel must retain page scrolling. Consume only an eligible Ctrl+wheel event over the SVG, with a nonpassive listener, finite nonzero supported delta. Ctrl+wheel trackpad pinch uses the same browser convention; do not invent a Meta+wheel shortcut that conflicts with the platform.

No global typing shortcut interception, semantic/layout writes, selection changes, forced recenter, or new dependencies. Clamp min/max safely and preserve loaded fit scales smaller than manual minimum. Cancel transient gestures before changing camera. Listener cleanup and current-state access must survive remount/StrictMode and changing projections. Keyboard and explicit navbar zoom remain available without a wheel.

## Exclusive write set

- This handoff.
- `Docs/Plans/HANDOFF-GRAPH-navbar-polish.md` (settle predecessor only).
- `apps/live-control-ui/src/localWorld/worldGraphCanvas/WorldGraphCanvas.tsx`
- `apps/live-control-ui/src/localWorld/worldGraphCanvas/WorldGraphCanvas.test.tsx`
- `apps/live-control-ui/src/nativeGraphDemo/NativeGraphDemo.tsx` (interaction help only).
- `apps/live-control-ui/src/nativeGraphDemo/NativeGraphDemo.test.tsx` (help assertions only, if needed).

Canvas worker owns canvas files; coordinator owns handoffs and native help. No registry/style, route/API/auth/backend/dependency changes. Existing historical graph PRs are superseded by merged2504 and not edited. Current hosted read-only boundary remains authoritative.

## Verification and delivery

Focused tests: cursor-anchor invariance, scaled coordinates, modifier scoping, plain scrolling, limits, malformed deltas, keyboard input guard, listener cleanup and no semantic/layout writes. Typecheck/build, cumulative source review and exact-head canonical hosted qualification. Run full discovery at meaningful integrated checkpoint; retain known165 inherited failures visibly red, compare identities rather than calling the suite green. No browser verification claim unless actually performed. Commit/push/open one PR and pursue authorized scoped merge after review/qualification; no live service deployment.
