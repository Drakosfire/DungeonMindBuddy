# INGEST: validate exact source rows before quote binding

Status: ACTIVE. Root adopts this bounded owner fix under the existing ingestion implementation authorization.

## Lane and topology

Branch `codex/ingest-exact-row-binding`; exact base PR #2123 head `59143ed478706b0c894997bc4d8ed6829081d2f7`. Stacked: merge/rebase #2123 first, then this PR. Remote main/open PRs re-anchored before activation. No merge or deployment authorization implied. Root transfers only the resolver/test subset of its completed predecessor lease to this lane.

## Invariant and scope

Source packet rows preserve exact registered indentation/trailing whitespace. The quote resolver must verify those raw bytes against the source before using its existing stripped paragraph view for quote matching. It currently compares raw rows to stripped source text and abandons every item when any unrelated row has outer whitespace.

Session 5 proof: `c1s05-common-build-1f6e7b1c-whitespace-canonicalization-owner-proof-v1.json`, SHA256 `72916e1b73ff406c661387cdf45344192baca853c91671f248a6132459269759`. All eight raw fight quotations are literal and unique; the first names paragraph 50 instead of 48. Unrelated rows 44/46 have trailing spaces, preventing the existing exact-location resolver from running. The final quote guard correctly withheld the unresolved item.

Expected writes:
- `src/graph_memory/extraction/category_candidate_graph_extractor.py`: raw source-row validation in the existing resolver only.
- `tests/test_category_candidate_graph_extractor.py`: owning regression and fail-closed countercases.
- This handoff.

Do not edit claims, quotations, source rows or retained candidates. Preserve unique exact occurrence checks, authority eligibility, atomic handling of unresolved references, and the final quote guard. No new producer, representation, fallback, retry, schema, provider policy or semantic chronology repair. Existing Session 5 chronology failure is separate.

## Validation and delivery

Prove unrelated source whitespace no longer disables valid binding; forged row whitespace and nonliteral quotations still fail closed; raw inputs remain unchanged and binding is idempotent. Run existing resolver/extractor/source-authority/quote-guard suites; inspect cumulative diff; independent subagent review; commit/push/open one stacked PR. Fresh qualification/publication remain separate gates. All frozen evaluator runtimes, live cohort 28770 and primary data stay unchanged.
