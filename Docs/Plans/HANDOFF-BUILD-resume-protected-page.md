# BUILD: resume saving a representable protected page

Status: ACTIVE. PRIME owns the operator's current Edge Save-loop correction;
ARCHITECTURE independently reviews. Base origin/main@06dbb61373a7251a2efdf5a571205c97589b97a6.
Branch codex/build-resume-protected-page, reuse buddy-context-loop/dependencies.
Topology serial Build slice; disjoint from DOGFOOD's operational Session29 run.
Previous source-link implementation is merged/adopted, its code lease released.

Observed: current Edge has two images and authored tables; Save blocked by a
sticky source-authority flag. Review is a huge text dump with actions below it;
operator reports Review and Discard do not escape the loop. Readonly actual saved
revision7/digestf1526b3906137d1b7779525fb5ed05ea2f3f44d8230813e1d145e45554f70404
imports and serializes without diagnostics. Do not equate that with proof the
live projection is identical/safe or execute discard/rebuild on the operator's page.

Outcome: clearly distinguish a currently unsupported source from an old protected
copy; compact review with reachable actions; explicit Keep current page and resume
saving when live editor JSON exactly survives schema-normalized Markdown roundtrip
and both preserved/saved source are supported. First checkpoint exact original
live JSON + preserved Markdown/seal/base, verify storage before changing local
state. No auto Save/unseal, no bypass of actual unsupported data, no server/source
write. Restore stays fenced, preserves independently changed storage/new edits.
Retain alternate rebuild and explicit discard-to-saved-source with reachable,
accurate confirmation/result; prove actual mounted controls escape stale seal.

Expected exclusive write lease:
- this handoff
- apps/live-control-ui/src/workspaceDocument/workspaceDocumentRecovery.ts
- apps/live-control-ui/src/workspaceDocument/useWorkspaceDocumentAuthoring.ts
- apps/live-control-ui/src/workspaceDocument/useWorkspaceDocumentAuthoring.markdownFidelity.test.tsx
- apps/live-control-ui/src/markdownCanvas/markdownCanvasTypes.ts
- apps/live-control-ui/src/markdownCanvas/MarkdownCanvasSession.tsx
- apps/live-control-ui/src/buildSurface/buildMarkdownCanvasAdapter.tsx
- apps/live-control-ui/src/buildSurface/buildMarkdownCanvasAdapter.test.tsx
- apps/live-control-ui/src/buildSurface/BuildSurfaceContext.test.tsx

Verify old seal + real image/table editor → review → Keep current → Save admission,
exact original restore after remount; current/source unsupported/mismatched roundtrip,
quota/missing/diverged storage, stale review/live edits no mutation; actual Discard
remounts saved source and no immediate reseal on supported source. Keep server Save
explicit. Focused owning suites/typecheck/build/cumulative diff, PR, independent
review then UI5202 delivery. No provider/API/schema/retained draft mutation, no
/tmp/new checkouts/env/preview. User's live page is observed only during diagnosis.

## Activated serial successor: explicit spacer normalization

Predecessor #1381 merged10e268361d17a729f1c2535a9a98fb5c0cb6e04e and deployed.
Its exact keep-current check is not sufficient for the ACTUAL Edge draft: normal
UI review still refuses; readonly visible editor DOM shows an empty root spacer
paragraph between The place and Economic Activities. Saved source remains clean.
Reuse same checkout and exact write lease on codex/build-protected-spacing from
origin/main@10e268361d17a729f1c2535a9a98fb5c0cb6e04e. This is a serial corrective
successor for the same operator-reported Save loop, no parallel recovery writer.

Keep strict current mode unchanged. Add an explicit separate normalization choice
ONLY when full schema-normalized model equality differs solely by plain empty
root paragraph spacers (no content, marks or nondefault attributes). Count and
disclose removed spacers before choice; require distinct normalized-current mode,
recompute/fence on confirmation, checkpoint original full JSON before replacement.
Normalize only those spacers. Any text, image, reference, mark, table, nested or
other structural mismatch remains blocked. No source/server Save automatically.
Regression: strict mode rejects a spacer difference; explicit normalized choice
keeps all authored nodes, enables Save, restores exact original including spacer.
Verify actual Edge eligibility through normal review only; leave its final choice
to the operator. Independent review and separate corrective PR before UI adoption.
