# GRAPH: compact explorer menu

Status: ACTIVE. Owner queued this slice; coordinator delegated bounded design and implementation on 2026-11-12. Serial successor to #2510, merged ab33d3302444ca072838d9b53c5b9eb9f5894cba. Base fetched origin/main at that commit; branch codex/graph-explorer-menu-20261112. One draft implementation PR; merge separate.

## Invariant and critique

Keep identity and connections immediately readable. Move names, counts, record scope/status and secondary actions into a keyboard-operable hamburger disclosure in the existing sticky explorer navbar. Keep character classification without role-unspecified clutter; no inferred PC/NPC. Focus and Close become labeled icons. Partial-state badge stays visible, loading/errors stay visible, and record qualifications remain in opened connections. No evidence loss, inferred current truth, new permissions, sources or writes. Native disclosure semantics rather than an ARIA menu allow nested information and normal Tab traversal; Escape dismisses and returns focus. Selection/revision changes dismiss stale metadata.

## Lane, ownership and write lease

Reuse the clean retained graph-node-explorer checkout and private dependencies on Projects storage. No runtime 5202/8000 or auth/data changes. Stable read-only preview 5248 only. Open PRs2517,2516,2501,2462 are disjoint; historical2326 UI ownership was superseded by merged2504 and2510. Exclusive paths: this handoff; predecessor HANDOFF-GRAPH-readable-node-explorer.md for truthful settlement; apps/live-control-ui/src/nativeGraphDemo/GraphNodeExplorer.tsx, GraphNodeExplorer.test.tsx, nativeGraphDemo.css; existing NativeGraphDemo.test.tsx and App.guestEntry.test.tsx expectations only if needed. No shared projection/API/canvas/dependency changes.

## Verification

Focused component and caller regression tests, typecheck, independent cumulative review, exact-SHA hosted qualification and discovered diagnostic with inherited failures red. Preserve hosted source restrictions, pending navigation guards, repeated open/close, Escape focus return and selection reset. Verify same-port preview assets separately from browser acceptance. No live/deployment/merge claim from static checks.
