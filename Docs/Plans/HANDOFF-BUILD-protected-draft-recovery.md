# BUILD: recover protected drafts without losing local edits

Status: ACTIVE. PRIME implements under refreshed operator goal for Build saving
and durable authored material; ARCHITECTURE independently reviews.
Base: origin/main@ae394d6d3b98e49a4111c9e268efaa9174d24eca.
Branch: codex/build-draft-recovery; reuse buddy-context-loop and dependencies.
Topology: serial Build recovery PR, independent of DOGFOOD's PC-fill paths.

Observed: settled Edge UI shows unsaved edits with disabled Save and no reason.
Actual browser authority flag is not inspected. Code separately proves that
Build hides the existing authoritative-source re-import action with footer
controls. Do not infer a specific live flag or mutate Edge during diagnosis.

Outcome: show the computed Save-block reason; expose explicit recovery review.
Before re-import, retain exact live editor JSON plus preserved source Markdown,
identity/base/seal/dirty metadata in one verified browser-local checkpoint.
Provide Restore after remount. Failed storage, changed source/document/editor
or active command must leave draft/seal intact. Cancellation changes nothing.
No automatic unseal/Save, parser weakening, source overwrite or provider call.
Source/projection choice is not a merge and does not prove general fidelity.
Checkpoint restore is local, fenced to same base, restores the original seal,
and cannot bypass ordinary Save admission. Preserve the first checkpoint until
explicit restore/disposition; never silently overwrite a unique recovery copy.

Exact lease:
- this handoff
- Docs/Plans/HANDOFF-AGENT-turn-trace-retention.md (settle merged predecessor)
- apps/live-control-ui/src/workspaceDocument/workspaceDocumentRecovery.ts (new local boundary)
- apps/live-control-ui/src/workspaceDocument/useWorkspaceDocumentAuthoring.ts
- apps/live-control-ui/src/workspaceDocument/useWorkspaceDocumentAuthoring.markdownFidelity.test.tsx
- apps/live-control-ui/src/markdownCanvas/markdownCanvasTypes.ts
- apps/live-control-ui/src/markdownCanvas/MarkdownCanvasSession.tsx
- apps/live-control-ui/src/buildSurface/buildMarkdownCanvasAdapter.tsx
- apps/live-control-ui/src/buildSurface/buildMarkdownCanvasAdapter.test.tsx
- apps/live-control-ui/src/buildSurface/BuildSurfaceContext.tsx
- apps/live-control-ui/src/buildSurface/BuildSurfaceContext.test.tsx

Verify real hook/storage backup+restore after remount, quota/readback failure,
review stale after edits/switch/base changes, unsupported source remains blocked,
explicit success preserving frontmatter/identities, no server write, actual
Build nav integration and unchanged other surface defaults. Focused owning
suites, UI typecheck/build, cumulative diff and exact-head independent review.
Use existing checkout .pytest_cache build/test output, no /tmp, new worktree,
server or environment. PRIME owns coordinated 5202 UI adoption; retain drafts.

Predecessor: Agent trace retention #1376 merged ae394d6d after review cycle2
PASS at941c43ee7 and22 focused independent cases. API8000 adopted; real natural
turn attribution awaits user traffic, not another synthetic benchmark.
