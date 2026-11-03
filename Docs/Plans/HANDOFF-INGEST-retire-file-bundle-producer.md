# INGEST: retire the unused file-bundle extraction producer

Status: ACTIVE under the operator's code cleanup and demolition goal.
Owner: PRIME. Base: origin/main@1b729d40784fc29c23cf0400c265536734fb23f2.
Branch: codex/retire-file-bundle-extractor.
Checkout: /home/drakosfire/.codex/worktrees/buddy-context-loop/DungeonMindBuddy.
Topology: serial after merged/delivered PR2042; parallel-independent of ADVERSARY's
inline-heading parser and later profile changes. No shared write/runtime/data
lease. Existing checkout/dependencies; no new worktree or environment.

## Outcome

Delete the unused alternate file-bundle producer and compatibility shim, with
only their exclusive tests. Ordinary extraction already creates saved APP
ExtractionRuns through the registered category controller. Removing this producer
also removes its shortened-reference repair, separate validator, file mirrors,
profile-option aliases, file manifest assembly and alternative OpenAI dispatch.
Do not build another wrapper or port retired behavior into the saved-run owner.

## Caller evidence and critique

The producer has no repository runtime, CLI or eval invocation. Its shim is pure
re-export with no main entrypoint. The producer's public entrypoint is invoked
only by its own test module. Remaining imports are one current quote-boundary assertion, two old
packaging-only party-fill tests and a packaging-write sandbox test.

ADVERSARY independently scanned 483 Python/shell scripts in its known private
roots with zero legacy consumers or parse errors. Exact audit retained as
legacy-file-bundle-private-consumer-audit-v1.json, SHA256
c5c276ee752a80132e83b33b07c8f11ccdb26e3195613de88c1462cc07150166.
Frozen source snapshots are historical evidence and remain untouched. Static
search cannot prove absence of unknown external scripts or arbitrary dynamic
imports; inspect exact repository callers again before implementation.

## Exclusive write set

- Delete src/graph_memory/extraction/graph_ingest_packaging.py.
- Delete evals/graph_memory_layer/graph_preview_runner.py.
- Delete tests/test_graph_memory_category_graph_preview_runner.py.
- Delete tests/test_live_control_server_no_evals_graph_ingest_packaging_import.py;
  it only checks imports of the deleted shim, not a wider live boundary.
- tests/test_recap_quote_integrity.py: preserve its public-run source-support
  assertion using the existing literal matcher on the cited source span; remove
  the dependency on the retired packaging helper. Keep all active quote tests.
- tests/test_party_fill_source_binding.py: remove only the two file-packaging
  tests and unused imports. Preserve producer schema/host source binding tests.
- tests/test_artifact_data_root.py: remove only the obsolete packaging-write test;
  preserve live artifact-root, retained-source and publication tests.
- Docs/Design/DESIGN-contextual-vocabulary-layer.md: correct its stale current
  runtime workflow to the saved-run owner; preserve historical design evidence.
- Docs/Plans/HANDOFF-RETRIEVAL-remove-claim-hydration-compat.md: settle the predecessor
  only after its actual merge/delivery, with exact evidence.
- The activated copy of this handoff in Docs/Plans.

## Boundaries

Keep GraphIngest manifest decoding and historical adoption/inventory consumers;
they have real exercised callers and require a separate retirement decision.
Keep all source Markdown, retained fixtures, Gold, historical captures, reports,
APP components and native data untouched. No manual Graph curation or provider
calls. ADVERSARY owns Gold and quality assessment independently.

The audit also found file-discovery run/latest endpoints and older developer
projections still exposed. Their consumers and runtime effects are a distinct
successor. This slice does not claim all file discovery or D4/D9 is resolved.
Likewise, the apparently orphaned claimed-fill feature/schema branch needs its
own current-caller/experiment audit; it is not absorbed here.

## Verification and delivery

Use existing registered production-runner/route, exact saved-run review/output,
quote integrity, source binding and artifact-root tests with disposable54329.
Confirm import/caller closure and cumulative diff/Ruff checks; no primary state.
Tests protecting retired file output or reference repair must not be recreated
against a fake replacement. Preserve real source-integrity and publication guards
at their current owners. Obtain independent exact-head Bugbot review and CI,
commit/push/open one coherent PR, then merge/conserved delivery under standing
PRIME authority. Quality assessment and ordinary end-to-end proof remain separate.

## Review map and coupling

This is one retired execution path, not a bundle of new capabilities. Review the
producer/shim removal first, then its exclusive tests and stale workflow text,
then the preserved registered-runner and source/publication test contracts. The
large deletion is indivisible: keeping the shim or its tests after removing their
only implementation would preserve a broken or misleading alternate path. No
replacement producer, compatibility adapter or new public contract is introduced.

## Initial author checks

The first broader cohort passed 116 checks and failed 20. Validation identified
one current quote-test assertion using the legacy packaging helper; it is kept
and now uses the existing literal matcher against the exact cited span. Ruff and
diff checks pass after correction. The other 19 failures concern old page-file
fixtures and a profile-version expectation; baseline comparison is pending and
must not be reported as inherited until measured. No primary/provider/Graph effects.
