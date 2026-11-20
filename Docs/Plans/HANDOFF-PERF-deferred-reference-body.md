# Deferred document-reference presentation

**Status:** COMPLETE. PR1499 merged c3603df9a3196a15ebaffdf200c0b6efb7d80980 and accepted on 5202. Base 76e370c79accb00410e6577e8cb1d786863dbc4b; serial branch codex/defer-reference-body in existing Buddy checkout. UI-only delivery on 5202.

## Bounded ownership contract

The global DocumentReferenceProvider currently imports both saved-document renderers and Markdown conversion, retaining 36 editor/ProseMirror modules in the initial entry even after controller splitting. Defer only the parsed read-only body through the existing module-scope deferredComponent. The parent retains exact reference validation, generation fences, source/World lifetime, bounded nested history, saved provenance, close/Back/focus and source scroll. No request, authority, dependency, storage or editing changes. Both supported-body and source-rendering behavior remain identical.

A suspended body can clamp pane scroll. Its post-DOM layout callback must reapply the current history entry's scroll after body commit, including Back, and never resurrect a dismissed or obsolete reference. Keep current render/source errors and explicit deferred-load retry. No generic helper redesign or compatibility path.

## Gates

Prove no renderer import while closed/loading/error; suspended latest-reference behavior; close/source/World isolation; Back scroll restoration after delayed body; explicit failed-chunk retry; existing real rendering, source writer draft/selection/undo/focus and nested history. Inspect cumulative diff, actual app TypeScript and production chunk ownership; independent exact-head review, merge, native cold Index omission plus opened saved reference/Back/close behavior and protected 17 comparison. Preserve existing recovery bytes and active tabs. Bundle bytes are not 8 GB hardware measurements.

Rules stage remains user + Buddy cited lookup. Rules graph experiments wait until all four goal objectives are delivered.

## Author verification

Five focused files: 45/45 PASS (7 controlled loader cases, 8 real provider/writer cases, 4 surface host, 23 exact reference validation and 3 shared deferred helper). Existing nested-history test now waits for body DOM before setting or asserting pane scroll; header arrival is not body readiness. Actual app TypeScript and Vite production build PASS. Production entry index-fTmtUm6C.js is 464,768 raw / 131,516 gzip level-6 bytes versus accepted 1,010,642 raw / 294,869 gzip level-6. In-memory build audit with build.write=false preserves dist index digest; initial static chunk closure has zero Tiptap/ProseMirror modules and body has its own dynamic chunk. This is author build/source evidence, pending independent review and native acceptance. No API/runtime/data/dependency changes.

## Accepted settlement

Architecture Cycle 1 source APPROVE e47dc5f75f1bd2413ac99597f0f0385ff988badc, independent 45/45 and Bugbot no findings. Accepted cold entry index-fTmtUm6C.js: 464,768 raw / 131,802 native encoded bytes; no editor, reference body or World controller chunks on unselected Index. Real Plan Document link opens saved Dustwalker registry revision 2 through unchanged source-rendering fallback. Reopening that same saved reference then Previous restores exactly 888.888916px pane scroll after body DOM. Close restores source-link focus; writer DOM unchanged. These real references contain no nested document link, so distinct-target nesting remains covered by owner tests rather than claimed native evidence. Zero inference; 17 protected responses unchanged; API health OK. Temporary QA tabs/trace HTML removed; prior hashed assets retained. No target-hardware claim.
