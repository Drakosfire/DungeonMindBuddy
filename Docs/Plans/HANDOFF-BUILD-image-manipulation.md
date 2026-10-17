# Build image manipulation

Status: ACTIVE. PRIME designs and implements the operator-requested image resize, drag scrolling and collapse controls. Serial single PR in existing buddy-context-loop checkout; base origin/main@1c2df51b4b087d87c282e46e94e934eb029f1f84. ARCHITECTURE independent exact-head review precedes PRIME merge and delivery.

Invariant: manipulate existing ready media references without changing asset identity, source content or page order except an intentional drop. Drag resize preserves aspect ratio and responsive fit. Collapse preserves the media node. Edge dragging scrolls the actual editor scroll container and stops on drop/cancel/unmount. Saving/reopening retains supported presentation attributes; legacy references remain valid. No provider generation, credentials, publication or database migration.

Contract: optional canonical Markdown image title `dmb-image:v1 width=N collapsed=B` stores integer percentage 20–100 and boolean true/false. Absent title retains legacy defaults. Unknown/malformed presentation remains blocked. No arbitrary CSS/HTML or remote URL authority. Backend save admission and frontend parser/serializer must agree.

Failure cases: resize outside editor/read-only; lost pointer capture; unavailable asset; malformed title; ordinary image titles; drag leaving viewport, nested scrollers and stationary pointer near edge; stale drag after drop; resize should not initiate move; original default JSON should roundtrip.

Exclusive write lease:
- This handoff.
- apps/live-control-ui/src/tiptap/extensions/MediaImageNode.tsx
- apps/live-control-ui/src/tiptap/extensions/MediaImageNode.css
- apps/live-control-ui/src/tiptap/extensions/mediaImageDragScroll.ts
- apps/live-control-ui/src/tiptap/extensions/MediaImageNode.test.tsx
- apps/live-control-ui/src/tiptap/extensions/mediaImageDragScroll.test.ts
- apps/live-control-ui/src/media/mediaReferences.ts
- apps/live-control-ui/src/tiptap/markdown/mediaReferences.test.ts
- apps/live-control-ui/src/tiptap/markdown/markdownAdmission.ts
- apps/live-control-ui/src/tiptap/markdown/calloutMarkdown.ts
- apps/live-control-ui/src/tiptap/markdown/semanticMarkdownSafety.ts
- apps/live_control_server/services/tiptap_markdown_write.py
- tests/test_image_presentation_admission.py

Verification: owning real editor resize/collapse transactions and Markdown roundtrip, rejected metadata, backend admission; drag scrolling/stop tests; UI typecheck/build. Then review and delivery 5202/API8000 with existing process leases and retained data preserved. Rendered resize/collapse/placement/save/reopen on disposable media acceptance document only; do not recover/discard/save operator Edge draft. Existing rollout output/evidence locations reused, no new environment/worktree or /tmp paths. Plan acceptance tab remains separate and intact. Ingest #1383 adoption remains pending, no replay authorized.

Verification note: the existing test_tiptap_markdown_write module requires disposable PostgreSQL54329 even for pure helper cases; all60 cases failed setup with54329 absent. No retained database was used. New pure presentation/owned-asset admission cases live in a separate non-DB module; this does not replace full persistence acceptance.

Implementation verification: 58 UI tests passed across real media NodeView pointer/keyboard resize, collapse, cancel, internal HTML/Markdown identity and presentation roundtrip, drag lifecycle plus workspace fidelity/recovery suites. Eight pure backend admission/ownership cases passed, Ruff passed. TypeScript and Vite production build passed (inherited large-chunk advisory). Full DB-backed Markdown suite remains unverified because54329 is unavailable (60 setup errors); retained54331 untouched. No live rendered acceptance or rollout yet.
