# CLEANUP: Build lossy-source editor content readiness

Status: ACTIVE under the standing cleanup goal's implementation, independent
review and merge authority. Base `80768107187f916def203bf79c8363f21a70fe97`,
branch `codex/build-editor-content-readiness`, reused isolated checkout.

## Serial prerequisite and lease

Merge/requalify order: this bounded Build readiness correction first, parked
saved-review readiness #4131 second, parked navigation #4128 third. Preserve
their raw failed diagnostics; do not absorb their code or bypass their holds.

Exclusive writes: this handoff and only the content-readiness assertion in
`apps/live-control-ui/src/buildSurface/BuildSurfaceShell.test.tsx`'s existing
lossy-source Save-guard case. Current open PR paths and paginated #3824 paths
show no competing test write. No runtime, fixtures, parser, classification,
API, dependency, deployment, browser data or service changes.

## Owning invariant and controlled evidence

The editor's actual initialization branch exposes the same test ID with empty
content before readiness. The test finds that node and immediately checks its
content. The raw #4131 full run newly observed empty rather than Hesta's Apothecary.

An isolated diagnostic invokes the actual TipTap hook but withholds its returned
handle for100ms: the actual MarkdownEditorCore renders its initializing branch.
The old test passes an explicit initializing-state assertion, then fails the
original content assertion. Awaiting that same content assertion passes this
controlled case and the complete Build module. Delay/hook instrumentation is
diagnostic only and must not ship.

Critique: editor existence does not prove hydrated content. Await the original
content predicate; preserve the exact source fixture, no-source-reader check,
disabled Save, absent unguarded recovery button, zero prepare/commit and clean
draft-status assertions. No sleeps, dropped assertions or forced editor state.

## Verification

Retain original full failure, controlled old/new raw artifacts and source hashes.
Exact-head full discovered comparison, hosted/build/validator and independent
review required before merge. Prove unchanged frontend/verifier baseline inputs
across intervening backend-only merges. Inherited109failures and observed variants
remain red; this readiness correction earns no invented persistent failure fix.
