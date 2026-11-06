# INGEST: define beat presentation rank

Status: ACTIVE. Owning study steward adopts the independently reviewed forward-only
contract clarification. Historical unspecified fields and H1 judgments are not
reinterpreted.

## Lane and topology

Branch `codex/ingest-beat-presentation-rank`, isolated existing ingest-draft-navigation
checkout. Stacked on PR #2152 at `9de7c37ae69a594ccff17ed4ffdfbc95bba5c6ee`;
merge parent before child. The evaluator stack (#2154 → #2155 → #2156 → #2160)
is separate. No rejected #2157 behavior is inherited. No other active lane edits
this lease; inspected open WRITER #2163 is disjoint. No merge authority.

## Invariant and failure cases

`SessionBeat.order` is positive presentation/navigation rank: smaller values rank
before larger ones; ties retain input sequence. Neither rank nor array/source
position establishes fictional chronology. Explicit source-supported temporal
claims remain accountable in model prose and typed precedence. Missing/falsey
rank retains existing normalization to 1; supplied values retain existing integer
conversion and positive-value validation. This slice adds no sorting or inference.

One owner constant supplies the neutral schema and model-facing meaning. Beat
consumers must not receive an undefined temporal hint. Host exact excerpt titles
and summaries do not turn retained model ranks into host source ordinals or erase
raw authored output defects.

## Expected write lease

- `src/graph_memory/candidate_graph_preview.py`
- `src/graph_memory/extraction/category_candidate_graph_schema.py`
- `src/graph_memory/extraction/category_candidate_graph_extractor.py`
- `src/graph_memory/extraction/staged_edge_extraction.py`
- `tests/test_recap_source_quote_beat_summary.py`
- `Docs/Design/GRAPH-MEMORY-CANDIDATE-GRAPH-PREVIEW-IR.md`
- this handoff

## Validation and delivery

Inspect all rank consumers, exercise tied/reversed/nonconsecutive ranks with
source quotations and explicit temporal text held fixed, validate positive rank
at the existing IR boundary, inspect exact downstream prompt meaning, and prove
contribution mapping does not derive chronology from beats. Run related extractor
and schema tests, inspect cumulative parent→head diff, independent subagent review,
commit/push/open bounded PR. Do not publish or deploy.

No provider, primary/isolated DB, runtime port or source/Gold writes. Frozen baseline
and heldout sources remain unchanged. H2 must adopt and disclose this common
corrected contract for both arms, pin the revised controls, and pass review before
calls; it cannot claim an exact-original-prompt allocation-only comparison.

## Verification evidence

- 73 passed: `test_recap_source_quote_beat_summary.py` and
  `test_category_candidate_graph_extractor.py`.
- 26 passed: staged-edge extraction, category schema, candidate preview IR and
  encounter-job pass tests.
- Broader `test_graph_memory_encounter_job_edge_guidance.py`: 4 passed, 2 failed.
  Both failures reproduce on an untouched Git archive of exact parent `9de7c37`:
  `test_edge_pass_can_emit_encounter_job_edges_with_existing_predicates` expects
  `edge:enc-rats-located-in-cellar` in an empty edge collection; and
  `test_unknown_invented_predicates_remain_flagged` finds neither its expected
  edge nor predicate issue. This slice does not repair or claim those tests pass.
- Initial new-test authoring error referenced nonexistent
  `GraphContribution.candidate_edges` (AttributeError); removed that assertion.
  The tested owning result is the complete assertion collection containing only
  the fixture's one node assertion, with no beat-derived temporal assertion.
- Independent working-diff review found no actionable defects and independently
  reproduced the 73-test pass. Committed-head review is required before delivery.
