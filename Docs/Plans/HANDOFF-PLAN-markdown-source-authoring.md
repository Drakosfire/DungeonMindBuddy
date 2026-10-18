# PLAN — simple Markdown entry

Status ACTIVE. Operator explicitly requested simple Markdown write-in, popup syntax help and now execution during travel2026-10-18.
Owner PRIME implementation/delivery; ARCHITECTURE independent review.
Base4958acdb0a2d7592558985e6c86c40da2a29c763; branchcodex/plan-markdown-authoring; existing buddy-context-loop checkout.
Topology parallel-independent from DOGFOOD Build autosave; no unmerged dependency.

## Exact write lease

PlanSurfacePage.tsx/.test.tsx and new components/PlanMarkdownSource.tsx/.css under apps/live-control-ui/src/planSurface; this handoff. Settle predecessor HANDOFF-DOGFOOD-plan-durable-autosave.md, HANDOFF-PLAN-card-document-dividers.md and HANDOFF-AUTHOR-explicit-source-link-activation.md after their reviewed merge/live delivery. DOGFOOD Plan lease ended at1416merge4958; its successor owns Build paths only. No shared global styles or workspaceDocument edits.

## Invariant

Offer direct Markdown entry alongside rendered Document and Cards using exactly the existing Plan draft, local recovery, CAS autosave and durable server timestamp. Source entry edits the body only; existing leading YAML metadata stays outside the textarea and is reattached byte-for-byte, as in the visual editor. Never strip comments/media markers or invent card IDs. Preview is a derived projection; source edits invalidate stale editor/Agent generations. Keep visual editor mounted but hidden while source writing; synchronize its programmatic content without treating hydration as an edit. Existing fidelity checks continue to pause automatic saving for unsupported text, while source entry remains available to repair it. No graph publication, startPlay or new storage endpoint.

Markdown help explains # headings, emphasis, lists, explicit links and > [!READ-ALOUD] with proper quote prefixes, plus keeping existing card markers with their headings. Actual horizontal card divisions already ship in Document from1415. This slice does not claim direct focused-Card editing or new reorder controls.

## Acceptance

Mounted World Plan route source edit through actual autosave API boundary sends exact Markdown including frontmatter and playable IDs; switch Document/Markdown without dropping edits; open help without changing content. Protect target/World changes, pending-write recovery and in-flight typing. Typecheck/build, focused owning tests, cumulative diff inspection, independent exact-head review, then actual disposable save/reopen and reversible5202 delivery. No real session Plan edits, source exports, new worktrees/envs or /tmp directories.

## Evidence

Four focused mounted Plan cases pass: exact Markdown source/CRLF metadata/card-ID save and view switching with stale Bold action rejection; existing autosave debounce, in-flight follow-up and uncertain outcome recovery. UI typecheck and final Vite build PASS (existing chunk warning), diffcheckPASS. Full older Plan suite remains untriaged, not claimed green.

Existing PRIME disposable Plan3aa3df48-533c-44be-9ef8-2162e8d21196 was edited in source mode without Save: Read Aloud source committed automatically at revision13/server17:00:10.300681Z, all original playable marker strings unchanged. Rendered Document showed the Read Aloud text; switching back retained exact source, reload reopened the saved text/status. Narrow source layout has no horizontal overflow; popup syntax help inspected. Original fixture preserved privately before test; no session Plan/provider/graph/Play change. Final stale-action guards tested in mounted route; browser source interaction predates only that guard strengthening. Independent review pending.
