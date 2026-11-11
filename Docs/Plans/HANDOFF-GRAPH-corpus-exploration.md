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
