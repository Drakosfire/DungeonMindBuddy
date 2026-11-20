# Build: welcoming, visible authoring

Status: ACTIVE — operator explicitly assigned PRIME implementation and live dogfooding, 2026-10-16.
Base: origin/main@70c894a25ab64a0b08dd2e7a4f293f5e262eff4b.
Lane: codex/build-welcoming-authoring, /tmp/prime-build-welcoming-authoring.
Topology: parallel-independent of DOGFOOD's Ingest #1276; no shared styles edits. PRIME's Jev provider-inclusion work remains preserved in its separate checkout.

Outcome: a clear New page control, actionable welcoming studio, an optional editable worldbuilding starter in explicitly created pages, visible document/graph-reference tools, and compact draft recovery beside Save. Use existing Agent conversation and document persistence authority. Never overwrite existing text, auto-save starter content, or imply linking is direct Graph publication.

Exclusive write set:
- this handoff
- apps/live-control-ui/src/buildSurface/BuildSurfaceContext.tsx
- apps/live-control-ui/src/buildSurface/BuildDocumentCreateControl.tsx
- apps/live-control-ui/src/buildSurface/BuildSurfaceShell.tsx
- apps/live-control-ui/src/buildSurface/buildMarkdownCanvasAdapter.tsx
- apps/live-control-ui/src/buildSurface/useBuildWorkspaceDocumentController.ts
- apps/live-control-ui/src/buildSurface/buildSurface.css
- apps/live-control-ui/src/buildSurface/buildStudioActions.ts (new)
- corresponding BuildSurfaceContext, BuildDocumentCreateControl, BuildSurfaceShell, buildMarkdownCanvasAdapter and BuildSurfacePage tests

Contract: studio actions are Build-local UI events; creation retains existing destination admission. A starter is queued only after explicit document creation, keyed to its returned document ID, then applied only to its empty editor as an unsaved edit. Discard retains exact-document confirmation. Existing toolbar/Agent authority does not change; direct World node creation remains separate from existing-reference insertion.

Verification: focused owning UI tests, typecheck/build, exact cumulative diff and independent ARCHITECTURE review before merge. After merge, deploy matched main to operator's 5202/8000; read-only rendered desktop/narrow checks. Preserve current drafts and retained records; no ingestion/model/publication calls for checks. PRIME owns merge under operator delegation; DOGFOOD retains Ingest.
