# BUILD Page composer Slice A

Status: COMPLETE. Implementation merged in #3690 at 26bfa85d5e822902766977297832474b8033c246. Its UI lease is superseded by [contextual layout controls](HANDOFF-BUILD-contextual-layout-controls.md); original scope and evidence below are historical.

Original authorization: Alan authorized Build it, reviews and merge; latest direction is local only, no server deployment. Root assigned this serial successor after persistence #3689 merged as dd98d40af4d48e92bc49337cc9296f904186bf7f.

Authority: design at 56507b4cc47241be61a1d27fbd53a87e5d3a7421:Docs/Backlog/DESIGN-build-page-composer.md. Base fetched main dd98d40af4d48e92bc49337cc9296f904186bf7f; branch codex/build-composer-row-20261115; isolated Projects build-composer-ui-20261115/source. No active runtime/DB reuse, especially existing port8000. Draft PR separate from docs #3683. Root coordinates merge/rollout.

## Scope and ownership
One Build Page-only two-slot row, existing editor block reuse, snapped 12-unit divider and keyboard controls, explicit move/unwrap, ordinary undo/redo and text selection, narrow ordered stacking. Atomic typed presentation hydrate/dehydrate, layout-only byte preservation, dirty/recovery/CAS parity and no source publication on layout edits. No Slice B extra row controls, C layering or D print.

Expected write set: this handoff; new tiptap/pageComposer modules/tests/CSS; markdownCanvas/MarkdownCanvas.tsx, MarkdownCanvasSession.tsx, markdownCanvasTypes.ts and focused tests; workspaceDocument/useWorkspaceDocumentAuthoring.ts, openWorkspaceDocumentAuthoringState.ts, reconcileLocalDraft.ts, workspaceDocumentRecovery.ts, workspaceDraftCoordinator.ts and focused tests; workspaceDocument/verifyCommitReceiptAgainstSnapshot.ts and test (independent layout receipt identity); tiptap/state/tiptapLocalState.ts and tests; minimal known-wrapper semantic flattening in tiptap/markdown/calloutMarkdown.ts and semanticMarkdownSafety.ts if needed. API additions isolated in new pageComposer types augmentation, no api/types.ts, liveApi.ts or BuildSurfacePage.tsx edits.

Fresh open PR file scan: 56 reviewed; api/types.ts shared with #3532/#2087/#1235, deliberately excluded. No owned editor/state paths overlap. #2298 touches markdownIngressCorpus.test.ts, excluded. Workers may split new pure mapper and extension modules within this single PR; root worker exclusively owns state/session integration.

## Invariants and gates
Absent legacy presentation is not intentional null unwrap. Valid source blocks bind exact UTF-8 boundaries, never guessed AST indexes; YAML preserved outside bindings. Unsupported uncomposed source remains editable with composer disabled; invalid composed source refuses hydration without losing drafts. Resize-only preserves original Markdown bytes. Layout identity independently contributes to dirty/base/recovery/save completion. Preserve edits landing during save. Existing tables, callouts, managed artwork and media authorization stay authoritative.

Verify mapper/schema roundtrips, actual editor transactions, keyboard/history, resize-only recovery, stale save and in-flight edits at owning hooks. Browser proof on isolated local DB/API and owned port only. Exact-head repo hosted frontend verifier plus full discovery diagnostic with baseline accounting as needed; affected backend checks if backend changes become necessary (not currently owned). No qualification claim for unrun/failed checks. Publish draft after cumulative review, never merge from this worker.

## Inventory gate correction
Root authorized the bounded addition of the three new composer Vitest files to `ci/test-classification.json` after Actions run 43736577986 reported them unclassified. This extends the write set only for those entries in the existing fast lane. Known #2298 inventory overlap remains disjoint; no existing classifications, workflow selection, or gates change. Re-anchor confirmed main 7d2e7084b6c0911100a2b471d1e30b6d12c9c1be.
