# SURFACE: wire the local World graph into the World Surface

**Status:** ACTIVE — bounded current-main route integration authorized by Alan's front-door plan.
Created: 2026-11-09
Flow / owner: SURFACE / DungeonMindBuddy.
Topology: graph primitives PR #2267 merged at `c14828cb50f57c426ded2f9ca80e866eb9f96282`; this route slice was re-anchored conflict-free onto current `main@c12bafca6b6949ae3aad5012c716eefbe6b61c81`.
Branch / isolated checkout: `codex/world-graph-surface-route-20261109`; isolated qualification worktree `codex/graph-final-qualification-20261109`.
PR: #2276. The route is a two-parent merge of current main and the published PR ancestry; current main advances are retained. Prior candidate `ce49b339a9028745a6a17a090fea315add1dce93` passed the exact-source hosted safety verifier and manual Hosted workflow; main has since advanced through #2306. This new head requires fresh exact-source verification, manual workflows and independent review; the cumulative diff remains the seven leased graph-route paths.

## Mission

Make the existing authenticated local World Surface render and edit the same World through the reviewed graph projection and repository adapters. A World title stays editable in the Surface header. A user can deliberately seed a small connected example, add/rename objects, connect selected objects, move nodes, reopen the World, and export/parse a package containing the same semantics and layout.

The route has one state authority: `LocalWorldRepository`. Semantic commits use expected local revision and remain in history; layout writes use their separate layout revision. The graph is lazy-loaded, bounded, keyboard accessible, and does not introduce a second graph store, provider call, or automatic blank-world mutation.

## Write lease (exclusive)

- `Docs/Plans/HANDOFF-SURFACE-phase4-world-graph-route-integration.md` — this authority and evidence.
- `apps/live-control-ui/src/localWorld/localWorldSurface/LocalWorldSurface.tsx` — route composition, seed action, and parent completion guards.
- `apps/live-control-ui/src/localWorld/localWorldSurface/LocalWorldSurface.test.tsx` — Surface-level graph lifecycle, conflict, layout, and package round-trip tests.
- `apps/live-control-ui/src/localWorld/localWorldSurface/localWorldSurface.css` — entry and conflict presentation.
- `apps/live-control-ui/src/localWorld/worldGraphCanvas/WorldGraphCanvas.tsx` — narrow transferred seam for versioned editor-draft snapshots/restoration; do not change projection, rendering, adapter, or lifecycle behavior outside this seam.
- `apps/live-control-ui/src/localWorld/worldGraphCanvas/WorldGraphCanvas.test.tsx` — focused snapshot restore, stale completion, and unmount/remount regressions for the transferred seam.

No wildcard. The phase3 graph lane transferred only the two exact canvas paths above under the root-authorized 2026-11-09 correction transfer; all other `worldGraphCanvas/*` files remain read-only. `App.tsx` and auth/guest route composition remain outside this lease. The existing authenticated index route composes `LocalWorldSurface`; guest `/` composition is owned by #2262 or its scoped replacement and must be reviewed as a separate change.

## Required behavior

- Seed only after an explicit click; create Mara Venn and Tomas Reed (People), Amber Quay (Location), and Lantern Festival (Event), with `knows`, two `attends`, and `held at` relationships in one semantic CAS transaction.
- On an empty World, allow the user to create a custom first object directly; the example graph remains optional.
- Keep title editing in the parent Surface. Load the graph editor with a dynamic import so its renderer does not add to the eager index bundle.
- Parent callbacks only return repository results. Result handlers verify the captured World ID and operation generation. A semantic completion applies only if its revision is not older than the active record; a conflict installs the committed record and retains the candidate and the canvas draft. Missing/error results never replace current state.
- Layout completion verifies World/generation and monotonic layout revision, updates only layout fields, and never changes semantic revision/history.
- Do not allow stale completion from a switched/unmounted World to overwrite the active World. Preserve newer layout when applying a semantic record and newer semantic data when applying a layout result.
- When a graph completion adopts a newer World title, synchronize the title editor only when it is clean; preserve an intentional dirty title draft.
- Keep each of the three most recently opened graph editor instances mounted but hidden so unfinished form drafts survive World A → B → A navigation. Before opening a fourth distinct graph, ask for confirmation before evicting the oldest editor draft and state that saved World data remains intact.
- Preserve graph form drafts across route-level Surface unmount/remount with a versioned volatile registry keyed by World. Track all saved graph drafts in the existing tab-level beforeunload guard, retaining the guard until every draft, title/notes draft, and pending local write is resolved. Restore matching drafts on reopen; only clear a draft after explicit cancel or a committed submission whose exact draft version still matches. Failures, conflicts, and stale completions must not erase newer drafts.
- Track independent monotonically increasing tokens for rename, object, and relationship candidates. A successful unmounted submission may clear only the candidate field set captured by that operation and only while its field token still matches; preserve unrelated form drafts and edits made after remount, even if the newer text is later changed back to the submitted text. Keep unload protection while any form draft remains.
- Persist the empty-World custom first-object candidate by World through the same tab-level work protection, including after failed creation and Surface remount. Keep example-graph seeding disabled while a custom first-object name is pending so choosing the example cannot hide that draft.
- Exercise create, rename, connect, keyboard movement, reopen, package encode/parse, and semantic-conflict retry. Preserve candidate records in repository history.

## Verification / acceptance

Focused tests cover the Surface callbacks and graph component controls, including clean/dirty title behavior under graph conflict, A → B → A draft recovery, failed-write draft recovery, and custom first-object creation. Unmounted successful submission regressions cover object commit with concurrent rename or relationship drafts and a newer same-form candidate entered after remount. Run the live UI build and inspect the emitted `WorldGraphCanvas-*.js` lazy chunk. Review the full cumulative diff from the final merged graph base. The current-main candidate has no route-level browser acceptance evidence, no hosted/guest deployment, and no browser download testing. Do not claim Alan can review a remotely deployed route. After merge, the authenticated `/` route is the intended local review entry when Alan runs the Buddy app.

The prior focused pre-cutover checks were 126/126 LocalWorld tests, typecheck, build, and diff-check. On prior candidate `ce49b339a9028745a6a17a090fea315add1dce93`, the repository exact-source local verifier `--suite hosted` completed with fresh `npm ci`, all 1,242 cases selected by the hosted safety manifest passing with collection parity, production build exit 0, and cleanup complete; evidence is at `/home/drakosfire/evidence-graph-ce49-hosted-20261109/evidence.json` and validates against that exact SHA. Manual Hosted workflow 42670343424 passed; World ownership workflow 42670342605 had two suites passing and two still running at the last check. The new `c12bafca` integrated tree is pending rerun. Regressions cover draft restoration for failed create/relationship/rename and custom-first-object actions, failed and pending route unmount/remount, object completion alongside unrelated rename or relationship drafts, same-text object draft re-entry after cancel/remount, and unload-warning cleanup after all World drafts are resolved. Vite emits `WorldGraphCanvas-*.js` as a separate lazy chunk. Existing connectedPageApi/localWorldPackageV1 import warnings and the >500 KB eager index warning remain. Full discovered diagnostic and isolated browser interaction are still pending; local verifier evidence is not a GitHub workflow check.

The graph primitives are in main, so this route slice no longer depends on an unmerged primitives branch. It targets the existing local Buddy Surface at `/`. Guest route composition is separately gated by #2262 and is not part of this lease. Browser visual acceptance and a remotely deployed review route have not been verified; do not claim either. After merge, Alan can review through his local app setup.

Stop if a required write path outside this lease is needed, if the graph parent changes behavior materially, or if exact current-main integration reveals a conflicting lease. No schema, dependency, lockfile, App route, or auth-boundary edits are authorized here.
