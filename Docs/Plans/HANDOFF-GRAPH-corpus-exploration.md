# GRAPH: explore every loaded corpus object

Status: ACTIVE. One bounded implementation slice authorized by the user's corpus graph report and coordinating root assignment on 2026-11-11. No merge, deployment, provider use, or live data change.

## 1. Invariant and plan

Every object in the loaded native snapshot remains searchable and selectable, including those after position 511. Rendering remains bounded; a selected object can anchor a bounded neighborhood and expand to further connections. A renderer-hidden endpoint is not invalid. True missing endpoints remain visible as bounded diagnostics with exact aggregate counts. The source snapshot, IDs, native revision and existing edit/inspection authority remain unchanged.

One coherent PR: projection/index, canvas exploration controls, native integration, and boundary tests. Serial within this new GRAPH corpus exploration slice; parallel-independent of the open legacy SURFACE #2326 and wrapper cleanup #2405. No unmerged behavior is consumed. This declaration does not transfer or close either prior lane. #2326 remains an open historical local-toy stack and overlaps the canvas paths. Root explicitly directed proceeding on current main while preserving those changes. Current main includes the shared canvas behavior plus 820 added/50 removed lines relative to #2326's recorded b30833e head; this lane does not edit that branch or restore its older source. Recheck overlaps before publication.

## 2. Pinned authority and isolation

Base: 547d891fe87cce85b79afd72e3bb03ee2bef3a5d, remote main verified through the GitHub connector and identical to local origin/main. CLI fetch was denied by network policy; no bypass. Current committed AGENTS.md, not the dirty primary checkout's legacy policy, governs this lane. Branch: codex/corpus-graph-exploration-20261111. Worktree: /home/drakosfire/Projects/.codex/corpus-graph-exploration-20261111/worktrees/DungeonMindBuddy. Projects UUID 48fa5d10-fe99-4557-9fc9-d8a2a4b41ac8 and writable parent verified.

Synthetic fixture tests only. No existing runtime ports, browser storage, corpus or database. Task-owned scratch/cache/verification below the same task root. Honor the shared frontend verification lock. No authority sync is needed for an uncompleted predecessor; this slice consumes already merged main.

## 3. Failure critique

- Validate edges against all loaded IDs before view filtering. Keep parallel relationship IDs, reverse edges and cycles.
- Index once per snapshot and memoize projection so camera motion does not scan the corpus. Render and search-result DOM stay explicitly bounded.
- Search all loaded labels, types and IDs, including isolated objects; paginate results without losing later matches.
- Seed-focused traversal must keep the requested object even when it is late in source order; deeper/high-degree neighbors can remain hidden with truthful counts.
- Revision/World changes clear transient exploration state and must not show stale inspection or alter semantic drafts/CAS checks.
- Native server partial-read status is separate from the browser's bounded view. Do not imply unloaded entities were searched.

## 4. Expected write lease

- Docs/Plans/HANDOFF-GRAPH-corpus-exploration.md
- apps/live-control-ui/src/localWorld/worldGraphCanvas/graphProjection.ts
- apps/live-control-ui/src/localWorld/worldGraphCanvas/graphProjection.test.ts
- apps/live-control-ui/src/localWorld/worldGraphCanvas/WorldGraphCanvas.tsx
- apps/live-control-ui/src/localWorld/worldGraphCanvas/WorldGraphCanvas.test.tsx
- apps/live-control-ui/src/localWorld/worldGraphCanvas/worldGraphCanvas.css
- apps/live-control-ui/src/nativeGraphDemo/NativeGraphDemo.tsx
- apps/live-control-ui/src/nativeGraphDemo/NativeGraphDemo.test.tsx

## 5. Verification and review

Test the observed 1404-node/559-edge shape, valid hidden endpoints, truly invalid endpoints, late focused IDs, disconnected nodes, cycles/parallel edges, expansion, pagination, repeated focus/reset and revision/World transitions. Preserve existing canvas/native component tests. Run typecheck/build and exact-source hosted verifier, plus one full discovered diagnostic, retaining failures and baseline limits. Independent exact-head review required; merge authority separate.

## 6. Retention

Owner: corpus graph exploration task. Retain task-owned worktree, scratch/cache and verification until PR review/acceptance. No deletion authorized or performed; report final retained paths and cleanup follow-up.

## Implementation checkpoint

Full loaded-snapshot index separates hidden valid relationships from absent endpoints. Native embedded graph adds a 20-result paginated search over name/type/ID, focus-centered breadth-first neighborhoods, expansion and overview. Render ceilings remain 512/1024. Canvas camera updates reuse index/projection. Verified placements for late objects are preserved rather than discarded by the former first-512 guard. No semantic/revision/auth transport changes.

Working-tree diagnostic: 127 focused tests pass across seven graph/native files; typecheck and production build pass (existing split-import/chunk-size warnings). Tests reproduce 1404 objects/559 relationships as 512/43 displayed, 892/516 hidden and zero false diagnostics; late and isolated focus, expansion, pagination, revision refresh, dense traversal, true missing endpoints beyond caps, long hidden prefixes, index reuse and late creation placement are covered. CUA browser inventory is unavailable (`native pipe path unavailable`), so no real-browser witness is claimed. Exact-source aggregate verification and independent review are still required.

## Review correction and verification limits

Independent cycle 1 found two related camera-reset defects: Fit then Show overview, and revision refresh after focusing a saved late object, could restore the overview node set while leaving the camera outside it. The repair frames the current projection when no saved overview camera remains and explicitly refits on a revision reset that clears a neighborhood. Ordinary non-neighborhood refresh retains its prior camera behavior. New component regressions check transforms, not only DOM counts; 129 focused tests plus typecheck/build pass.

The mandatory clean hosted verifier at local b98bede3a0ef481f1042d7f2a4fbe846107edce6 allocated an exact-SHA checkout but its fresh install was stopped by network policy denying registry.npmjs.org. No aggregate tests ran there and no clean-install qualification is claimed. Evidence/logs remain in the task verification/hosted-local and scratch directories. A copied-dependency discovered diagnostic is separate and cannot replace that gate. Initial remote publication cc30591591f279cb82244baf8c40c70c72337c7b had exact tree parity with b98bede3a; the correction requires a new formal exact-head review.

## Current-main continuation, 2026-11-11

Alan requested continuing #2431. Re-anchor: remote main and local object both identify f6f5f3ba5d9e570027dfbb5c1770a4935130e69c. Integrate that exact main into this feature lane, retaining the graph change and its existing native authority. Main's intervening PDF/agent changes do not overlap this slice's eight paths, verifier or dependency manifests. The three-way merge is clean. No independent successor PR or capability is added.

Open legacy #2326 remains unchanged at b30833ede97cb4c79acf17a1fe55ff50446c7452 on its old guest/toy parent; no lease transfer, closure, retarget, or branch edit is performed. Its historical canvas changes are already preserved in the newer main implementation this slice consumes.

The 129 focused tests, type/build, 7,436-pass/159-fail full diagnostic and exact reproduction of all 159 failing IDs on the original base remain historical evidence for ecf0342102fdc4026a4ea52aeb95340e8366f267. Current-main integration needs fresh diagnostics and independent exact-head review. Mandatory fresh-install verification remains blocked by the earlier registry network denial; no material permission change exists, so do not repeat or bypass that operation. Browser inventory was rechecked and still reports missing native pipe. No copied dependency diagnostic is a substitute for either gate.

This continuation changes no live service, corpus, migrations or deployment settings. Current main includes APP 0154/0155; any later deployment proposal must inspect the actual runtime/database state and obtain its own explicit migration/service-switch authority. This feature branch is not deployment authorization.
