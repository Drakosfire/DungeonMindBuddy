# INGEST: retire unused party claimed-fill execution

Status: ACTIVE under the operator's cleanup and demolition goal.
Owner: PRIME. Base: origin/main@e7c0ec84508d212c7dc211c7c270393534e7b375.
Branch: codex/retire-party-claimed-fill.
Checkout: /home/drakosfire/.codex/worktrees/buddy-context-loop/DungeonMindBuddy.
Topology: parallel-independent of PRIME PR2046 (catalog/controller retry) and
ADVERSARY PR2047 (recap profile common guidance). No shared expected write paths.
Reuse this checkout serially; previous PR heads remain immutable. No new worktree,
environment, provider, primary database, runtime or Graph/Gold effect lease.

## Outcome and caller evidence

Delete the unused 466-line party claimed-fill implementation, its schema-dispatch
branches and exclusively supporting tests. Source-only category extraction no
longer calls its enrichment builder, binder or application functions. The current
schema module imports it for every schema selection even though no current
profile/controller constructs that pass. Remove that accidental runtime coupling.

Current repository searches find no runtime/eval/CLI invocation outside schema
selection. A bounded audit of 548 Python/shell scripts in the three established
private evidence roots finds no import/textual reference or scan error. Frozen
source/environment copies were excluded and remain historical evidence. Audit:
party-claimed-fill-current-caller-audit-v1.json, SHA256
9d46176910975fa2e8cb727103984ffa9c06294f3a32a9be5d13cd8a7c13dd38.
This does not certify unknown external scripts or arbitrary dynamic import text.
No caller-driven replacement or compatibility branch is justified.

## Exclusive expected write set

- Delete src/graph_memory/extraction/party_claimed_fill.py.
- src/graph_memory/extraction/category_candidate_graph_schema.py: remove only
  claimed-fill imports and its two unused dispatcher branches.
- src/graph_memory/extraction/extraction_profile.py: remove retired kind from the
  explanatory comment; retain the actual dataclass and every current pass kind.
- Delete tests/test_party_claimed_fill.py and
  tests/test_party_fill_source_binding.py, which now directly exercise only this
  orphan implementation. Current literal quotation/source tests remain elsewhere.
- tests/test_recap_planning_section_pipeline.py: remove its fake retired-pass
  fixture option and sole duplicate test for an execution path that no longer
  exists. Keep every actual planning selection/citation rejection test.
- Docs/Plans/HANDOFF-INGEST-pc-fill-modality.md: close its stale historical ACTIVE
  lease truthfully. Original implementation5e107415 is an ancestor of fetched
  main; do not claim this removal merged before its own delivery.
- This handoff.

## Preservation, critique and validation

Preserve historical candidate enrichment/session_actions fields and their readers,
including tests/test_graph_memory_candidate_graph_preview.py. Removing an unused
producer does not authorize rewriting retained candidates or stripping metadata.
Keep current source admission, actor source handles, literal quote validation,
semantic state, publication and private execution evidence unchanged. This slice
does not replace the shared database-diagnostics design or claim it is completed.
ADVERSARY owns Gold and ingestion quality independently; no manual Graph curation.

Verify all current profile pass schemas/prompts still construct, current recap
planning/citation rejection and saved-run extraction work, Worldbuilding and
historical candidate parsing remain exercised, caller/import closure holds and
Ruff/cumulative diff checks pass. Use existing disposable54329 and synthetic
providers only. Obtain independent exact-head Bugbot review and applicable CI,
then commit/push/open, merge and conserved delivery under standing PRIME authority.
The module, schema branches and exclusive tests retire together as one coherent
execution-path deletion. No source-only replacement enrichment mechanism.

## Author verification

Before deletion, 22 current schema/prompt/planning/historical-reader checks pass.
After deletion, the broader owning cohort passes100 checks and fails one profile
alias expectation (test_legacy_profile_aliases_resolve_to_recap_profile expects
v1 while runtime resolves v2). The exact same test, assertion and v1/v2 mismatch
reproduce at fetched base e7c0ec845; original base/head logs remain private
runtime evidence. This unrelated test debt is not treated as a pass or repaired
by restoring retired behavior. Ruff and cumulative diff checks pass.
Only historical candidate-reader data still references the retired enrichment
name in executable source/tests; there are no producer imports/callers remaining.
