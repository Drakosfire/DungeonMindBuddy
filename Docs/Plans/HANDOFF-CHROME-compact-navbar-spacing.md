# CHROME — compact navbar spacing

Status: ACTIVE. Operator authorized accumulated dogfood fixes during travel, 2026-10-18.

Owner: PRIME implementation/delivery; ARCHITECTURE independent review.
Base: d50b0d9b8509c52930eb443aa568161f04a749b9.
Lane: existing buddy-context-loop checkout, codex/compact-navbar-spacing.
Topology: parallel-independent from DOGFOOD autosave; no behavioral dependency.
Exclusive write lease: this handoff and apps/live-control-ui/src/styles.css only.
No other open PR currently reserves this bounded whitespace change; DOGFOOD notified to use component-local CSS.

## Invariant and change

Reduce empty space above/below shared core navigation without changing control sizes, wrapping, sticky behavior or document persistence. AppChrome measures its actual header edge with ResizeObserver; do not change its offset contract. Use 6px wrapper top padding, sticky top offset and header bottom margin instead of 16px/10px/20px. Measured geometry remains owned by AppChrome.

Failure cases: clipped menus, header/content overlap, horizontal overflow, lost control targets, or incorrect drawer top after the header shrinks.

## Verification and completion

Inspect exact cumulative diff; build existing UI dependencies; render desktop and narrow Plan, verify header/content bounds and menus. No live document edits, Graph writes, provider calls or API changes. Commit/push one PR; independent review before PRIME merge and reversible static UI rollout on5202. Existing service/source/data retained. No new worktree, clone, environment or /tmp directory.

## Verification receipt

- Vite production build passed (existing large chunk warning). Existing dependencies reused; no typecheck rerun for three CSS declarations.
- Actual Plan rendered on isolated UI port5210 with current API reads only. Desktop1422x800 CSS viewport and narrow433x937 CSS viewport (390x844 requested browser override at existing zoom): no horizontal overflow, header ends before document content, all surface controls retained. World selector menu opens and remains visible at both sizes. Screenshots retained in PRIME visualization directory; viewport restored.
- Preview Graph status requires local session for this different origin; it is not graph readiness evidence. No authoring, persistence, graph or provider behavior changed.
- Cumulative CSS diff is exactly three spacing declarations; git diff --check passed. Independent review and merge still pending.
