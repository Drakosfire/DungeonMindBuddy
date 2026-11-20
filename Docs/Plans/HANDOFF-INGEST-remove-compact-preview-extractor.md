# INGEST: remove the unused compact preview extractor

Status: MERGED and API-delivered through PR2041 at
0ca2eba73adeffb9a4a2bfe80a204647686c6faf. Implementation and delivery leases released.
Owner: PRIME. Base: origin/main@e3878370db6a8c87e0be4f9bfdc3a465aa1800bd.
Branch: codex/remove-compact-preview-extractor.
Checkout: /home/drakosfire/.codex/worktrees/buddy-context-loop/DungeonMindBuddy.
Topology: parallel-independent of ADVERSARY PR2040 and its serial parser/prompt
successors; no shared write paths, unmerged dependency or runtime/data effects.

## Outcome and exclusive write set

Remove the deprecated compact single-call extractor, its direct OpenAI client,
separate schema/prompt/sanitizer and wildcard export. Repository-wide module and
symbol searches found no exercised caller. The live runner imports and calls
category_candidate_graph_extractor; keep all explicit category package exports.

- Delete src/graph_memory/extraction/preview_candidate_graph_extractor.py.
- Remove its wildcard import from src/graph_memory/extraction/__init__.py.
- Shrink its provider-debt entry in tests/test_e5a_boundary_fitness.py.
- Correct removed-extractor runtime references in both copies of
  GRAPH-MEMORY-PROJECT-LAYOUT.md (Docs/Design and the design-agent ACTIVE_REFERENCE),
  evals/graph_memory_layer/README.md and FIXTURE-STATUS.md.
- This handoff.

Historical reports, frozen fixtures, results, retained extraction formats and data
are untouched. No replacement adapter, compatibility export, new schema, provider
call, manual Graph curation or database/runtime lease is introduced.

## Verification and delivery

Trace module and exported-symbol callers; verify ordinary category extraction,
runner and provider boundary tests after deletion, plus lint and cumulative diff.
Obtain independent Bugbot review of the exact head, push/open a bounded PR, and
merge/deliver only with the applicable gates satisfied. Existing runtime startup
must still select the registered category pipeline; tests do not establish fresh
ingestion quality. ADVERSARY retains independent Gold and quality assessment.

## Verification evidence

Repository-wide module/exported-symbol search found only the removed module's
own definitions and its package wildcard import as executable references. The
registered runner directly imports/calls the category extractor. Its explicit
package exports are retained and marked as public re-exports.

The owning category, registered runner, GE-default route and provider-import
checks passed: 63 tests using disposable PostgreSQL on 54329. The first sandboxed
run could not reach that fixture; the host rerun succeeded. Four non-provider E5A
architecture-baseline tests already fail identically on the fetched base and
this change (GenerationEngine imports and three DungeonMind import baselines).
Their assertion messages were compared exactly; do not rebaseline that unrelated
architecture debt in this deletion PR. No PRIMARY, provider or Graph effects.

## Settlement

Independent Bugbot approved exact head 667c834fbba920a5ed2d138d9cc39a89b39c3fb7;
all seven CI checks passed before merge. The unchanged reviewed conserved delivery
recipe verified 8,955 source blobs, all 91 retained primary tables and nine session
files, unchanged saved Plan HTTP and UI, and API readiness. No provider calls,
database writes or Graph changes. This proves removal and conserved delivery,
not new ingestion quality or operator acceptance.
