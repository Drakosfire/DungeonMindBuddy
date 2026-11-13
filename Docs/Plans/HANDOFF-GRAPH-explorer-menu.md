# GRAPH: compact explorer menu

Status: COMPLETED. PR #2518 merged as `62e6b58c3cf3005ac92dd5bc17ab94865030517d`, preserving reviewed head `c2b58a7db1c1b048fb5d139f99d348f927e3c917`. Exact hosted qualification passed; completed baseline comparison found 168 inherited broad-discovery failures with no new failures, removals, inactive cases or collection omissions. Independent review approved the bounded change. No live deployment is implied by this settlement. Successor: `HANDOFF-GRAPH-readable-arrow-focus.md`.

## Invariant and critique

Keep identity and connections immediately readable. Move names, counts, record scope/status and secondary actions into a keyboard-operable hamburger disclosure in the existing sticky explorer navbar. Keep character classification without role-unspecified clutter; no inferred PC/NPC. Focus and Close become labeled icons. Partial-state badge stays visible, loading/errors stay visible, and record qualifications remain in opened connections. No evidence loss, inferred current truth, new permissions, sources or writes. Native disclosure semantics rather than an ARIA menu allow nested information and normal Tab traversal; Escape dismisses and returns focus. Selection/revision changes dismiss stale metadata.

## Lane, ownership and write lease

Reuse the clean retained graph-node-explorer checkout and private dependencies on Projects storage. No runtime 5202/8000 or auth/data changes. Stable read-only preview 5248 only. Open PRs2517,2516,2501,2462 are disjoint; historical2326 UI ownership was superseded by merged2504 and2510. Exclusive paths: this handoff; predecessor HANDOFF-GRAPH-readable-node-explorer.md for truthful settlement; apps/live-control-ui/src/nativeGraphDemo/GraphNodeExplorer.tsx, GraphNodeExplorer.test.tsx, nativeGraphDemo.css; existing NativeGraphDemo.test.tsx and App.guestEntry.test.tsx expectations only if needed. No shared projection/API/canvas/dependency changes.

## Verification

Focused component and caller regression tests, typecheck, independent cumulative review, exact-SHA hosted qualification and discovered diagnostic with inherited failures red. Preserve hosted source restrictions, pending navigation guards, repeated open/close, Escape focus return and selection reset. Verify same-port preview assets separately from browser acceptance. No live/deployment/merge claim from static checks.
