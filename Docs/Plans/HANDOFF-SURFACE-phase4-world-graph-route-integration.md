# SURFACE: wire the local World graph into the World Surface

**Status:** ACTIVE — bounded stacked route integration authorized by Alan's front-door plan.
Created: 2026-11-09
Flow / owner: SURFACE / DungeonMindBuddy.
Topology: serial successor after graph primitives PR #2267 merged at `c14828cb50f57c426ded2f9ca80e866eb9f96282`. Current base: `main@c14828cb50f57c426ded2f9ca80e866eb9f96282`.
Branch / isolated checkout: `codex/world-graph-surface-route-20261109` / task-owned `graph-route` worktree.
PR: draft #2276; route correction is being prepared on the existing branch. Independent review is required before the hold can clear.

## Mission

Make the existing authenticated local World Surface render and edit the same World through the reviewed graph projection and repository adapters. A World title stays editable in the Surface header. A user can deliberately seed a small connected example, add/rename objects, connect selected objects, move nodes, reopen the World, and export/parse a package containing the same semantics and layout.

The route has one state authority: `LocalWorldRepository`. Semantic commits use expected local revision and remain in history; layout writes use their separate layout revision. The graph is lazy-loaded, bounded, keyboard accessible, and does not introduce a second graph store, provider call, or automatic blank-world mutation.

## Write lease (exclusive)

- `Docs/Plans/HANDOFF-SURFACE-phase4-world-graph-route-integration.md` — this authority and evidence.
- `apps/live-control-ui/src/localWorld/localWorldSurface/LocalWorldSurface.tsx` — route composition, seed action, and parent completion guards.
- `apps/live-control-ui/src/localWorld/localWorldSurface/LocalWorldSurface.test.tsx` — Surface-level graph lifecycle, conflict, layout, and package round-trip tests.
- `apps/live-control-ui/src/localWorld/localWorldSurface/localWorldSurface.css` — entry and conflict presentation.

No wildcard. The graph component lane owns `worldGraphCanvas/*` and its handoff; this route consumes those files read-only. `App.tsx` and auth/guest route composition remain outside this lease. The existing authenticated index route already composes `LocalWorldSurface`; the guest `/` route remains separately gated by #2262.

## Required behavior

- Seed only after an explicit click; create Mara Venn and Tomas Reed (People), Amber Quay (Location), and Lantern Festival (Event), with `knows`, two `attends`, and `held at` relationships in one semantic CAS transaction.
- On an empty World, allow the user to create a custom first object directly; the example graph remains optional.
- Keep title editing in the parent Surface. Load the graph editor with a dynamic import so its renderer does not add to the eager index bundle.
- Parent callbacks only return repository results. Result handlers verify the captured World ID and operation generation. A semantic completion applies only if its revision is not older than the active record; a conflict installs the committed record and retains the candidate and the canvas draft. Missing/error results never replace current state.
- Layout completion verifies World/generation and monotonic layout revision, updates only layout fields, and never changes semantic revision/history.
- Do not allow stale completion from a switched/unmounted World to overwrite the active World. Preserve newer layout when applying a semantic record and newer semantic data when applying a layout result.
- When a graph completion adopts a newer World title, synchronize the title editor only when it is clean; preserve an intentional dirty title draft.
- Keep each of the three most recently opened graph editor instances mounted but hidden so unfinished form drafts survive World A → B → A navigation. Before opening a fourth distinct graph, ask for confirmation before evicting the oldest editor draft and state that saved World data remains intact.
- Exercise create, rename, connect, keyboard movement, reopen, package encode/parse, and semantic-conflict retry. Preserve candidate records in repository history.

## Verification / acceptance

Focused tests cover the Surface callbacks and graph component controls, including clean/dirty title behavior under graph conflict, A → B → A draft recovery, failed-write draft recovery, and custom first-object creation. Run the live UI build and inspect the emitted `WorldGraphCanvas-*.js` lazy chunk. Review the full cumulative diff from the final merged graph base. Current implementation has no route-level browser acceptance evidence, no hosted/guest deployment, and no browser download testing; do not claim Alan can review a remotely deployed route. After merge, the authenticated `/` route is the intended local review entry when Alan runs the Buddy app.

Current local verification after route corrections: focused Surface + graph component tests 52/52; `npm run typecheck`; `npm run build`; `git diff --check`. Vite emits `WorldGraphCanvas-*.js` as a separate lazy chunk. Existing connectedPageApi/localWorldPackageV1 import warnings and the >500 KB eager index warning remain.

The graph primitives are now in main, so this route slice is no longer stacked on an unmerged branch. It targets the existing authenticated Buddy Surface at `/`. Guest access is not part of this lease. Browser visual acceptance and a remotely deployed review route have not been verified; do not claim either. After merge, Alan can review through the authenticated local app setup.

Stop if a required write path outside this lease is needed, if the graph parent changes behavior materially, or if exact current-main integration reveals a conflicting lease. No schema, dependency, lockfile, App route, or auth-boundary edits are authorized here.
