# INGEST: exact source handles for recap node passes

Status: ACTIVE. Root adopts the bounded design under the user's ingestion implementation authorization.

## Lane and topology

Branch `codex/ingest-node-source-handles`, base PR #2122 at `d934233711f2ee29f3dea1b72befb8250a2d4836`. Stacked: merge #2122, then rebase/merge this successor. No merge authorization is implied. Root owns this lane; inspected current remote/open PRs before activation. PRIME's Build delivery owns separate runtime paths. The running evaluator `/tmp/c1s06-source-navigation-eval-v1` and PostgreSQL 55447 are immutable to this slice.

## Outcome and invariant

Reuse the existing actor source-sentence packet/wire/materialization for all five ordinary recap node passes. Models select source handles; the host copies their exact source slices into the existing canonical evidence references. Handles establish location, never semantic support. No new producer, fallback, provider retry, claim repair or relaxed quote guard.

Session 1 raw location output included the required town description but invented the quote `It had a job board` where source says `It did have a job board`. The final guard correctly held the town and four dependent links. Preserve that failure; do not salvage its output. Generic handle reuse prevents this quotation-construction mechanism, not unsupported prose or wrong handle selection.

## Expected write lease

- `src/graph_memory/extraction/source_sentence_evidence.py`
- `src/graph_memory/extraction/category_candidate_graph_extractor.py`
- `src/graph_memory/extraction/bounded_recap_execution.py`
- `tests/test_source_sentence_evidence.py`
- `tests/test_bounded_recap_execution.py`
- `tests/test_category_candidate_graph_extractor.py`
- `tests/test_worldbuilding_collective_source_fidelity.py`
- `tests/test_worldbuilding_location_source_fidelity.py`
- This handoff.

Rename actor-only capability/helper/context names coherently, without compatibility aliases. Cover observation, ignored and deferred evidence consistently; retain legal empty disposition references. Gate on ordinary recap node passes after source-authority partition. Do not expand worldbuilding, encounter/job, beat or edge passes. Preserve existing actor handles in other recap preview profiles. Preserve full source, raw and normalized receipts, source hashes/coordinates and canonical consumers.

## Validation and delivery

Owning tests must exercise non-actor bounded requests, enum rejection, exact materialization, dispositions including empty references, source-authority gating and unaffected worldbuilding/beat/edge contracts. Inspect cumulative diff, independent subagent review, commit/push/open one PR. Fresh extraction and governed publication remain separate quality gates; neither tests nor handle integrity imply semantic Gold success. Existing cohort captures remain on their original build; new build qualification cannot silently renew them.
