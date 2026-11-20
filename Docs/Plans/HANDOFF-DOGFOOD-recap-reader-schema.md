# DOGFOOD — Align recap reader with admitted Markdown

Status: ACTIVE under direct operator authority for targeted UX repairs. DOGFOOD proved the source-to-mounted-reader mismatch at main d7e32dbc: parser admits tables/callouts, while the active World recap reader returns an empty display. Isolated browser screenshots and failed owning tests are saved in the task-local recap-formatting audit.

Base: d7e32dbc0fee4d658c61221bfc21f13fe9bb4660. Branch: codex/dogfood-recap-reader-schema. Managed isolated checkout is attached to this task. No production runtime checkout is used.

Topology: parallel-independent. Current #970 Graph inspection, #979 Plan default, #985 recap target, #986 dock, #988 scene reader and #989 note retention have no overlap with this write set. #970's exact file inventory was checked; it changes the Plan read-body/inspector path, not this reader. No behavior depends on those unmerged PRs.

Exclusive expected writes: apps/live-control-ui/src/planSurface/graphProjectionReader/GraphProjectionReader.tsx and its test; this handoff; owned before/after evidence under Docs/Plans/evidence/dogfood-recap-reader-schema/. No shared extension registry, parser, safety policy, Graph controller, source-span logic, authoring policy, API/provider/database or global stylesheet changes.

Invariant: the active read-only editor consumes the existing shared default Markdown extension set so nodes already admitted by the parser can render. It must retain non-editable content, graph chip callbacks, source-span and authoring-selection semantics. Original source remains unchanged. Do not invent support for ordinary links/media or remove admission warnings.

Failure cases: tables/callouts currently blank the entire reader; nested structures and mixed Graph pills must render without unknown-node warnings; richer nodes must not make the reader editable. Unsafe or unsupported source URLs remain governed by existing admission behavior. The shared extension collection is reused rather than copied into a competing schema registry.

Verification: carry the failing mounted table/callout cases into owning tests; exercise mixed formatting and graph inspection plus read-only input behavior. Run the reader, Markdown import and adjacent recap suites; compare cumulative diff against expected paths and inherited typecheck error. Use only isolated no-API fixtures on free 5203 for browser before/after evidence; stop them and close temporary tabs.

Completion: commit, push, open one repair PR, attach and send exact head/evidence to PRIME for independent review. Merge and operator runtime adoption remain separate. This is not full source-aesthetic or media support.

PRIME explicitly adopted this bounded repair on 2026-10-07, requiring the mounted published recap path, read-only/chip/selection/span proof and preserved unsupported-format diagnostics. The source-span matching algorithm stays unchanged; its effect now runs after the Editor exists, fixing a failure exposed by the mounted rich-content test. Actual parser diagnostics are preserved in a closed Source formatting disclosure; no link/media feature is added.

Author verification: all 108 tests pass across five reader/parser/source-overlay/World-recap/local-authoring suites. Existing adjacent tests emit React act/flushSync warnings; these are not a clean-console claim. Full UI typecheck retains ThreatPublicationPanel.tsx:553 TS2503 JSX namespace error. Isolated browser confirms heading+table and READ-ALOUD text through PublishedRecapLocalAuthoring→GraphProjectionReader, with contenteditable=false. Before images show base reader reproduction; after images include the active publisher wrapper, so this is functional evidence rather than a pixel-identical styling comparison. Graph-pill callback, selection/source identity and span attachment are owning-test evidence; no live native Graph lookup or operator saved-recap mutation was used. Fixture 5203 stopped and temporary tab closed.

Predecessor settlement: #986 is verified MERGED at 6aa5d19c3fd03b0cdd489c65740022b3ebfb69da from independently reviewed b79c162c03a65a80eda3f4b744ba4f7f81bd4e8a. This accepts the reusable dock only; production mounting, real touch hardware, IME/provider behavior and operator journey remain unverified. The reader branch will rebase on this disjoint current main before handback; its shared-reader source/dependencies are unchanged by that merge.
