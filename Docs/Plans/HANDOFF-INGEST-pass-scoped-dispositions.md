# INGEST: scope recap disposition identities by producer pass

Status: ACTIVE. Root adopts this bounded aggregation fix under the user’s ingestion implementation authorization.

## Lane and topology

Branch `codex/ingest-pass-scoped-dispositions`, base PR #2126 at `2475ba08dce5a632cea7d4e18cee9f98e7832933`. Stacked: merge/rebase #2126 first, then this slice. Remote main and open PR ownership re-anchored; #2125 connected-page storage is independent. No merge or deployment authority.

## Invariant and evidence

Model disposition IDs are local to each extraction pass. Aggregation must preserve distinct records from different passes even when their local IDs match. IDs missing or duplicated within a pass across either ignored or deferred collections remain invalid. Do not deduplicate claims or alter evidence to obtain acceptance.

Actual isolated Session 4 run `86b8defc-5b93-4c51-a6f9-1c98f7986bb1` emitted valid object `D001` and distinct thread `D001`; consolidation appended both without scoping. The strict quote guard correctly rejected the aggregate. Independent diagnosis SHA256 `0bb6e206dda64afe831a89b6fde87b83ea846100ab7292c0450a6a05a0a868e4`. Raw and normalized payloads and the failed run remain preserved. Whole cohort exec22938 exited2; never replay it or salvage its failed candidate.

Failure cases: cross-pass equal local IDs, same-pass duplicates, whitespace-equivalent IDs, missing IDs, positive/host-generated namespaces, and disposition evidence loss. Qualify recap disposition identity at aggregation and preserve reasons, quotes, warnings and next steps. Original local IDs remain inspectable in retained pass output. Keep non-recap behavior unchanged. No new schema, producer, retry, publication bypass or quote-guard relaxation.

Design critique SHA256 `87dfa10d7c0b703a90694f8741440367977814cf5a627f2586b0be31c692a3e0` identified the combined ignored/deferred uniqueness scope. Adopt pass + local-ID tuple encoding without collection kind; validate the shared same-pass namespace.

## Exclusive expected writes

- `src/graph_memory/extraction/category_candidate_graph_extractor.py`
- `tests/test_recap_object_dispositions.py`
- `tests/test_category_candidate_graph_extractor.py` (existing custom-pass contract expectation and raw-ID preservation)
- `tests/test_recap_quote_integrity.py`
- This handoff.

## Validation and delivery

Exercise consolidation through the strict recap quote guard using synthetic distinct pass-local records with the same ID; both must survive with exact evidence. Reject malformed local IDs and same-pass duplicates. Verify repeatable qualification, no input mutation, ignored/deferred distinction, unchanged non-recap behavior and normal object disposition contract. Run affected suites, inspect exact cumulative base-to-head diff, obtain independent subagent review, commit, push and open one stacked PR. Current failed run and all previous semantic failures remain evidence, not new acceptance. Fresh extraction and governed publication remain required after reviewed runtime composition. Primary data, evaluator database state and frozen runtimes are outside this write lease.

Composition checkpoint: the first composed-runtime suite passed 210 tests and exposed one old custom recap-pass assertion expecting unqualified disposition IDs. Extend this same slice to update that owning test; no new capability or production scope. Preserve the failed manifest/test output and obtain renewed exact-head review.
